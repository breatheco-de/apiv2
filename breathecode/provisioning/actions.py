from datetime import datetime
import json
import os, re, requests
from typing import TypedDict
from django.utils import timezone
from breathecode.authenticate.models import CredentialsGithub, User
from breathecode.utils.validation_exception import ValidationException
from breathecode.utils import getLogger
from breathecode.services.github import Github
from breathecode.utils.i18n import translation
from breathecode.authenticate.actions import get_user_language, get_user_settings
from breathecode.admissions.models import CohortUser
from .models import ProvisioningActivity, ProvisioningBill, ProvisioningProfile, ProvisioningVendor

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


class ActivityContext(TypedDict):
    provisioning_bills: dict[str, ProvisioningBill]
    provisioning_vendors: dict[str, ProvisioningVendor]
    credentials_github: dict[str, CredentialsGithub]
    users: dict[str, User]
    http_github: dict[str, requests.Request]
    hash: str


def add_codespaces_activity(context: ActivityContext, field: dict):

    user = None
    c = None
    if field['Username'] in context['credentials_github']:
        c = context['credentials_github'].get(field['Username'])

    else:
        c = CredentialsGithub.objects.filter(username=field['Username']).first()
        context['credentials_github'][field['Username']] = c

    if c:
        context['credentials_github'][field['Username']] = c
        user = c.user

    if not user:
        response = context['http_github'].get(
            field['Username'], requests.get(f'https://api.github.com/users/{field["Username"]}'))

        if response.status_code == 200 and (json := response.json()) and 'email' in json:
            user = User.objects.filter(email=json['email']).first()

        context['http_github'][field['Username']] = response

    if not user:
        logger.error(f'User {field["Username"]} not found')
        return

    cohort_user = CohortUser.objects.filter(
        user=user, cohort__syllabus_version__json__icontains=field['Repository Slug']).order_by(
            '-cohort__kickoff_date').first()

    if not cohort_user:
        cohort_user = CohortUser.objects.filter(user=user).order_by('-cohort__kickoff_date').first()

    if not cohort_user:
        logger.error(f'User {field["Username"]} not found in any cohort')
        return

    academy = cohort_user.cohort.academy

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

    pa = ProvisioningActivity()

    pa.bill = provisioning_bill
    pa.username = field['Username']
    pa.registered_at = datetime.strptime(field['Date'], '%Y-%m-%d')
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

    user = None
    c = None
    if metadata['userName'] in context['credentials_github']:
        c = context['credentials_github'].get(metadata['userName'])

    else:
        c = CredentialsGithub.objects.filter(username=metadata['userName']).first()
        context['credentials_github'][metadata['userName']] = c

    if c:
        context['credentials_github'][metadata['userName']] = c
        user = c.user

    if not user:
        response = context['http_github'].get(
            metadata['userName'], requests.get(f'https://api.github.com/users/{metadata["userName"]}'))

        if response.status_code == 200 and (j := response.json()) and 'email' in j:
            user = User.objects.filter(email=j['email']).first()

        context['http_github'][metadata['userName']] = response

    if not user:
        logger.error(f'User {metadata["userName"]} not found')
        return

    pattern = r'^https://github\.com/[^/]+/([^/]+)/?'
    if not (result := re.findall(pattern, metadata['contextURL'])):
        raise Exception(f'Invalid repository URL {metadata["contextURL"]}')

    slug = result[0]

    cohort_user = CohortUser.objects.filter(
        user=user, cohort__syllabus_version__json__icontains=slug).order_by('-cohort__kickoff_date').first()

    if not cohort_user:
        cohort_user = CohortUser.objects.filter(user=user).order_by('-cohort__kickoff_date').first()

    if not cohort_user:
        logger.error(f'User {metadata["userName"]} not found in any cohort')
        return

    academy = cohort_user.cohort.academy

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

    pa = ProvisioningActivity()
    pa.bill = provisioning_bill
    pa.username = metadata['userName']
    pa.registered_at = iso_to_datetime(field['effectiveTime'])
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
