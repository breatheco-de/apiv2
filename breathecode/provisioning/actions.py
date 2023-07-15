from datetime import datetime
import pytz
import re
import random
from typing import Optional, TypedDict
from django.utils import timezone
from breathecode.authenticate.models import (AcademyAuthSettings, CredentialsGithub, GithubAcademyUser,
                                             GithubAcademyUserLog, ProfileAcademy)
from breathecode.payments.models import Currency
from breathecode.utils.validation_exception import ValidationException
from breathecode.utils import getLogger
from breathecode.services.github import Github
from breathecode.utils.i18n import translation
from breathecode.admissions.models import Academy, CohortUser
from .models import (ProvisioningUserConsumption, ProvisioningConsumptionEvent, ProvisioningConsumptionKind,
                     ProvisioningPrice, ProvisioningBill, ProvisioningProfile, ProvisioningVendor)
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
            ret[n - 1]['ending_at'] = log.created_at

        obj = {
            'starting_at': log.created_at,
            'ending_at': limit,
            'storage_status': log.storage_status,
            'storage_action': log.storage_action,
        }

        ret.append(obj)

    starts_limit = limit - relativedelta(months=1, weeks=1)
    ret = [x for x in ret if x['ending_at'] < starts_limit]

    if len(ret) > 0 and ret[0]['storage_status'] == 'SYNCHED' and ret[0]['storage_action'] == 'DELETE':
        ret = [
            {
                'starting_at': logs[0].created_at - relativedelta(months=12),
                'ending_at': logs[0].created_at,
                'storage_status': log.storage_status,
                'storage_action': log.storage_action,
            },
            *ret,
        ]

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
    orgs = [
        x for x in orgs if GithubAcademyUser.objects.filter(
            academy=x.academy, storage_action='ADD', storage_status='SYNCHED').count()
    ]

    if not orgs:
        logger.error(f'Organization {organization} not found')
        return []

    user = None

    credentials = None
    if username:
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


def add_codespaces_activity(context: ActivityContext, field: dict, position: int) -> None:
    if isinstance(field['Username'], float):
        field['Username'] = ''

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

    if not academies and not GithubAcademyUser.objects.filter(username=field['Username']).count():
        academies = handle_pending_github_user(field['Owner'], field['Username'])

    if not not_found:
        academies = random.choices(academies, k=1)

    errors = []
    ignores = []
    logs = {}
    provisioning_bills = {}
    provisioning_vendor = None

    provisioning_vendor = context['provisioning_vendors'].get('Codespaces', None)
    if not provisioning_vendor:
        provisioning_vendor = ProvisioningVendor.objects.filter(name='Codespaces').first()
        context['provisioning_vendors']['Codespaces'] = provisioning_vendor

    if not provisioning_vendor:
        errors.append(f'Provisioning vendor Codespaces not found')

    for academy in academies:
        ls = context['logs'].get((field['Username'], academy.id), None)
        if ls is None:
            ls = get_github_academy_user_logs(academy, field['Username'], context['limit'])
            context['logs'][(field['Username'], academy.id)] = ls
            logs[academy.id] = ls

        provisioning_bill = context['provisioning_bills'].get(academy.id, None)
        if not provisioning_bill and (provisioning_bill := ProvisioningBill.objects.filter(
                academy=academy, status='PENDING', hash=context['hash']).first()):
            context['provisioning_bills'][academy.id] = provisioning_bill
            provisioning_bills[academy.id] = provisioning_bill

        if not provisioning_bill:
            provisioning_bill = ProvisioningBill()
            provisioning_bill.academy = academy
            provisioning_bill.vendor = provisioning_vendor
            provisioning_bill.status = 'PENDING'
            provisioning_bill.hash = context['hash']
            provisioning_bill.save()

            context['provisioning_bills'][academy.id] = provisioning_bill
            provisioning_bills[academy.id] = provisioning_bill

    date = datetime.strptime(field['Date'], '%Y-%m-%d')
    for academy_id in logs.keys():
        for log in logs[academy_id]:
            if (log['storage_action'] == 'DELETE' and log['storage_status'] == 'SYNCHED'
                    and log['starting_at'] <= pytz.utc.localize(date) <= log['ending_at']):
                provisioning_bills.pop(academy_id, None)
                ignores.append(
                    f'User {field["Username"]} was deleted from the academy during this event at {date}')

    if not_found:
        errors.append(f'User {field["Username"]} not found in any academy')

    if not (kind := context['provisioning_activity_kinds'].get((field['Product'], field['SKU']), None)):
        kind, _ = ProvisioningConsumptionKind.objects.get_or_create(
            product_name=field['Product'],
            sku=field['SKU'],
        )
        context['provisioning_activity_kinds'][(field['Product'], field['SKU'])] = kind

    if not (currency := context['currencies'].get('USD', None)):
        currency, _ = Currency.objects.get_or_create(code='USD', name='US Dollar', decimals=2)
        context['currencies']['USD'] = currency

    if not (price := context['provisioning_activity_prices'].get(
        (field['Unit Type'], field['Price Per Unit ($)'], field['Multiplier']), None)):
        price, _ = ProvisioningPrice.objects.get_or_create(
            currency=currency,
            unit_type=field['Unit Type'],
            price_per_unit=field['Price Per Unit ($)'],
            multiplier=field['Multiplier'],
        )

        context['provisioning_activity_prices'][(field['Unit Type'], field['Price Per Unit ($)'],
                                                 field['Multiplier'])] = price

    pa, _ = ProvisioningUserConsumption.objects.get_or_create(username=field['Username'],
                                                              hash=context['hash'],
                                                              kind=kind,
                                                              defaults={'processed_at': timezone.now()})

    item, _ = ProvisioningConsumptionEvent.objects.get_or_create(
        vendor=provisioning_vendor,
        price=price,
        registered_at=date,
        quantity=field['Quantity'],
        repository_url=f"https://github.com/{field['Owner']}/{field['Repository Slug']}",
        task_associated_slug=field['Repository Slug'],
        csv_row=position,
    )

    if errors and not (len(errors) == 1 and not_found):
        pa.status = 'ERROR'
        pa.status_text = pa.status_text + (',' if pa.status_text else '') + ', '.join(errors + ignores)

    elif pa.status != 'ERROR' and ignores and not provisioning_bills:
        pa.status = 'IGNORED'
        pa.status_text = pa.status_text + (',' if pa.status_text else '') + ', '.join(ignores)

    else:
        pa.status = 'PERSISTED'
        pa.status_text = pa.status_text + (',' if pa.status_text else '') + ', '.join(errors + ignores)

    pa.save()

    current_bills = pa.bills.all()
    for provisioning_bill in provisioning_bills.values():
        if provisioning_bill not in current_bills:
            pa.bills.add(provisioning_bill)

    pa.events.add(item)


def add_gitpod_activity(context: ActivityContext, field: dict, position: int):
    profile_academies = context['profile_academies'].get(field['userName'], None)
    if profile_academies is None:
        profile_academies = ProfileAcademy.objects.filter(user__credentialsgithub__username=field['userName'],
                                                          status='ACTIVE')

        context['profile_academies'][field['userName']] = profile_academies

    if profile_academies:
        academies = random.choices(list({profile.academy for profile in profile_academies}), k=1)

    else:
        if 'academies' not in context:
            context['academies'] = Academy.objects.filter()
        academies = list(context['academies'])

    errors = []
    if not academies:
        errors.append(f'User {field["userName"]} not found in any academy')

    pattern = r'^https://github\.com/[^/]+/([^/]+)/?'
    if not (result := re.findall(pattern, field['contextURL'])):
        errors.append(f'Invalid repository URL {field["contextURL"]}')
        slug = 'unknown'

    else:
        slug = result[0]

    provisioning_bills = []
    provisioning_vendor = context['provisioning_vendors'].get('Gitpod', None)
    if not provisioning_vendor:
        provisioning_vendor = ProvisioningVendor.objects.filter(name='Gitpod').first()
        context['provisioning_vendors']['Gitpod'] = provisioning_vendor

    if not provisioning_vendor:
        errors.append(f'Provisioning vendor Gitpod not found')

    if academies:
        for academy in academies:
            provisioning_bill = context['provisioning_bills'].get(academy.id, None)

            if provisioning_bill:
                provisioning_bills.append(provisioning_bill)

            elif provisioning_bill := ProvisioningBill.objects.filter(academy=academy,
                                                                      status='PENDING',
                                                                      hash=context['hash']).first():
                context['provisioning_bills'][academy.id] = provisioning_bill
                provisioning_bills.append(provisioning_bill)

            else:
                provisioning_bill = ProvisioningBill()
                provisioning_bill.academy = academy
                provisioning_bill.vendor = provisioning_vendor
                provisioning_bill.status = 'PENDING'
                provisioning_bill.hash = context['hash']
                provisioning_bill.save()

                context['provisioning_bills'][academy.id] = provisioning_bill
                provisioning_bills.append(provisioning_bill)

    provisioning_bills = list(set(provisioning_bills))

    date = iso_to_datetime(field['startTime'])

    if not (kind := context['provisioning_activity_kinds'].get(field['kind'], None)):
        kind, _ = ProvisioningConsumptionKind.objects.get_or_create(
            product_name=field['kind'],
            sku=field['kind'],
        )
        context['provisioning_activity_kinds'][field['kind']] = kind

    if not (currency := context['currencies'].get('USD', None)):
        currency, _ = Currency.objects.get_or_create(code='USD', name='US Dollar', decimals=2)
        context['currencies']['USD'] = currency

    if not (price := context['provisioning_activity_prices'].get(currency.id, None)):
        price, _ = ProvisioningPrice.objects.get_or_create(
            currency=currency,
            unit_type='Credits',
            price_per_unit=0.036,
            multiplier=1,
        )

        context['provisioning_activity_prices'][currency.id] = price

    pa, _ = ProvisioningUserConsumption.objects.get_or_create(username=field['userName'],
                                                              hash=context['hash'],
                                                              kind=kind,
                                                              defaults={'processed_at': timezone.now()})

    item, _ = ProvisioningConsumptionEvent.objects.get_or_create(
        external_pk=field['id'],
        vendor=provisioning_vendor,
        price=price,
        registered_at=date,
        quantity=field['credits'],
        repository_url=field['contextURL'],
        task_associated_slug=slug,
        csv_row=position,
    )

    if pa.status == 'PENDING':
        pa.status = 'PERSISTED' if not errors else 'ERROR'

    pa.status_text = pa.status_text + (',' if pa.status_text else '') + ', '.join(errors)
    pa.save()

    current_bills = pa.bills.all()
    for provisioning_bill in provisioning_bills:
        if provisioning_bill not in current_bills:
            pa.bills.add(provisioning_bill)

    pa.events.add(item)
