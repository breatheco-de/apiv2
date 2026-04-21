import math
import os
import random
import re
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal, localcontext
from typing import Any, Optional, TypedDict

from capyc.core.i18n import translation
from capyc.rest_framework.exceptions import ValidationException
from dateutil.relativedelta import relativedelta
from django.db.models import F, Q, QuerySet
from django.utils import timezone
from linked_services.django.actions import get_user

from breathecode.admissions.models import Academy, CohortUser
from breathecode.authenticate.actions import get_user_language
from breathecode.authenticate.models import (
    ACTIVE as PROFILE_ACADEMY_ACTIVE,
    AcademyAuthSettings,
    CredentialsGithub,
    GithubAcademyUser,
    GithubAcademyUserLog,
    ProfileAcademy,
)
from breathecode.payments.models import Consumable, Currency, PlanFinancing, Subscription
from breathecode.payments.signals import consume_service
from breathecode.registry.models import Asset
from breathecode.services.github import Github
from breathecode.utils import getLogger
from breathecode.utils.decorators import service_deprovisioner

from .models import (
    ProvisioningAcademy,
    ProvisioningBill,
    ProvisioningConsumptionEvent,
    ProvisioningConsumptionKind,
    ProvisioningContainer,
    ProvisioningPrice,
    ProvisioningProfile,
    ProvisioningUserConsumption,
    ProvisioningLLM,
    ProvisioningVendor,
    ProvisioningVPS,
)
from .utils.llm_client import LLMClientError, get_llm_client
from .utils.vps_client import get_vps_client

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
            f"No provisioning vendors have been found for this academy {academy.name}, please speak with your program manager"
        )

    for_me = all_profiles.filter(members__id=profile_academy.id, cohorts=None)
    if for_me.count() > 1:
        vendors = [f"{p.vendor.name} in profile {p.id}" for p in for_me]
        raise Exception(
            "More than one provisioning vendor found for your profile in this academy, please speak with your program manager: "
            + ",".join(vendors)
        )
    if for_me.count() == 1:
        p_profile = for_me.first()
        return p_profile.vendor

    for_my_cohort = all_profiles.filter(cohorts__id=cohort.id, members=None)
    if for_my_cohort.count() > 1:
        vendors = [f"{p.vendor.name} in profile {p.id}" for p in for_my_cohort]
        raise Exception(
            "More than one provisioning vendor found for your cohort, please speak with your program manager: "
            + ",".join(vendors)
        )
    if for_my_cohort.count() == 1:
        p_profile = for_my_cohort.first()
        return p_profile.vendor

    entire_academy = all_profiles.filter(cohorts=None, members=None)
    if entire_academy.count() > 1:
        vendors = [f"{p.vendor.name} in profile {p.id}" for p in entire_academy]
        raise Exception(
            "More than one provisioning vendor found for the entire academy, please speak with your program manager: "
            + ",".join(vendors)
        )
    if entire_academy.count() == 1:
        p_profile = entire_academy.first()
        return p_profile.vendor

    raise Exception(
        "We couldn't find any provisioning vendors for you, your cohort or your academy. Please speak with your program manager."
    )


def get_vps_provisioning_academy_for_academy(academy: Academy, lang: str = "en"):
    """
    Resolve ProvisioningAcademy with VPS client and credentials for a fixed academy.
    Returns (academy, provisioning_academy). Raises ValidationException if not configured.
    """
    profiles = ProvisioningProfile.objects.filter(academy=academy).select_related("vendor")
    for profile in profiles:
        if not profile.vendor_id:
            continue
        client = get_vps_client(profile.vendor)
        if client is None:
            continue
        provisioning_academy = ProvisioningAcademy.objects.filter(academy=academy, vendor=profile.vendor).first()
        if not provisioning_academy or not (
            provisioning_academy.credentials_token or provisioning_academy.credentials_key
        ):
            continue
        return (academy, provisioning_academy)
    raise ValidationException(
        translation(
            lang,
            en="Your academy does not have VPS provisioning configured. Please contact your program manager.",
            es="Tu academia no tiene configurado el aprovisionamiento de VPS. Contacta a tu programa.",
            slug="academy-vps-not-configured",
        )
    )


def user_belongs_to_academy_for_vps(user, academy: Academy) -> bool:
    """True if user has an active ProfileAcademy or active CohortUser in a cohort of this academy."""
    if ProfileAcademy.objects.filter(user=user, academy=academy, status=PROFILE_ACADEMY_ACTIVE).exists():
        return True
    if CohortUser.objects.filter(
        user=user,
        cohort__academy_id=academy.id,
        educational_status="ACTIVE",
    ).exists():
        return True
    return False


def get_eligible_academy_and_vendor_for_vps(user):
    """
    Resolve academy and ProvisioningAcademy for VPS provisioning for this user.
    Ensures ProvisioningProfile with a VPS-capable vendor and ProvisioningAcademy with credentials.
    Returns (academy, provisioning_academy). Raises ValidationException with translation if none found.
    """
    academy = None
    active_cohorts = get_active_cohorts(user)
    if active_cohorts.exists():
        academy = active_cohorts.first().cohort.academy
    if not academy:
        pa = ProfileAcademy.objects.filter(user=user).first()
        if pa:
            academy = pa.academy
    if not academy:
        raise ValidationException(
            translation(
                getattr(user, "lang", None) or "en",
                en="No academy found for your account. You must belong to an academy to request a VPS.",
                es="No se encontró academia para tu cuenta. Debes pertenecer a una academia para solicitar un VPS.",
                slug="no-academy-for-vps",
            )
        )
    profiles = ProvisioningProfile.objects.filter(academy=academy).select_related("vendor")
    for profile in profiles:
        if not profile.vendor_id:
            continue
        client = get_vps_client(profile.vendor)
        if client is None:
            continue
        provisioning_academy = ProvisioningAcademy.objects.filter(academy=academy, vendor=profile.vendor).first()
        if not provisioning_academy or not (
            provisioning_academy.credentials_token or provisioning_academy.credentials_key
        ):
            continue
        return (academy, provisioning_academy)
    raise ValidationException(
        translation(
            getattr(user, "lang", None) or "en",
            en="Your academy does not have VPS provisioning configured. Please contact your program manager.",
            es="Tu academia no tiene configurado el aprovisionamiento de VPS. Contacta a tu programa.",
            slug="academy-vps-not-configured",
        )
    )


def resolve_provisioning_academy_for_llm(academy):
    """
    Given an academy, return the first ProvisioningAcademy whose vendor is registered
    in the LLM client registry and has credentials configured.  Returns None when no
    suitable configuration is found.

    Used by both ``ensure_llm_user`` and the student-facing LLM views.
    """
    for pa in ProvisioningAcademy.objects.select_related("vendor").filter(academy=academy, vendor__isnull=False):
        if get_llm_client(pa) is not None:
            return pa
    return None


def ensure_llm_user(user, provisioning_academy, client=None):
    """
    Ensure a ProvisioningLLM record exists for ``user`` + ``provisioning_academy``.

    Creates the record (status ACTIVE) when missing, and re-activates a
    previously deprovisioned record when the user still holds entitlement.
    Returns the ProvisioningLLM instance.
    """
    if not provisioning_academy:
        return None

    vendor = provisioning_academy.vendor

    academy_slug = getattr(provisioning_academy.academy, "slug", "") or str(provisioning_academy.academy_id)
    external_user_id = f"{user.username}-{academy_slug}"

    provisioning_llm, created = ProvisioningLLM.objects.get_or_create(
        user=user,
        academy=provisioning_academy.academy,
        vendor=vendor,
        defaults={
            "external_user_id": external_user_id,
            "status": ProvisioningLLM.STATUS_ACTIVE,
            "deprovisioned_at": None,
            "error_message": "",
        },
    )
    # Note: even if we just created the ProvisioningLLM row, we still want to ensure
    # that the user exists in the external LLM provider before generating API keys.

    changed = False

    if provisioning_llm.status == ProvisioningLLM.STATUS_DEPROVISIONED:
        academy_id = provisioning_academy.academy.id
        has_entitlement = (
            Consumable.list(
                user=user,
                service="free-monthly-llm-budget",
                extra={"subscription__academy_id": academy_id},
            ).exists()
            or Consumable.list(
                user=user,
                service="free-monthly-llm-budget",
                extra={"plan_financing__academy_id": academy_id},
            ).exists()
        )
        if has_entitlement:
            provisioning_llm.status = ProvisioningLLM.STATUS_ACTIVE
            provisioning_llm.deprovisioned_at = None
            provisioning_llm.error_message = ""
            changed = True

    external_user_id = provisioning_llm.external_user_id or str(user.username)

    if provisioning_llm.external_user_id != external_user_id:
        provisioning_llm.external_user_id = external_user_id
        changed = True

    if changed:
        provisioning_llm.save(
            update_fields=["external_user_id", "status", "deprovisioned_at", "error_message", "updated_at"]
        )

    if client is None:
        client = get_llm_client(provisioning_academy)
    if client and hasattr(client, "get_user_info") and hasattr(client, "create_user"):
        try:
            client.get_user_info(user_id=external_user_id)
        except LLMClientError as exc:
            exc_str = str(exc).lower()
            # LiteLLM returns: User <id> not found (code 404 in our wrapper)
            if "404" in exc_str and "not found" in exc_str:
                user_email = getattr(user, "email", None) or ""
                try:
                    user_metadata = {"email": user_email} if user_email else None
                    client.create_user(
                        user_id=external_user_id,
                        user_alias=getattr(user, "username", None),
                        metadata=user_metadata,
                    )
                except LLMClientError:
                    # If the user already exists due to a race condition, generation will work anyway.
                    retry_msg = str(exc).lower()
                    if "409" not in retry_msg and "already" not in retry_msg:
                        raise

    return provisioning_llm


def resolve_llm_client_and_external_id(request, ensure_llm_user_record: bool = False):
    """
    Resolve an LLM client and the external_user_id.

    The ``Academy`` or ``academy`` request header (academy id) is **required**
    for POST create and DELETE key flows. The global GET ``me/llm/keys`` listing
    does not use this helper.

    When *ensure_llm_user_record* is True the ProvisioningLLM row is created
    synchronously (used by POST endpoints).  When False (default) only an
    existing row is looked up (used by DELETE).

    Returns: (client, external_user_id)
    """
    user = request.user
    lang = get_user_language(request)

    raw_academy_id = request.headers.get("Academy") or request.headers.get("academy")
    if raw_academy_id is None or (isinstance(raw_academy_id, str) and not raw_academy_id.strip()):
        raise ValidationException(
            translation(
                lang,
                en="The Academy header is required to manage LLM API keys.",
                es="El header Academy es obligatorio para administrar las llaves de API de LLM.",
                slug="llm-academy-header-required",
            ),
            code=400,
        )

    try:
        academy_id = int(str(raw_academy_id).strip())
    except ValueError:
        raise ValidationException(
            translation(
                lang,
                en="Invalid Academy header.",
                es="El header Academy no es válido.",
                slug="academy-header-invalid",
            ),
            code=400,
        )

    has_entitlement = (
        Consumable.list(
            user=user,
            service="free-monthly-llm-budget",
            extra={"subscription__academy_id": academy_id},
        ).exists()
        or Consumable.list(
            user=user,
            service="free-monthly-llm-budget",
            extra={"plan_financing__academy_id": academy_id},
        ).exists()
    )
    if not has_entitlement:
        raise ValidationException(
            translation(
                lang,
                en="You don't have the LLM budget consumable required to manage API keys.",
                es="No tienes el consumible de presupuesto de LLM necesario para administrar llaves de API.",
                slug="llm-budget-required",
            ),
            code=403,
        )

    academy = Academy.objects.filter(id=academy_id).first()
    if not academy:
        raise ValidationException(
            translation(
                lang,
                en="Academy not found.",
                es="Academia no encontrada.",
                slug="academy-not-found",
            ),
            code=404,
        )

    is_member = get_active_cohorts(user).filter(cohort__academy_id=academy_id).exists()
    if not is_member:
        is_member = ProfileAcademy.objects.filter(user=user, academy_id=academy_id).exists()

    if not is_member:
        raise ValidationException(
            translation(
                lang,
                en="You do not have permission for this Academy.",
                es="No tienes permiso para esta academia.",
                slug="academy-not-permitted",
            ),
            code=403,
        )

    provisioning_academy = resolve_provisioning_academy_for_llm(academy)
    if not provisioning_academy:
        raise ValidationException(
            translation(
                lang,
                en="Your academy does not have LLM provisioning configured. Please contact your program manager.",
                es="Tu academia no tiene configurado el aprovisionamiento de LLM. Contacta a tu programa.",
                slug="academy-llm-not-configured",
            ),
            code=400,
        )

    client = get_llm_client(provisioning_academy)
    if client is None:
        raise ValidationException(
            translation(
                lang,
                en="LLM provisioning is not configured for your academy.",
                es="El aprovisionamiento de LLM no está configurado para tu academia.",
                slug="llm-client-not-configured",
            ),
            code=400,
        )

    if ensure_llm_user_record:
        provisioning_llm = ensure_llm_user(user, provisioning_academy, client=client)
    else:
        provisioning_llm = ProvisioningLLM.objects.filter(
            user=user,
            academy=academy,
            vendor=provisioning_academy.vendor,
        ).first()

    academy_slug = getattr(academy, "slug", "") or str(academy_id)
    external_user_id = f"{user.username}-{academy_slug}"
    if provisioning_llm and provisioning_llm.external_user_id:
        external_user_id = provisioning_llm.external_user_id

    return client, external_user_id


def request_vps(user, plan_slug=None):
    """
    Request a new VPS for the user. Consumes one vps_server consumable, creates ProvisioningVPS, enqueues task.
    Returns the ProvisioningVPS instance. Raises ValidationException if ineligible, duplicate, or no credits.
    """
    academy, provisioning_academy = get_eligible_academy_and_vendor_for_vps(user)
    lang = getattr(user, "lang", None) or "en"
    return get_vps_provisioning_academy_for_academy(academy, lang=lang)


def _request_vps_core(
    user,
    academy: Academy,
    provisioning_academy: ProvisioningAcademy,
    plan_slug=None,
    vendor_selection=None,
    *,
    lang: Optional[str] = None,
    for_staff: bool = False,
):
    lang = lang or getattr(user, "lang", None) or "en"
    active_statuses = [
        ProvisioningVPS.VPS_STATUS_PENDING,
        ProvisioningVPS.VPS_STATUS_PROVISIONING,
        ProvisioningVPS.VPS_STATUS_ACTIVE,
    ]
    if ProvisioningVPS.objects.filter(user=user, academy=academy, status__in=active_statuses).exists():
        if for_staff:
            msg = translation(
                lang,
                en="This student already has an active or pending VPS for this academy.",
                es="Este estudiante ya tiene un VPS activo o pendiente para esta academia.",
                slug="duplicate-vps",
            )
        else:
            msg = translation(
                lang,
                en="You already have an active or pending VPS for this academy.",
                es="Ya tienes un VPS activo o pendiente para esta academia.",
                slug="duplicate-vps",
            )
        raise ValidationException(msg)
    consumables = Consumable.list(user=user, service="vps_server", include_zero_balance=False)
    consumables = consumables.filter(how_many__gt=0)
    if not consumables.exists():
        if for_staff:
            msg = translation(
                lang,
                en="This student doesn't have VPS server credits.",
                es="Este estudiante no tiene créditos de servidor VPS.",
                slug="insufficient-vps-server-credits",
            )
        else:
            msg = translation(
                lang,
                en="You don't have VPS server credits.",
                es="No tienes créditos de servidor VPS.",
                slug="insufficient-vps-server-credits",
            )
        raise ValidationException(msg)
    consumable = consumables.first()
    consume_service.send(sender=Consumable, instance=consumable, how_many=1)
    requested_at = timezone.now()
    vps = ProvisioningVPS.objects.create(
        user=user,
        academy=academy,
        vendor=provisioning_academy.vendor,
        consumed_consumable=consumable,
        status=ProvisioningVPS.VPS_STATUS_PENDING,
        plan_slug=plan_slug or "",
        requested_at=requested_at,
    )
    from .tasks import provision_vps_task

    provision_vps_task.delay(vps.id, vendor_selection=vendor_selection or {})
    return vps


def request_vps_for_student(student_user, academy: Academy, plan_slug=None, vendor_selection=None, lang: str = "en"):
    """
    Staff flow: request a VPS for a student in a fixed academy. Consumes the student's vps_server consumable.
    """
    if not user_belongs_to_academy_for_vps(student_user, academy):
        raise ValidationException(
            translation(
                lang,
                en="This user is not an active member of this academy.",
                es="Este usuario no es miembro activo de esta academia.",
                slug="student-not-in-academy",
            )
        )
    _, provisioning_academy = get_vps_provisioning_academy_for_academy(academy, lang=lang)
    return _request_vps_core(
        student_user,
        academy,
        provisioning_academy,
        plan_slug,
        vendor_selection=vendor_selection,
        lang=lang,
        for_staff=True,
    )


def get_active_cohorts(user):
    now = timezone.now()
    active = CohortUser.objects.filter(user=user, educational_status="ACTIVE", role="STUDENT")
    # only cohorts that end
    cohorts_that_end = active.filter(cohort__never_ends=False)
    # also are withing calendar dates and STARTED or FINAL PROJECT
    active_dates = cohorts_that_end.filter(
        cohort__kickoff_date__gte=now, cohort__ending_date__lte=now, cohort__stage__in=["STARTED", "FINAL_PROJECT"]
    )

    return active_dates


def create_container(user, task, fresh=False, lang="en"):

    cont = ProvisioningContainer.objects.filter(user=user, task_associated_slug=task.slug).first()
    if not fresh and cont is not None:
        raise ValidationException(
            translation(
                en="There is another container already created for this assignment",
                es="Hay otro contenedor ya creado para esta asignacion",
                slug="duplicated-container",
            )
        )

    # active_cohorts = get_active_cohorts(user)
    credentials = CredentialsGithub.objects.filter(user=user).first()
    if credentials is None:
        raise ValidationException(
            translation(
                en="No github github credentials found, please connect your github account",
                es="No se han encontrado credentials para github, por favor conecta tu cuenta de github",
                slug="no-github-credentials",
            )
        )

    # FIXME: the code belog have variables that are not defined, so, it never worked, uncomment it if you want to fix it
    # gb = Github(token=credentials.token, host=provisioning_academy.vendor.api_url)

    # asset = Asset.objects.filter(slug=task.associated_slug).first()
    # _, repo_name, _ = asset.get_repo_meta()

    # machines = gb.get_machines_types(repo_name)


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
    string = re.sub(r"Z$", "", iso)
    date = datetime.fromisoformat(string)
    return timezone.make_aware(date)


class GithubAcademyUserObject(TypedDict):
    storage_status: str
    storage_action: str
    created_at: datetime
    ended_at: datetime


def get_github_academy_user_logs(academy: Academy, username: str, limit: datetime) -> list[GithubAcademyUserObject]:
    ret = []
    logs = GithubAcademyUserLog.objects.filter(
        Q(valid_until__isnull=True) | Q(valid_until__gte=limit - relativedelta(months=1, weeks=1)),
        academy_user__username=username,
        academy_user__academy=academy,
    ).order_by("created_at")

    for n in range(len(logs)):
        log = logs[n]

        if n != 0:
            ret[n - 1]["ending_at"] = log.created_at

        obj = {
            "starting_at": log.created_at,
            "ending_at": limit,
            "storage_status": log.storage_status,
            "storage_action": log.storage_action,
        }

        ret.append(obj)

    starts_limit = limit - relativedelta(months=1, weeks=1)
    ret = [x for x in ret if x["ending_at"] < starts_limit]

    if len(ret) > 0 and ret[0]["storage_status"] == "SYNCHED" and ret[0]["storage_action"] == "DELETE":
        ret = [
            {
                "starting_at": logs[0].created_at - relativedelta(months=12),
                "ending_at": logs[0].created_at,
                "storage_status": log.storage_status,
                "storage_action": log.storage_action,
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


def is_valid_string(value):
    return isinstance(value, str) and value.strip() != ""


def handle_pending_github_user(
    organization: Optional[str], username: str, starts: Optional[datetime] = None
) -> list[Academy]:
    # Handle NaN values from pandas DataFrame
    if organization is not None and (isinstance(organization, float) and math.isnan(organization)):
        organization = None

    orgs = (
        AcademyAuthSettings.objects.filter(github_username__iexact=organization)
        if organization
        else AcademyAuthSettings.objects.filter()
    )
    orgs = [
        x
        for x in orgs
        if GithubAcademyUser.objects.filter(academy=x.academy, storage_action="ADD", storage_status="SYNCHED").count()
    ]

    if not orgs and organization:
        logger.error(f"Organization {organization} not found")
        return []

    if not orgs and organization is None:
        logger.error("Organization not provided, in this case, all organizations will be used")

    if not orgs:
        orgs = AcademyAuthSettings.objects.filter()

    user = None

    credentials = None
    if is_valid_string(username):
        credentials = CredentialsGithub.objects.filter(username__isnull=False, username__iexact=username).first()

    else:
        logger.error(f"Username is invalid, cannot find github credentials for username {username}")

    if credentials:
        user = credentials.user

    if starts and organization is None:
        new_orgs = []
        for org in orgs:

            has_any_cohort_user = (
                CohortUser.objects.filter(
                    Q(cohort__ending_date__lte=starts) | Q(cohort__never_ends=True),
                    cohort__kickoff_date__gte=starts,
                    cohort__academy__id=org.academy.id,
                    user__credentialsgithub__username=username,
                )
                .order_by("-created_at")
                .exists()
            )

            if has_any_cohort_user:
                new_orgs.append(org)

        if new_orgs:
            org = new_orgs

    for org in orgs:
        pending, created = GithubAcademyUser.objects.get_or_create(
            username=username,
            academy=org.academy,
            user=user,
            defaults={
                "storage_status": "PAYMENT_CONFLICT",
                "storage_action": "IGNORE",
            },
        )

        if not created and pending.storage_action not in ["ADD", "DELETE"]:
            pending.storage_status = "PAYMENT_CONFLICT"
            pending.storage_action = "IGNORE"
            pending.save()

    return [org.academy for org in orgs]


def get_multiplier() -> Decimal:
    try:
        x = os.getenv("PROVISIONING_MULTIPLIER", "1.1").replace(",", ".")
        x = Decimal(x)
    except Exception:
        x = Decimal("1.1")

    return x


def add_codespaces_activity(context: ActivityContext, field: dict, position: int) -> None:
    # Validate input values
    quantity = Decimal(str(field["quantity"])).quantize(Decimal(".000000001"), rounding=ROUND_HALF_UP)
    applied_cost = Decimal(str(field["applied_cost_per_quantity"])).quantize(
        Decimal(".000000001"), rounding=ROUND_HALF_UP
    )

    field["Multiplier"] = Decimal("1.1")  # Use Decimal instead of integer

    # Initialize variables
    errors = []
    warnings = []
    logs = {}
    provisioning_bills = {}
    provisioning_vendor = None

    # change this
    date = datetime.fromisoformat(field["date"])

    if isinstance(field["username"], float):
        field["username"] = ""

    # Handle NaN values in organization field
    if isinstance(field["organization"], float) and math.isnan(field["organization"]):
        field["organization"] = None
    elif not field["organization"]:  # Handle empty strings or None
        field["organization"] = None

    github_academy_user_log = context["github_academy_user_logs"].get(field["username"], None)
    not_found = False
    academies = []

    if github_academy_user_log is None:
        # make a function that calculate the user activity in the academies by percentage
        github_academy_user_log = GithubAcademyUserLog.objects.filter(
            Q(valid_until__isnull=True) | Q(valid_until__gte=context["limit"] - relativedelta(months=1, weeks=1)),
            created_at__lte=context["limit"],
            academy_user__username=field["username"],
            storage_status="SYNCHED",
            storage_action="ADD",
        ).order_by("-created_at")

        context["github_academy_user_logs"][field["username"]] = github_academy_user_log

    if github_academy_user_log:
        academies = [x.academy_user.academy for x in github_academy_user_log]

    if not academies:
        credentials = CredentialsGithub.objects.filter(username__iexact=field["username"]).first()
        if credentials and credentials.user and credentials.user.email:
            email_academy_users = GithubAcademyUser.objects.filter(
                user=credentials.user, storage_status="SYNCHED", storage_action="ADD"
            )
            academies = [x.academy for x in email_academy_users]

    if not academies:
        not_found = True

    if not academies and GithubAcademyUser.objects.filter(username=field["username"]).count():
        invited_synched = GithubAcademyUser.objects.filter(
            username=field["username"], storage_status="SYNCHED", storage_action="INVITE"
        )
        if invited_synched.exists():
            academies = [x.academy for x in invited_synched]
            warnings.append(
                f'User {field["username"]} assigned to academies ({len(academies)}) that had SYNCHED+INVITE status with this user.'
            )

        elif GithubAcademyUser.objects.filter(username=field["username"], storage_status="SYNCHED").exists():
            last_synched_github_academy_user = GithubAcademyUser.objects.filter(
                username=field["username"], storage_status="SYNCHED"
            )
            academies = [x.academy for x in last_synched_github_academy_user]
            warnings.append(
                f'User {field["username"]} assigned to academies ({len(academies)}) that had SYNCHED status with this user.'
            )

        else:
            all_github_academy_users = GithubAcademyUser.objects.filter(username=field["username"])
            academies = [x.academy for x in all_github_academy_users]
            warnings.append(
                f'User {field["username"]} has GithubAcademyUser records but none with SYNCHED status. '
                f"Assigning to all academies ({len(academies)}) for investigation."
            )

    if not academies and not GithubAcademyUser.objects.filter(username=field["username"]).count():
        academies = handle_pending_github_user(field["organization"], field["username"], date)

    if not not_found and academies:
        academies = random.choices(academies, k=1)

    provisioning_vendor = context["provisioning_vendors"].get("Codespaces", None)
    if not provisioning_vendor:
        provisioning_vendor = ProvisioningVendor.objects.filter(name="Codespaces").first()
        context["provisioning_vendors"]["Codespaces"] = provisioning_vendor

    if not provisioning_vendor:
        errors.append("Provisioning vendor Codespaces not found")

    # TODO: if not academies: no academy has been found responsable for this activity
    for academy in academies:
        ls = context["logs"].get((field["username"], academy.id), None)
        if ls is None:
            ls = get_github_academy_user_logs(academy, field["username"], context["limit"])
            context["logs"][(field["username"], academy.id)] = ls
            logs[academy.id] = ls

        provisioning_bill = context["provisioning_bills"].get(academy.id, None)
        provisioning_bills[academy.id] = provisioning_bill

        if not provisioning_bill and (
            provisioning_bill := ProvisioningBill.objects.filter(
                academy=academy, status="PENDING", hash=context["hash"]
            ).first()
        ):
            context["provisioning_bills"][academy.id] = provisioning_bill
            provisioning_bills[academy.id] = provisioning_bill

        if not provisioning_bill:
            provisioning_bill = ProvisioningBill()
            provisioning_bill.academy = academy
            provisioning_bill.vendor = provisioning_vendor
            provisioning_bill.status = "PENDING"
            provisioning_bill.hash = context["hash"]
            provisioning_bill.save()

            context["provisioning_bills"][academy.id] = provisioning_bill
            provisioning_bills[academy.id] = provisioning_bill

    if not_found:
        warnings.append(
            f'We could not find enough information about {field["username"]}, mark this user user as '
            "deleted if you don't recognize it"
        )

    if not (kind := context["provisioning_activity_kinds"].get((field["product"], field["sku"]), None)):
        kind, _ = ProvisioningConsumptionKind.objects.get_or_create(
            product_name=field["product"],
            sku=field["sku"],
        )
        context["provisioning_activity_kinds"][(field["product"], field["sku"])] = kind

    if not (currency := context["currencies"].get("USD", None)):
        currency, _ = Currency.objects.get_or_create(code="USD", defaults={"name": "US Dollar", "decimals": 2})
        context["currencies"]["USD"] = currency

    if not (
        price := context["provisioning_activity_prices"].get(
            (field["unit_type"], applied_cost, field["Multiplier"]), None
        )
    ):
        # Calculate price with proper decimal precision
        price_per_unit = (applied_cost * context["provisioning_multiplier"]).quantize(
            Decimal(".000000001"), rounding=ROUND_HALF_UP
        )

        price, _ = ProvisioningPrice.objects.get_or_create(
            currency=currency,
            unit_type=field["unit_type"],
            price_per_unit=price_per_unit,
            multiplier=field["Multiplier"].quantize(Decimal(".01"), rounding=ROUND_HALF_UP),
        )

        context["provisioning_activity_prices"][(field["unit_type"], applied_cost, field["Multiplier"])] = price

    pa, _ = ProvisioningUserConsumption.objects.get_or_create(
        username=field["username"], hash=context["hash"], kind=kind, defaults={"processed_at": timezone.now()}
    )

    item, _ = ProvisioningConsumptionEvent.objects.get_or_create(
        vendor=provisioning_vendor,
        price=price,
        registered_at=date,
        quantity=quantity,
        repository_url=f"https://github.com/{field['organization']}/{field['repository']}",
        task_associated_slug=field["repository"],
        csv_row=position,
    )

    last_status_list = [x for x in pa.status_text.split(", ") if x]
    if errors:
        pa.status = "ERROR"
        pa.status_text = ", ".join(last_status_list + errors + warnings)

    elif warnings:
        if pa.status != "ERROR":
            pa.status = "WARNING"

        pa.status_text = ", ".join(last_status_list + warnings)

    else:
        pa.status = "PERSISTED"
        pa.status_text = ", ".join(last_status_list + errors + warnings)

    pa.status_text = ", ".join([x for x in sorted(set(pa.status_text.split(", "))) if x])
    pa.status_text = pa.status_text[:255]
    pa.save()

    current_bills = pa.bills.all()
    for provisioning_bill in provisioning_bills.values():
        if provisioning_bill not in current_bills:
            pa.bills.add(provisioning_bill)

    pa.events.add(item)


def add_gitpod_activity(context: ActivityContext, field: dict, position: int):
    academies = []
    profile_academies = context["profile_academies"].get(field["userName"], None)
    if profile_academies is None:
        profile_academies = ProfileAcademy.objects.filter(
            user__credentialsgithub__username=field["userName"], status="ACTIVE"
        )

        context["profile_academies"][field["userName"]] = profile_academies

    if profile_academies:
        academies = sorted(list({profile.academy for profile in profile_academies}), key=lambda x: x.id)

    date = iso_to_datetime(field["startTime"])
    end = iso_to_datetime(field["endTime"])

    if len(academies) > 1:
        cohort_users = CohortUser.objects.filter(
            Q(cohort__ending_date__lte=end) | Q(cohort__never_ends=True),
            cohort__kickoff_date__gte=date,
            user__credentialsgithub__username=field["userName"],
        ).order_by("-created_at")

        if cohort_users:
            academies = sorted(list({cohort_user.cohort.academy for cohort_user in cohort_users}), key=lambda x: x.id)

    if not academies:
        if "academies" not in context:
            context["academies"] = Academy.objects.filter()
        academies = list(context["academies"])

    errors = []
    warnings = []
    if not academies:
        warnings.append(
            f'We could not find enough information about {field["userName"]}, mark this user user as '
            "deleted if you don't recognize it"
        )

    pattern = r"^https://github\.com/[^/]+/([^/]+)/?"
    if not (result := re.findall(pattern, field["contextURL"])):
        warnings.append(f'Invalid repository URL {field["contextURL"]}')
        slug = "unknown"

    else:
        slug = result[0]

    provisioning_bills = []
    provisioning_vendor = context["provisioning_vendors"].get("Gitpod", None)
    if not provisioning_vendor:
        provisioning_vendor = ProvisioningVendor.objects.filter(name="Gitpod").first()
        context["provisioning_vendors"]["Gitpod"] = provisioning_vendor

    if not provisioning_vendor:
        errors.append("Provisioning vendor Gitpod not found")

    if academies:
        for academy in academies:
            provisioning_bill = context["provisioning_bills"].get(academy.id, None)

            if provisioning_bill:
                provisioning_bills.append(provisioning_bill)

            elif provisioning_bill := ProvisioningBill.objects.filter(
                academy=academy, status="PENDING", hash=context["hash"]
            ).first():
                context["provisioning_bills"][academy.id] = provisioning_bill
                provisioning_bills.append(provisioning_bill)

            else:
                provisioning_bill = ProvisioningBill()
                provisioning_bill.academy = academy
                provisioning_bill.vendor = provisioning_vendor
                provisioning_bill.status = "PENDING"
                provisioning_bill.hash = context["hash"]
                provisioning_bill.save()

                context["provisioning_bills"][academy.id] = provisioning_bill
                provisioning_bills.append(provisioning_bill)

    provisioning_bills = list(set(provisioning_bills))

    if not (kind := context["provisioning_activity_kinds"].get(field["kind"], None)):
        kind, _ = ProvisioningConsumptionKind.objects.get_or_create(
            product_name=field["kind"],
            sku=field["kind"],
        )
        context["provisioning_activity_kinds"][field["kind"]] = kind

    if not (currency := context["currencies"].get("USD", None)):
        currency, _ = Currency.objects.get_or_create(code="USD", defaults={"name": "US Dollar", "decimals": 2})
        context["currencies"]["USD"] = currency

    if not (price := context["provisioning_activity_prices"].get(currency.id, None)):
        price, _ = ProvisioningPrice.objects.get_or_create(
            currency=currency,
            unit_type="Credits",
            price_per_unit=Decimal("0.036") * context["provisioning_multiplier"],
            multiplier=1,
        )

        context["provisioning_activity_prices"][currency.id] = price

    pa, _ = ProvisioningUserConsumption.objects.get_or_create(
        username=field["userName"], hash=context["hash"], kind=kind, defaults={"processed_at": timezone.now()}
    )

    item, _ = ProvisioningConsumptionEvent.objects.get_or_create(
        external_pk=field["id"],
        vendor=provisioning_vendor,
        price=price,
        registered_at=date,
        quantity=field["credits"],
        repository_url=field["contextURL"],
        task_associated_slug=slug,
        csv_row=position,
    )

    if pa.status == "PENDING":
        pa.status = "PERSISTED" if not errors else "ERROR"

    last_status_list = [x for x in pa.status_text.split(", ") if x]
    if errors:
        pa.status = "ERROR"
        pa.status_text = ", ".join(last_status_list + errors + warnings)

    elif warnings:
        if pa.status != "ERROR":
            pa.status = "WARNING"

        pa.status_text = ", ".join(last_status_list + warnings)

    else:
        pa.status = "PERSISTED"
        pa.status_text = ", ".join(last_status_list + errors + warnings)

    pa.status_text = ", ".join([x for x in sorted(set(pa.status_text.split(", "))) if x])
    pa.status_text = pa.status_text[:255]
    pa.save()

    current_bills = pa.bills.all()
    for provisioning_bill in provisioning_bills:
        if provisioning_bill not in current_bills:
            pa.bills.add(provisioning_bill)

    pa.events.add(item)


def add_rigobot_activity(context: ActivityContext, field: dict, position: int) -> None:
    errors = []
    warnings = []

    if field["organization"] != "4Geeks":
        return

    user = get_user(app="rigobot", sub=field["user_id"])

    if user is None:
        logger.error(f'User {field["user_id"]} not found')
        return

    # if field["billing_status"] != "OPEN":
    #     return

    github_academy_user_log = context["github_academy_user_logs"].get(user.id, None)
    date = datetime.fromisoformat(field["consumption_period_start"])
    academies = []
    not_found = False

    if github_academy_user_log is None:
        # make a function that calculate the user activity in the academies by percentage
        github_academy_user_log = GithubAcademyUserLog.objects.filter(
            Q(valid_until__isnull=True) | Q(valid_until__gte=context["limit"] - relativedelta(months=1, weeks=1)),
            created_at__lte=context["limit"],
            academy_user__user=user,
            academy_user__username=field["github_username"],
            storage_status="SYNCHED",
            storage_action="ADD",
        ).order_by("-created_at")

        context["github_academy_user_logs"][user.id] = github_academy_user_log

    if github_academy_user_log:
        academies = [x.academy_user.academy for x in github_academy_user_log]

    if not academies:
        not_found = True
        github_academy_users = GithubAcademyUser.objects.filter(
            username=field["github_username"], storage_status="PAYMENT_CONFLICT", storage_action="IGNORE"
        )

        academies = [x.academy for x in github_academy_users]

    if not academies:
        academies = handle_pending_github_user(None, field["github_username"], date)

    if not_found is False and academies:
        academies = random.choices(academies, k=1)

    logs = {}
    provisioning_bills = {}
    provisioning_vendor = None

    provisioning_vendor = context["provisioning_vendors"].get("Rigobot", None)
    if not provisioning_vendor:
        provisioning_vendor = ProvisioningVendor.objects.filter(name="Rigobot").first()
        context["provisioning_vendors"]["Rigobot"] = provisioning_vendor

    if not provisioning_vendor:
        errors.append("Provisioning vendor Rigobot not found")

    for academy in academies:
        ls = context["logs"].get((field["github_username"], academy.id), None)
        if ls is None:
            ls = get_github_academy_user_logs(academy, field["github_username"], context["limit"])
            context["logs"][(field["github_username"], academy.id)] = ls
            logs[academy.id] = ls

        provisioning_bill = context["provisioning_bills"].get(academy.id, None)
        if not provisioning_bill and (
            provisioning_bill := ProvisioningBill.objects.filter(
                academy=academy, status="PENDING", hash=context["hash"]
            ).first()
        ):
            context["provisioning_bills"][academy.id] = provisioning_bill
            provisioning_bills[academy.id] = provisioning_bill

        if not provisioning_bill:
            provisioning_bill = ProvisioningBill()
            provisioning_bill.academy = academy
            provisioning_bill.vendor = provisioning_vendor
            provisioning_bill.status = "PENDING"
            provisioning_bill.hash = context["hash"]
            provisioning_bill.save()

            context["provisioning_bills"][academy.id] = provisioning_bill
            provisioning_bills[academy.id] = provisioning_bill

    # not implemented yet
    if not_found:
        warnings.append(
            f'We could not find enough information about {field["github_username"]}, mark this user user as '
            "deleted if you don't recognize it"
        )

    s_slug = f'{field["purpose_slug"] or "no-provided"}--{field["pricing_type"].lower()}--{field["model"].lower()}'
    s_name = f'{field["purpose"]} (type: {field["pricing_type"]}, model: {field["model"]})'
    if not (kind := context["provisioning_activity_kinds"].get((s_name, s_slug), None)):
        kind, _ = ProvisioningConsumptionKind.objects.get_or_create(
            product_name=s_name,
            sku=s_slug,
        )
        context["provisioning_activity_kinds"][(s_name, s_slug)] = kind

    if not (currency := context["currencies"].get("USD", None)):
        currency, _ = Currency.objects.get_or_create(code="USD", defaults={"name": "US Dollar", "decimals": 2})
        context["currencies"]["USD"] = currency

    if not (price := context["provisioning_activity_prices"].get((field["total_spent"], field["total_tokens"]), None)):
        with localcontext(prec=10):
            price, _ = ProvisioningPrice.objects.get_or_create(
                currency=currency,
                unit_type="Tokens",
                price_per_unit=Decimal(field["total_spent"]) / Decimal(field["total_tokens"]),
                multiplier=context["provisioning_multiplier"],
            )

        context["provisioning_activity_prices"][(field["total_spent"], field["total_tokens"])] = price

    pa, _ = ProvisioningUserConsumption.objects.get_or_create(
        username=field["github_username"], hash=context["hash"], kind=kind, defaults={"processed_at": timezone.now()}
    )

    item, _ = ProvisioningConsumptionEvent.objects.get_or_create(
        vendor=provisioning_vendor,
        price=price,
        registered_at=date,
        external_pk=field["consumption_item_id"],
        quantity=field["total_tokens"],
        repository_url=None,
        task_associated_slug=None,
        csv_row=position,
    )

    last_status_list = [x for x in pa.status_text.split(", ") if x]
    if errors:
        pa.status = "ERROR"
        pa.status_text = ", ".join(last_status_list + errors + warnings)

    elif warnings:
        if pa.status != "ERROR":
            pa.status = "WARNING"

        pa.status_text = ", ".join(last_status_list + warnings)

    else:
        pa.status = "PERSISTED"
        pa.status_text = ", ".join(last_status_list + errors + warnings)

    pa.status_text = ", ".join([x for x in sorted(set(pa.status_text.split(", "))) if x])
    pa.status_text = pa.status_text[:255]
    pa.save()

    current_bills = pa.bills.all()
    for provisioning_bill in provisioning_bills.values():
        if provisioning_bill not in current_bills:
            pa.bills.add(provisioning_bill)

    pa.events.add(item)


NEXT_CHARGE_PULL_FORWARD = timedelta(hours=12)
EARLY_USE_AFTER_CONSUMABLE_CREATION = timedelta(hours=12)


def apply_early_vps_billing_alignment(vps: ProvisioningVPS) -> None:
    """
    Pull next_payment_at earlier only when all apply:
    - ServiceItem.third_party_billing_cycle is True (third-party billing e.g. Hostinger).
    - The VPS is provisioned (consumable used) within EARLY_USE_AFTER_CONSUMABLE_CREATION after the
      consumable was created (activation / grant of that consumable row).

    At most one pull-forward per subscription or plan financing: idempotency is enforced with a single
    atomic UPDATE on Subscription/PlanFinancing (filter flag False, then set flag True with F() on
    next_payment_at), so many VPS becoming ACTIVE in parallel (e.g. up to 5) cannot double-apply -12h.
    """
    if not vps.consumed_consumable_id or not vps.provisioned_at:
        return

    consumable = (
        Consumable.objects.filter(id=vps.consumed_consumable_id)
        .select_related("service_item")
        .only(
            "id",
            "created_at",
            "subscription_id",
            "plan_financing_id",
            "service_item_id",
            "service_item__third_party_billing_cycle",
        )
        .first()
    )
    if not consumable or not consumable.service_item_id:
        return

    if not getattr(consumable.service_item, "third_party_billing_cycle", False):
        return

    if vps.provisioned_at - consumable.created_at > EARLY_USE_AFTER_CONSUMABLE_CREATION:
        return

    sub_id = consumable.subscription_id
    pf_id = consumable.plan_financing_id
    if not sub_id and not pf_id:
        return

    from breathecode.payments.actions import reschedule_billing_after_vps_next_payment_pull_forward

    if sub_id:
        updated = Subscription.objects.filter(
            pk=sub_id,
            next_charge_pull_applied=False,
        ).update(
            next_payment_at=F("next_payment_at") - NEXT_CHARGE_PULL_FORWARD,
            next_charge_pull_applied=True,
        )
        if updated:
            logger.info(
                "VPS %s third_party_billing_cycle: pulled Subscription %s next_payment_at back by %s",
                vps.pk,
                sub_id,
                NEXT_CHARGE_PULL_FORWARD,
            )
            reschedule_billing_after_vps_next_payment_pull_forward(subscription_id=sub_id)
        return

    updated = PlanFinancing.objects.filter(
        pk=pf_id,
        next_charge_pull_applied=False,
    ).update(
        next_payment_at=F("next_payment_at") - NEXT_CHARGE_PULL_FORWARD,
        next_charge_pull_applied=True,
    )
    if updated:
        logger.info(
            "VPS %s third_party_billing_cycle: pulled PlanFinancing %s next_payment_at back by %s",
            vps.pk,
            pf_id,
            NEXT_CHARGE_PULL_FORWARD,
        )
        reschedule_billing_after_vps_next_payment_pull_forward(plan_financing_id=pf_id)


@service_deprovisioner("free-monthly-llm-budget")
def deprovision_free_monthly_llm_budget(user_id: int, context: dict | None = None, **_: Any):
    """
    Deprovision the free monthly LLM budget for the given user and academy.
    """
    # The signal receiver calls handlers synchronously; keep this handler lightweight.
    from breathecode.provisioning.tasks import deprovision_litellm_user_task

    academy_id = None
    if isinstance(context, dict):
        academy_id = context.get("academy_id") or context.get("academy")
    deprovision_litellm_user_task.delay(user_id=user_id, academy_id=academy_id)


@service_deprovisioner("vps_server")
def deprovision_vps_server(user_id: int, context: dict | None = None, **_: Any):
    """
    Deprovision VPS instances for a user when vps_server entitlement is lost.
    """
    # Keep receiver fast: enqueue one task per VPS instead of destroying synchronously.
    from breathecode.provisioning.tasks import deprovision_vps_task

    if isinstance(context, dict) and context.get("provisioning_vps_ids"):
        for raw_id in context["provisioning_vps_ids"]:
            deprovision_vps_task.delay(int(raw_id))
        return

    academy_id = None
    if isinstance(context, dict):
        academy_id = context.get("academy_id") or context.get("academy")
    if academy_id is not None:
        try:
            academy_id = int(academy_id)
        except Exception:
            academy_id = None

    statuses = [
        ProvisioningVPS.VPS_STATUS_PENDING,
        ProvisioningVPS.VPS_STATUS_PROVISIONING,
        ProvisioningVPS.VPS_STATUS_ACTIVE,
    ]
    vps_qs = ProvisioningVPS.objects.filter(user_id=user_id, status__in=statuses)
    if academy_id:
        vps_qs = vps_qs.filter(academy_id=academy_id)

    for vps_id in vps_qs.values_list("id", flat=True):
        deprovision_vps_task.delay(vps_id)
