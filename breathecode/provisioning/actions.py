from datetime import datetime
import json
import re
import random
from typing import Optional, TypedDict
from django.utils import timezone
from breathecode.authenticate.models import (CredentialsGithub, GithubAcademyUser, GithubAcademyUserLog,
                                             PendingGithubUser, User)
from breathecode.utils.validation_exception import ValidationException
from breathecode.utils import getLogger
from breathecode.services.github import Github
from breathecode.utils.i18n import translation
from breathecode.admissions.models import Academy, CohortUser
from .models import ProvisioningActivity, ProvisioningBill, ProvisioningProfile, ProvisioningVendor
from django.db.models import QuerySet, Q
from dateutil.relativedelta import relativedelta

logger = getLogger(__name__)


def sync_machine_types(provisioning_academy, assignment):

    gb = Github(token=provisioning_academy.credentials_token, host=provisioning_academy.vendor.api_url)

    asset = Asset.objects.filter(slug=assignment.associated_slug).first()
    org_name, repo_name, branch_name = asset.get_repo_meta()

    machines = gb.get_machines_types(repo_name)
    print(machines)


def get_provisioning_vendor(user_id, profile_academy, cohort):

    academy = profile_academy.academy
    all_profiles = ProvisioningProfile.objects.filter(academy=academy)
    if all_profiles.count() == 0:
        raise Exception(
            f'No provisioning vendors have been found for this academy {academy.name}, please speak with your program manager'
        )

    for_me = all_profiles.filter(members__id=profile_academy.id, cohorts=None)
    if for_me.count() > 1:
        vendors = [f'{p.vendor.name} in profile {p.id}' for p in for_me]
        raise Exception(
            'More than one provisioning vendor found for your profile in this academy, please speak with your program manager: '
            + ','.join(vendors))
    if for_me.count() == 1:
        p_profile = for_me.first()
        return p_profile.vendor

    for_my_cohort = all_profiles.filter(cohorts__id=cohort.id, members=None)
    if for_my_cohort.count() > 1:
        vendors = [f'{p.vendor.name} in profile {p.id}' for p in for_my_cohort]
        raise Exception(
            'More than one provisioning vendor found for your cohort, please speak with your program manager: '
            + ','.join(vendors))
    if for_my_cohort.count() == 1:
        p_profile = for_my_cohort.first()
        return p_profile.vendor

    entire_academy = all_profiles.filter(cohorts=None, members=None)
    if entire_academy.count() > 1:
        vendors = [f'{p.vendor.name} in profile {p.id}' for p in entire_academy]
        raise Exception(
            'More than one provisioning vendor found for the entire academy, please speak with your program manager: '
            + ','.join(vendors))
    if entire_academy.count() == 1:
        p_profile = entire_academy.first()
        return p_profile.vendor

    raise Exception(
        request,
        "We couldn't find any provisioning vendors for you, your cohort or your academy. Please speak with your program manager."
    )


def get_active_cohorts(user):
    now = timezone.now()
    active = CohortUser.objects.filter(user=user, educational_status='ACTIVE', role='STUDENT')
    # only cohorts that end
    cohorts_that_end = active.filter(never_ends=False)
    # also are withing calendar dates and STARTED or FINAL PROJECT
    active_dates = cohorts_that_end.filter(cohort__kickoff_date__gte=now,
                                           cohort__ending_date__lte=now,
                                           cohort__stage__in=['STARTED', 'FINAL_PROJECT'])

    return active_dates


def create_container(user, task, fresh=False, lang='en'):

    cont = ProvisioningContainer.objects.filter(user=user, task_associated_slug=task.slug).first()
    if not fresh and cont is not None:
        raise ValidationException(
            translation(en='There is another container already created for this assignment',
                        es='Hay otro contenedor ya creado para esta asignacion',
                        slug='duplicated-container'))

    # active_cohorts = get_active_cohorts(user)
    credentials = CredentialsGithub.objects.filter(user=user).first()
    if credentials is None:
        raise ValidationException(
            translation(
                en='No github github credentials found, please connect your github account',
                es='No se han encontrado credentials para github, por favor conecta tu cuenta de github',
                slug='no-github-credentials'))

    gb = Github(token=credentials.token, host=provisioning_academy.vendor.api_url)

    asset = Asset.objects.filter(slug=task.associated_slug).first()
    org_name, repo_name, branch_name = asset.get_repo_meta()

    machines = gb.get_machines_types(repo_name)


def iso_to_datetime(iso: str) -> datetime:
    """
    Transform a ISO 8601 format to datetime.

    Usage:

    ```py
    utc_now = timezone.now()

    # equals to datetime.datetime(2022, 3, 21, 2, 51, 55, 068)
    self.bc.datetime.from_iso_string('2022-03-21T07:51:55.068Z')
    ```
    """
    string = re.sub(r'Z$', '', iso)
    date = datetime.fromisoformat(string)
    return timezone.make_aware(date)


class GithubAcademyUserObject(TypedDict):
    storage_status: str
    storage_action: str
    created_at: datetime
    ended_at: datetime


def get_github_academy_user_logs(academy: Academy, username: str,
                                 limit: datetime) -> list[GithubAcademyUserObject]:
    ret = []
    logs = GithubAcademyUserLog.objects.filter(academy_user__username=username,
                                               academy_user__academy=academy,
                                               created_at__lte=limit).order_by('created_at')

    for n in range(len(logs)):
        log = logs[n]

        if n != 0:
            logs[n - 1]['ending_at'] = log.created_at

        obj = {
            'starting_at': log.created_at,
            'ending_at': limit,
            'storage_status': log.storage_status,
            'storage_action': log.storage_action,
        }

        ret.append(obj)

    starts_limit = limit - relativedelta(months=1, weeks=1)
    ret = [x for x in ret if x['ending_at'] < starts_limit]

    return ret


class ActivityContext(TypedDict):
    provisioning_bills: dict[str, ProvisioningBill]
    provisioning_vendors: dict[str, ProvisioningVendor]
    github_academy_user_logs: dict[QuerySet[GithubAcademyUserLog]]
    hash: str
    limit: datetime
    logs: dict[str, list[GithubAcademyUserObject]]


def handle_pending_github_user(username: str, hash: str) -> list[GithubAcademyUser]:
    github_academy_users = []
    now = timezone.now()
    credentials = CredentialsGithub.objects.filter(username=username).first()

    if credentials:
        cohort_users = CohortUser.objects.filter(
            Q(cohort__never_ends=True)
            | Q(cohort__never_ends=False, cohort__ending_date__gte=now),
            cohort__kickoff_date__lte=now,
            user=credentials.user).exclude(stage__in=['ENDED', 'DELETED'])

        academies = {cohort_user.cohort.academy for cohort_user in cohort_users}

    else:
        academies = set()

    if not academies:
        source = 'LINKED' if credentials else 'UNLINKED'
        pending, _ = PendingGithubUser.objects.get_or_create(username=username,
                                                             source=source,
                                                             defaults={
                                                                 'status': 'PENDING',
                                                                 'hashes': [hash]
                                                             })

        if hash not in pending.hashes:
            pending.hashes.append(hash)
            pending.save()

    else:
        for academy in academies:
            pending, _ = PendingGithubUser.objects.get_or_create(username=username,
                                                                 academy=academy,
                                                                 source='COHORT',
                                                                 defaults={
                                                                     'status': 'PENDING',
                                                                     'hashes': [hash]
                                                                 })

            if hash not in pending.hashes:
                pending.hashes.append(hash)
                pending.save()
        # for academy in academies:
        #     github_user, _ = GithubAcademyUser.objects.get_or_create(username=username,
        #                                                              academy=academy,
        #                                                              user=credentials.user,
        #                                                              defaults={
        #                                                                  'storage_status': 'PENDING',
        #                                                                  'storage_action': 'ADD',
        #                                                              })

        #     if github_user.storage_status in ['PENDING', 'SYNCHED'] and github_user.storage_action == 'ADD':
        #         github_academy_users.append(github_user)

    return github_academy_users


def add_codespaces_activity(context: ActivityContext, field: dict):
    github_academy_user_log = context['github_academy_user_logs'].get(field['Username'], None)

    if github_academy_user_log is None:
        # sort by created at
        github_academy_user_log = GithubAcademyUserLog.objects.filter(
            academy_user__username=field['Username'],
            storage_status='SYNCHED',
            storage_action='ADD',
            created_at__lte=context['limit']).order_by('-created_at')

        context['github_academy_user_logs'][field['Username']] = github_academy_user_log

    if not github_academy_user_log:
        academy = handle_pending_github_user(field['Username'], context['hash'])

    if (how_many := len(github_academy_user_log)) == 0:
        logger.error(f'User {field["Username"]} not found in any academy')
        return

    if how_many == 1:
        github_academy_user_log = github_academy_user_log[0]

    else:
        github_academy_user_log = github_academy_user_log[random.randint(0, how_many - 1)]

    academy = github_academy_user_log.academy_user.academy

    logs = context['logs'].get(field['Username'], None)
    if logs is None:
        logs = get_github_academy_user_logs(academy, field['Username'], context['limit'])
        context['logs'][field['Username']] = logs

    provisioning_bill = context['provisioning_bills'].get(academy.id, None)
    if not provisioning_bill:
        provisioning_bill = ProvisioningBill.objects.filter(academy=academy, status='PENDING').first()

    if not provisioning_bill:
        provisioning_bill = ProvisioningBill()
        provisioning_bill.academy = academy
        provisioning_bill.status = 'PENDING'
        provisioning_bill.hash = context['hash']
        provisioning_bill.save()

    provisioning_vendor = context['provisioning_vendors'].get('Codespaces', None)
    if not provisioning_vendor:
        provisioning_vendor = ProvisioningVendor.objects.filter(name='Codespaces').first()

    if not provisioning_vendor:
        raise Exception(f'Provisioning vendor Codespaces not found')

    date = datetime.strptime(field['Date'], '%Y-%m-%d')
    for log in logs:
        if (log['storage_action'] == 'DELETE' and log['storage_status'] == 'SYNCHED'
                and log['starting_at'] <= date <= log['ending_at']):
            logger.error(f'User {field["Username"]} was deleted from the academy during this event at {date}')
            return

    pa = ProvisioningActivity()

    pa.bill = provisioning_bill
    pa.username = field['Username']
    pa.registered_at = date
    pa.product_name = field['Product']
    pa.sku = field['SKU']
    pa.quantity = field['Quantity']
    pa.unit_type = field['Unit Type']
    pa.price_per_unit = field['Price Per Unit ($)']
    pa.currency_code = 'USD'
    pa.multiplier = field['Multiplier']
    pa.repository_url = f"https://github.com/{field['Owner']}/{field['Repository Slug']}"
    pa.task_associated_slug = field['Repository Slug']
    pa.processed_at = timezone.now()
    pa.status = 'PERSISTED'
    pa.save()


def add_gitpod_activity(context: ActivityContext, field: dict):
    try:
        metadata = json.loads(field['metadata'])
    except:
        logger.warning(f'Skipped field with kind {field["kind"]}')
        return

    github_academy_user_log = context['github_academy_user_logs'].get(metadata['userName'], None)

    if github_academy_user_log is None:
        github_academy_user_log = GithubAcademyUserLog.objects.filter(
            academy_user__username=metadata['userName'], storage_status='SYNCHED', storage_action='ADD')

        context['github_academy_user_logs'][metadata['userName']] = github_academy_user_log

    if not github_academy_user_log:
        academy = handle_pending_github_user(metadata['userName'], context['hash'])

    if (how_many := len(github_academy_user_log)) == 0:
        logger.error(f'User {metadata["userName"]} not found in any academy')
        return

    if how_many == 1:
        github_academy_user_log = github_academy_user_log[0]

    else:
        github_academy_user_log = github_academy_user_log[random.randint(0, how_many - 1)]

    academy = github_academy_user_log.academy_user.academy

    logs = context['logs'].get(metadata['userName'], None)
    if logs is None:
        logs = get_github_academy_user_logs(academy, metadata['userName'], context['limit'])
        context['logs'][metadata['userName']] = logs

    pattern = r'^https://github\.com/[^/]+/([^/]+)/?'
    if not (result := re.findall(pattern, metadata['contextURL'])):
        raise Exception(f'Invalid repository URL {metadata["contextURL"]}')

    slug = result[0]

    provisioning_bill = context['provisioning_bills'].get(academy.id, None)
    if not provisioning_bill:
        provisioning_bill = ProvisioningBill.objects.filter(academy=academy, status='PENDING').first()

    if not provisioning_bill:
        provisioning_bill = ProvisioningBill()
        provisioning_bill.academy = academy
        provisioning_bill.status = 'PENDING'
        provisioning_bill.hash = context['hash']
        provisioning_bill.save()

    provisioning_vendor = context['provisioning_vendors'].get('Codespaces', None)
    if not provisioning_vendor:
        provisioning_vendor = ProvisioningVendor.objects.filter(name='Codespaces').first()

    if not provisioning_vendor:
        raise Exception(f'Provisioning vendor Codespaces not found')

    date = iso_to_datetime(field['effectiveTime'])
    for log in logs:
        if (log['storage_action'] == 'DELETE' and log['storage_status'] == 'SYNCHED'
                and log['starting_at'] <= date <= log['ending_at']):
            logger.error(f'User {field["Username"]} was deleted from the academy during this event at {date}')
            return

    pa = ProvisioningActivity()
    pa.bill = provisioning_bill
    pa.username = metadata['userName']
    pa.registered_at = date
    pa.product_name = field['kind']
    pa.sku = field['id']
    pa.quantity = field['creditCents']
    pa.unit_type = 'Credit cents'
    pa.price_per_unit = 0.00036
    pa.currency_code = 'USD'
    pa.repository_url = metadata['contextURL']

    pa.task_associated_slug = slug
    pa.processed_at = timezone.now()
    pa.status = 'PERSISTED'
    pa.save()
