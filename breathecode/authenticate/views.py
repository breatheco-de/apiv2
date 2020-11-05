import os, requests, base64, logging
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth import update_session_auth_hash
from rest_framework.response import Response
from django.http import HttpResponseRedirect, HttpResponse
from django.conf import settings
from rest_framework.exceptions import APIException, ValidationError, PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status, serializers
from django.contrib.auth.models import User, Group, AnonymousUser
from django.contrib import messages
from rest_framework.authtoken.views import ObtainAuthToken
from urllib.parse import urlencode, parse_qs
from django.shortcuts import render
from django.http import HttpResponseRedirect
from rest_framework.views import APIView
from django.utils import timezone
from .models import Profile
from .authentication import ExpiringTokenAuthentication

from .forms import PickPasswordForm, PasswordChangeCustomForm
from .models import Profile, CredentialsGithub, Token, CredentialsSlack
from breathecode.admissions.models import Academy
from breathecode.notify.models import SlackTeam
from .serializers import UserSerializer, AuthSerializer, GroupSerializer

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
    authentication_classes: [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        Token.objects.filter(token_type='login').delete()
        request.auth.delete()
        return Response({
            'message': "User tokens successfully deleted",
        })

class LoginView(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        # delete expired tokens
        utc_now = timezone.now()
        Token.objects.filter(expires_at__lt=utc_now).delete()

        serializer = AuthSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user, token_type="login")
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'email': user.email
        })

@api_view(['GET'])
def get_users_me(request):

    logger.error("Get me just called")
    try:
        if isinstance(request.user, AnonymousUser):
            raise PermissionDenied("There is not user")    
        request.user
    except User.DoesNotExist:
        raise PermissionDenied("You don't have a user")

    users = UserSerializer(request.user)
    return Response(users.data)

# Create your views here.
@api_view(['GET'])
def get_users(request):
    queryset = User.objects.all().order_by('-date_joined')
    users = UserSerializer(queryset, many=True)
    return Response(users.data)

# # Create your views here.
# @api_view(['GET'])
# def get_groups(request):
#     queryset = Group.objects.all()
#     groups = GroupSerializer(queryset, many=True)
#     return Response(groups.data)

# Create your views here.
@api_view(['GET'])
@permission_classes([AllowAny])
def get_github_token(request):
    url = request.query_params.get('url', None)
    if url == None:
        raise ValidationError("No callback URL specified")

    # url = base64.b64decode(url).decode("utf-8")
    params = {
        "client_id": os.getenv('GITHUB_CLIENT_ID', ""),
        "redirect_uri": os.getenv('GITHUB_REDIRECT_URL', "")+"?url="+url,
        "scope": 'user repo read:org',
    }

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

    error = request.query_params.get('error', False)
    error_description = request.query_params.get('error_description', '')
    if error:
        raise APIException("Github: "+error_description)

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
    resp = requests.post('https://github.com/login/oauth/access_token', data=payload, headers=headers)
    if resp.status_code == 200:

        logger.debug("Github responded with 200")

        body = resp.json()
        if 'access_token' not in body:
            raise APIException(body['error_description'])

        github_token = body['access_token']
        resp = requests.get('https://api.github.com/user', headers={'Authorization': 'token '+github_token })
        if resp.status_code == 200:
            github_user = resp.json()
            logger.debug(github_user)
            if github_user['email'] is None:
                resp = requests.get('https://api.github.com/user/emails', headers={'Authorization': 'token '+github_token })
                if resp.status_code == 200:
                    emails = resp.json()
                    primary_emails = [x for x in emails if x["primary"] == True]
                    if len(primary_emails) > 0:
                        github_user['email'] = primary_emails[0]["email"]
                    elif len(emails) > 0:
                        github_user['email'] = emails[0]["email"]

            if github_user['email'] is None:
                raise ValidationError("Imposible to retrieve user email")
                
            user = User.objects.filter(email=github_user['email']).first()
            if user is None:
                user = User(username=github_user['login'], email=github_user['email'])
                user.save()

            CredentialsGithub.objects.filter(github_id=github_user['id']).delete()
            github_credentials = CredentialsGithub(
                github_id = github_user['id'],
                user=user,
                token = github_token,
                email = github_user['email'],
                avatar_url = github_user['avatar_url'],
                name = github_user['name'],
                blog = github_user['blog'],
                bio = github_user['bio'],
                company = github_user['company'],
                twitter_username = github_user['twitter_username']
            )
            github_credentials.save()

            profile = Profile.objects.filter(user__email=github_user['email']).first()
            if profile is None:
                profile = Profile(user=user, 
                    avatar_url=github_user['avatar_url'],
                    blog=github_user['blog'],
                    bio=github_user['bio'],
                    twitter_username=github_user['twitter_username']
                )
                profile.save()

            token, created = Token.objects.get_or_create(user=user, token_type='login')

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
        raise APIException("Slack: "+ error_description)

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

        # delete all previous credentials for the same team
        CredentialsSlack.objects.filter(app_id=slack_data['app_id'], team_id=slack_data['team']['id']).delete()
        credentials = CredentialsSlack(
            user=user,
            app_id = slack_data['app_id'],
            bot_user_id = slack_data['bot_user_id'],
            token = slack_data['access_token'],
            team_id = slack_data['team']['id'],
            team_name = slack_data['team']['name'],
            authed_user = slack_data['authed_user']['id'],
        )
        credentials.save()

        team = SlackTeam.objects.filter(slack_id=slack_data['team']['id']).first()
        if team is None:
            team = SlackTeam(slack_id = slack_data['team']['id'])

        team.name = slack_data['team']['name'],
        team.owner = user    
        team.academy = academy    
        team.credentials = credentials    
        team.save()

        return HttpResponseRedirect(redirect_to=payload["url"][0])


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
        # print("Github error: ", resp.status_code)
        # print("Error: ", resp.json())
        raise APIException("Error from github")

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
                return HttpResponseRedirect(request.POST.get("callback"))
            else:
                return render(request, 'message.html', {
                    'message': 'You password has been reset successfully, you can close this window.'
                })

    return render(request, 'form.html', {
        'form': form
    })