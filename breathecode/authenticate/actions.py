import os, string, logging, urllib.parse, random
from django.contrib.auth.models import User, Group
from django.utils import timezone
from .models import DeviceId, Token, CredentialsSlack, UserInvite
from breathecode.notify.actions import send_email_message
from random import randint

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
    token, created = Token.objects.get_or_create(user=user,
                                                 token_type="temporal",
                                                 expires_at=expires_at)
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
    from breathecode.notify.actions import send_email_message
    if users is None or len(users) == 0:
        raise Exception("Missing users")

    for user in users:
        token = Token.create_temp(user)

        # returns true or false if the email was send
        return send_email_message(
            'pick_password', user.email, {
                "SUBJECT": "You asked to reset your password at BreatheCode",
                "LINK": os.getenv('API_URL', '') + f"/v1/auth/password/{token}"
            })

    return True


def resend_invite(token=None, email=None, first_name=None):
    params = {"callback": "https://admin.breatheco.de"}
    querystr = urllib.parse.urlencode(params)
    url = os.getenv(
        'API_URL',
        '') + "/v1/auth/member/invite/" + str(token) + "?" + querystr
    send_email_message(
        "welcome_academy", email, {
            "email": email,
            "subject": "Invitation",
            "LINK": url,
            "FIST_NAME": first_name
        })


def server_id():
    key = DeviceId.objects.filter(name='server').values_list(
        'key', flat=True).first()

    if key:
        return key

    n1 = str(randint(0, 100))
    n2 = str(randint(0, 100))
    n3 = str(randint(0, 100))

    letters = string.ascii_lowercase
    s1 = ''.join(random.choice(letters) for i in range(2))
    s2 = ''.join(random.choice(letters) for i in range(2))
    s3 = ''.join(random.choice(letters) for i in range(2))

    key = f'{n1}{s1}.{n2}{s2}.{n3}{s3}'

    device = DeviceId(name='server', key=key)
    device.save()

    return key
