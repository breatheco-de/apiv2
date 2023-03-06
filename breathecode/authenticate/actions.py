import datetime
import logging
import os
import random
import re
import string
import urllib.parse
from random import randint
from django.core.handlers.wsgi import WSGIRequest

from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Q
from breathecode.admissions.models import Academy, CohortUser
from breathecode.notify.actions import send_email_message
from breathecode.utils import ValidationException
from breathecode.utils.i18n import translation
from breathecode.services.github import Github

from .models import (CredentialsGithub, DeviceId, GitpodUser, ProfileAcademy, Role, Token, UserSetting,
                     AcademyAuthSettings, GithubAcademyUser)

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

    # reset status, i don't want to override this value if already set in this function
    gitpod_user.delete_status = ''
    gitpod_user.target_cohort = None

    logger.debug(f'Gitpod user: {gitpod_user.id}')
    # If no user is connected, find the user on breathecode by searching the github credentials
    if gitpod_user.user is None:
        github_user = CredentialsGithub.objects.filter(username=gitpod_user.github_username).first()
        if github_user is not None:
            gitpod_user.user = github_user.user

    if gitpod_user.user is not None:
        # find last cohort
        cu = gitpod_user.user.cohortuser_set.filter(
            educational_status__in=['ACTIVE'],
            cohort__never_ends=False,
            cohort__stage__in=['PREWORK', 'STARTED',
                               'FINAL_PROJECT']).order_by('-cohort__ending_date').first()
        if cu is not None:
            gitpod_user.expires_at = cu.cohort.ending_date + datetime.timedelta(
                days=14) if cu.cohort.ending_date is not None else None
            gitpod_user.academy = cu.cohort.academy
            gitpod_user.target_cohort = cu.cohort
            gitpod_user.delete_status = f'User will be deleted 14 days after cohort {cu.cohort.name} finishes on {cu.cohort.ending_date}'
        else:
            # if no active academy was found, at least we can retreive the latest one to asociate the user to an academy
            last_cohort = gitpod_user.user.cohortuser_set.filter(
                cohort__never_ends=False).order_by('-cohort__ending_date').first()
            if last_cohort is not None:
                gitpod_user.academy = last_cohort.cohort.academy
                gitpod_user.target_cohort = last_cohort.cohort
                gitpod_user.delete_status = f'It will be deleted soon because no active cohort was found, the last one it had active was ' + last_cohort.cohort.name

    if (gitpod_user.user is None or gitpod_user.expires_at is None) and gitpod_user.delete_status == '':
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

            if user['github'] == 'username' or user['github'] == '':
                continue

            if user['github'] in all_usernames:
                raise ValidationException(
                    f"Error: user '{user['github']}' seems to be duplicated on the incoming list from Gitpod",
                    slug='duplicated-user')

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


def get_user_settings(user_id: int) -> UserSetting:
    from breathecode.admissions.models import CohortUser
    from breathecode.assessment.models import Assessment, Question, UserAssessment
    from breathecode.events.models import Event
    from breathecode.marketing.models import FormEntry
    from breathecode.feedback.models import Answer

    settings, created = UserSetting.objects.get_or_create(user_id=user_id)

    if created and (cohort_user :=
                    CohortUser.objects.filter(user__id=user_id).exclude(cohort__language='').first()):
        created = False
        settings.lang = cohort_user.cohort.language
        settings.save()

    if created and (lead := FormEntry.objects.filter(
            email=user_id, browser_lang__isnull=False).exclude(browser_lang='').first()):
        try:
            settings.lang = lead.browser_lang
            settings.save()
            created = False
        except:
            ...

    # if created and (contact := Contact.objects.filter(author__id=user_id,
    #                                                   lang__isnull=False).exclude(lang='').first()):
    #     created = False
    #     settings.lang = contact.language
    #     settings.save()

    if created and (assessment := Assessment.objects.filter(author__id=user_id,
                                                            lang__isnull=False).exclude(lang='').first()):
        created = False
        settings.lang = assessment.lang
        settings.save()

    if created and (answer := Answer.objects.filter(user__id=user_id,
                                                    lang__isnull=False).exclude(lang='').first()):
        created = False
        settings.lang = answer.lang
        settings.save()

    if created and (event := Event.objects.filter(author__id=user_id,
                                                  lang__isnull=False).exclude(lang='').first()):
        created = False
        settings.lang = event.lang
        settings.save()

    if created and (user_assessment := UserAssessment.objects.filter(
            owner__id=user_id, lang__isnull=False).exclude(lang='').first()):
        created = False
        settings.lang = user_assessment.lang
        settings.save()

    if created and (question := Question.objects.filter(author__id=user_id,
                                                        lang__isnull=False).exclude(lang='').first()):
        created = False
        settings.lang = question.lang
        settings.save()

    return settings


def get_user_language(request: WSGIRequest):
    lang = request.META.get('HTTP_ACCEPT_LANGUAGE')

    if not lang and request.user.id:
        settings = get_user_settings(request.user.id)
        lang = settings.lang

    if not lang:
        lang = 'en'

    return lang


def add_to_organization(cohort_id, user_id):

    cohort_user = CohortUser.objects.filter(cohort__id=cohort_id, user__id=user_id).first()
    if cohort_user is None:
        raise ValidationException(translation(
            en=f'User {user_id} does not belong to cohort {cohort_id}',
            es=f'El usuario {user_id} no pertenece a esta cohort {cohort_id}'),
                                  slug='invalid-cohort-user')

    academy = cohort_user.cohort.academy
    user = cohort_user.user

    try:
        github_user = GithubAcademyUser.objects.filter(user=user, academy=academy).first()
        if github_user is None:
            github_user = GithubAcademyUser(academy=academy,
                                            user=user,
                                            storage_status='PENDING',
                                            storage_action='ADD',
                                            storage_synch_at=timezone.now())
            github_user.save()

        if github_user.storage_status == 'SYNCHED' and github_user.storage_action == 'ADD':
            # user already added
            github_user.log(f'User was already added')
            return True

        github_user.storage_status = 'PENDING'
        github_user.storage_action = 'ADD'
        github_user.log(f'Scheduled to add to organization because in cohort={cohort_user.cohort.slug}')
        github_user.save()
        return True
    except Exception as e:
        github_user.log(str(e))
        github_user.save()
        return False


def remove_from_organization(cohort_id, user_id):

    logger.debug(f'Removing user {user_id} from organization')
    cohort_user = CohortUser.objects.filter(cohort__id=cohort_id, user__id=user_id).first()
    if cohort_user is None:
        raise ValidationException(translation(
            en=f'User {user_id} does not belong to cohort {cohort_id}',
            es=f'El usuario {user_id} no pertenece a esta cohort {cohort_id}'),
                                  slug='invalid-cohort-user')
    academy = cohort_user.cohort.academy
    user = cohort_user.user
    github_user = GithubAcademyUser.objects.filter(user=user, academy=academy).first()
    try:

        active_cohorts_in_academy = CohortUser.objects.filter(user=user,
                                                              cohort__academy=academy,
                                                              educational_status='ACTIVE').first()
        if active_cohorts_in_academy is not None:
            raise ValidationException(translation(
                en=
                f'Cannot remove user={user.id} from organization because edu_status is ACTIVE in {active_cohorts_in_academy.cohort.slug}',
                es=
                f'No se pudo remover usuario id={user.id} de la organization su edu_status=ACTIVE en cohort={active_cohorts_in_academy.cohort.slug}'
            ),
                                      slug='still-active')

        if github_user is None:
            raise ValidationException(translation(
                en=
                f'Cannot remove user id={user.id} from organization because it was not found on its list of current members',
                es=
                f'No se pudo remover usuario id={user.id} de la organization porque no se encontro en su lista de miembros'
            ),
                                      slug='user-not-found-in-org')

        github_user.storage_status = 'PENDING'
        github_user.storage_action = 'DELETE'
        github_user.log(
            f'Scheduled to remove from organization because edu_status={cohort_user.educational_status} in cohort={cohort_user.cohort.slug}'
        )
        github_user.save()
        return True
    except Exception as e:
        if github_user is None:
            raise e

        github_user.log(str(e))
        github_user.save()
        return False


def sync_organization_members(academy_id, only_status=[]):

    now = timezone.now()

    settings = AcademyAuthSettings.objects.filter(academy__id=academy_id).first()
    if settings is None or not settings.github_is_sync:
        return False

    siblings = AcademyAuthSettings.objects.filter(github_username=settings.github_username)
    without_sync_active = list(siblings.filter(github_is_sync=False).values_list('academy__slug', flat=True))
    academy_slugs = list(siblings.values_list('academy__slug', flat=True))
    if len(without_sync_active) > 0:
        raise ValidationException(translation(
            en=
            f"All organizations with the same username '{settings.github_username}' must activate with github synch before starting to sync members: {', '.join(without_sync_active)}",
            es=
            f"Todas las organizaciones con el mismo username '{settings.github_username}' deben tener github_synch activo para poder empezar la sincronizacion: {','.join(without_sync_active)}"
        ),
                                  slug='not-everyone-in-synch')

    credentials = CredentialsGithub.objects.filter(user=settings.github_owner).first()
    if settings.github_owner is None or credentials is None:
        raise ValidationException(translation(
            en=f'Organization has no owner or it has no github credentials',
            es=f'La organizacion no tiene dueño o no este tiene credenciales para github'),
                                  slug='invalid-owner')

    # print('Procesing following slugs', academy_slugs)
    # retry errored users
    GithubAcademyUser.objects.filter(academy__slug__in=academy_slugs,
                                     storage_status='ERROR')\
                        .update(storage_status='PENDING', storage_synch_at=None)

    # users without github credentials are marked as error
    no_github_credentials = GithubAcademyUser.objects.filter(academy__slug__in=academy_slugs,
                                                             user__credentialsgithub__isnull=True)
    print('no_github_credentials', [u.id for u in no_github_credentials])
    no_github_credentials.update(
        storage_status='ERROR',
        storage_log=[GithubAcademyUser.create_log('This user needs connect to github')])

    gb = Github(org=settings.github_username, token=settings.github_owner.credentialsgithub.token)
    members = gb.get_org_members()

    remaining_usernames = set([m['login'] for m in members])

    org_users = GithubAcademyUser.objects.filter(academy__slug__in=academy_slugs)

    # if we only want to process a particular storage_action, E.g: ADD
    if len(only_status) > 0:
        org_users = org_users.filter(storage_action__in=only_status)

    for _member in org_users:
        github = CredentialsGithub.objects.filter(user=_member.user).first()
        if _member.storage_status in ['PENDING'] and _member.storage_action in ['ADD', 'INVITE']:
            if github.username in remaining_usernames:
                _member.log('User was already added to github')
                _member.storage_status = 'SYNCHED'
                # chage action to ADD just in case it was INVITE (its a confirmation)
                _member.storage_action = 'ADD'
                _member.storage_synch_at = now
                _member.save()
            else:

                teams = []
                if settings.github_default_team_ids != '':
                    teams = [int(id) for id in settings.github_default_team_ids.split(',')]

                gb.invite_org_member(github.email, team_ids=teams)
                _member.storage_status = 'SYNCHED'
                _member.log(f'Sent invitation to {github.email}')
                _member.storage_action == 'INVITE'
                _member.storage_synch_at = now
                _member.save()

        if _member.storage_status in ['PENDING'] and _member.storage_action == 'DELETE':
            if github.username not in remaining_usernames:
                _member.log('User was already deleted from github')
                _member.storage_status = 'SYNCHED'
                _member.storage_synch_at = now
                _member.save()
            else:
                added_elsewere = GithubAcademyUser.objects.filter(
                    Q(user=_member.user)
                    | Q(username=github.username)).filter(academy__slug__in=academy_slugs).exclude(
                        storage_status__in=['DELETE']).exclude(id=_member.id).first()
                if added_elsewere is None:
                    gb.delete_org_member(github.username)
                    _member.log('Successfully deleted in github organization')
                else:
                    _member.log(
                        f"User belongs to another academy '{added_elsewere.academy.slug}', it will have to be marked as deleted there before it can be deleted from github organization"
                    )
                _member.storage_status = 'SYNCHED'
                _member.storage_synch_at = now
                _member.save()

        github_username = github.username if github is not None else ''
        remaining_usernames = set(
            [username for username in remaining_usernames if username != github_username])

    print('remaining_usernames', remaining_usernames)
    # there are some users from github we could not find in the cohorts
    for u in remaining_usernames:
        _user = CredentialsGithub.objects.filter(username=u).first()
        if _user is not None:
            _user = _user.user

        # we look if the user is present in this particular academy, not from academy_slugs because we do want
        # to duplicate this users per academy, that way each academy can decide if wants to delete or not
        # you should see in the code for deletion that users will only be deleted if all the academies for
        # the same organization delete it
        _query = GithubAcademyUser.objects.filter(academy=settings.academy).filter(username=u)
        if _user is not None:
            _query = _query.filter(user=_user)
        uknown_user = _query.first()

        if uknown_user is None:
            uknown_user = GithubAcademyUser(academy=settings.academy,
                                            user=_user,
                                            username=u,
                                            storage_status='UNKNOWN',
                                            storage_action='IGNORE',
                                            storage_synch_at=now)
            uknown_user.save()

        uknown_user.storage_status = 'UNKNOWN'
        uknown_user.storage_action = 'IGNORE'
        uknown_user.storage_synch_at = now
        uknown_user.log(
            "This user is coming from github, we don't know if its a student from your academy or if it should be added or deleted, keep it as IGNORED to avoid deletion",
            reset=True)
        uknown_user.save()

    return True


# def invite_org_member(academy_id, org_member_id):

#     settings = AcademyAuthSettings.objects.filter(academy__id=academy_id).first()
#     if settings is None or not settings.github_is_sync:
#         return False

#     _member = GithubAcademyUser.objects.filter(id=org_member_id)
#     if _member is None or _member.storage_status != 'PENDING' and _member.storage_action != 'INVITE':
#         # no need to invite
#         return False

#     gb = Github(org=settings.github_username, token=settings.github_owner.credentialsgithub.token)

#     teams = []
#     if settings.github_default_team_ids != "":
#         teams = [int(id) for id in settings.github_default_team_ids.split(',')]

#     resp = gb.invite_org_member(_member.credentialsgithub.email, team_ids=teams)
#     if resp.status_code == 200:
#         _member.storage_status = 'SYNCHED'
#         _member.log('Invited to github organization')
#         _member.save()
#         return True

#     else:
#         _member.storage_status = 'ERROR'
#         _member.log('Error inviting member to organization')
#         _member.save()
#         return False
