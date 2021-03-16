import os, requests, logging, urllib.parse
from django.contrib.auth.models import User, Group
from django.utils import timezone
from .models import Token, CredentialsSlack, UserInvite
from breathecode.notify.actions import send_email_message

logger = logging.getLogger(__name__)

def get_user(github_id=None, email=None):
    user = None
    if email is not None:
        user = User.objects.get(email=email)
    return user

def create_user(github_id=None, email=None):
    user = None
    if email is not None:
        user = User.objects.get(email=email)
    return user

def create_token(user, hours_length=1):
    utc_now = timezone.now()
    expires_at = utc_now + timezone.timedelta(hours=hours_length)
    token, created = Token.objects.get_or_create(user=user, token_type="temporal", expires_at=expires_at)
    return token

def delete_tokens(users=None, status='expired'):
    now = timezone.now()
    
    tokens = Token.objects.all()
    if users is not None:
        tokens = tokens.filter(user__id__in=[users])
    if status == 'expired':
        tokens = Token.objects.filter(expires_at__lt=now)

    count = len(tokens)
    tokens.delete()
    return count

def reset_password(users=None):

    if users is None or len(users) == 0:
        raise Exception("Missing users")

    for user in users:
        token = Token.create_temp(user)

        # returns true or false if the email was send
        return send_email_message('pick_password', user.email, {
            "SUBJECT": "You asked to reset your password at BreatheCode",
            "LINK": os.getenv('API_URL','') + f"/v1/auth/password/{token}"
        })
    
    return True

def resend_invite(token=None,email=None, first_name=None ):
    params = { "callback": "https://admin.breatheco.de" }
    querystr = urllib.parse.urlencode(params)
    url = os.getenv('API_URL', '') + "/v1/auth/user/invite/" + str(token) + "?" + querystr
    send_email_message("welcome_academy",email, {
                "email": email,
                "subject": "Invitation",
                "LINK": url,
                "FIST_NAME": first_name
            })