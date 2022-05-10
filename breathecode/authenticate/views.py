import os, requests, base64, logging
import urllib.parse
import breathecode.notify.actions as notify_actions
from datetime import timezone, timedelta
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth import update_session_auth_hash
from rest_framework.response import Response
from django.db.models import Q
from django.http import HttpResponseRedirect, HttpResponse
from django.conf import settings
from django.urls import resolve
from rest_framework.exceptions import APIException, ValidationError, PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status, serializers
from django.contrib.auth.models import User, Group, AnonymousUser
from django.contrib import messages
from rest_framework.authtoken.views import ObtainAuthToken
from urllib.parse import urlencode, parse_qs, urlparse, parse_qsl
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from rest_framework.schemas.openapi import AutoSchema
from rest_framework.views import APIView
from django.utils import timezone
from datetime import datetime

from breathecode.mentorship.models import MentorProfile
from breathecode.mentorship.serializers import GETMentorSmallSerializer
from breathecode.utils.api_view_extensions.api_view_extensions import APIViewExtensions
from .authentication import ExpiringTokenAuthentication

from .forms import PickPasswordForm, PasswordChangeCustomForm, ResetPasswordForm, LoginForm, InviteForm
from .models import (
    Profile,
    CredentialsGithub,
    CredentialsGoogle,
    Token,
    CredentialsSlack,
    CredentialsFacebook,
    UserInvite,
    Role,
    ProfileAcademy,
)
from .actions import reset_password, resend_invite, generate_academy_token
from breathecode.admissions.models import Academy, CohortUser
from breathecode.notify.models import SlackTeam
from breathecode.notify.actions import send_email_message
from breathecode.utils import (capable_of, ValidationException, HeaderLimitOffsetPagination,
                               GenerateLookupsMixin)
from breathecode.utils.views import private_view, render_message, set_query_parameter
from breathecode.utils.find_by_full_name import query_like_by_full_name
from breathecode.utils.views import set_query_parameter
from .serializers import (GetProfileAcademySmallSerializer, UserInviteWaitingListSerializer, UserSerializer,
                          AuthSerializer, UserSmallSerializer, GetProfileAcademySerializer,
                          MemberPOSTSerializer, MemberPUTSerializer, StudentPOSTSerializer,
                          RoleSmallSerializer, UserMeSerializer, UserInviteSerializer, TokenSmallSerializer,
                          RoleBigSerializer, ProfileAcademySmallSerializer, UserTinySerializer)

logger = logging.getLogger(__name__)
APP_URL = os.getenv('APP_URL', '')


class TemporalTokenView(ObtainAuthToken):
    schema = AutoSchema()
    permission_classes = [IsAuthenticated]

    def post(self, request):

        token, created = Token.get_or_create(user=request.user, token_type='temporal')
        return Response({
            'token': token.key,
            'token_type': token.token_type,
            'expires_at': token.expires_at,
            'user_id': token.user.pk,
            'email': token.user.email
        })


class AcademyTokenView(ObtainAuthToken):
    schema = AutoSchema()
    permission_classes = [IsAuthenticated]

    @capable_of('get_academy_token')
    def get(self, request, academy_id):
        academy = Academy.objects.get(id=academy_id)
        academy_user = User.objects.filter(username=academy.slug).first()
        if academy_user is None:
            raise ValidationException('No academy token has been generated yet',
                                      slug='academy-token-not-found')

        token = Token.objects.filter(user=academy_user, token_type='permanent').first()
        if token is None:
            raise ValidationException('No academy token has been generated yet',
                                      slug='academy-token-not-found')

        return Response({
            'token': token.key,
            'token_type': token.token_type,
            'expires_at': token.expires_at,
        })

    @capable_of('generate_academy_token')
    def post(self, request, academy_id):

        token = generate_academy_token(academy_id, True)
        return Response({
            'token': token.key,
            'token_type': token.token_type,
            'expires_at': token.expires_at,
        })


class LogoutView(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        Token.objects.filter(token_type='login').delete()
        request.auth.delete()
        return Response({
            'message': 'User tokens successfully deleted',
        })


class WaitingListView(APIView, HeaderLimitOffsetPagination, GenerateLookupsMixin):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserInviteWaitingListSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MemberView(APIView, GenerateLookupsMixin):
    extensions = APIViewExtensions(paginate=True)

    @capable_of('read_member')
    def get(self, request, academy_id, user_id_or_email=None):
        handler = self.extensions(request)

        if user_id_or_email is not None:
            item = None
            if user_id_or_email.isnumeric():
                item = ProfileAcademy.objects.filter(user__id=user_id_or_email, academy_id=academy_id).first()
            else:
                item = ProfileAcademy.objects.filter(user__email=user_id_or_email,
                                                     academy_id=academy_id).first()

            if item is None:
                raise ValidationException('Profile not found for this user and academy',
                                          code=404,
                                          slug='profile-academy-not-found')

            serializer = GetProfileAcademySerializer(item, many=False)
            return Response(serializer.data)

        items = ProfileAcademy.objects.filter(academy__id=academy_id).exclude(role__slug='student')

        roles = request.GET.get('roles', None)
        if roles is not None:
            items = items.filter(role__in=roles.split(','))

        status = request.GET.get('status', None)
        if status is not None:
            items = items.filter(status__iexact=status)

        like = request.GET.get('like', None)
        if like is not None:
            items = query_like_by_full_name(like=like, items=items)

        items = items.exclude(user__email__contains='@token.com')

        items = handler.queryset(items)
        serializer = GetProfileAcademySmallSerializer(items, many=True)

        return handler.response(serializer.data)

    @capable_of('crud_member')
    def post(self, request, academy_id=None):
        serializer = MemberPOSTSerializer(data=request.data,
                                          context={
                                              'academy_id': academy_id,
                                              'request': request
                                          })
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('crud_member')
    def put(self, request, academy_id=None, user_id_or_email=None):

        already = None
        if user_id_or_email.isnumeric():
            already = ProfileAcademy.objects.filter(user__id=user_id_or_email, academy_id=academy_id).first()
        else:
            raise ValidationException('User id must be a numeric value',
                                      code=404,
                                      slug='user-id-is-not-numeric')

        request_data = {**request.data, 'user': user_id_or_email, 'academy': academy_id}
        if already:
            serializer = MemberPUTSerializer(already, data=request_data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            serializer = MemberPOSTSerializer(data=request_data,
                                              context={
                                                  'academy_id': academy_id,
                                                  'request': request
                                              })
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('crud_member')
    def delete(self, request, academy_id=None, user_id_or_email=None):
        lookups = self.generate_lookups(request, many_fields=['id'])

        if lookups and user_id_or_email:
            raise ValidationException(
                'user_id or cohort_id was provided in url '
                'in bulk mode request, use querystring style instead',
                code=400,
                slug='user-id-and-bulk-mode')

        if lookups:
            items = ProfileAcademy.objects.filter(**lookups,
                                                  academy__id=academy_id).exclude(role__slug='student')

            for item in items:
                item.delete()

            return Response(None, status=status.HTTP_204_NO_CONTENT)

        if user_id_or_email and not user_id_or_email.isnumeric():
            raise ValidationException('User id must be a numeric value',
                                      code=404,
                                      slug='user-id-is-not-numeric')

        member = ProfileAcademy.objects.filter(user=user_id_or_email,
                                               academy__id=academy_id).exclude(role__slug='student').first()

        if member is None:
            raise ValidationException('Member not found', code=404, slug='profile-academy-not-found')

        member.delete()
        return Response(None, status=status.HTTP_204_NO_CONTENT)


class MeInviteView(APIView, HeaderLimitOffsetPagination, GenerateLookupsMixin):
    def get(self, request):
        invites = UserInvite.objects.filter(email=request.user.email)

        status = request.GET.get('status', '')
        if status != '':
            invites = invites.filter(status__in=status.split(','))
        else:
            invites = invites.filter(status='PENDING')

        serializer = UserInviteSerializer(invites, many=True)
        return Response(serializer.data)

    def put(self, request, new_status=None):
        lookups = self.generate_lookups(request, many_fields=['id'])

        if new_status is None:
            raise ValidationException(f'Please specify new status for the invites', slug='missing-status')

        if new_status.upper() not in ['ACCEPTED', 'REJECTED']:
            raise ValidationException(f'Invalid invite status {new_status}', slug='invalid-status')

        if lookups:
            items = UserInvite.objects.filter(**lookups, email=request.user.email)

            for item in items:

                item.status = new_status.upper()
                item.save()

                exists = ProfileAcademy.objects.filter(email=item.email, academy__id=item.academy.id)

                if exists.count() == 0:
                    profile_academy = ProfileAcademy(academy=item.academy,
                                                     role=item.role,
                                                     status='ACTIVE',
                                                     email=item.email,
                                                     first_name=item.first_name,
                                                     last_name=item.last_name)
                    profile_academy.save()

            serializer = UserInviteSerializer(items, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        else:
            raise ValidationException('Invite ids were not provided', code=400, slug='missing-ids')


class AcademyInviteView(APIView, HeaderLimitOffsetPagination, GenerateLookupsMixin):
    @capable_of('read_invite')
    def get(self, request, academy_id=None, profileacademy_id=None, invite_id=None):

        if invite_id is not None:
            invite = UserInvite.objects.filter(academy__id=academy_id, id=invite_id, status='PENDING').first()
            if invite is None:
                raise ValidationException('No pending invite was found for this user and academy',
                                          code=404,
                                          slug='user-invite-not-found')

            serializer = UserInviteSerializer(invite, many=False)
            return Response(serializer.data)

        if profileacademy_id is not None:
            profile = ProfileAcademy.objects.filter(academy__id=academy_id, id=profileacademy_id).first()
            if profile is None:
                raise ValidationException('Profile not found', code=404, slug='profile-academy-not-found')

            invite = UserInvite.objects.filter(academy__id=academy_id, email=profile.email,
                                               status='PENDING').first()

            if invite is None and profile.status != 'INVITED':
                raise ValidationException(
                    'No pending invite was found for this user and academy',
                    code=404,
                    slug='user-invite-and-profile-academy-with-status-invited-not-found')

            # IMPORTANT: both serializers need to include "invite_url" property to have a consistent response
            if invite is not None:
                serializer = UserInviteSerializer(invite, many=False)
                return Response(serializer.data)

            if profile.status == 'INVITED':
                serializer = GetProfileAcademySerializer(profile, many=False)
                return Response(serializer.data)

        invites = UserInvite.objects.filter(academy__id=academy_id)

        status = request.GET.get('status', '')
        if status != '':
            invites = invites.filter(status__in=status.split(','))
        else:
            invites = invites.filter(status='PENDING')

        invites = invites.order_by(request.GET.get('sort', '-created_at'))

        page = self.paginate_queryset(invites, request)
        serializer = UserInviteSerializer(page, many=True)

        if self.is_paginate(request):
            return self.get_paginated_response(serializer.data)
        else:
            return Response(serializer.data, status=200)

    @capable_of('crud_invite')
    def delete(self, request, academy_id=None):
        lookups = self.generate_lookups(request, many_fields=['id'])
        if lookups:
            items = UserInvite.objects.filter(**lookups, academy__id=academy_id)

            for item in items:
                item.delete()
            return Response(None, status=status.HTTP_204_NO_CONTENT)
        else:
            raise ValidationException('Invite ids were not provided', 404, slug='missing_ids')

    @capable_of('invite_resend')
    def put(self, request, invite_id=None, profileacademy_id=None, academy_id=None):
        invite = None
        profile_academy = None
        if invite_id is not None:
            invite = UserInvite.objects.filter(academy__id=academy_id, id=invite_id, status='PENDING').first()
            if invite is None:
                raise ValidationException('No pending invite was found for this user and academy',
                                          code=404,
                                          slug='user-invite-not-found')

        elif profileacademy_id is not None:
            profile_academy = ProfileAcademy.objects.filter(id=profileacademy_id).first()

            if profile_academy is None:
                raise ValidationException('Member not found', code=400, slug='profile-academy-not-found')

            invite = UserInvite.objects.filter(academy__id=academy_id, email=profile_academy.email).first()

        if (invite is None and profile_academy is not None and profile_academy.status == 'INVITED'
                and (profile_academy.user.email or invite.email)):
            notify_actions.send_email_message(
                'academy_invite', profile_academy.user.email or invite.email, {
                    'subject': f'Invitation to study at {profile_academy.academy.name}',
                    'invites': [ProfileAcademySmallSerializer(profile_academy).data],
                    'user': UserSmallSerializer(profile_academy.user).data,
                    'LINK': os.getenv('API_URL') + '/v1/auth/academy/html/invite',
                })
            serializer = GetProfileAcademySerializer(profile_academy)
            return Response(serializer.data)

        if invite is None:
            raise ValidationException('Invite not found', code=400, slug='user-invite-not-found')

        if invite.sent_at is not None:
            now = timezone.now()
            minutes_diff = (now - invite.sent_at).total_seconds() / 60.0

            if minutes_diff < 2:
                raise ValidationException('Impossible to resend invitation',
                                          code=400,
                                          slug='sent-at-diff-less-two-minutes')

        email = (profile_academy and profile_academy.user and profile_academy.user.email) or invite.email
        if not email:
            raise ValidationException('Impossible to determine the email of user',
                                      code=400,
                                      slug='without-email')

        resend_invite(invite.token, email, invite.first_name)

        invite.sent_at = timezone.now()
        invite.save()
        serializer = UserInviteSerializer(invite, many=False)
        return Response(serializer.data)


class StudentView(APIView, GenerateLookupsMixin):
    extensions = APIViewExtensions(paginate=True)

    @capable_of('read_student')
    def get(self, request, academy_id=None, user_id_or_email=None):
        handler = self.extensions(request)

        if user_id_or_email is not None:
            profile = None
            if user_id_or_email.isnumeric():
                profile = ProfileAcademy.objects.filter(academy__id=academy_id,
                                                        user__id=user_id_or_email).first()
            else:
                profile = ProfileAcademy.objects.filter(academy__id=academy_id,
                                                        user__email=user_id_or_email).first()

            if profile is None:
                raise ValidationException('Profile not found', code=404, slug='profile-academy-not-found')

            serializer = GetProfileAcademySerializer(profile, many=False)
            return Response(serializer.data)

        items = ProfileAcademy.objects.filter(role__slug='student', academy__id=academy_id)

        like = request.GET.get('like', None)
        if like is not None:
            items = query_like_by_full_name(like=like, items=items)

        status = request.GET.get('status', None)
        if status is not None:
            items = items.filter(status__iexact=status)

        items = handler.queryset(items)
        serializer = GetProfileAcademySmallSerializer(items, many=True)

        return handler.response(serializer.data)

    @capable_of('crud_student')
    def post(self, request, academy_id=None):
        serializer = StudentPOSTSerializer(data=request.data,
                                           context={
                                               'academy_id': academy_id,
                                               'request': request
                                           })
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('crud_student')
    def put(self, request, academy_id=None, user_id_or_email=None):
        if not user_id_or_email.isnumeric():
            raise ValidationException('User id must be a numeric value',
                                      code=404,
                                      slug='user-id-is-not-numeric')

        student = ProfileAcademy.objects.filter(user__id=user_id_or_email, academy__id=academy_id).first()

        if student and student.role.slug != 'student':
            raise ValidationException(
                f'This endpoint can only update student profiles (not {student.role.slug})',
                code=400,
                slug='trying-to-change-a-staff')

        request_data = {**request.data, 'user': user_id_or_email, 'academy': academy_id, 'role': 'student'}
        if 'role' in request.data:
            raise ValidationException(
                'The student role cannot be updated with this endpoint, user /member instead.',
                code=400,
                slug='trying-to-change-role')

        if not student:
            raise ValidationException('The user is not a student in this academy',
                                      code=404,
                                      slug='profile-academy-not-found')

        serializer = MemberPUTSerializer(student, data=request_data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('crud_student')
    def delete(self, request, academy_id=None, user_id_or_email=None):
        lookups = self.generate_lookups(request, many_fields=['id'])

        if lookups and user_id_or_email:
            raise ValidationException(
                'user_id was provided in url '
                'in bulk mode request, use querystring style instead',
                code=400,
                slug='user-id-and-bulk-mode')

        if lookups:
            items = ProfileAcademy.objects.filter(**lookups, academy__id=academy_id, role__slug='student')

            for item in items:

                item.delete()

            return Response(None, status=status.HTTP_204_NO_CONTENT)

        if academy_id is None or user_id_or_email is None:
            raise serializers.ValidationError('Missing user_id or academy_id', code=400)

        if user_id_or_email and not user_id_or_email.isnumeric():
            raise ValidationException('User id must be a numeric value',
                                      code=404,
                                      slug='user-id-is-not-numeric')

        profile = ProfileAcademy.objects.filter(academy__id=academy_id,
                                                user__id=user_id_or_email,
                                                role__slug='student').first()
        if profile is None:
            raise ValidationException('User doest not exist or does not belong to this academy',
                                      code=404,
                                      slug='profile-academy-not-found')

        profile.delete()
        return Response(None, status=status.HTTP_204_NO_CONTENT)


class LoginView(ObtainAuthToken):
    schema = AutoSchema()

    def post(self, request, *args, **kwargs):

        serializer = AuthSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.get_or_create(user=user, token_type='login')
        return Response({'token': token.key, 'user_id': user.pk, 'email': user.email})


@api_view(['GET'])
@permission_classes([AllowAny])
def get_token_info(request, token):

    token = Token.objects.filter(key=token).first()

    if token is None or token.expires_at < timezone.now():
        raise PermissionDenied('Expired or invalid token')

    return Response({
        'token': token.key,
        'token_type': token.token_type,
        'expires_at': token.expires_at,
        'user_id': token.user.pk
    })


class UserMeView(APIView):
    def get(self, request, format=None):
        # TODO: This should be not accessible because this endpoint require auth
        try:
            if isinstance(request.user, AnonymousUser):
                raise ValidationException('There is not user', slug='without-auth', code=403)

        except User.DoesNotExist:
            raise ValidationException('You don\'t have a user', slug='user-not-found', code=403)

        users = UserSerializer(request.user)
        return Response(users.data)

    def put(self, request):
        # TODO: This should be not accessible because this endpoint require auth
        try:
            if isinstance(request.user, AnonymousUser):
                raise ValidationException('There is not user', slug='without-auth', code=403)

        except User.DoesNotExist:
            raise ValidationException('You don\'t have a user', slug='user-not-found', code=403)

        serializer = UserMeSerializer(request.user, data=request.data, context={'request': request})
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
        query = query.filter(Q(first_name__icontains=name) | Q(last_name__icontains=name))

    like = request.GET.get('like', None)
    if like is not None:
        query = query.filter(
            Q(first_name__icontains=like) | Q(last_name__icontains=like)
            | Q(email__icontains=like))

    query = query.exclude(email__contains='@token.com')
    query = query.order_by('-date_joined')
    users = UserSmallSerializer(query, many=True)
    return Response(users.data)


@api_view(['GET'])
def get_user_by_id_or_email(request, id_or_email):

    query = None
    if id_or_email.isnumeric():
        query = User.objects.filter(id=id_or_email).first()
    else:
        query = User.objects.filter(email=id_or_email).first()

    if query is None:
        raise ValidationException('User with that id or email does not exists',
                                  slug='user-dont-exists',
                                  code=404)

    users = UserSmallSerializer(query, many=False)
    return Response(users.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_roles(request, role_slug=None):

    if role_slug is not None:
        role = Role.objects.filter(slug=role_slug).first()
        if role is None:
            raise ValidationException('Role not found', code=404)

        serializer = RoleBigSerializer(role)
        return Response(serializer.data)

    queryset = Role.objects.all()
    serializer = RoleSmallSerializer(queryset, many=True)
    return Response(serializer.data)


# Create your views here.


@api_view(['GET'])
@permission_classes([AllowAny])
def get_github_token(request, token=None):

    url = request.query_params.get('url', None)
    if url == None:
        raise ValidationException('No callback URL specified', slug='no-callback-url')

    if token is not None:
        if Token.get_valid(token) is None:
            raise ValidationException('Invalid or missing token', slug='invalid-token')
        else:
            url = url + f'&user={token}'

    params = {
        'client_id': os.getenv('GITHUB_CLIENT_ID', ''),
        'redirect_uri': os.getenv('GITHUB_REDIRECT_URL', '') + f'?url={url}',
        'scope': 'user repo read:org',
    }

    logger.debug('Redirecting to github')
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

    logger.debug('Github callback just landed')
    logger.debug(request.query_params)

    error = request.query_params.get('error', False)
    error_description = request.query_params.get('error_description', '')
    if error:
        raise APIException('Github: ' + error_description)

    url = request.query_params.get('url', None)
    if url == None:
        raise ValidationException('No callback URL specified', slug='no-callback-url')

    # the url may or may not be encoded
    try:
        url = base64.b64decode(url.encode('utf-8')).decode('utf-8')
    except Exception as e:
        pass

    code = request.query_params.get('code', None)
    if code == None:
        raise ValidationException('No github code specified', slug='no-code')

    token = request.query_params.get('user', None)

    payload = {
        'client_id': os.getenv('GITHUB_CLIENT_ID', ''),
        'client_secret': os.getenv('GITHUB_SECRET', ''),
        'redirect_uri': os.getenv('GITHUB_REDIRECT_URL', ''),
        'code': code,
    }
    headers = {'Accept': 'application/json'}
    resp = requests.post('https://github.com/login/oauth/access_token', data=payload, headers=headers)
    if resp.status_code == 200:

        logger.debug('Github responded with 200')

        body = resp.json()
        if 'access_token' not in body:
            raise APIException(body['error_description'])

        github_token = body['access_token']
        resp = requests.get('https://api.github.com/user', headers={'Authorization': 'token ' + github_token})
        if resp.status_code == 200:
            github_user = resp.json()
            logger.debug(github_user)

            if github_user['email'] is None:
                resp = requests.get('https://api.github.com/user/emails',
                                    headers={'Authorization': 'token ' + github_token})
                if resp.status_code == 200:
                    emails = resp.json()
                    primary_emails = [x for x in emails if x['primary'] == True]
                    if len(primary_emails) > 0:
                        github_user['email'] = primary_emails[0]['email']
                    elif len(emails) > 0:
                        github_user['email'] = emails[0]['email']

            if github_user['email'] is None:
                raise ValidationError('Impossible to retrieve user email')

            user = None  # assuming by default that its a new user
            # is a valid token??? if not valid it will become None
            if token is not None and token != '':
                token = Token.get_valid(token)
                if not token:
                    logger.debug(f'Token not found or is expired')
                    raise ValidationException(
                        'Token was not found or is expired, please use a different token',
                        code=404,
                        slug='token-not-found')
                user = User.objects.filter(auth_token=token.id).first()
            else:
                # for the token to become null for easier management
                token = None

            # user can't be found thru token, lets try thru the github credentials
            if token is None and user is None:
                user = User.objects.filter(
                    Q(credentialsgithub__github_id=github_user['id'])
                    | Q(email__iexact=github_user['email'])).first()

            # create the user if not exists
            if user is None:
                user = User(username=github_user['email'].lower(), email=github_user['email'].lower())
                user.save()

            github_credentials = CredentialsGithub.objects.filter(github_id=github_user['id']).first()

            # update latest credentials if the user.id doesn't match
            if github_credentials and github_credentials.user.id != user.id:
                github_credentials.delete()
                github_credentials = None

            # create a new credentials if it doesn't exists
            if github_credentials is None:
                github_credentials = CredentialsGithub(github_id=github_user['id'], user=user)

            github_credentials.token = github_token
            github_credentials.username = github_user['login']
            github_credentials.email = github_user['email'].lower()
            github_credentials.avatar_url = github_user['avatar_url']
            github_credentials.name = github_user['name']
            github_credentials.blog = github_user['blog']
            github_credentials.bio = github_user['bio']
            github_credentials.company = github_user['company']
            github_credentials.twitter_username = github_user['twitter_username']
            github_credentials.save()

            profile = Profile.objects.filter(user=user).first()
            if profile is None:
                profile = Profile(user=user,
                                  avatar_url=github_user['avatar_url'],
                                  blog=github_user['blog'],
                                  bio=github_user['bio'],
                                  twitter_username=github_user['twitter_username'])
                profile.save()

            student_role = Role.objects.get(slug='student')
            cus = CohortUser.objects.filter(user=user, role='STUDENT')
            for cu in cus:
                profile_academy = ProfileAcademy.objects.filter(user=cu.user,
                                                                academy=cu.cohort.academy).first()
                if profile_academy is None:
                    profile_academy = ProfileAcademy(user=cu.user,
                                                     academy=cu.cohort.academy,
                                                     role=student_role,
                                                     email=cu.user.email,
                                                     first_name=cu.user.first_name,
                                                     last_name=cu.user.last_name,
                                                     status='ACTIVE')
                    profile_academy.save()

            if not token:
                token, created = Token.get_or_create(user=user, token_type='login')

            return HttpResponseRedirect(redirect_to=url + '?token=' + token.key)

        else:
            raise APIException('Error from github')


# Create your views here.
@api_view(['GET'])
@permission_classes([AllowAny])
def get_slack_token(request):
    """Generate stack redirect url for authorize"""
    url = request.query_params.get('url', None)
    if url is None:
        raise ValidationError('No callback URL specified')

    # the url may or may not be encoded
    try:
        url = base64.b64decode(url.encode('utf-8')).decode('utf-8')
    except Exception as e:
        pass

    user_id = request.query_params.get('user', None)
    if user_id is None:
        raise ValidationError('No user specified on the URL')

    academy = request.query_params.get('a', None)
    if academy is None:
        raise ValidationError('No academy specified on the URL')

    # Missing scopes!! admin.invites:write, identify
    scopes = ('app_mentions:read', 'channels:history', 'channels:join', 'channels:read', 'chat:write',
              'chat:write.customize', 'commands', 'files:read', 'files:write', 'groups:history',
              'groups:read', 'groups:write', 'incoming-webhook', 'team:read', 'users:read',
              'users:read.email', 'users.profile:read', 'users:read')

    query_string = f'a={academy}&url={url}&user={user_id}'.encode('utf-8')
    payload = str(base64.urlsafe_b64encode(query_string), 'utf-8')
    params = {
        'client_id': os.getenv('SLACK_CLIENT_ID', ''),
        'redirect_uri': os.getenv('SLACK_REDIRECT_URL', '') + '?payload=' + payload,
        'scope': ','.join(scopes)
    }
    redirect = 'https://slack.com/oauth/v2/authorize?'
    for key in params:
        redirect += f'{key}={params[key]}&'

    if settings.DEBUG:
        return HttpResponse(f"Redirect to: <a href='{redirect}'>{redirect}</a>")
    else:
        return HttpResponseRedirect(redirect_to=redirect)


# Create your views here.


@api_view(['GET'])
@permission_classes([AllowAny])
def save_slack_token(request):
    """Get Slack token and redirect to authorization route"""
    logger.debug('Slack callback just landed')

    error = request.query_params.get('error', False)
    error_description = request.query_params.get('error_description', '')
    if error:
        raise APIException('Slack: ' + error_description)

    original_payload = request.query_params.get('payload', None)
    payload = request.query_params.get('payload', None)
    if payload is None:
        raise ValidationError('No payload specified')
    else:
        try:
            payload = base64.b64decode(payload).decode('utf-8')
            payload = parse_qs(payload)
        except:
            raise ValidationError('Cannot decode payload in base64')

    if 'url' not in payload:
        logger.exception(payload)
        raise ValidationError('No url specified from the slack payload')

    if 'user' not in payload:
        logger.exception(payload)
        raise ValidationError('No user id specified from the slack payload')

    if 'a' not in payload:
        logger.exception(payload)
        raise ValidationError('No academy id specified from the slack payload')

    try:
        academy = Academy.objects.get(id=payload['a'][0])
    except Exception as e:
        raise ValidationError('Not exist academy with that id') from e

    user = None
    try:
        user = User.objects.get(id=payload['user'][0])
    except Exception as e:
        raise ValidationError('Not exist user with that id') from e

    code = request.query_params.get('code', None)
    if code is None:
        raise ValidationError('No slack code specified')

    params = {
        'client_id': os.getenv('SLACK_CLIENT_ID', ''),
        'client_secret': os.getenv('SLACK_SECRET', ''),
        'redirect_uri': os.getenv('SLACK_REDIRECT_URL', '') + '?payload=' + original_payload,
        'code': code,
    }
    resp = requests.post('https://slack.com/api/oauth.v2.access', data=params)
    if resp.status_code == 200:

        logger.debug('Slack responded with 200')

        slack_data = resp.json()
        if 'access_token' not in slack_data:
            print('Slack response body', slack_data)
            raise APIException('Slack error status: ' + slack_data['error'])

        slack_data = resp.json()
        logger.debug(slack_data)

        # delete all previous credentials for the same team and cohort
        CredentialsSlack.objects.filter(app_id=slack_data['app_id'],
                                        team_id=slack_data['team']['id'],
                                        user__id=user.id).delete()
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

        team = SlackTeam.objects.filter(academy__id=academy.id, slack_id=slack_data['team']['id']).first()
        if team is None:
            team = SlackTeam(slack_id=slack_data['team']['id'], owner=user, academy=academy)

        team.name = slack_data['team']['name']
        team.save()

        return HttpResponseRedirect(redirect_to=payload['url'][0])


# Create your views here.
@api_view(['GET'])
@permission_classes([AllowAny])
def get_facebook_token(request):
    """Generate stack redirect url for authorize"""
    url = request.query_params.get('url', None)
    if url is None:
        raise ValidationError('No callback URL specified')

    # the url may or may not be encoded
    try:
        url = base64.b64decode(url.encode('utf-8')).decode('utf-8')
    except Exception as e:
        pass

    user_id = request.query_params.get('user', None)
    if user_id is None:
        raise ValidationError('No user specified on the URL')

    academy = request.query_params.get('a', None)
    if academy is None:
        raise ValidationError('No academy specified on the URL')

    # Missing scopes!! admin.invites:write, identify
    scopes = (
        'email',
        'ads_read',
        'business_management',
        'leads_retrieval',
        'pages_manage_metadata',
        'pages_read_engagement',
    )
    query_string = f'a={academy}&url={url}&user={user_id}'.encode('utf-8')
    payload = str(base64.urlsafe_b64encode(query_string), 'utf-8')
    params = {
        'client_id': os.getenv('FACEBOOK_CLIENT_ID', ''),
        'redirect_uri': os.getenv('FACEBOOK_REDIRECT_URL', ''),
        'scope': ','.join(scopes),
        'state': payload
    }
    redirect = 'https://www.facebook.com/v8.0/dialog/oauth?'
    for key in params:
        redirect += f'{key}={params[key]}&'

    if settings.DEBUG:
        return HttpResponse(f"Redirect to: <a href='{redirect}'>{redirect}</a>")
    else:
        return HttpResponseRedirect(redirect_to=redirect)


# Create your views here.
@api_view(['GET'])
@permission_classes([AllowAny])
def save_facebook_token(request):
    """Save facebook token"""
    logger.debug('Facebook callback just landed')
    error = request.query_params.get('error_code', False)
    error_description = request.query_params.get('error_message', '')
    if error:
        raise APIException('Facebook: ' + error_description)

    original_payload = request.query_params.get('state', None)
    payload = request.query_params.get('state', None)
    if payload is None:
        raise ValidationError('No payload specified')
    else:
        try:
            payload = base64.b64decode(payload).decode('utf-8')
            payload = parse_qs(payload)
        except:
            raise ValidationError('Cannot decode payload in base64')

    if 'url' not in payload:
        logger.exception(payload)
        raise ValidationError('No url specified from the slack payload')

    if 'user' not in payload:
        logger.exception(payload)
        raise ValidationError('No user id specified from the slack payload')

    if 'a' not in payload:
        logger.exception(payload)
        raise ValidationError('No academy id specified from the slack payload')

    try:
        academy = Academy.objects.get(id=payload['a'][0])
    except Exception as e:
        raise ValidationError('Not exist academy with that id') from e

    try:
        user = User.objects.get(id=payload['user'][0])
    except Exception as e:
        raise ValidationError('Not exist user with that id') from e

    # token = request.query_params.get('token', None)
    # if token == None:
    #     raise ValidationError("No facebook token specified")

    code = request.query_params.get('code', None)
    if code is None:
        raise ValidationError('No slack code specified')

    params = {
        'client_id': os.getenv('FACEBOOK_CLIENT_ID', ''),
        'client_secret': os.getenv('FACEBOOK_SECRET', ''),
        'redirect_uri': os.getenv('FACEBOOK_REDIRECT_URL', ''),
        'code': code,
    }
    resp = requests.post('https://graph.facebook.com/v8.0/oauth/access_token', data=params)
    if resp.status_code == 200:

        logger.debug('Facebook responded with 200')

        facebook_data = resp.json()
        if 'access_token' not in facebook_data:
            logger.debug('Facebook response body')
            logger.debug(facebook_data)
            raise APIException('Facebook error status: ' + facebook_data['error_message'])

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
            logger.debug('Facebook responded with 200')
            facebook_data = resp.json()
            if 'email' in facebook_data:
                credentials.email = facebook_data['email']
            if 'id' in facebook_data:
                credentials.facebook_id = facebook_data['id']
            credentials.save()

        return HttpResponseRedirect(redirect_to=payload['url'][0])


def change_password(request, token):
    if request.method == 'POST':
        form = PasswordChangeCustomForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, 'Your password was successfully updated!')
            return redirect('change_password')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeCustomForm(request.user)
    return render(request, 'form.html', {'form': form})


class TokenTemporalView(APIView):
    @capable_of('generate_temporal_token')
    def post(self, request, profile_academy_id=None, academy_id=None):
        profile_academy = ProfileAcademy.objects.filter(id=profile_academy_id).first()
        if profile_academy is None:
            raise ValidationException('Member not found', code=404, slug='member-not-found')

        token, created = Token.get_or_create(user=profile_academy.user, token_type='temporal')
        serializer = TokenSmallSerializer(token)
        return Response(serializer.data)


def reset_password_view(request):

    if request.method == 'POST':
        _dict = request.POST.copy()
        form = PickPasswordForm(_dict)

        if 'email' not in _dict or _dict['email'] == '':
            messages.error(request, 'Email is required')
            return render(request, 'form.html', {'form': form})

        users = User.objects.filter(email__iexact=_dict['email'])
        if (users.count() > 0):
            reset_password(users)
        else:
            logger.debug('No users with ' + _dict['email'] + ' email to reset password')

        if 'callback' in _dict and _dict['callback'] != '':
            return HttpResponseRedirect(redirect_to=_dict['callback'] +
                                        '?msg=Check your email for a password reset!')
        else:
            return render(request, 'message.html', {'MESSAGE': 'Check your email for a password reset!'})
    else:
        _dict = request.GET.copy()
        _dict['callback'] = request.GET.get('callback', '')
        form = ResetPasswordForm(_dict)
    return render(request, 'form.html', {'form': form})


def pick_password(request, token):
    _dict = request.POST.copy()
    _dict['token'] = token
    _dict['callback'] = request.GET.get('callback', '')

    form = PickPasswordForm(_dict)
    if request.method == 'POST':
        password1 = request.POST.get('password1', None)
        password2 = request.POST.get('password2', None)
        if password1 != password2:
            messages.error(request, 'Passwords don\'t match')
            return render(request, 'form.html', {'form': form})

        token = Token.get_valid(request.POST.get('token', None))
        if token is None:
            messages.error(request, 'Invalid or expired token ' + str(token))

        else:
            user = token.user
            user.set_password(password1)
            user.save()
            token.delete()
            callback = request.POST.get('callback', None)
            if callback is not None and callback != '':
                return HttpResponseRedirect(redirect_to=request.POST.get('callback'))
            else:
                return render(
                    request, 'message.html',
                    {'message': 'You password has been reset successfully, you can close this window.'})

    return render(request, 'form.html', {'form': form})


class PasswordResetView(APIView):
    @capable_of('send_reset_password')
    def post(self, request, profileacademy_id=None, academy_id=None):

        profile_academy = ProfileAcademy.objects.filter(id=profileacademy_id).first()
        if profile_academy is None:
            raise ValidationException('Member not found', 400)

        if reset_password([profile_academy.user]):
            token = Token.objects.filter(user=profile_academy.user, token_type='temporal').first()
            serializer = TokenSmallSerializer(token)
            return Response(serializer.data)
        else:
            raise ValidationException('Reset password token could not be sent')


class ProfileInviteMeView(APIView):
    def get(self, request):
        invites = UserInvite.objects.filter(email=request.user.email)
        profile_academies = ProfileAcademy.objects.filter(user=request.user, status='INVITED')
        mentor_profiles = MentorProfile.objects.filter(user=request.user, status='INVITED')

        return Response({
            'invites': UserInviteSerializer(invites, many=True).data,
            'profile_academies': GetProfileAcademySerializer(profile_academies, many=True).data,
            'mentor_profiles': GETMentorSmallSerializer(mentor_profiles, many=True).data,
        })


def render_invite(request, token, member_id=None):
    _dict = request.POST.copy()
    _dict['token'] = token
    _dict['callback'] = request.GET.get('callback', '')

    if request.method == 'GET':

        invite = UserInvite.objects.filter(token=token, status='PENDING').first()
        if invite is None:
            callback_msg = ''
            if _dict['callback'] != '':
                callback_msg = ". You can try and login at <a href='" + _dict['callback'] + "'>" + _dict[
                    'callback'] + '</a>'
            return render_message(
                request, 'Invitation not found with this token or it was already accepted' + callback_msg)

        form = InviteForm({
            'callback': [''],
            **_dict,
            'first_name': invite.first_name,
            'last_name': invite.last_name,
            'phone': invite.phone,
        })

        return render(request, 'form_invite.html', {
            'form': form,
        })

    if request.method == 'POST':
        form = InviteForm(_dict)
        password1 = request.POST.get('password1', None)
        password2 = request.POST.get('password2', None)

        invite = UserInvite.objects.filter(token=str(token), status='PENDING', email__isnull=False).first()
        if invite is None:
            messages.error(request, 'Invalid or expired invitation ' + str(token))
            return render(request, 'form_invite.html', {'form': form})

        first_name = request.POST.get('first_name', None)
        last_name = request.POST.get('last_name', None)
        if first_name is None or first_name == '' or last_name is None or last_name == '':
            messages.error(request, 'Invalid first or last name')
            return render(request, 'form_invite.html', {
                'form': form,
            })

        if password1 != password2:
            messages.error(request, 'Passwords don\'t match')
            return render(request, 'form_invite.html', {
                'form': form,
            })

        if not password1:
            messages.error(request, 'Password is empty')
            return render(request, 'form_invite.html', {
                'form': form,
            })

        user = User.objects.filter(email=invite.email).first()
        if user is None:
            user = User(email=invite.email, first_name=first_name, last_name=last_name, username=invite.email)
            user.save()
            user.set_password(password1)
            user.save()

        if invite.academy is not None:
            profile = ProfileAcademy.objects.filter(email=invite.email, academy=invite.academy).first()
            if profile is None:
                role = invite.role
                if not role:
                    role = Role.objects.filter(slug='student').first()

                if not role:
                    messages.error(
                        request, 'Unexpected error occurred with invite, please contact the '
                        'staff of 4geeks')
                    return render(request, 'form_invite.html', {
                        'form': form,
                    })

                profile = ProfileAcademy(email=invite.email,
                                         academy=invite.academy,
                                         role=role,
                                         first_name=first_name,
                                         last_name=last_name)

                if invite.first_name is not None and invite.first_name != '':
                    profile.first_name = invite.first_name
                if invite.last_name is not None and invite.last_name != '':
                    profile.last_name = invite.last_name

            profile.user = user
            profile.status = 'ACTIVE'
            profile.save()

        if invite.cohort is not None:
            role = 'student'
            if invite.role is not None and invite.role.slug != 'student':
                role = invite.role.slug.upper()

            cu = CohortUser.objects.filter(user=user, cohort=invite.cohort).first()
            if cu is None:
                cu = CohortUser(user=user, cohort=invite.cohort, role=role)
                cu.save()

        invite.status = 'ACCEPTED'
        invite.save()

        callback = request.POST.get('callback', None)
        if callback:
            uri = callback[0] if isinstance(callback, list) else callback
            if len(uri) > 0 and uri[0] == '[':
                uri = uri[2:-2]
            if settings.DEBUG:
                print(type(callback))
                return HttpResponse(f"Redirect to: <a href='{uri}'>{uri}</a>")
            else:
                return HttpResponseRedirect(redirect_to=uri)
        else:
            return render(request, 'message.html',
                          {'MESSAGE': 'Welcome to 4Geeks, you can go ahead an log in'})


@private_view()
def render_academy_invite(request, token):
    callback_url = request.GET.get('callback', '')
    accepting = request.GET.get('accepting', '')
    rejecting = request.GET.get('rejecting', '')
    if accepting.strip() != '':
        ProfileAcademy.objects.filter(id__in=accepting.split(','), user__id=token.user.id,
                                      status='INVITED').update(status='ACTIVE')
    if rejecting.strip() != '':
        ProfileAcademy.objects.filter(id__in=rejecting.split(','), user__id=token.user.id).delete()

    pending_invites = ProfileAcademy.objects.filter(user__id=token.user.id, status='INVITED')
    if pending_invites.count() == 0:
        return render_message(request,
                              f'You don\'t have any more pending invites',
                              btn_label='Continue to 4Geeks',
                              btn_url=APP_URL)

    querystr = urllib.parse.urlencode({'callback': APP_URL, 'token': token.key})
    url = os.getenv('API_URL') + '/v1/auth/academy/html/invite?' + querystr
    return render(
        request, 'academy_invite.html', {
            'subject': f'Invitation to study at 4Geeks.com',
            'invites': ProfileAcademySmallSerializer(pending_invites, many=True).data,
            'LINK': url,
            'user': UserTinySerializer(token.user, many=False).data
        })


def login_html_view(request):

    _dict = request.GET.copy()
    form = LoginForm(_dict)

    if request.method == 'POST':

        try:

            url = request.POST.get('url', None)
            if url is None or url == '':
                raise Exception('Invalid redirect url, you must specify a url to redirect to')

            # the url may or may not be encoded
            try:
                url = base64.b64decode(url.encode('utf-8')).decode('utf-8')
            except Exception as e:
                pass

            email = request.POST.get('email', None)
            password = request.POST.get('password', None)

            user = None
            if email and password:
                user = User.objects.filter(Q(email=email) | Q(username=email)).first()
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

            token, created = Token.get_or_create(user=user, token_type='login')

            request.session['token'] = token.key
            return HttpResponseRedirect(
                set_query_parameter(set_query_parameter(url, 'attempt', '1'), 'token', str(token)))

        except Exception as e:
            messages.error(request, e.message if hasattr(e, 'message') else e)
            return render(request, 'login.html', {'form': form})
    else:
        url = request.GET.get('url', None)
        if url is None or url == '':
            messages.error(request,
                           "You must specify a 'url' (querystring) to redirect to after successfull login")

    return render(request, 'login.html', {'form': form, 'redirect_url': request.GET.get('url', None)})


@api_view(['GET'])
@permission_classes([AllowAny])
def get_google_token(request, token=None):

    if token == None:
        raise ValidationException('No session token has been specified', slug='no-session-token')

    url = request.query_params.get('url', None)
    if url == None:
        raise ValidationException('No callback URL specified', slug='no-callback-url')

    try:
        url = base64.b64decode(url.encode('utf-8')).decode('utf-8')
    except Exception as e:
        pass

    token = Token.get_valid(
        token)  # IMPORTANT!! you can only connect to google with temporal short lasting tokens
    if token is None or token.token_type != 'temporal':
        raise ValidationException('Invalid or inactive token', code=403, slug='invalid-token')

    params = {
        'response_type': 'code',
        'client_id': os.getenv('GOOGLE_CLIENT_ID', ''),
        'redirect_uri': os.getenv('GOOGLE_REDIRECT_URL', ''),
        'access_type': 'offline',  #we need offline access to receive refresh token and avoid total expiration
        'scope': 'https://www.googleapis.com/auth/calendar.events',
        'state': f'token={token.key}&url={url}'
    }

    logger.debug('Redirecting to google')
    logger.debug(params)

    redirect = f'https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}'

    if settings.DEBUG:
        return HttpResponse(f"Redirect to: <a href='{redirect}'>{redirect}</a>")
    else:
        return HttpResponseRedirect(redirect_to=redirect)


# Create your views here.


@api_view(['GET'])
@permission_classes([AllowAny])
def save_google_token(request):

    logger.debug('Google callback just landed')
    logger.debug(request.query_params)

    error = request.query_params.get('error', False)
    error_description = request.query_params.get('error_description', '')
    if error:
        raise APIException('Google OAuth: ' + error_description)

    state = parse_qs(request.query_params.get('state', None))

    if state['url'] == None:
        raise ValidationException('No callback URL specified', slug='no-callback-url')
    if state['token'] == None:
        raise ValidationException('No user token specified', slug='no-user-token')

    code = request.query_params.get('code', None)
    if code == None:
        raise ValidationException('No google code specified', slug='no-code')

    payload = {
        'client_id': os.getenv('GOOGLE_CLIENT_ID', ''),
        'client_secret': os.getenv('GOOGLE_SECRET', ''),
        'redirect_uri': os.getenv('GOOGLE_REDIRECT_URL', ''),
        'grant_type': 'authorization_code',
        'code': code,
    }
    headers = {'Accept': 'application/json'}
    resp = requests.post('https://oauth2.googleapis.com/token', data=payload, headers=headers)
    if resp.status_code == 200:

        logger.debug('Google responded with 200')

        body = resp.json()
        if 'access_token' not in body:
            raise APIException(body['error_description'])

        logger.debug(body)

        token = Token.get_valid(state['token'][0])
        if not token:
            logger.debug(f'Token {state["token"][0]} not found or is expired')
            raise ValidationException('Token was not found or is expired, please use a different token',
                                      code=404,
                                      slug='token-not-found')

        user = token.user
        refresh = ''
        if 'refresh_token' in body:
            refresh = body['refresh_token']

        CredentialsGoogle.objects.filter(user__id=user.id).delete()
        google_credentials = CredentialsGoogle(
            user=user,
            token=body['access_token'],
            refresh_token=refresh,
            expires_at=timezone.now() + timedelta(seconds=body['expires_in']),
        )
        google_credentials.save()

        return HttpResponseRedirect(redirect_to=state['url'][0] + '?token=' + token.key)

    else:
        logger.error(resp.json())
        raise APIException('Error from google credentials')
