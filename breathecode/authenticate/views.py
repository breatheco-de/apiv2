import os
import requests
import base64
import logging
import urllib.parse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth import update_session_auth_hash
from rest_framework.response import Response
from django.db.models import Q
from django.http import HttpResponseRedirect, HttpResponse
from django.conf import settings
from rest_framework.exceptions import APIException, ValidationError, PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status, serializers
from django.contrib.auth.models import User, Group, AnonymousUser
from django.contrib import messages
from rest_framework.authtoken.views import ObtainAuthToken
from urllib.parse import urlencode, parse_qs
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from rest_framework.views import APIView
from django.utils import timezone
from datetime import datetime
from .models import Profile, ProfileAcademy, Role, UserInvite
from .authentication import ExpiringTokenAuthentication

from .forms import PickPasswordForm, PasswordChangeCustomForm, ResetPasswordForm, LoginForm, InviteForm
from .models import Profile, CredentialsGithub, Token, CredentialsSlack, CredentialsFacebook, UserInvite
from .actions import reset_password, resend_invite
from breathecode.admissions.models import Academy, CohortUser
from breathecode.notify.models import SlackTeam
from breathecode.utils import localize_query, capable_of, ValidationException, HeaderLimitOffsetPagination, GenerateLookupsMixin
from .serializers import (
    UserSerializer, AuthSerializer, GroupSerializer, UserSmallSerializer, GETProfileAcademy,
    StaffSerializer, MemberPOSTSerializer, MemberPUTSerializer, StudentPOSTSerializer,
    RoleSmallSerializer, UserMeSerializer, UserInviteSerializer
)

logger = logging.getLogger(__name__)


class TemporalTokenView(ObtainAuthToken):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        user = request.user
        Token.objects.filter(token_type='temporal').delete()
        token = Token.objects.create(user=user, token_type='temporal')
        token.save()
        return Response({
            'token': token.key,
            'token_type': token.token_type,
            'expires_at': token.expires_at,
            'user_id': user.pk,
            'email': user.email
        })


class LogoutView(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        Token.objects.filter(token_type='login').delete()
        request.auth.delete()
        return Response({
            'message': "User tokens successfully deleted",
        })


class MemberView(APIView, HeaderLimitOffsetPagination, GenerateLookupsMixin):

    @capable_of('read_member')
    def get(self, request, academy_id, user_id=None):
        is_many = bool(not user_id)

        if user_id is not None:
            item = ProfileAcademy.objects.filter(
                user__id=user_id, academy_id=academy_id).first()
            if item is None:
                raise ValidationException(
                    'Profile not found for this user and academy', 404)

            serializer = GETProfileAcademy(item, many=False)
            return Response(serializer.data)

        items = ProfileAcademy.objects.filter(
            academy__id=academy_id).exclude(role__slug="student")

        roles = request.GET.get('roles', None)
        if is_many and roles is not None:
            items = items.filter(role__in=roles.split(","))

        status = request.GET.get('status', None)
        if is_many and status is not None:
            items = items.filter(status__iexact=status)

        if not is_many:
            items = items.first()

        page = self.paginate_queryset(items, request)
        serializer = GETProfileAcademy(page, many=is_many)

        if self.is_paginate(request):
            return self.get_paginated_response(serializer.data)
        else:
            return Response(serializer.data, status=200)

    @capable_of('crud_member')
    def post(self, request, academy_id=None):
        serializer = MemberPOSTSerializer(data=request.data, context={
            'academy_id': academy_id,
            "request": request
        })
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('crud_member')
    def put(self, request, academy_id=None, user_id=None):

        already = ProfileAcademy.objects.filter(
            user=user_id, academy__id=academy_id).first()
        request_data = {**request.data, "user": user_id, "academy": academy_id}
        if already:
            serializer = MemberPUTSerializer(already, data=request_data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            serializer = MemberPOSTSerializer(data=request_data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('crud_member')
    def delete(self, request, academy_id=None, user_id=None):
        lookups = self.generate_lookups(
            request,
            many_fields=['id']
        )

        print("printing items", lookups)

        if lookups and user_id:
            raise ValidationException('user_id or cohort_id was provided in url '
                                      'in bulk mode request, use querystring style instead', code=400)

        if lookups:
            items = ProfileAcademy.objects.filter(**lookups,
                                                  academy__id=academy_id).exclude(role__slug="student")

            for item in items:

                item.delete()

            return Response(None, status=status.HTTP_204_NO_CONTENT)

        member = ProfileAcademy.objects.filter(
            user=user_id, academy__id=academy_id).exclude(role__slug="student").first()
        if member is None:
            raise ValidationException("Member not found", 404)
        member.delete()
        return Response(None, status=status.HTTP_204_NO_CONTENT)


class MeInviteView(APIView, HeaderLimitOffsetPagination, GenerateLookupsMixin):

    def get(self, request):

        if request.user is None:
            raise ValidationException("User not found", 404)

        invite = UserInvite.objects.filter(email=request.user.email, status='PENDING').first()
        if invite is None:
            raise ValidationException("No pending invite was found", 404)

        serializer = UserInviteSerializer(invite, many=False)
        return Response(serializer.data)
    

class ProfileInviteView(APIView, HeaderLimitOffsetPagination, GenerateLookupsMixin):

    @capable_of('read_invite')
    def get(self, request, academy_id, profileacademy_id):

        profile = ProfileAcademy.objects.filter(
            academy__id=academy_id, id=profileacademy_id).first()
        if profile is None:
            raise ValidationException("Profile not found", 404)

        invite = UserInvite.objects.filter(
            academy__id=academy_id, email=profile.email, status='PENDING').first()
        if invite is None:
            raise ValidationException("No pending invite was found", 404)

        serializer = UserInviteSerializer(invite, many=False)
        return Response(serializer.data)


class StudentView(APIView, HeaderLimitOffsetPagination, GenerateLookupsMixin):

    @capable_of('read_student')
    def get(self, request, academy_id=None, user_id=None):

        if user_id is not None:
            profile = ProfileAcademy.objects.filter(
                academy__id=academy_id, user__id=user_id).first()
            if profile is None:
                raise ValidationException("Profile not found", 404)

            serializer = GETProfileAcademy(profile, many=False)
            return Response(serializer.data)

        items = ProfileAcademy.objects.filter(
            role__slug='student', academy__id=academy_id)

        like = request.GET.get('like', None)
        if like is not None:
            items = items.filter(Q(first_name__icontains=like) | Q(
                last_name__icontains=like) | Q(email__icontains=like))

        status = request.GET.get('status', None)
        if status is not None:
            items = items.filter(status__iexact=status)

        page = self.paginate_queryset(items, request)
        serializer = GETProfileAcademy(page, many=True)

        if self.is_paginate(request):
            return self.get_paginated_response(serializer.data)
        else:
            return Response(serializer.data, status=200)

    @capable_of('crud_student')
    def post(self, request, academy_id=None):
        serializer = StudentPOSTSerializer(data=request.data, context={
            'academy_id': academy_id,
            "request": request
        })
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('crud_student')
    def put(self, request, academy_id=None, user_id=None):

        already = ProfileAcademy.objects.filter(
            user=user_id, academy__id=academy_id).first()

        if already and already.role.slug != "student":
            raise ValidationException(
                f"This endpoint can only update student profiles (not {already.role.slug})")

        request_data = {**request.data, "user": user_id,
                        "academy": academy_id, "role": "student"}
        if "role" in request.data:
            raise ValidationException(
                "The student role cannot be updated with this endpoint, user /member instead.")

        if already:
            serializer = MemberPUTSerializer(already, data=request_data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            # TODO: StaffPOSTSerializer is not defined
            serializer = StaffPOSTSerializer(data=request_data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('crud_student')
    def delete(self, request, academy_id=None, user_id=None):
        lookups = self.generate_lookups(
            request,
            many_fields=['id']
        )

        if lookups and user_id:
            raise ValidationException('user_id was provided in url '
                                      'in bulk mode request, use querystring style instead', code=400)

        if lookups:
            items = ProfileAcademy.objects.filter(
                **lookups, academy__id=academy_id, role__slug='student')

            for item in items:

                item.delete()

            return Response(None, status=status.HTTP_204_NO_CONTENT)

        if academy_id is None or user_id is None:
            raise serializers.ValidationError(
                "Missing user_id or academy_id", code=400)

        profile = ProfileAcademy.objects.filter(
            academy__id=academy_id, user__id=user_id, role__slug='student').first()
        if profile is None:
            raise serializers.ValidationError(
                'User doest not exist or does not belong to this academy')

        profile.delete()
        return Response(None, status=status.HTTP_204_NO_CONTENT)


class LoginView(ObtainAuthToken):

    def post(self, request, *args, **kwargs):
        # delete expired tokens
        utc_now = timezone.now()
        Token.objects.filter(expires_at__lt=utc_now).delete()

        serializer = AuthSerializer(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(
            user=user, token_type="login")
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'email': user.email
        })


@api_view(['GET'])
@permission_classes([AllowAny])
def get_token_info(request, token):

    token = Token.objects.filter(key=token).first()

    if token is None or token.expires_at < timezone.now():
        raise PermissionDenied("Expired or invalid token")

    return Response({
        'token': token.key,
        'token_type': token.token_type,
        'expires_at': token.expires_at,
        'user_id': token.user.pk
    })


class UserMeView(APIView):
    def get(self, request, format=None):

        try:
            if isinstance(request.user, AnonymousUser):
                raise PermissionDenied("There is not user")

        except User.DoesNotExist:
            raise PermissionDenied("You don't have a user")

        users = UserSerializer(request.user)
        return Response(users.data)

    def put(self, request):

        try:
            if isinstance(request.user, AnonymousUser):
                raise PermissionDenied("There is not user")

        except User.DoesNotExist:
            raise PermissionDenied("You don't have a user")

        serializer = UserMeSerializer(
            request.user, data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Create your views here.


@api_view(['GET'])
def get_users(request):

    query = User.objects.all()

    name = request.GET.get('name', None)
    if name is not None:
        query = query.filter(Q(first_name__icontains=name)
                             | Q(last_name__icontains=name))

    like = request.GET.get('like', None)
    if like is not None:
        query = query.filter(Q(first_name__icontains=like) | Q(
            last_name__icontains=like) | Q(email__icontains=like))

    query = query.order_by('-date_joined')
    users = UserSmallSerializer(query, many=True)
    return Response(users.data)


@api_view(['GET'])
def get_roles(request):
    queryset = Role.objects.all()
    serializer = RoleSmallSerializer(queryset, many=True)
    return Response(serializer.data)

# Create your views here.


@api_view(['GET'])
@permission_classes([AllowAny])
def get_github_token(request):
    # TODO: user_id
    # url = request.query_params.get('url', None)
    # if url == None:
    #     raise ValidationError("No callback URL specified")

    url = request.query_params.get('url', None)
    if url == None:
        raise ValidationError("No callback URL specified")

    # url = base64.b64decode(url).decode("utf-8")
    params = {
        "client_id": os.getenv('GITHUB_CLIENT_ID', ""),
        "redirect_uri": os.getenv('GITHUB_REDIRECT_URL', "")+"?url="+url,
        "scope": 'user repo read:org',
    }

    logger.debug("Redirecting to github")
    logger.debug(params)

    redirect = f'https://github.com/login/oauth/authorize?{urlencode(params)}'

    if settings.DEBUG:
        return HttpResponse(f"Redirect to: <a href='{redirect}'>{redirect}</a>")
    else:
        return HttpResponseRedirect(redirect_to=redirect)

# Create your views here.


@api_view(['GET'])
@permission_classes([AllowAny])
def save_github_token(request):

    logger.debug("Github callback just landed")
    logger.debug(request.query_params)

    error = request.query_params.get('error', False)
    error_description = request.query_params.get('error_description', '')
    if error:
        raise APIException("Github: " + error_description)

    url = request.query_params.get('url', None)
    if url == None:
        raise ValidationError("No callback URL specified")
    code = request.query_params.get('code', None)
    if code == None:
        raise ValidationError("No github code specified")

    payload = {
        'client_id': os.getenv('GITHUB_CLIENT_ID', ""),
        'client_secret': os.getenv('GITHUB_SECRET', ""),
        'redirect_uri': os.getenv('GITHUB_REDIRECT_URL', ""),
        'code': code,
    }
    headers = {'Accept': 'application/json'}
    resp = requests.post(
        'https://github.com/login/oauth/access_token', data=payload, headers=headers)
    if resp.status_code == 200:

        logger.debug("Github responded with 200")

        body = resp.json()
        if 'access_token' not in body:
            raise APIException(body['error_description'])

        github_token = body['access_token']
        resp = requests.get('https://api.github.com/user',
                            headers={'Authorization': 'token ' + github_token})
        if resp.status_code == 200:
            github_user = resp.json()
            logger.debug(github_user)
            if github_user['email'] is None:
                resp = requests.get('https://api.github.com/user/emails',
                                    headers={'Authorization': 'token ' + github_token})
                if resp.status_code == 200:
                    emails = resp.json()
                    primary_emails = [
                        x for x in emails if x["primary"] == True]
                    if len(primary_emails) > 0:
                        github_user['email'] = primary_emails[0]["email"]
                    elif len(emails) > 0:
                        github_user['email'] = emails[0]["email"]

            if github_user['email'] is None:
                raise ValidationError("Imposible to retrieve user email")

            # TODO: if user_id: User.objects.filter(id=user_id).first()

            user = User.objects.filter(Q(credentialsgithub__github_id=github_user['id']) | Q(
                email__iexact=github_user['email'])).first()
            if user is None:
                user = User(
                    username=github_user['email'], email=github_user['email'])
                user.save()

            CredentialsGithub.objects.filter(
                github_id=github_user['id']).delete()
            github_credentials = CredentialsGithub(
                github_id=github_user['id'],
                user=user,
                token=github_token,
                username=github_user['login'],
                email=github_user['email'],
                avatar_url=github_user['avatar_url'],
                name=github_user['name'],
                blog=github_user['blog'],
                bio=github_user['bio'],
                company=github_user['company'],
                twitter_username=github_user['twitter_username']
            )
            github_credentials.save()

            profile = Profile.objects.filter(user=user).first()
            if profile is None:
                profile = Profile(user=user,
                                  avatar_url=github_user['avatar_url'],
                                  blog=github_user['blog'],
                                  bio=github_user['bio'],
                                  twitter_username=github_user['twitter_username']
                                  )
                profile.save()

            student_role = Role.objects.get(slug="student")
            cus = CohortUser.objects.filter(user=user, role="STUDENT")
            for cu in cus:
                profile_academy = ProfileAcademy.objects.filter(
                    user=cu.user, academy=cu.cohort.academy).first()
                if profile_academy is None:
                    profile_academy = ProfileAcademy(
                        user=cu.user,
                        academy=cu.cohort.academy,
                        role=student_role,
                        email=cu.user.email,
                        first_name=cu.user.first_name,
                        last_name=cu.user.last_name,
                        status='ACTIVE'
                    )
                    profile_academy.save()

            token, created = Token.objects.get_or_create(
                user=user, token_type='login')

            return HttpResponseRedirect(redirect_to=url+'?token='+token.key)
        else:
            # print("Github error: ", resp.status_code)
            # print("Error: ", resp.json())
            raise APIException("Error from github")


# Create your views here.
@api_view(['GET'])
@permission_classes([AllowAny])
def get_slack_token(request):
    """Generate stack redirect url for authorize"""
    url = request.query_params.get('url', None)
    if url is None:
        raise ValidationError("No callback URL specified")

    user_id = request.query_params.get('user', None)
    if user_id is None:
        raise ValidationError("No user specified on the URL")

    academy = request.query_params.get('a', None)
    if academy is None:
        raise ValidationError("No academy specified on the URL")

    url = base64.b64decode(url).decode("utf-8")
    # Missing scopes!! admin.invites:write, identify
    scopes = ("app_mentions:read", "channels:history", "channels:join", "channels:read",
              "chat:write", "chat:write.customize", "commands", "files:read", "files:write",
              "groups:history", "groups:read", "groups:write", "incoming-webhook", "team:read",
              "users:read", "users:read.email", "users.profile:read", "users:read")

    query_string = f'a={academy}&url={url}&user={user_id}'.encode("utf-8")
    payload = str(base64.urlsafe_b64encode(query_string), "utf-8")
    params = {
        "client_id": os.getenv('SLACK_CLIENT_ID', ""),
        "redirect_uri": os.getenv('SLACK_REDIRECT_URL', "")+"?payload="+payload,
        "scope": ",".join(scopes)
    }
    redirect = "https://slack.com/oauth/v2/authorize?"
    for key in params:
        redirect += f"{key}={params[key]}&"

    if settings.DEBUG:
        return HttpResponse(f"Redirect to: <a href='{redirect}'>{redirect}</a>")
    else:
        return HttpResponseRedirect(redirect_to=redirect)

# Create your views here.


@api_view(['GET'])
@permission_classes([AllowAny])
def save_slack_token(request):
    """Get Slack token and redirect to authorization route"""
    logger.debug("Slack callback just landed")

    error = request.query_params.get('error', False)
    error_description = request.query_params.get('error_description', '')
    if error:
        raise APIException("Slack: " + error_description)

    original_payload = request.query_params.get('payload', None)
    payload = request.query_params.get('payload', None)
    if payload is None:
        raise ValidationError("No payload specified")
    else:
        try:
            payload = base64.b64decode(payload).decode("utf-8")
            payload = parse_qs(payload)
        except:
            raise ValidationError("Cannot decode payload in base64")

    if "url" not in payload:
        logger.exception(payload)
        raise ValidationError("No url specified from the slack payload")

    if "user" not in payload:
        logger.exception(payload)
        raise ValidationError("No user id specified from the slack payload")

    if "a" not in payload:
        logger.exception(payload)
        raise ValidationError("No academy id specified from the slack payload")

    try:
        academy = Academy.objects.get(id=payload["a"][0])
    except Exception as e:
        raise ValidationError("Not exist academy with that id") from e

    user = None
    try:
        user = User.objects.get(id=payload["user"][0])
    except Exception as e:
        raise ValidationError("Not exist user with that id") from e

    code = request.query_params.get('code', None)
    if code is None:
        raise ValidationError("No slack code specified")

    params = {
        'client_id': os.getenv('SLACK_CLIENT_ID', ""),
        'client_secret': os.getenv('SLACK_SECRET', ""),
        'redirect_uri': os.getenv('SLACK_REDIRECT_URL', "")+"?payload="+original_payload,
        'code': code,
    }
    # print("params", params)
    resp = requests.post('https://slack.com/api/oauth.v2.access', data=params)
    if resp.status_code == 200:

        logger.debug("Slack responded with 200")

        slack_data = resp.json()
        if 'access_token' not in slack_data:
            print("Slack response body", slack_data)
            raise APIException("Slack error status: "+slack_data['error'])

        slack_data = resp.json()
        logger.debug(slack_data)

        # delete all previous credentials for the same team and cohort
        CredentialsSlack.objects.filter(
            app_id=slack_data['app_id'], team_id=slack_data['team']['id'], user__id=user.id).delete()
        credentials = CredentialsSlack(
            user=user,
            app_id=slack_data['app_id'],
            bot_user_id=slack_data['bot_user_id'],
            token=slack_data['access_token'],
            team_id=slack_data['team']['id'],
            team_name=slack_data['team']['name'],
            authed_user=slack_data['authed_user']['id'],
        )
        credentials.save()

        team = SlackTeam.objects.filter(
            academy__id=academy.id, slack_id=slack_data['team']['id']).first()
        if team is None:
            team = SlackTeam(
                slack_id=slack_data['team']['id'],
                owner=user,
                academy=academy
            )

        team.name = slack_data['team']['name']
        team.save()

        return HttpResponseRedirect(redirect_to=payload["url"][0])


# Create your views here.
@api_view(['GET'])
@permission_classes([AllowAny])
def get_facebook_token(request):
    """Generate stack redirect url for authorize"""
    url = request.query_params.get('url', None)
    if url is None:
        raise ValidationError("No callback URL specified")

    user_id = request.query_params.get('user', None)
    if user_id is None:
        raise ValidationError("No user specified on the URL")

    academy = request.query_params.get('a', None)
    if academy is None:
        raise ValidationError("No academy specified on the URL")

    url = base64.b64decode(url).decode("utf-8")
    # Missing scopes!! admin.invites:write, identify
    scopes = ("email",
              "ads_read", "business_management", "leads_retrieval", "pages_manage_metadata", "pages_read_engagement",
              )
    query_string = f'a={academy}&url={url}&user={user_id}'.encode("utf-8")
    payload = str(base64.urlsafe_b64encode(query_string), "utf-8")
    params = {
        "client_id": os.getenv('FACEBOOK_CLIENT_ID', ""),
        "redirect_uri": os.getenv('FACEBOOK_REDIRECT_URL', ""),
        "scope": ",".join(scopes),
        "state": payload
    }
    redirect = "https://www.facebook.com/v8.0/dialog/oauth?"
    for key in params:
        redirect += f"{key}={params[key]}&"

    if settings.DEBUG:
        return HttpResponse(f"Redirect to: <a href='{redirect}'>{redirect}</a>")
    else:
        return HttpResponseRedirect(redirect_to=redirect)


# Create your views here.
@api_view(['GET'])
@permission_classes([AllowAny])
def save_facebook_token(request):
    """Save facebook token"""
    logger.debug("Facebook callback just landed")
    print(request.GET)
    error = request.query_params.get('error_code', False)
    error_description = request.query_params.get('error_message', '')
    if error:
        raise APIException("Facebook: " + error_description)

    original_payload = request.query_params.get('state', None)
    payload = request.query_params.get('state', None)
    if payload is None:
        raise ValidationError("No payload specified")
    else:
        try:
            payload = base64.b64decode(payload).decode("utf-8")
            payload = parse_qs(payload)
        except:
            raise ValidationError("Cannot decode payload in base64")

    if "url" not in payload:
        logger.exception(payload)
        raise ValidationError("No url specified from the slack payload")

    if "user" not in payload:
        logger.exception(payload)
        raise ValidationError("No user id specified from the slack payload")

    if "a" not in payload:
        logger.exception(payload)
        raise ValidationError("No academy id specified from the slack payload")

    try:
        academy = Academy.objects.get(id=payload["a"][0])
    except Exception as e:
        raise ValidationError("Not exist academy with that id") from e

    try:
        user = User.objects.get(id=payload["user"][0])
    except Exception as e:
        raise ValidationError("Not exist user with that id") from e

    # token = request.query_params.get('token', None)
    # if token == None:
    #     raise ValidationError("No facebook token specified")

    code = request.query_params.get('code', None)
    if code is None:
        raise ValidationError("No slack code specified")

    params = {
        'client_id': os.getenv('FACEBOOK_CLIENT_ID', ""),
        'client_secret': os.getenv('FACEBOOK_SECRET', ""),
        'redirect_uri': os.getenv('FACEBOOK_REDIRECT_URL', ""),
        'code': code,
    }
    resp = requests.post(
        'https://graph.facebook.com/v8.0/oauth/access_token', data=params)
    if resp.status_code == 200:

        logger.debug("Facebook responded with 200")

        facebook_data = resp.json()
        if 'access_token' not in facebook_data:
            logger.debug("Facebook response body")
            logger.debug(facebook_data)
            raise APIException("Facebook error status: " +
                               facebook_data['error_message'])

        # delete all previous credentials for the same team
        CredentialsFacebook.objects.filter(user_id=user.id).delete()

        utc_now = timezone.now()
        expires_at = utc_now + \
            timezone.timedelta(milliseconds=facebook_data['expires_in'])

        credentials = CredentialsFacebook(
            user=user,
            academy=academy,
            expires_at=expires_at,
            token=facebook_data['access_token'],
        )
        credentials.save()

        params = {
            'access_token': facebook_data['access_token'],
            'fields': 'id,email',
        }
        resp = requests.post('https://graph.facebook.com/me', data=params)
        if resp.status_code == 200:
            logger.debug("Facebook responded with 200")
            facebook_data = resp.json()
            if "email" in facebook_data:
                credentials.email = facebook_data['email']
            if "id" in facebook_data:
                credentials.facebook_id = facebook_data['id']
            credentials.save()

        return HttpResponseRedirect(redirect_to=payload["url"][0])


def change_password(request, token):
    if request.method == 'POST':
        form = PasswordChangeCustomForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(
                request, 'Your password was successfully updated!')
            return redirect('change_password')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeCustomForm(request.user)
    return render(request, 'form.html', {
        'form': form
    })


def reset_password_view(request):

    if request.method == 'POST':
        _dict = request.POST.copy()
        form = PickPasswordForm(_dict)

        if "email" not in _dict or _dict["email"] == "":
            messages.error(request, 'Email is required')
            return render(request, 'form.html', {
                'form': form
            })

        users = User.objects.filter(email__iexact=_dict["email"])
        if(users.count() > 0):
            reset_password(users)
        else:
            logger.debug("No users with " +
                         _dict["email"] + " email to reset password")

        if "callback" in _dict and _dict["callback"] != "":
            return HttpResponseRedirect(redirect_to=_dict["callback"]+"?msg=Check your email for a password reset!")
        else:
            return render(request, 'message.html', {
                'message':  'Check your email for a password reset!'
            })
    else:
        _dict = request.GET.copy()
        _dict["callback"] = request.GET.get("callback", '')
        form = ResetPasswordForm(_dict)
    return render(request, 'form.html', {
        'form': form
    })


def pick_password(request, token):
    _dict = request.POST.copy()
    _dict["token"] = token
    _dict["callback"] = request.GET.get("callback", '')

    form = PickPasswordForm(_dict)
    if request.method == 'POST':
        password1 = request.POST.get("password1", None)
        password2 = request.POST.get("password2", None)
        if password1 != password2:
            messages.error(request, 'Passwords don\'t match')
            return render(request, 'form.html', {
                'form': form
            })

        token = Token.get_valid(request.POST.get("token", None))
        if token is None:
            messages.error(request, 'Invalid or expired token ' + str(token))

        else:
            user = token.user
            user.set_password(password1)
            user.save()
            token.delete()
            callback = request.POST.get("callback", None)
            if callback is not None and callback != "":
                return HttpResponseRedirect(redirect_to=request.POST.get("callback"))
            else:
                return render(request, 'message.html', {
                    'message': 'You password has been reset successfully, you can close this window.'
                })

    return render(request, 'form.html', {
        'form': form
    })


class AcademyInviteView(APIView):
    @capable_of('crud_member')
    def put(self, request, pa_id=None, academy_id=None):
        if pa_id is not None:
            profile_academy = ProfileAcademy.objects.filter(
                id=pa_id).first()

            if profile_academy is None:
                raise ValidationException("Member not found", 400)
            invite = UserInvite.objects.filter(
                academy__id=academy_id, email=profile_academy.email).first()

            if invite is None:
                raise ValidationException("Invite not found", 400)

            if invite.sent_at is not None:
                now = timezone.now()
                minutes_diff = (now - invite.sent_at).total_seconds() / 60.0

                if minutes_diff < 2:
                    raise ValidationException(
                        "Imposible to resend invitation", 400)
            resend_invite(invite.token, invite.email, invite.first_name)

            invite.sent_at = timezone.now()
            invite.save()
            serializer = UserInviteSerializer(invite, many=False)
            return Response(serializer.data)


def render_invite(request, token, member_id=None):
    _dict = request.POST.copy()
    _dict["token"] = token
    _dict["callback"] = request.GET.get("callback", '')

    if request.method == 'GET':

        invite = UserInvite.objects.filter(
            token=token, status='PENDING').first()
        if invite is None:
            return render(request, 'message.html', {
                'message': 'Invitation noot found with this token or it was already accepted'
            })
        form = InviteForm({
            **_dict,
            'first_name': invite.first_name,
            'last_name': invite.last_name,
            'phone': invite.phone
        })

        return render(request, 'form_invite.html', {
            'form': form,
        })

    if request.method == 'POST':
        form = InviteForm(_dict)
        password1 = request.POST.get("password1", None)
        password2 = request.POST.get("password2", None)

        if password1 != password2:
            messages.error(request, 'Passwords don\'t match')
            return render(request, 'form_invite.html', {
                'form': form,
            })

        invite = UserInvite.objects.filter(
            token=str(token), status='PENDING').first()
        if invite is None:
            messages.error(
                request, 'Invalid or expired invitation'+str(token))
            return render(request, 'form_invite.html', {
                'form': form
            })

        first_name = request.POST.get("first_name", None)
        last_name = request.POST.get("last_name", None)

        user = User.objects.filter(email=invite.email).first()
        if user is None:
            user = User(email=invite.email, first_name=first_name,
                        last_name=last_name, username=invite.email)
            user.save()
            user.set_password(password1)
            user.save()

        if invite.academy is not None:
            profile = ProfileAcademy.objects.filter(
                email=invite.email, academy=invite.academy).first()
            if profile is None:
                role = invite.role.slug
                profile = ProfileAcademy(
                    email=invite.email, academy=invite.academy, role=invite.role)

            profile.user = user
            profile.status = 'ACTIVE'
            profile.save()

        if invite.cohort is not None:
            role = 'student'
            if invite.role is not None and invite.role.slug != 'student':
                role = invite.role.slug.upper()
            cu = CohortUser.objects.filter(
                user=user, cohort=invite.cohort).first()
            if cu is None:
                cu = CohortUser(user=user, cohort=invite.cohort, role=role)
                cu.save()

        invite.status = 'ACCEPTED'
        invite.save()

        callback = str(request.POST.get("callback", None))
        if callback is not None and callback != "" and callback != "['']":
            return HttpResponseRedirect(redirect_to=callback[2:-2])
        else:
            return render(request, 'message.html', {
                'message': 'Welcome to BreatheCode, you can go ahead an log in'
            })


def login_html_view(request):

    _dict = request.GET.copy()
    form = LoginForm(_dict)

    if request.method == 'POST':

        try:

            url = request.POST.get("url", None)
            if url is None or url == "":
                raise Exception(
                    "Invalid redirect url, you must specify a url to redirect to")

            email = request.POST.get("email", None)
            password = request.POST.get("password", None)

            user = None
            if email and password:
                user = User.objects.filter(
                    Q(email=email) | Q(username=email)).first()
                if not user:
                    msg = 'Unable to log in with provided credentials.'
                    raise Exception(msg)
                if user.check_password(password) != True:
                    msg = 'Unable to log in with provided credentials.'
                    raise Exception(msg)
                # The authenticate call simply returns None for is_active=False
                # users. (Assuming the default ModelBackend authentication
                # backend.)
            else:
                msg = 'Must include "username" and "password".'
                raise Exception(msg, code=403)

            token, created = Token.objects.get_or_create(
                user=user, token_type='login')
            return HttpResponseRedirect(url+"?token="+str(token))

        except Exception as e:
            messages.error(request, e.message if hasattr(e, 'message') else e)
            return render(request, 'login.html', {
                'form': form
            })
    else:
        url = request.GET.get("url", None)
        if url is None or url == "":
            messages.error(
                request, "You must specify a 'url' (querystring) to redirect to after successfull login")

    return render(request, 'login.html', {
        'form': form,
        'redirect_url': request.GET.get("url", None)
    })
