import os, string, logging, urllib.parse, random
from django.contrib.auth.models import User
from django.utils import timezone
from .models import DeviceId, Token, Role, ProfileAcademy
from breathecode.notify.actions import send_email_message
from breathecode.admissions.models import Academy
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
        raise Exception('Missing users')

    for user in users:
        token, created = Token.get_or_create(user, token_type='temporal')

        # returns true or false if the email was send
        return send_email_message(
            'pick_password', user.email, {
                'SUBJECT': 'You asked to reset your password at 4Geeks',
                'LINK': os.getenv('API_URL', '') + f'/v1/auth/password/{token}'
            })

    return True


def resend_invite(token=None, email=None, first_name=None):
    params = {'callback': 'https://admin.breatheco.de'}
    querystr = urllib.parse.urlencode(params)
    url = os.getenv('API_URL', '') + '/v1/auth/member/invite/' + str(token) + '?' + querystr
    send_email_message('welcome', email, {
        'email': email,
        'subject': 'Invitation to join 4Geeks',
        'LINK': url,
        'FIST_NAME': first_name
    })


def server_id():
    key = DeviceId.objects.filter(name='server').values_list('key', flat=True).first()

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


def generate_academy_token(academy_id, force=False):

    academy = Academy.objects.get(id=academy_id)
    academy_user = User.objects.filter(username=academy.slug).first()
    if academy_user is None:
        academy_user = User(username=academy.slug, email=f'{academy.slug}@token.com')
        academy_user.save()

        role = Role.objects.get(slug='academy_token')
        # this profile is for tokens, that is why we need no  email validation status=ACTIVE, role must be academy_token
        # and the email is empty
        profile_academy = ProfileAcademy(user=academy_user, academy=academy, role=role, status='ACTIVE')
        profile_academy.save()

    if force:
        Token.objects.filter(user=academy_user).delete()

    token = Token.objects.filter(user=academy_user).first()
    if token is None:
        token = Token.objects.create(user=academy_user, token_type='permanent')
        token.save()

    return token
