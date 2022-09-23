import os, string, logging, urllib.parse, random, re, datetime
from django.contrib.auth.models import User
from django.utils import timezone
from .models import DeviceId, Token, Role, ProfileAcademy, GitpodUser, CredentialsGithub
from breathecode.notify.actions import send_email_message
from breathecode.utils import ValidationException
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
    params = {'callback': 'https://admin.4geeks.com'}
    querystr = urllib.parse.urlencode(params)
    url = os.getenv('API_URL', '') + '/v1/auth/member/invite/' + str(token) + '?' + querystr
    send_email_message('welcome_academy', email, {
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


def set_gitpod_user_expiration(gitpoduser_id):

    gitpod_user = GitpodUser.objects.filter(id=gitpoduser_id).first()
    if gitpod_user is None:
        raise Exception(f'Invalid gitpod user id: {gitpoduser_id}')

    # If no user is connected, find the user on breathecode by searching the github credentials
    if gitpod_user.user is None:
        github_user = CredentialsGithub.objects.filter(username=gitpod_user.github_username).first()
        if github_user is not None:
            gitpod_user.user = github_user.user

    if gitpod_user.user is not None:
        # find last cohort
        cu = gitpod_user.user.cohortuser_set.filter(educational_status__in=['ACTIVE'],
                                                    cohort__never_ends=False,
                                                    cohort__stage__in=[
                                                        'PREWORK', 'STARTED', 'FINAL_PROJECT'
                                                    ]).order_by('-cohort__ending_date').first()
        if cu is not None:
            gitpod_user.expires_at = cu.cohort.ending_date + datetime.timedelta(
                days=14) if cu.cohort.ending_date is not None else None
            gitpod_user.academy = cu.cohort.academy
            gitpod_user.target_cohort = cu.cohort
            gitpod_user.delete_status = f'User will be deleted 14 days after cohort {cu.cohort.name} finishes on {cu.cohort.ending_date}'
        else:
            # if no active academy was found, at least we can retreive the latest one to asociate the user to an academy
            last_cohort = gitpod_user.user.cohortuser_set.all().order_by('-cohort__ending_date').first()
            if last_cohort is not None:
                gitpod_user.academy = last_cohort.cohort.academy
                gitpod_user.target_cohort = last_cohort.cohort
                gitpod_user.delete_status = f'It will be deleted soon because no active cohort was found, the last one it had active was ' + last_cohort.cohort.name

    if gitpod_user.user is None or gitpod_user.expires_at is None:
        gitpod_user.expires_at = timezone.now() + datetime.timedelta(days=3)
        gitpod_user.delete_status = 'User will be deleted because no active cohort could be associated to it, please set a cohort if you want to avoid deletion'

    if gitpod_user.user is not None:
        conflict = GitpodUser.objects.filter(user=gitpod_user.user).first()
        if conflict is not None:
            if conflict.assignee_id != gitpod_user.assignee_id:
                return None
            else:
                if conflict.expires_at is None:
                    conflict.expires_at = gitpod_user.expires_at
                    conflict.target_cohort = gitpod_user.target_cohort
                    conflict.academy = gitpod_user.academy
                    conflict.delete_status = gitpod_user.delete_status
                    conflict.save()

    gitpod_user.save()
    return gitpod_user


def update_gitpod_users(html):
    all_active_users = []
    all_inactive_users = []
    all_usernames = []
    findings = list(re.finditer(r'<div\sclass="flex\sflex-grow\sflex-row\sspace-x-2">(.*?)<\/div>', html))

    position = 0
    while len(findings) > 0:
        position += 1
        user = {'position': position}
        match = findings.pop(0)
        input_html = html[match.start():match.end()]

        matches = list(re.finditer('>Reactivate<', input_html))
        if len(matches) > 0:
            all_inactive_users.append(user)
            continue

        matches = list(re.finditer('"assignee-([\w\-]+)"', input_html))
        if len(matches) > 0:
            match = matches.pop(0)
            user['assignee'] = match.group(1)

        matches = list(re.finditer('github\.com\/([\w\-]+)"', input_html))
        if len(matches) > 0:
            match = matches.pop(0)
            user['github'] = match.group(1)

            logger.debug('Found active user ' + user['github'])

            if user['github'] == "username" or user['github'] == "":
                continue
                
            if user['github'] in all_usernames:
                raise ValidationException(f"Error: user '{user['github']}' seems to be duplicated on the incoming list from Gitpod", slug="duplicated-user")

            all_usernames.append(user['github'])
            all_active_users.append(user)

    GitpodUser.objects.exclude(github_username__in=all_usernames).delete()
    for user in all_active_users:

        # create if not exists
        gitpod_user = GitpodUser.objects.filter(github_username=user['github']).first()
        if gitpod_user is None:
            gitpod_user = GitpodUser(github_username=user['github'],
                                     position_in_gitpod_team=user['position'],
                                     assignee_id=user['assignee'])
            gitpod_user.save()

        if set_gitpod_user_expiration(gitpod_user.id) is None:
            raise Exception(
                f'Gitpod user {user["github"]} could not be processed, maybe its duplicated or another user is incorrectly assigned to the Gitpod account'
            )

    return {'active': all_active_users, 'inactive': all_inactive_users}
