import os, requests, base64, logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.http import HttpResponseRedirect, HttpResponse
from django.conf import settings
from rest_framework.exceptions import APIException, ValidationError, PermissionDenied
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from django.contrib.auth.models import User, Group, AnonymousUser
from breathecode.authenticate.models import CredentialsGithub
from breathecode.authenticate.serializers import UserSerializer, AuthSerializer, GroupSerializer
from rest_framework.authtoken.views import ObtainAuthToken
from urllib.parse import urlencode

logger = logging.getLogger('authenticate')

class CustomAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = AuthSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
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

# Create your views here.
@api_view(['GET'])
def get_groups(request):
    queryset = Group.objects.all()
    groups = GroupSerializer(queryset, many=True)
    return Response(groups.data)

# Create your views here.
@api_view(['GET'])
@permission_classes([AllowAny])
def get_github_token(request):
    url = request.query_params.get('url', None)
    if url == None:
        raise ValidationError("No callback URL specified")

    url = base64.b64decode(url).decode("utf-8")
    params = {
        "client_id": os.getenv('GITHUB_CLIENT_ID'),
        "redirect_uri": os.getenv('GITHUB_REDIRECT_URL')+"?url="+url,
        "scope": 'user repo read:org',
    }

    redirect = 'https://github.com/login/oauth/authorize?'+urlencode(params)
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
        'client_id': os.getenv('GITHUB_CLIENT_ID'),
        'client_secret': os.getenv('GITHUB_SECRET'),
        'redirect_uri': os.getenv('GITHUB_REDIRECT_URL'),
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
            print(github_user)
            if github_user['email'] is None:
                resp = requests.get('https://api.github.com/user/emails', headers={'Authorization': 'token '+github_token })
                if resp.status_code == 200:
                    emails = resp.json()
                    primary_emails = [x for x in emails if x["primary"] == True]
                    github_user['email'] = primary_emails[0]

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

            token, created = Token.objects.get_or_create(user=user)

            return HttpResponseRedirect(redirect_to=url+'?token='+token.key)
        else:
            print("Github error: ", resp.status_code)
            print("Error: ", resp.json())
            raise APIException("Error from github")
