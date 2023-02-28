import os, re, requests
from django.utils import timezone
from breathecode.utils.validation_exception import ValidationException
from breathecode.utils import getLogger
from breathecode.services import Github
from breathecode.utils.i18n import translation
from breathecode.authenticate.actions import get_user_language, get_user_settings
from breathecode.admissions.models import CohortUser

logger = getLogger(__name__)


def sync_machine_types(provisioning_academy, assignment):

    gb = Github(token=provisioning_academy.credentials_token, host=provisioning_academy.vendor.api_url)

    asset = Asset.objects.filter(slug=assignment.associated_slug).first()
    org_name, repo_name, branch_name = asset.get_repo_meta()

    machines = gb.get_machines_types(repo_name)
    print(machines)


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


#     print(machines)
