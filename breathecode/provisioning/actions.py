from datetime import datetime
import json
import re
import random
from typing import Optional, TypedDict
from django.utils import timezone
from breathecode.authenticate.models import (AcademyAuthSettings, CredentialsGithub, GithubAcademyUser,
                                             GithubAcademyUserLog, ProfileAcademy)
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
    logs = GithubAcademyUserLog.objects.filter(Q(valid_until__isnull=True)
                                               | Q(valid_until__gte=limit - relativedelta(months=1, weeks=1)),
                                               academy_user__username=username,
                                               academy_user__academy=academy).order_by('created_at')

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
    github_academy_user_logs: dict[str, QuerySet[GithubAcademyUserLog]]
    hash: str
    limit: datetime
    logs: dict[str, list[GithubAcademyUserObject]]
    profile_academies: dict[str, QuerySet[ProfileAcademy]]


def handle_pending_github_user(organization: str, username: str) -> list[Academy]:
    orgs = AcademyAuthSettings.objects.filter(github_username__iexact=organization)
    if not orgs:
        logger.error(f'Organization {organization} not found')
        return []

    user = None
    credentials = CredentialsGithub.objects.filter(username__iexact=username).first()
    if credentials:
        user = credentials.user

    for org in orgs:
        pending, created = GithubAcademyUser.objects.get_or_create(username=username,
                                                                   academy=org.academy,
                                                                   user=user,
                                                                   defaults={
                                                                       'storage_status': 'PAYMENT_CONFLICT',
                                                                       'storage_action': 'IGNORE',
                                                                   })

        if not created:
            pending.storage_status = 'PAYMENT_CONFLICT'
            pending.storage_action = 'IGNORE'
            pending.save()

    return [org.academy for org in orgs]


def add_codespaces_activity(context: ActivityContext, field: dict) -> None:

    def write_activity(academy: Optional[Academy] = None) -> None:
        errors = []
        provisioning_bill = None

        if academy:
            logs = context['logs'].get(field['Username'], None)
            if logs is None:
                logs = get_github_academy_user_logs(academy, field['Username'], context['limit'])
                context['logs'][field['Username']] = logs

        if academy:
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
            errors.append(f'Provisioning vendor Codespaces not found')

        date = datetime.strptime(field['Date'], '%Y-%m-%d')
        if academy:
            for log in logs:
                if (log['storage_action'] == 'DELETE' and log['storage_status'] == 'SYNCHED'
                        and log['starting_at'] <= date <= log['ending_at']):
                    errors.append(
                        f'User {field["Username"]} was deleted from the academy during this event at {date}')

        else:
            errors.append(f'User {field["Username"]} not found in any academy')

        pa = ProvisioningActivity()

        pa.bill = provisioning_bill
        pa.hash = context['hash']
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
        pa.status = 'PERSISTED' if not errors else 'ERROR'
        pa.status_text = ', '.join(errors)
        pa.save()

    github_academy_user_log = context['github_academy_user_logs'].get(field['Username'], None)
    not_found = False
    academies = []

    if github_academy_user_log is None:
        github_academy_user_log = GithubAcademyUserLog.objects.filter(
            Q(valid_until__isnull=True)
            | Q(valid_until__gte=context['limit'] - relativedelta(months=1, weeks=1)),
            created_at__lte=context['limit'],
            academy_user__username=field['Username'],
            storage_status='SYNCHED',
            storage_action='ADD').order_by('-created_at')

        context['github_academy_user_logs'][field['Username']] = github_academy_user_log

    if github_academy_user_log:
        academies = [x.academy_user.academy for x in github_academy_user_log]

    if not academies:
        not_found = True
        github_academy_users = GithubAcademyUser.objects.filter(username=field['Username'],
                                                                storage_status='PAYMENT_CONFLICT',
                                                                storage_action='IGNORE')

        academies = [x.academy for x in github_academy_users]

    if not academies:
        academies = handle_pending_github_user(field['Owner'], field['Username'])

    if not not_found:
        academies = random.choices(academies, k=1)

    if not academies:
        write_activity()
        return

    for academy in academies:
        write_activity(academy)


def add_gitpod_activity(context: ActivityContext, field: dict):

    def write_activity(academy: Optional[Academy] = None):
        errors = []
        if not academy:
            errors.append(f'User {metadata["userName"]} not found in any academy')

        pattern = r'^https://github\.com/[^/]+/([^/]+)/?'
        if not (result := re.findall(pattern, metadata['contextURL'])):
            errors.append(f'Invalid repository URL {metadata["contextURL"]}')
            slug = 'unknown'

        else:
            slug = result[0]

        provisioning_bill = None
        if academy:
            provisioning_bill = context['provisioning_bills'].get(academy.id, None)

        if academy and not provisioning_bill:
            provisioning_bill = ProvisioningBill.objects.filter(academy=academy, status='PENDING').first()

        if academy and not provisioning_bill:
            provisioning_bill = ProvisioningBill()
            provisioning_bill.academy = academy
            provisioning_bill.status = 'PENDING'
            provisioning_bill.hash = context['hash']
            provisioning_bill.save()

        provisioning_vendor = context['provisioning_vendors'].get('Codespaces', None)
        if not provisioning_vendor:
            provisioning_vendor = ProvisioningVendor.objects.filter(name='Codespaces').first()

        if not provisioning_vendor:
            errors.append(f'Provisioning vendor Codespaces not found')

        date = iso_to_datetime(field['effectiveTime'])

        pa = ProvisioningActivity()
        pa.bill = provisioning_bill
        pa.hash = context['hash']
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
        pa.status = 'PERSISTED' if not errors else 'ERROR'
        pa.status_text = ', '.join(errors)
        pa.save()

    try:
        metadata = json.loads(field['metadata'])
    except:
        logger.warning(f'Skipped field with kind {field["kind"]}')
        return

    profile_academies = context['profile_academies'].get(metadata['userName'], None)
    if profile_academies is None:
        profile_academies = ProfileAcademy.objects.filter(
            user__credentialsgithub__username=metadata['userName'], status='ACTIVE')

        context['profile_academies'][metadata['userName']] = profile_academies

    if profile_academies:
        academies = random.choices(list({profile.academy for profile in profile_academies}), k=1)

    else:
        if 'academies' not in context:
            context['academies'] = Academy.objects.filter()
        academies = list(context['academies'])

    if not academies:
        write_activity()
        return

    for academy in academies:
        write_activity(academy)
