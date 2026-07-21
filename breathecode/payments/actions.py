import json
import os
import re
import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import ROUND_FLOOR, Decimal
from functools import lru_cache
from typing import Any, Literal, Optional, Tuple, Type, TypedDict, Union

import redis
import redis.lock
from adrf.requests import AsyncRequest
from capyc.core.i18n import translation
from capyc.rest_framework.exceptions import ValidationException
from dateutil.relativedelta import relativedelta
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.handlers.wsgi import WSGIRequest
from django.db import transaction
from django.db.models import F, Q, QuerySet, Sum
from django.http import HttpRequest
from django.utils import timezone
from django_redis import get_redis_connection
from pytz import UTC
from rest_framework.request import Request
from task_manager.core.exceptions import AbortTask, RetryTask
from task_manager.django.actions import schedule_task

from breathecode.admissions import tasks as admissions_tasks
from breathecode.admissions.models import Academy, Cohort, CohortUser, Syllabus
from breathecode.authenticate.actions import get_app_url, get_invite_url, get_user_settings
from breathecode.authenticate.models import Role, UserInvite, UserSetting
from breathecode.marketing.actions import validate_email_local
from breathecode.media.models import File
from breathecode.monitoring.models import StripeEvent
from breathecode.notify import actions as notify_actions
from breathecode.payments import tasks
from breathecode.payments.signals import consume_service, deprovision_service
from breathecode.utils import getLogger
from breathecode.utils.decorators.service_deprovisioner import get_service_deprovisioner
from breathecode.utils.validate_conversion_info import validate_conversion_info
from settings import GENERAL_PRICING_RATIOS

from .models import (
    DAY,
    MONTH,
    PAY_EVERY_UNIT,
    SERVICE_UNITS,
    WEEK,
    YEAR,
    AbstractIOweYou,
    AcademyPaymentSettings,
    AcademyService,
    Bag,
    CohortSet,
    CohortSetCohort,
    Consumable,
    Coupon,
    CreditLedgerEntry,
    CreditNote,
    Currency,
    EventTypeSet,
    FinancingOption,
    Invoice,
    MentorshipServiceSet,
    PaymentMethod,
    Plan,
    PlanFinancing,
    PlanFinancingSeat,
    PlanFinancingTeam,
    PlanServiceItem,
    ProofOfPayment,
    Service,
    ServiceItem,
    Subscription,
    SubscriptionBillingTeam,
    SubscriptionSeat,
)

logger = getLogger(__name__)

# Schedule charge tasks a few seconds after `next_payment_at` so execution time is strictly
# past the deadline (avoids clock skew and ``next_payment_at > utc_now`` in charge tasks).
SCHEDULE_CHARGE_LAG_AFTER_NEXT_PAYMENT = timedelta(seconds=3)


def sync_micro_cohorts_into_cohort_sets(macro: Cohort, micro_pks: Iterable[int]) -> None:
    """
    Add newly linked micro cohorts to every CohortSet that already contains the macro.

    Only adds; never removes micros from a set when they are unlinked from the macro.
    Micros that fail CohortSetCohort validation (e.g. not available as SaaS) are skipped.
    """
    micro_pk_list = list(micro_pks)
    if not micro_pk_list:
        return

    cohort_sets = CohortSet.objects.filter(cohorts=macro)
    if not cohort_sets.exists():
        return

    micros = list(Cohort.objects.filter(pk__in=micro_pk_list))
    if not micros:
        return

    for cohort_set in cohort_sets:
        for micro in micros:
            if CohortSetCohort.objects.filter(cohort_set=cohort_set, cohort=micro).exists():
                continue
            try:
                CohortSetCohort(cohort_set=cohort_set, cohort=micro).save()
            except ValidationError as e:
                logger.warning(
                    "Skipping micro cohort %s for cohort set %s after linking to macro %s: %s",
                    micro.id,
                    cohort_set.id,
                    macro.id,
                    e,
                )


def _cancel_pending_future_scheduled(task_callable: Any, entity_id: int, *, utc_now: datetime) -> None:
    from task_manager.core.actions import get_fn_desc, parse_payload
    from task_manager.django.models import ScheduledTask

    module_name, function_name = get_fn_desc(task_callable)
    if not module_name or not function_name:
        return
    arguments = parse_payload({"args": [entity_id], "kwargs": {}})
    ScheduledTask.objects.filter(
        task_module=module_name,
        task_name=function_name,
        arguments=arguments,
        status="PENDING",
        eta__gte=utc_now,
    ).update(status="CANCELLED")


def _eta_for_schedule_at(target: datetime, utc_now: datetime) -> str:
    """
    Build an :mod:`celery_task_manager` eta (``"{n}{unit}"`` with a single unit) so
    that ``utc_now + delta`` ≈ ``target`` (the manager only allows one of ``s|m|h|d|w``).

    Using **seconds** gives a precise wall-clock ``eta``; callers that schedule charges
    should pass ``next_payment_at + SCHEDULE_CHARGE_LAG_AFTER_NEXT_PAYMENT`` as ``target``
    so :func:`breathecode.payments.tasks.charge_subscription` does not abort with
    ``next_payment_at`` still in the future.
    """
    if target <= utc_now:
        return "60s"
    total_seconds = int((target - utc_now).total_seconds())
    if total_seconds < 1:
        return "1s"
    return f"{total_seconds}s"


def resolve_grant_valid_until(
    duration: int | str | None,
    duration_unit: str | None,
    lang: str,
    service: Service,
) -> Optional[datetime]:
    """
    Compute consumable ``valid_until`` from grant ``duration`` and ``duration_unit``.

    If both are omitted (``None``), returns ``None`` unless the service has a deprovisioner (then both are
    required). If only one is set, raises ``ValidationException``.

    When ``service`` has a deprovisioner, subtract one hour so scheduled teardown at ``valid_until``
    matches loss of entitlement in ``Consumable.list``.
    """
    slug = service.slug
    has_deprovisioner = bool(slug and get_service_deprovisioner(slug))

    if duration is None and duration_unit is None:
        if has_deprovisioner:
            raise ValidationException(
                translation(
                    lang,
                    en="duration and duration_unit are required for this service",
                    es="duration y duration_unit son obligatorios para este servicio",
                    slug="duration-required-for-deprovisioned-service",
                ),
                code=400,
            )
        return None
    if duration is None or duration_unit is None:
        raise ValidationException(
            translation(
                lang,
                en="duration and duration_unit must be sent together",
                es="duration y duration_unit deben enviarse juntos",
                slug="incomplete-duration",
            ),
            code=400,
        )

    allowed_units = {choice[0] for choice in PAY_EVERY_UNIT}

    try:
        duration = int(duration)
    except (TypeError, ValueError):
        raise ValidationException(
            translation(
                lang,
                en="duration must be a positive integer",
                es="duration debe ser un entero positivo",
                slug="invalid-duration",
            ),
            code=400,
        )

    if duration <= 0:
        raise ValidationException(
            translation(
                lang,
                en="duration must be a positive integer",
                es="duration debe ser un entero positivo",
                slug="invalid-duration",
            ),
            code=400,
        )

    if not isinstance(duration_unit, str):
        raise ValidationException(
            translation(
                lang,
                en="duration_unit must be a string",
                es="duration_unit debe ser una cadena",
                slug="invalid-duration-unit-type",
            ),
            code=400,
        )
    unit = duration_unit.strip().upper()

    if unit not in allowed_units:
        allowed = ", ".join(sorted(allowed_units))
        raise ValidationException(
            translation(
                lang,
                en=f"duration_unit must be one of {allowed}",
                es=f"duration_unit debe ser uno de {allowed}",
                slug="invalid-duration-unit",
            ),
            code=400,
        )

    valid_until = timezone.now() + calculate_relative_delta(duration, unit)
    if has_deprovisioner:
        return valid_until - timedelta(hours=1)
    return valid_until


def user_has_service_entitlement_in_academy(
    user: User,
    service: Service | str,
    academy_id: int,
) -> bool:
    """Whether the user still has active consumables for ``service`` in ``academy_id``."""

    def _has(extra: dict) -> bool:
        return Consumable.list(user=user, service=service, extra=extra).exists()

    return (
        _has({"subscription__academy_id": academy_id})
        or _has({"plan_financing__academy_id": academy_id})
        or _has({"standalone_invoice__bag__academy_id": academy_id})
    )


def schedule_standalone_consumable_deprovision(consumable_id: int, valid_until: datetime, service: Service) -> None:
    """
    Schedule ``deprovision_standalone_consumable`` at ``valid_until`` for VOID services with a deprovisioner.

    ``valid_until`` on the consumable is already adjusted at grant time when a deprovisioner exists.
    """
    from breathecode.provisioning.tasks import deprovision_standalone_consumable

    if service.type != Service.Type.VOID:
        return

    slug = service.slug
    if not slug or not get_service_deprovisioner(slug):
        return

    utc_now = timezone.now()
    run_at = valid_until

    _cancel_pending_future_scheduled(deprovision_standalone_consumable, consumable_id, utc_now=utc_now)

    eta = _eta_for_schedule_at(run_at, utc_now)
    schedule_task(deprovision_standalone_consumable, eta).call(consumable_id)


def _vps_alignment_billing_scope(consumable: Consumable) -> dict | None:
    """
    Misma suscripción/plan/asiento (o team) que el consumible renovado.

    Evita alinear créditos y máquinas a nivel usuario entero: si el plan A renueva
    y el plan B sigue sin filas con saldo, no debemos deprovisionar VPS cargados
    al consumible del plan B.
    """
    if consumable.subscription_id:
        scope: dict[str, bool | int] = {"subscription_id": consumable.subscription_id}
        if consumable.subscription_seat_id:
            scope["subscription_seat_id"] = consumable.subscription_seat_id
        else:
            scope["subscription_seat__isnull"] = True
        return scope

    if consumable.plan_financing_id:
        scope_pf: dict[str, bool | int] = {"plan_financing_id": consumable.plan_financing_id}
        if consumable.plan_financing_seat_id:
            scope_pf["plan_financing_seat_id"] = consumable.plan_financing_seat_id
        else:
            scope_pf["plan_financing_seat__isnull"] = True
        return scope_pf

    if consumable.subscription_billing_team_id:
        return {"subscription_billing_team_id": consumable.subscription_billing_team_id}

    if consumable.plan_financing_team_id:
        return {"plan_financing_team_id": consumable.plan_financing_team_id}

    return None


def align_consumer_vps_stock_with_active_machines(consumable: Consumable) -> None:
    """VPS consumer: equilibrar máquinas ACTIVE vs créditos del mismo contexto de facturación; señales de deprovision/pre-consume."""
    from breathecode.provisioning.models import ProvisioningVPS

    current_consumable = (
        Consumable.objects.filter(pk=consumable.pk)
        .select_related("service_item__service", "user", "subscription_seat__user", "plan_financing_seat__user")
        .first()
    )
    if (
        not current_consumable
        or current_consumable.service_item.service.consumer != Service.Consumer.VPS_SERVER
        or current_consumable.service_item.how_many <= 0
    ):
        return

    user = current_consumable.user or (
        current_consumable.subscription_seat.user
        if current_consumable.subscription_seat_id and current_consumable.subscription_seat.user_id
        else None
    ) or (
        current_consumable.plan_financing_seat.user
        if current_consumable.plan_financing_seat_id and current_consumable.plan_financing_seat.user_id
        else None
    )
    if not user:
        return

    user_id = user.id
    active_vps_status = ProvisioningVPS.VPS_STATUS_ACTIVE
    billing_scope = _vps_alignment_billing_scope(current_consumable)
    consumer_extra = {"service_item__service__consumer": Service.Consumer.VPS_SERVER}

    if billing_scope:
        consumer_extra.update(billing_scope)

    vps_scope_kwargs = (
        {f"consumed_consumable__{key}": value for key, value in billing_scope.items()}
        if billing_scope
        else {}
    )

    credit_sum = Consumable.list(
        user=user_id,
        include_zero_balance=False,
        extra=consumer_extra,
    ).aggregate(total_units=Sum("how_many"))["total_units"]

    total_credits = int(credit_sum or 0)
    active_machine_count = ProvisioningVPS.objects.filter(
        user_id=user_id,
        status=active_vps_status,
        **vps_scope_kwargs,
    ).count()

    if active_machine_count > total_credits:
        excess = active_machine_count - total_credits
        vps_ids_to_deprovision = list(
            ProvisioningVPS.objects.filter(user_id=user_id, status=active_vps_status, **vps_scope_kwargs)
            .order_by("-provisioned_at", "-id")
            .values_list("id", flat=True)[:excess]
        )
        if vps_ids_to_deprovision:
            deprovision_service.send_robust(
                sender=Service,
                instance=current_consumable.service_item.service,
                user_id=user_id,
                context={"provisioning_vps_ids": vps_ids_to_deprovision},
            )

    current_consumable.refresh_from_db()
    active_after = ProvisioningVPS.objects.filter(
        user_id=user_id,
        status=active_vps_status,
        **vps_scope_kwargs,
    ).count()

    pre_consume_units = min(active_after, current_consumable.how_many)
    if pre_consume_units > 0:
        consume_service.send_robust(sender=Consumable, instance=current_consumable, how_many=pre_consume_units)


def sync_llm_member_budget_to_llm_provider(
    provisioning_llm,
    provisioning_academy,
    client,
    *,
    team_data: dict | None = None,
) -> None:
    """
    Push the user's LiteLLM team member budget to match consumables.

    Sums active llm-budget consumables for the provisioning user and academy, then sets
    ``max_budget_in_team`` to current LiteLLM spend plus that pool (USD). Also applies
    tpm/rpm from the team template and records sync metadata on ``ProvisioningLLM``.

    When ``team_data`` is provided (e.g. from ``align_llm_member_budget_with_consumables``),
    skips ``GET /team/info``.
    """

    def _skip_budget_sync(message: str) -> None:
        logger.warning(message)
        provisioning_llm.last_budget_sync_error = message[:255]
        provisioning_llm.save(update_fields=["last_budget_sync_error", "updated_at"])

    vendor_settings = provisioning_academy.vendor_settings or {}
    team_id = str(vendor_settings.get("team_id") or "").strip()
    if not team_id:
        _skip_budget_sync(f"LLM budget sync skipped: academy {provisioning_academy.id} has no LiteLLM team_id")
        return

    external_user_id = provisioning_llm.external_user_id
    if not external_user_id:
        _skip_budget_sync(
            f"LLM budget sync skipped: ProvisioningLLM {provisioning_llm.id} has no external_user_id"
        )
        return

    if provisioning_llm.litellm_team_id and provisioning_llm.litellm_team_id != team_id:
        # Academy team_id changed since last sync: zero the spend cursor and store the new team.
        logger.warning(
            "LiteLLM team_id changed for ProvisioningLLM %s (%s -> %s); resetting last_known_spend",
            provisioning_llm.id,
            provisioning_llm.litellm_team_id,
            team_id,
        )
        provisioning_llm.last_known_spend = Decimal("0")
        provisioning_llm.litellm_team_id = team_id
        provisioning_llm.save(update_fields=["last_known_spend", "litellm_team_id", "updated_at"])

    if team_data is None:
        team_data = client.get_team_info(team_id=team_id)

    membership = None
    for row in team_data.get("team_memberships") or []:
        if row["user_id"] == external_user_id:
            membership = row
            break
    if membership is None:
        is_team_member = False
        for row in ((team_data.get("team_info") or {}).get("members_with_roles") or []):
            if isinstance(row, dict) and row.get("user_id") == external_user_id:
                is_team_member = True
                break

        if not is_team_member:
            _skip_budget_sync(
                f"LLM budget sync skipped: member {external_user_id} not in team_memberships for team {team_id}"
            )
            return

        membership = {
            "user_id": external_user_id,
            "spend": 0,
            "litellm_budget_table": {},
        }

    member_spend = Decimal(str(membership["spend"]))

    academy_id = provisioning_llm.academy_id
    utc_now = timezone.now()
    sub_cutoff = utc_now + timedelta(hours=1)
    pf_cutoff = utc_now + timedelta(hours=2)

    # Calculate the total budget to grant in the LLM provider.
    # Exclude consumables in the renew rollover window (subscription 1h, PF 2h).
    budget_total = (
        Consumable.list(
            user=provisioning_llm.user_id,
            service="llm-budget",
            include_zero_balance=False,
        )
        .filter(
            Q(subscription__academy_id=academy_id)
            | Q(plan_financing__academy_id=academy_id)
            | Q(standalone_invoice__bag__academy_id=academy_id)
            | Q(subscription_seat__billing_team__subscription__academy_id=academy_id)
            | Q(plan_financing_seat__team__financing__academy_id=academy_id)
        )
        .filter(
            Q(subscription__isnull=False)
            & (Q(valid_until__isnull=True) | Q(valid_until__gt=sub_cutoff))
            | Q(subscription_seat__isnull=False)
            & (Q(valid_until__isnull=True) | Q(valid_until__gt=sub_cutoff))
            | Q(plan_financing__isnull=False)
            & (Q(valid_until__isnull=True) | Q(valid_until__gt=pf_cutoff))
            | Q(plan_financing_seat__isnull=False)
            & (Q(valid_until__isnull=True) | Q(valid_until__gt=pf_cutoff))
            | Q(standalone_invoice__isnull=False)
        )
        .aggregate(total=Sum("how_many"))["total"]
    )

    budget_cents_to_grant = int(budget_total or 0)
    if budget_cents_to_grant <= 0:
        _skip_budget_sync(
            f"LLM budget sync skipped: user {provisioning_llm.user_id} "
            f"has no active llm-budget balance in academy {academy_id}"
        )
        return

    team_info = team_data.get("team_info")
    if team_info and team_info.get("team_member_budget_table"):
        team_member_budget_table = team_info["team_member_budget_table"]
        member_tpm = team_member_budget_table.get("tpm_limit")
        member_rpm = team_member_budget_table.get("rpm_limit")
    else:
        member_budget = membership.get("litellm_budget_table") or {}
        member_tpm = member_budget.get("tpm_limit")
        member_rpm = member_budget.get("rpm_limit")

    # LiteLLM spend is cumulative: this cap is the member's total allowed spend in USD
    # (current spend plus the llm-budget pool we are granting from BreatheCode consumables).
    member_max_budget_in_team = member_spend + (Decimal(budget_cents_to_grant) / 100)

    try:
        client.update_team_member(
            team_id=team_id,
            user_id=external_user_id,
            max_budget_in_team=member_max_budget_in_team,
            budget_duration=None,
            tpm_limit=member_tpm,
            rpm_limit=member_rpm,
        )
    except Exception as exc:
        provisioning_llm.last_budget_sync_error = str(exc)[:255]
        provisioning_llm.save(update_fields=["last_budget_sync_error", "updated_at"])
        raise

    provisioning_llm.last_known_spend = member_spend
    provisioning_llm.litellm_team_id = team_id
    provisioning_llm.last_budget_sync_at = utc_now
    provisioning_llm.last_budget_sync_error = ""
    provisioning_llm.save()

    logger.info(
        "Aligned LLM member budget with LLM provider:user=%s academy=%s team=%s spend=%s max=%s budget_cents_to_grant=%s",
        provisioning_llm.user_id,
        provisioning_llm.academy_id,
        team_id,
        member_spend,
        member_max_budget_in_team,
        budget_cents_to_grant,
    )


def align_llm_member_budget_with_consumables(consumable: Consumable) -> None:
    """
    Runs after a new llm-budget consumable is issued on renew.

    Reads how much the user spent in LLM provider since the last sync and subtracts that
    amount from their llm-budget consumables in the academy (oldest first). Then updates
    LLM provider so their budget cap reflects current spend plus active consumables.
    """
    from breathecode.provisioning.actions import resolve_llm_provisioning_context

    current_consumable = (
        Consumable.objects.filter(pk=consumable.pk)
        .select_related(
            "service_item__service",
            "user",
            "subscription",
            "plan_financing",
            "subscription_seat__user",
            "plan_financing_seat__user",
        )
        .first()
    )
    if not current_consumable or current_consumable.service_item.service.consumer != Service.Consumer.LLM_BUDGET:
        return

    user = current_consumable.user or (
        current_consumable.subscription_seat.user
        if current_consumable.subscription_seat_id and current_consumable.subscription_seat.user_id
        else None
    ) or (
        current_consumable.plan_financing_seat.user
        if current_consumable.plan_financing_seat_id and current_consumable.plan_financing_seat.user_id
        else None
    )
    if not user:
        return

    academy_id = None
    if current_consumable.subscription_id and current_consumable.subscription.academy_id:
        academy_id = current_consumable.subscription.academy_id
    elif current_consumable.plan_financing_id and current_consumable.plan_financing.academy_id:
        academy_id = current_consumable.plan_financing.academy_id
    if not academy_id:
        return

    ctx = resolve_llm_provisioning_context(user, academy_id)
    if not ctx:
        return

    provisioning_llm, provisioning_academy, client = ctx
    vendor_settings = provisioning_academy.vendor_settings or {}
    team_id = str(vendor_settings.get("team_id") or "").strip()
    external_user_id = provisioning_llm.external_user_id

    if provisioning_llm.litellm_team_id and provisioning_llm.litellm_team_id != team_id:
        # Academy team_id changed since last sync: zero the spend cursor and store the new team.
        logger.warning(
            "LiteLLM team_id changed for ProvisioningLLM %s (%s -> %s); resetting last_known_spend",
            provisioning_llm.id,
            provisioning_llm.litellm_team_id,
            team_id,
        )
        provisioning_llm.last_known_spend = Decimal("0")
        provisioning_llm.litellm_team_id = team_id
        provisioning_llm.save(update_fields=["last_known_spend", "litellm_team_id", "updated_at"])

    team_data = client.get_team_info(team_id=team_id)
    membership = None
    for row in team_data["team_memberships"]:
        if row["user_id"] == external_user_id:
            membership = row
            break
    if not membership:
        return  # User not on the academy's configured LiteLLM team yet.

    member_spend = Decimal(str(membership["spend"]))

    # LiteLLM spend not yet reflected on consumables since last_known_spend.
    unreconciled_spend_cents = int((member_spend - provisioning_llm.last_known_spend) * 100)

    if unreconciled_spend_cents > 0:
        for consumable in (
            Consumable.list(
                user=user.id,
                service="llm-budget",
                include_zero_balance=False,
            )
            .filter(
                Q(subscription__academy_id=academy_id)
                | Q(plan_financing__academy_id=academy_id)
                | Q(standalone_invoice__bag__academy_id=academy_id)
                | Q(subscription_seat__billing_team__subscription__academy_id=academy_id)
                | Q(plan_financing_seat__team__financing__academy_id=academy_id)
            )
            .exclude(pk=current_consumable.pk)
            .order_by("valid_until", "id")
        ):
            if unreconciled_spend_cents <= 0:
                break

            # LiteLLM may have used more than this row can cover, or more than one row is needed (FEFO).
            # min: use the row's full balance when unreconciled usage is larger; otherwise only the leftover usage.
            consumption_cents = min(consumable.how_many, unreconciled_spend_cents)
            consume_service.send_robust(sender=Consumable, instance=consumable, how_many=consumption_cents)
            unreconciled_spend_cents -= consumption_cents

    provisioning_llm.last_known_spend = member_spend
    provisioning_llm.save()

    try:
        sync_llm_member_budget_to_llm_provider(
            provisioning_llm,
            provisioning_academy,
            client,
            team_data=team_data,
        )
    except Exception as exc:
        logger.error(
            "LLM budget renew sync failed user=%s academy=%s: %s",
            user.id,
            academy_id,
            exc,
        )


def reschedule_billing_tasks(
    *, subscription_id: int | None = None, plan_financing_id: int | None = None
) -> None:
    """
    After ``Subscription`` or ``PlanFinancing`` ``next_payment_at`` changes (e.g. manual deposit,
    VPS / third-party billing alignment), cancel future PENDING ``ScheduledTask`` rows for charge
    and renewal notify, then recreate them with an ETA aligned to the current ``next_payment_at``
    plus a short lag (seconds), so charges do not run before the payment instant.
    """
    from task_manager.django.actions import schedule_task

    utc_now = timezone.now()

    if subscription_id is not None:
        subscription = Subscription.objects.filter(pk=subscription_id).first()
        if not subscription:
            return

        for fn in (tasks.charge_subscription, tasks.notify_subscription_renewal):
            _cancel_pending_future_scheduled(fn, subscription_id, utc_now=utc_now)

        charge_at = subscription.next_payment_at + SCHEDULE_CHARGE_LAG_AFTER_NEXT_PAYMENT
        charge_eta = _eta_for_schedule_at(charge_at, utc_now)
        manager = schedule_task(tasks.charge_subscription, charge_eta)
        manager.call(subscription_id)

        payment_settings = AcademyPaymentSettings.objects.filter(academy=subscription.academy).first()
        early_renewal_window_days = payment_settings.early_renewal_window_days if payment_settings else 0

        if early_renewal_window_days > 0:
            notify_at = subscription.next_payment_at - timedelta(days=early_renewal_window_days)
            
            if notify_at > utc_now:
                notify_eta = _eta_for_schedule_at(notify_at, utc_now)
                schedule_task(tasks.notify_subscription_renewal, notify_eta).call(subscription_id)
        return

    if plan_financing_id is None:
        return

    plan_financing = PlanFinancing.objects.filter(pk=plan_financing_id).first()
    if not plan_financing:
        return

    for fn in (tasks.charge_plan_financing, tasks.notify_plan_financing_renewal):
        _cancel_pending_future_scheduled(fn, plan_financing_id, utc_now=utc_now)

    pf_charge_at = plan_financing.next_payment_at + SCHEDULE_CHARGE_LAG_AFTER_NEXT_PAYMENT
    pf_charge_eta = _eta_for_schedule_at(pf_charge_at, utc_now)
    schedule_task(tasks.charge_plan_financing, pf_charge_eta).call(plan_financing_id)

    if (plan_financing.next_payment_at - utc_now) > timedelta(days=2):
        notify_at = plan_financing.next_payment_at - timedelta(days=2)
        if notify_at > utc_now:
            pf_notify_eta = _eta_for_schedule_at(notify_at, utc_now)
            schedule_task(tasks.notify_plan_financing_renewal, pf_notify_eta).call(plan_financing_id)


def _raise_if_task_manager_failed(task_handler: Any) -> None:
    task_manager = getattr(task_handler, "task_manager", None)
    if task_manager is None:
        return

    if task_manager.status in ["ERROR", "ABORTED"]:
        message = task_manager.status_message or "Task execution failed"
        raise Exception(message)


def calculate_relative_delta(unit: float, unit_type: str):
    delta_args = {}
    if unit_type == "DAY":
        delta_args["days"] = unit

    elif unit_type == "WEEK":
        delta_args["weeks"] = unit

    elif unit_type == "MONTH":
        delta_args["months"] = unit

    elif unit_type == "YEAR":
        delta_args["years"] = unit

    return relativedelta(**delta_args)


class PlanFinder:
    cohort: Optional[Cohort] = None
    syllabus: Optional[Syllabus] = None

    def __init__(self, request: Request, lang: Optional[str] = None, query: Optional[Q] = None) -> None:
        self.request = request
        self.query = query

        if lang:
            self.lang = lang

        else:
            self.lang = request.META.get("HTTP_ACCEPT_LANGUAGE")

        if not self.lang and request.user.id:
            settings = get_user_settings(request.user.id)
            self.lang = settings.lang

        if not self.lang:
            self.lang = "en"

        self.academy_slug = request.GET.get("academy") or request.data.get("academy")

        if cohort := request.GET.get("cohort") or request.data.get("cohort"):
            self.cohort = self._get_instance(Cohort, cohort, self.academy_slug)

        if syllabus := request.GET.get("syllabus") or request.data.get("syllabus"):
            self.syllabus = self._get_instance(Syllabus, syllabus, self.academy_slug)

    def _get_pk(self, pk):
        if isinstance(pk, int) or pk.isnumeric():
            return int(pk)

        return 0

    def _get_instance(
        self, model: Type[Cohort | Syllabus], pk: str, academy: Optional[str] = None
    ) -> Optional[Cohort | Syllabus]:
        args = []
        kwargs = {}

        if isinstance(pk, int) or pk.isnumeric():
            kwargs["id"] = int(pk)
        else:
            kwargs["slug"] = pk

        if academy and model == Syllabus:
            args.append(Q(academy_owner__slug=academy) | Q(academy_owner__id=self._get_pk(academy)) | Q(private=False))

        elif academy and model == Cohort:
            args.append(Q(academy__slug=academy) | Q(academy__id=self._get_pk(academy)))

        resource = model.objects.filter(*args, **kwargs).first()
        if not resource:
            raise ValidationException(
                translation(
                    self.lang,
                    en=f"{model.__name__} not found",
                    es=f"{model.__name__} no encontrada",
                    slug=f"{model.__name__.lower()}-not-found",
                )
            )

        return resource

    def _cohort_handler(self, on_boarding: Optional[bool] = None, auto: bool = False):
        additional_args = {}

        if on_boarding is not None:
            additional_args["is_onboarding"] = on_boarding

        if not self.cohort.syllabus_version:
            return Plan.objects.none()

        if not additional_args and auto:
            additional_args["is_onboarding"] = not CohortUser.objects.filter(
                cohort__syllabus_version__syllabus=self.cohort.syllabus_version.syllabus
            ).exists()

        args = (self.query,) if self.query else tuple()
        plans = Plan.objects.filter(
            *args,
            cohort_set__cohorts__id=self.cohort.id,
            cohort_set__cohorts__stage__in=["INACTIVE", "PREWORK", "STARTED"],
            **additional_args,
        ).distinct()

        return plans

    def _syllabus_handler(self, on_boarding: Optional[bool] = None, auto: bool = False):
        additional_args = {}

        if on_boarding is not None:
            additional_args["is_onboarding"] = on_boarding

        if not additional_args and auto:
            additional_args["is_onboarding"] = not CohortUser.objects.filter(
                cohort__syllabus_version__syllabus=self.syllabus
            ).exists()

        args = (self.query,) if self.query else tuple()
        plans = Plan.objects.filter(
            *args,
            cohort_set__cohorts__syllabus_version__syllabus=self.syllabus,
            cohort_set__cohorts__stage__in=["INACTIVE", "PREWORK"],
            **additional_args,
        ).distinct()

        return plans

    def get_plans_belongs(self, on_boarding: Optional[bool] = None, auto: bool = False):
        if self.syllabus:
            return self._syllabus_handler(on_boarding, auto)

        if self.cohort:
            return self._cohort_handler(on_boarding, auto)

        raise NotImplementedError("Resource handler not implemented")

    def get_plans_belongs_from_request(self):
        is_onboarding = self.request.data.get("is_onboarding") or self.request.GET.get("is_onboarding")

        additional_args = {}

        if is_onboarding:
            additional_args["is_onboarding"] = is_onboarding

        if not additional_args:
            additional_args["auto"] = True

        return self.get_plans_belongs(**additional_args)


def ask_to_add_plan_and_charge_it_in_the_bag(
    plan: Plan,
    user: User,
    lang: str,
    early_renewal_subscription: Optional["Subscription"] = None,
):
    """
    Ask to add plan to bag, and return if it must be charged or not.
    """
    utc_now = timezone.now()
    plan_have_free_trial = plan.trial_duration and plan.trial_duration_unit

    if plan.is_renewable:
        price = plan.price_per_month or plan.price_per_quarter or plan.price_per_half or plan.price_per_year

    else:
        price = not plan.is_renewable and plan.financing_options.exists()

    subscriptions = Subscription.objects.filter(user=user, plans=plan)

    # avoid bought a free trial for financing if this was bought before
    if not price and plan_have_free_trial and not plan.is_renewable and subscriptions.filter(valid_until__gte=utc_now):
        raise ValidationException(
            translation(
                lang,
                en="Free trial plans can't be bought again",
                es="Los planes de prueba no pueden ser comprados de nuevo",
                slug="free-trial-plan-for-financing",
            ),
            code=400,
        )

    # avoid bought a plan if it doesn't have a price yet after free trial
    if not price and subscriptions:
        raise ValidationException(
            translation(
                lang,
                en="Free trial plans can't be bought more than once",
                es="Los planes de prueba no pueden ser comprados más de una vez",
                slug="free-trial-already-bought",
            ),
            code=400,
        )

    # avoid financing plans if it was financed before
    if not plan.is_renewable and PlanFinancing.objects.filter(user=user, plans=plan):
        raise ValidationException(
            translation(
                lang,
                en="You already have or had a financing on this plan",
                es="Ya tienes o tuviste un financiamiento en este plan",
                slug="plan-already-financed",
            ),
            code=400,
        )

    # avoid to buy a plan if exists a subscription with same plan with remaining days, except for early renewals
    active_subscriptions = subscriptions.filter(
        Q(valid_until=None, next_payment_at__gte=utc_now) | Q(valid_until__gte=utc_now)
    ).exclude(status__in=["CANCELLED", "DEPRECATED", "EXPIRED"])

    if price and plan.is_renewable and active_subscriptions.exists():
        if early_renewal_subscription:
            if active_subscriptions.count() == 1:
                active_sub = active_subscriptions.first()
                if active_sub.id != early_renewal_subscription.id:
                    raise ValidationException(
                        translation(
                            lang,
                            en="You already have a different subscription to this plan",
                            es="Ya tienes una suscripción diferente a este plan",
                            slug="different-subscription-exists",
                        ),
                        code=400,
                    )
                # The active subscription IS the one being renewed - allow it (continue)
            else:
                raise ValidationException(
                    translation(
                        lang,
                        en="Multiple active subscriptions found for this plan",
                        es="Múltiples suscripciones activas encontradas para este plan",
                        slug="multiple-active-subscriptions",
                    ),
                    code=400,
                )
        else:
            # Not an early renewal - reject if any active subscription exists
            raise ValidationException(
                translation(
                    lang,
                    en="You already have a subscription to this plan",
                    es="Ya tienes una suscripción a este plan",
                    slug="plan-already-bought",
                ),
                code=400,
            )

    # avoid to charge a plan if it has a free trial and was not bought before
    if not price or (plan_have_free_trial and not subscriptions.exists()):
        return False

    # charge a plan if it has a price
    return bool(price)


class BagHandler:

    def __init__(self, request: Request, bag: Bag, lang: str) -> None:
        self.request = request
        self.lang = lang
        self.bag = bag

        self.service_items = request.data.get("service_items")
        self.plans = request.data.get("plans")
        self.plan_addons = request.data.get("plan_addons")
        self.selected_cohort_set = request.data.get("cohort_set")
        self.selected_event_type_set = request.data.get("event_type_set")
        self.selected_mentorship_service_set = request.data.get("mentorship_service_set")
        self.country_code = request.data.get("country_code")
        # NEW: team seats for seat add-ons
        self.team_seats = request.data.get("team_seats")

        self.plans_not_found = set()
        self.plan_addons_not_found = set()
        self.service_items_not_found = set()
        self.cohort_sets_not_found = set()

    def _lookups(self, value, offset=""):
        args = ()
        kwargs = {}
        slug_key = f"{offset}slug__in"
        pk_key = f"{offset}id__in"

        values = value.split(",") if isinstance(value, str) and "," in value else [value]
        for v in values:
            if slug_key not in kwargs and (not isinstance(v, str) or not v.isnumeric()):
                kwargs[slug_key] = []

            if pk_key not in kwargs and (isinstance(v, int) or v.isnumeric()):
                kwargs[pk_key] = []

            if isinstance(v, int) or v.isnumeric():
                kwargs[pk_key].append(int(v))

            else:
                kwargs[slug_key].append(v)

        if len(kwargs) > 1:
            args = (Q(**{slug_key: kwargs[slug_key]}) | Q(**{pk_key: kwargs[pk_key]}),)
            kwargs = {}

        return args, kwargs

    def _more_than_one_generator(self, en, es):
        return translation(
            self.lang,
            en=f"You can only select one {en}",
            es=f"Solo puedes seleccionar una {es}",
            slug=f"more-than-one-{en}-selected",
        )

    def _validate_selected_resources(self):
        if (
            self.selected_cohort_set
            and not isinstance(self.selected_cohort_set, int)
            and not isinstance(self.selected_cohort_set, str)
        ):
            raise ValidationException(
                translation(self.lang, en="The cohort needs to be a id or slug", es="El cohort debe ser un id o slug"),
                slug="cohort-not-id-or-slug",
            )

        if (
            self.selected_event_type_set
            and not isinstance(self.selected_event_type_set, int)
            and not isinstance(self.selected_event_type_set, str)
        ):
            raise ValidationException(
                translation(
                    self.lang,
                    en="The event type set needs to be a id or slug",
                    es="El event type set debe ser un id o slug",
                ),
                slug="event-type-set-not-id-or-slug",
            )

        if (
            self.selected_mentorship_service_set
            and not isinstance(self.selected_mentorship_service_set, int)
            and not isinstance(self.selected_mentorship_service_set, str)
        ):
            raise ValidationException(
                translation(
                    self.lang,
                    en="The mentorship service set needs to be a id or slug",
                    es="El mentorship service set debe ser un id o slug",
                ),
                slug="mentorship-service-set-not-id-or-slug",
            )

    def _reset_bag(self):
        if "checking" in self.request.build_absolute_uri():
            self.bag.service_items.clear()
            self.bag.plans.clear()
            self.bag.plan_addons.clear()
            self.bag.token = None
            self.bag.expires_at = None

    def _validate_service_items_format(self):
        if isinstance(self.service_items, list):
            for item in self.service_items:
                if not isinstance(item, dict):
                    raise ValidationException(
                        translation(
                            self.lang,
                            en="The service item needs to be a object",
                            es="El service item debe ser un objeto",
                        ),
                        slug="service-item-not-object",
                    )

                if (
                    "how_many" not in item
                    or "service" not in item
                    or not isinstance(item["how_many"], int)
                    or not isinstance(item["service"], int)
                ):
                    raise ValidationException(
                        translation(
                            self.lang,
                            en="The service item needs to have the keys of the integer type how_many and service",
                            es="El service item debe tener las llaves de tipo entero how_many y service",
                        ),
                        slug="service-item-malformed",
                    )

                if "is_team_allowed" in item and not isinstance(item["is_team_allowed"], bool):
                    raise ValidationException(
                        translation(
                            self.lang,
                            en="The service item only accepts boolean type for is_team_allowed",
                            es="El service item solo acepta el tipo booleano para is_team_allowed",
                        ),
                        slug="service-item-is-team-allowed-malformed",
                    )

    def _get_service_items_that_not_found(self):
        if isinstance(self.service_items, list):
            for service_item in self.service_items:
                kwargs = {}

                if service_item["service"] and (
                    isinstance(service_item["service"], int) or service_item["service"].isnumeric()
                ):
                    kwargs["id"] = int(service_item["service"])
                else:
                    kwargs["slug"] = service_item["service"]

                if Service.objects.filter(**kwargs).count() == 0:
                    self.service_items_not_found.add(service_item["service"])

    def _get_plans_that_not_found(self):
        if isinstance(self.plans, list):
            for plan in self.plans:
                kwargs = {}
                exclude = {}

                if plan and (isinstance(plan, int) or plan.isnumeric()):
                    kwargs["id"] = int(plan)
                else:
                    kwargs["slug"] = plan

                if self.selected_cohort_set and isinstance(self.selected_cohort_set, int):
                    kwargs["cohort_set"] = self.selected_cohort_set

                elif self.selected_cohort_set and isinstance(self.selected_cohort_set, str):
                    kwargs["cohort_set__slug"] = self.selected_cohort_set

                if Plan.objects.filter(**kwargs).exclude(**exclude).count() == 0:
                    self.plans_not_found.add(plan)

    def _get_plan_addons_that_not_found(self):
        if isinstance(self.plan_addons, list):
            for addon in self.plan_addons:
                kwargs = {}

                if addon and (isinstance(addon, int) or (isinstance(addon, str) and addon.isnumeric())):
                    kwargs["id"] = int(addon)
                else:
                    kwargs["slug"] = addon

                if Plan.objects.filter(**kwargs).count() == 0:
                    self.plan_addons_not_found.add(addon)

    def _report_items_not_found(self):
        if (
            self.service_items_not_found
            or self.plans_not_found
            or self.cohort_sets_not_found
            or self.plan_addons_not_found
        ):
            raise ValidationException(
                translation(
                    self.lang,
                    en=(
                        f"Items not found: services={self.service_items_not_found}, "
                        f"plans={self.plans_not_found}, "
                        f"cohorts={self.cohort_sets_not_found}, "
                        f"plan_addons={self.plan_addons_not_found}"
                    ),
                    es=(
                        f"Elementos no encontrados: servicios={self.service_items_not_found}, "
                        f"planes={self.plans_not_found}, "
                        f"cohortes={self.cohort_sets_not_found}, "
                        f"plan_addons={self.plan_addons_not_found}"
                    ),
                    slug="some-items-not-found",
                ),
                code=404,
            )

    def _add_service_items_to_bag(self):
        if isinstance(self.service_items, list):
            add_ons: dict[int, AcademyService] = {}

            for plan in self.bag.plans.all():
                for add_on in plan.add_ons.all():
                    add_ons[add_on.service.id] = add_on

            for service_item in self.service_items:

                if service_item["service"] not in add_ons:
                    self.bag.service_items.filter(service__id=service_item["service"]).delete()
                    raise ValidationException(
                        translation(
                            self.lang,
                            en=f"The service {service_item['service']} is not available for the selected plans",
                            es=f"El servicio {service_item['service']} no está disponible para los planes seleccionados",
                        ),
                        slug="service-item-not-valid",
                    )

                add_ons[service_item["service"]].validate_transaction(service_item["how_many"], lang=self.lang)

            for service_item in self.service_items:
                args, kwargs = self._lookups(service_item["service"])

                service = Service.objects.filter(*args, **kwargs).first()
                service_item, _ = ServiceItem.get_or_create_for_service(
                    service=service,
                    how_many=service_item["how_many"],
                    is_team_allowed=service_item.get("is_team_allowed", True),
                )
                self.bag.service_items.add(service_item)

    def _add_plans_to_bag(self):
        if isinstance(self.plans, list):
            for plan in self.plans:
                kwargs = {}

                args, kwargs = self._lookups(plan)

                p = Plan.objects.filter(*args, **kwargs).first()

                if p and p not in self.bag.plans.filter():
                    self.bag.plans.add(p)

    def _add_plan_addons_to_bag(self):
        if not isinstance(self.plan_addons, list):
            return

        main_plan: Plan | None = self.bag.plans.first()

        if self.plan_addons and not main_plan:
            raise ValidationException(
                translation(
                    self.lang,
                    en="You must select a main plan to add plan addons",
                    es="Debes seleccionar un plan principal para agregar plan addons",
                    slug="plan-required-for-plan-addons",
                ),
                code=400,
            )

        for addon in self.plan_addons:
            args, kwargs = self._lookups(addon)
            addon_plan = Plan.objects.filter(*args, **kwargs).first()

            if not addon_plan:
                # already handled in _get_plan_addons_that_not_found
                continue

            if main_plan and not main_plan.plan_addons.filter(id=addon_plan.id).exists():
                raise ValidationException(
                    translation(
                        self.lang,
                        en=f"The plan {addon_plan.slug} is not allowed as addon for the selected plan",
                        es=f"El plan {addon_plan.slug} no está permitido como addon para el plan seleccionado",
                        slug="plan-addon-not-allowed",
                    ),
                    code=400,
                )

            if addon_plan not in self.bag.plan_addons.filter():
                self.bag.plan_addons.add(addon_plan)

    def _validate_just_one_plan(self):
        how_many_plans = self.bag.plans.count()

        if how_many_plans > 1:

            raise ValidationException(self._more_than_one_generator(en="plan", es="plan"), code=400)

    # NEW: validate team seat add-ons for selected plan
    def _validate_seat_add_ons(self):
        if not self.team_seats:
            return

        # normalize
        try:
            seats = int(self.team_seats)
        except Exception:
            raise ValidationException(
                translation(
                    self.lang,
                    en="Seats must be an integer",
                    es="Los asientos deben ser un número entero",
                    slug="seats-must-be-an-integer",
                ),
                code=400,
            )

        if seats <= 0:
            return

        plan: Plan | None = self.bag.plans.first()
        if not plan:
            raise ValidationException(
                translation(
                    self.lang,
                    en="You must select a plan to add seats",
                    es="Debes seleccionar un plan para agregar asientos",
                    slug="plan-required-for-seats",
                ),
                code=400,
            )

        if not plan.seat_service_price:
            raise ValidationException(
                translation(
                    self.lang,
                    en="This plan does not support teams",
                    es="Este plan no soporta equipos",
                    slug="plan-not-support-teams",
                ),
                code=400,
            )

    # NEW: add seat add-ons as ServiceItems into the bag
    def _add_seat_add_ons(self):

        if not self.team_seats:
            return

        seats = int(self.team_seats)

        if seats <= 0:
            return

        plan: Plan | None = self.bag.plans.first()
        service_item, _ = ServiceItem.objects.get_or_create(
            service=plan.seat_service_price.service, how_many=seats, is_renewable=False, is_team_allowed=True
        )

        self.bag.seat_service_item = service_item
        self.bag.save()

    def _ask_to_add_plan_and_charge_it_in_the_bag(self):
        for plan in self.bag.plans.all():
            ask_to_add_plan_and_charge_it_in_the_bag(plan, self.bag.user, self.lang)

    def execute(self):
        self._reset_bag()

        self._validate_selected_resources()
        self._validate_service_items_format()

        self._get_service_items_that_not_found()
        self._get_plans_that_not_found()
        self._get_plan_addons_that_not_found()
        self._report_items_not_found()
        self._add_plans_to_bag()
        # validate and add seat add-ons if requested
        self._validate_just_one_plan()
        self._validate_seat_add_ons()
        self._add_seat_add_ons()
        self._add_plan_addons_to_bag()
        self._add_service_items_to_bag()
        self._validate_just_one_plan()

        self._ask_to_add_plan_and_charge_it_in_the_bag()

        # Save the country code if provided
        if self.country_code:
            self.bag.country_code = self.country_code

        self.bag.save()


def add_items_to_bag(request, bag: Bag, lang: str):
    return BagHandler(request, bag, lang).execute()


def get_amount(
    bag: Bag,
    currency: Currency,
    lang: str,
    early_renewal_subscription: Optional["Subscription"] = None,
) -> tuple[float, float, float, float, Currency]:
    def add_currency(currency: Optional[Currency] = None):
        if not currency and main_currency:
            currencies[main_currency.code.upper()] = main_currency

        if currency and currency.code.upper() not in currencies:
            currencies[currency.code.upper()] = currency

    user = bag.user
    price_per_month = 0
    price_per_quarter = 0
    price_per_half = 0
    price_per_year = 0

    currencies = {}

    if not currency:
        currency, _ = Currency.objects.get_or_create(code="USD", defaults={"name": "US dollar", "decimals": 2})

    main_currency = currency

    # Initialize pricing ratio explanation with proper format
    pricing_ratio_explanation = {"plans": [], "service_items": [], "plan_addons": []}

    for plan in bag.plans.all():
        must_it_be_charged = ask_to_add_plan_and_charge_it_in_the_bag(
            plan,
            user,
            lang,
            early_renewal_subscription=early_renewal_subscription,
        )

        if not bag.how_many_installments and (bag.chosen_period != "NO_SET" or must_it_be_charged):
            # Get base prices
            base_price_per_month = plan.price_per_month or 0
            base_price_per_quarter = plan.price_per_quarter or 0
            base_price_per_half = plan.price_per_half or 0
            base_price_per_year = plan.price_per_year or 0

            # Apply pricing ratio if country code is available
            if bag.country_code:
                # Apply pricing ratio to each price type
                adjusted_price_per_month, ratio_per_month, c = apply_pricing_ratio(
                    base_price_per_month, bag.country_code, plan, lang=lang, price_attr="price_per_month"
                )
                adjusted_price_per_quarter, ratio_per_quarter, _ = apply_pricing_ratio(
                    base_price_per_quarter, bag.country_code, plan, lang=lang, price_attr="price_per_quarter"
                )
                adjusted_price_per_half, ratio_per_half, _ = apply_pricing_ratio(
                    base_price_per_half, bag.country_code, plan, lang=lang, price_attr="price_per_half"
                )
                adjusted_price_per_year, ratio_per_year, _ = apply_pricing_ratio(
                    base_price_per_year, bag.country_code, plan, lang=lang, price_attr="price_per_year"
                )

                add_currency(c)
                currency = c or currency

                # Calculate ratio for explanation if not direct price
                if adjusted_price_per_month != base_price_per_month and base_price_per_month > 0:
                    pricing_ratio_explanation["plans"].append({"plan": plan.slug, "ratio": ratio_per_month})

                elif adjusted_price_per_quarter != base_price_per_quarter and base_price_per_quarter > 0:
                    pricing_ratio_explanation["plans"].append({"plan": plan.slug, "ratio": ratio_per_quarter})

                elif adjusted_price_per_half != base_price_per_half and base_price_per_half > 0:
                    pricing_ratio_explanation["plans"].append({"plan": plan.slug, "ratio": ratio_per_half})

                elif adjusted_price_per_year != base_price_per_year and base_price_per_year > 0:
                    pricing_ratio_explanation["plans"].append({"plan": plan.slug, "ratio": ratio_per_year})

                # Use adjusted prices
                price_per_month += adjusted_price_per_month
                price_per_quarter += adjusted_price_per_quarter
                price_per_half += adjusted_price_per_half
                price_per_year += adjusted_price_per_year
            else:
                # No country code, use base prices
                price_per_month += base_price_per_month
                price_per_quarter += base_price_per_quarter
                price_per_half += base_price_per_half
                price_per_year += base_price_per_year

    plans = bag.plans.all()
    add_ons: dict[int, AcademyService] = {}
    for plan in plans:
        for add_on in plan.add_ons.filter(currency=currency):
            if add_on.service.id not in add_ons:
                add_ons[add_on.service.id] = add_on

    for service_item in bag.service_items.all():
        if service_item.service.id in add_ons:
            add_on = add_ons[service_item.service.id]

            try:
                add_on.validate_transaction(service_item.how_many, lang)
            except Exception as e:
                bag.service_items.filter().delete()
                bag.plans.filter().delete()
                raise e

            # Get discounted price first
            base_price, c, local_pricing_ratio_explanation = add_on.get_discounted_price(
                service_item.how_many, bag.country_code, lang
            )
            pricing_ratio_explanation["service_items"] += local_pricing_ratio_explanation["service_items"]
            add_currency(c)

            if price_per_month != 0:
                price_per_month += base_price

            if price_per_quarter != 0:
                price_per_quarter += base_price

            if price_per_half != 0:
                price_per_half += base_price

            if price_per_year != 0:
                price_per_year += base_price

    if len(currencies.keys()) > 1:
        raise ValidationException(
            translation(
                lang,
                en="Multiple currencies found, it means that the pricing ratio exceptions have a wrong configuration",
                es="Múltiples monedas encontradas, lo que significa que las excepciones de ratio de precios tienen una configuración incorrecta",
                slug="multiple-currencies-found",
            ),
            code=500,
        )

    # Save pricing ratio explanation if any ratios were applied
    if (
        pricing_ratio_explanation["plans"]
        or pricing_ratio_explanation["service_items"]
        or pricing_ratio_explanation.get("plan_addons")
        or not bag.currency
        or bag.currency.id != currency.id
    ):
        bag.pricing_ratio_explanation = pricing_ratio_explanation
        bag.currency = currency
        bag.save()

    if bag.seat_service_item:
        academy_service = AcademyService.objects.filter(
            service=bag.seat_service_item.service, academy=bag.academy
        ).first()
        if not academy_service:
            raise ValidationException(
                translation(
                    lang,
                    en="Price are not configured for per-seat purchases",
                    es="Precio no configurado para compras por asiento",
                    slug="price-not-configured-for-per-seat-purchases",
                ),
                code=400,
            )

        how_many_seats = bag.seat_service_item.how_many
        if how_many_seats > 0 and price_per_month != 0:
            price_per_month += academy_service.price_per_unit * how_many_seats
        if how_many_seats > 0 and price_per_quarter != 0:
            price_per_quarter += academy_service.price_per_unit * how_many_seats * 3
        if how_many_seats > 0 and price_per_half != 0:
            price_per_half += academy_service.price_per_unit * how_many_seats * 6
        if how_many_seats > 0 and price_per_year != 0:
            price_per_year += academy_service.price_per_unit * how_many_seats * 12

    get_plan_addons_amount(bag, lang)

    return price_per_month, price_per_quarter, price_per_half, price_per_year


def get_amount_by_chosen_period(bag: Bag, chosen_period: str, lang: str) -> float:
    amount = 0

    if chosen_period == "MONTH" and bag.amount_per_month:
        amount = bag.amount_per_month

    elif chosen_period == "QUARTER" and bag.amount_per_quarter:
        amount = bag.amount_per_quarter

    elif chosen_period == "HALF" and bag.amount_per_half:
        amount = bag.amount_per_half

    elif chosen_period == "YEAR" and bag.amount_per_year:
        amount = bag.amount_per_year

    # free trial
    if not amount and (bag.amount_per_month or bag.amount_per_quarter or bag.amount_per_half or bag.amount_per_year):
        raise ValidationException(
            translation(
                lang,
                en=f"The period {chosen_period} is disabled for this bag",
                es=f"El periodo {chosen_period} está deshabilitado para esta bolsa",
                slug="period-disabled-for-bag",
            ),
            code=400,
        )

    return amount


def get_bag_from_subscription(
    subscription: Subscription,
    settings: Optional[UserSetting] = None,
    lang: Optional[str] = None,
    coupons_as_of: Optional[datetime] = None,
) -> Bag:
    """
    Build a RENEWAL bag from an existing subscription.

    coupons_as_of: optional moment used to decide if subscription coupons are still
    valid for this charge. Defaults to now (actual renew / charge_subscription).
    Pass subscription.next_payment_at when previewing the upcoming scheduled charge.
    """
    bag = Bag()

    if not lang and not settings:
        settings = get_user_settings(subscription.user.id)
        lang = settings.lang
    elif settings:
        lang = settings.lang

    last_invoice = subscription.invoices.filter().last()
    if not last_invoice:
        raise Exception(
            translation(
                lang,
                en="Invalid subscription, this has no invoices",
                es="Suscripción invalida, esta no tiene facturas",
                slug="subscription-has-no-invoices",
            )
        )

    bag.status = "RENEWAL"
    bag.type = "CHARGE"
    bag.academy = subscription.academy
    bag.currency = subscription.currency or last_invoice.currency
    bag.user = subscription.user
    bag.is_recurrent = True
    bag.chosen_period = last_invoice.bag.chosen_period

    if bag.chosen_period == "NO_SET":
        bag.chosen_period = "MONTH"

    bag.save()

    for plan in subscription.plans.all():
        bag.plans.add(plan)

    # Include persisted subscription add-ons (SubscriptionServiceItem) in the bag so they are billed monthly
    qs = subscription.subscriptionserviceitem_set.select_related("service_item").all()
    for handler in qs:
        service_item = handler.service_item
        bag.service_items.add(service_item)

    # Coupons already on the subscription persist for renewals (see COUPONS.md):
    # do not re-check how_many_offers — that limit applies to acquiring new purchases.
    # Expiration is evaluated at coupons_as_of (now for real charges, next_payment_at for previews).
    utc_now = timezone.now()
    as_of = coupons_as_of or utc_now

    subscription_coupons = list(
        subscription.coupons.filter(Q(expires_at__isnull=True) | Q(expires_at__gte=as_of))
        .exclude(seller__user=subscription.user)
        .exclude(~Q(referral_type=Coupon.Referral.NO_REFERRAL))
    )

    # Auto-applied user-restricted coupons still go through availability (usage limits matter).
    user_coupon_slugs = list(
        Coupon.objects.filter(
            Q(offered_at=None) | Q(offered_at__lte=utc_now),
            Q(expires_at=None) | Q(expires_at__gte=as_of),
            allowed_user=subscription.user,
            auto=True,
        )
        .exclude(how_many_offers=0)
        .values_list("slug", flat=True)
    )

    valid_user_coupons = []
    if user_coupon_slugs:
        valid_user_coupons = get_available_coupons(
            subscription.plans.first(),
            user_coupon_slugs,
            subscription.user,
            only_sent_coupons=True,
            as_of=as_of,
        )

    if subscription_coupons or valid_user_coupons:
        # Deduplicate by id in case a coupon appears in both sets
        by_id = {c.id: c for c in [*subscription_coupons, *valid_user_coupons]}
        bag.coupons.set(by_id.values())

    early_renewal_subscription = (
        subscription if (subscription.next_payment_at and subscription.next_payment_at > utc_now) else None
    )

    bag.amount_per_month, bag.amount_per_quarter, bag.amount_per_half, bag.amount_per_year = get_amount(
        bag, subscription.currency or last_invoice.currency, lang, early_renewal_subscription=early_renewal_subscription
    )

    bag.save()

    return bag


def preview_subscription_renewal_amount(
    subscription: Subscription, settings: Optional[UserSetting] = None, lang: Optional[str] = None
) -> Optional[float]:
    """
    Compute the amount that would be charged on the next subscription renewal
    without persisting any Bag or related side effects.

    Uses the same pricing path as charge_subscription / renew, but rolls back
    the transaction so GET me/subscription does not create orphan RENEWAL bags.
    """
    try:
        with transaction.atomic():
            if not lang and not settings:
                settings = get_user_settings(subscription.user.id)
                lang = settings.lang
            elif settings and not lang:
                lang = settings.lang
            elif not lang:
                lang = "en"

            bag = get_bag_from_subscription(
                subscription,
                settings=settings,
                lang=lang,
                # Preview the scheduled charge: coupon must still be valid on that date.
                coupons_as_of=subscription.next_payment_at,
            )
            amount = get_amount_by_chosen_period(bag, bag.chosen_period, lang)
            coupons = list(bag.coupons.all())
            if coupons:
                amount = get_discounted_price(amount, coupons)

            transaction.set_rollback(True)
            return float(amount)
    except Exception:
        return None


def get_bag_from_plan_financing(plan_financing: PlanFinancing, settings: Optional[UserSetting] = None) -> Bag:
    bag = Bag()

    if not settings:
        settings = get_user_settings(plan_financing.user.id)

    last_invoice = plan_financing.invoices.filter().last()
    if not last_invoice:
        raise Exception(
            translation(
                settings.lang,
                en="Invalid plan financing, this has not charge",
                es="Plan financing es invalido, este no tiene cargos",
                slug="plan-financing-has-no-invoices",
            )
        )

    bag.status = "RENEWAL"
    bag.type = "CHARGE"
    bag.academy = plan_financing.academy
    bag.currency = plan_financing.currency or last_invoice.currency
    bag.user = plan_financing.user
    bag.is_recurrent = True
    bag.save()

    for plan in plan_financing.plans.all():
        bag.plans.add(plan)

    return bag


def filter_consumables(
    request: WSGIRequest,
    items: QuerySet[Consumable],
    queryset: QuerySet,
    key: str,
    custom_query_key: Optional[str] = None,
):

    if ids := request.GET.get(key):
        try:
            ids = [int(x) for x in ids.split(",")]
        except Exception:
            raise ValidationException(f"{key} param must be integer")

        query_key = custom_query_key or key
        queryset |= items.filter(**{f"{query_key}__id__in": ids})

    if slugs := request.GET.get(f"{key}_slug"):
        slugs = slugs.split(",")

        query_key = custom_query_key or key
        queryset |= items.filter(**{f"{query_key}__slug__in": slugs})

    if not ids and not slugs:
        query_key = custom_query_key or key
        queryset |= items.filter(**{f"{query_key}__isnull": False})

    queryset = queryset.distinct()
    return queryset


def filter_void_consumable_balance(request: WSGIRequest, items: QuerySet[Consumable]):
    consumables = items.filter(service_item__service__type="VOID")

    if ids := request.GET.get("service"):
        try:
            ids = [int(x) for x in ids.split(",")]
        except Exception:
            raise ValidationException("service param must be integer")

        consumables = consumables.filter(service_item__service__id__in=ids)

    if slugs := request.GET.get("service_slug"):
        slugs = slugs.split(",")

        consumables = consumables.filter(service_item__service__slug__in=slugs)

    if not consumables:
        return []

    result = {}

    for consumable in consumables:
        service = consumable.service_item.service
        if service.id not in result:
            result[service.id] = {
                "balance": {
                    "unit": 0,
                },
                "id": service.id,
                "slug": service.slug,
                "items": [],
            }

        if consumable.how_many < 0:
            result[service.id]["balance"]["unit"] = -1

        elif result[service.id]["balance"]["unit"] != -1:
            result[service.id]["balance"]["unit"] += consumable.how_many

        standalone_invoice = None
        if consumable.standalone_invoice_id:
            invoice = consumable.standalone_invoice
            bag = invoice.bag if invoice else None
            academy = bag.academy if bag else None
            standalone_invoice = {
                "id": invoice.id,
                "academy": (
                    {
                        "id": academy.id,
                        "slug": academy.slug,
                        "name": academy.name,
                    }
                    if academy
                    else None
                ),
            }

        result[service.id]["items"].append(
            {
                "id": consumable.id,
                "how_many": consumable.how_many,
                "unit_type": consumable.unit_type,
                "valid_until": consumable.valid_until,
                "subscription_seat": consumable.subscription_seat.id if consumable.subscription_seat else None,
                "subscription_billing_team": (
                    consumable.subscription_billing_team.id if consumable.subscription_billing_team else None
                ),
                "user": consumable.user.id if consumable.user else None,
                "subscription": consumable.subscription.id if consumable.subscription else None,
                "plan_financing": consumable.plan_financing.id if consumable.plan_financing else None,
                "standalone_invoice": standalone_invoice,
            }
        )

    return list(result.values())


def get_balance_by_resource(
    queryset: QuerySet[Consumable],
    key: str,
):
    result = []

    ids = {getattr(x, key).id for x in queryset}
    for id in ids:
        current = queryset.filter(**{f"{key}__id": id})

        instance = current.first()
        balance = {}
        items = []
        units = {x[0] for x in SERVICE_UNITS}
        for unit in units:
            per_unit = current.filter(unit_type=unit)
            sum_result = per_unit.aggregate(Sum("how_many"))["how_many__sum"]
            balance[unit.lower()] = (
                -1 if per_unit.filter(how_many=-1).exists() else (sum_result if sum_result is not None else 0)
            )

        for x in queryset:
            valid_until = x.valid_until
            if valid_until:
                valid_until = re.sub(r"\+00:00$", "Z", valid_until.replace(tzinfo=UTC).isoformat())

            standalone_invoice = None
            if x.standalone_invoice_id:
                invoice = x.standalone_invoice
                bag = invoice.bag if invoice else None
                academy = bag.academy if bag else None
                standalone_invoice = {
                    "id": invoice.id,
                    "academy": (
                        {
                            "id": academy.id,
                            "slug": academy.slug,
                            "name": academy.name,
                        }
                        if academy
                        else None
                    ),
                }

            items.append(
                {
                    "id": x.id,
                    "how_many": x.how_many,
                    "unit_type": x.unit_type,
                    "valid_until": x.valid_until,
                    # identity info
                    "subscription_seat": x.subscription_seat.id if x.subscription_seat else None,
                    "subscription_billing_team": (
                        x.subscription_billing_team.id if x.subscription_billing_team else None
                    ),
                    "user": x.user.id if x.user else None,
                    "subscription": x.subscription.id if x.subscription else None,
                    "plan_financing": x.plan_financing.id if x.plan_financing else None,
                    "standalone_invoice": standalone_invoice,
                }
            )

        result.append(
            {
                "id": getattr(instance, key).id,
                "slug": getattr(instance, key).slug,
                "balance": balance,
                "items": items,
            }
        )
    return result


def check_scheduler_renewal_issues(scheduler, utc_now):
    """
    Return a list of issue strings describing why renewal might be blocked for this scheduler.
    Mirrors diagnose_scheduler check_renewal_conditions; used by get_service_stock_status_for_user.
    """
    from breathecode.payments.models import (
        PlanFinancing,
        ServiceStockScheduler,
        Subscription,
    )

    issues: list[str] = []
    if not isinstance(scheduler, ServiceStockScheduler):
        return issues

    if scheduler.plan_handler and scheduler.plan_handler.subscription_id:
        sub = scheduler.plan_handler.subscription
        if sub.valid_until and sub.valid_until < utc_now:
            issues.append(f"Subscription {sub.id} is expired (valid_until: {sub.valid_until})")
        if sub.next_payment_at < utc_now:
            issues.append(f"Subscription {sub.id} needs to be paid (next_payment_at: {sub.next_payment_at})")
        if sub.status in (Subscription.Status.DEPRECATED, Subscription.Status.EXPIRED, Subscription.Status.PAYMENT_ISSUE):
            issues.append(f"Subscription {sub.id} has invalid status: {sub.status}")
        if scheduler.plan_handler.handler:
            si = scheduler.plan_handler.handler.service_item
            if not si.is_renewable:
                issues.append(f"Service item {si.id} is not renewable (is_renewable=False)")
            if si.service.type != "VOID":
                key = si.service.type.lower()
                if not getattr(sub, f"selected_{key}", None):
                    issues.append(f"Subscription has no linked resource for service {si.service.slug} (type: {si.service.type})")

    elif scheduler.plan_handler and scheduler.plan_handler.plan_financing_id:
        pf = (
            PlanFinancing.objects.select_related(
                "selected_mentorship_service_set", "selected_cohort_set", "selected_event_type_set"
            )
            .prefetch_related("plans")
            .filter(id=scheduler.plan_handler.plan_financing_id)
            .first()
        )
        if pf:
            if pf.plan_expires_at and pf.plan_expires_at < utc_now:
                issues.append(f"Plan financing {pf.id} is expired (plan_expires_at: {pf.plan_expires_at})")
            if pf.status == PlanFinancing.Status.ACTIVE and pf.next_payment_at < utc_now:
                issues.append(f"Plan financing {pf.id} needs to be paid (next_payment_at: {pf.next_payment_at})")
            if pf.status in (PlanFinancing.Status.CANCELLED, PlanFinancing.Status.DEPRECATED, PlanFinancing.Status.EXPIRED):
                issues.append(f"Plan financing {pf.id} has invalid status: {pf.status}")
            if scheduler.plan_handler.handler:
                si = scheduler.plan_handler.handler.service_item
                if not si.is_renewable:
                    issues.append(
                        f"Service item {si.id} is not renewable; first consumable may still be created."
                    )
                if si.service.type != "VOID":
                    key = si.service.type.lower()
                    if not getattr(pf, f"selected_{key}", None):
                        plans_have = [p.id for p in pf.plans.all() if getattr(p, key, None)]
                        if plans_have:
                            issues.append(
                                f"Plan financing {pf.id} has no linked resource for {si.service.slug}, "
                                f"but plans {plans_have} do; resource should be copied to plan financing."
                            )
                        else:
                            issues.append(
                                f"Plan financing {pf.id} has no linked resource for service {si.service.slug} "
                                "(consumable cannot be created without it)."
                            )

    elif scheduler.subscription_handler_id:
        sub = scheduler.subscription_handler.subscription
        if sub.valid_until and sub.valid_until < utc_now:
            issues.append(f"Subscription {sub.id} is expired (valid_until: {sub.valid_until})")
        if sub.next_payment_at < utc_now:
            issues.append(f"Subscription {sub.id} needs to be paid (next_payment_at: {sub.next_payment_at})")
        if sub.status in (Subscription.Status.DEPRECATED, Subscription.Status.EXPIRED, Subscription.Status.PAYMENT_ISSUE):
            issues.append(f"Subscription {sub.id} has invalid status: {sub.status}")
    else:
        issues.append("Scheduler has no plan_handler or subscription_handler")

    if scheduler.valid_until and scheduler.valid_until > utc_now:
        issues.append(
            f"Scheduler does not need renewal yet (valid_until={scheduler.valid_until} > now)"
        )

    return issues


def get_service_stock_status_for_user(
    user_id: int,
    academy_id: int,
    include_balance: bool = False,
    request: Optional[WSGIRequest] = None,
) -> Optional[dict]:
    """
    Build service stock status payload for a user in an academy: schedulers, issues, optional balance.
    Returns None if user not found or has no link to the academy.
    """
    from breathecode.payments.models import (
        PlanFinancing,
        PlanServiceItemHandler,
        ServiceStockScheduler,
        Subscription,
    )

    user = User.objects.filter(id=user_id).first()
    if not user:
        return None

    utc_now = timezone.now()

    user_q = (
        Q(plan_handler__subscription__user_id=user_id)
        | Q(plan_handler__plan_financing__user_id=user_id)
        | Q(subscription_handler__subscription__user_id=user_id)
        | Q(subscription_seat__user_id=user_id)
        | Q(plan_financing_seat__user_id=user_id)
        | Q(subscription_billing_team__subscription__user_id=user_id)
        | Q(plan_financing_team__financing__user_id=user_id)
    )
    academy_q = (
        Q(plan_handler__subscription__academy_id=academy_id)
        | Q(plan_handler__plan_financing__academy_id=academy_id)
        | Q(subscription_handler__subscription__academy_id=academy_id)
        | Q(subscription_seat__billing_team__subscription__academy_id=academy_id)
        | Q(plan_financing_seat__team__financing__academy_id=academy_id)
        | Q(plan_financing_team__financing__academy_id=academy_id)
        | Q(subscription_billing_team__subscription__academy_id=academy_id)
    )

    schedulers_qs = (
        ServiceStockScheduler.objects.filter(user_q, academy_q)
        .select_related(
            "plan_handler__subscription",
            "plan_handler__plan_financing",
            "plan_handler__handler__service_item__service",
            "subscription_handler__subscription",
            "subscription_handler__service_item__service",
            "subscription_seat",
            "plan_financing_seat",
        )
        .prefetch_related("consumables")
    )

    schedulers_payload: list[dict] = []
    for s in schedulers_qs:
        if s.plan_handler_id:
            service_item = s.plan_handler.handler.service_item if s.plan_handler.handler_id else None
            subscription = getattr(s.plan_handler, "subscription", None)
            plan_financing = getattr(s.plan_handler, "plan_financing", None)
            source_type = "subscription" if subscription else "plan_financing"
            source_id = subscription.id if subscription else (plan_financing.id if plan_financing else None)
        else:
            service_item = s.subscription_handler.service_item if s.subscription_handler_id else None
            subscription = s.subscription_handler.subscription if s.subscription_handler_id else None
            plan_financing = None
            source_type = "subscription"
            source_id = subscription.id if subscription else None

        resource = None
        if subscription:
            resource = subscription
        elif plan_financing:
            resource = plan_financing

        resource_linked = True
        if service_item and resource and service_item.service.type != "VOID":
            key = service_item.service.type.lower()
            resource_linked = bool(getattr(resource, f"selected_{key}", None))

        consumables_list = list(s.consumables.all().order_by("-id")[:5])
        consumables_sample = []
        for c in consumables_list:
            v = c.valid_until
            if v:
                v = re.sub(r"\+00:00$", "Z", v.replace(tzinfo=UTC).isoformat())
            consumables_sample.append({
                "id": c.id,
                "how_many": c.how_many,
                "valid_until": v,
                "user_id": c.user_id,
            })

        scheduler_valid_until = s.valid_until
        if scheduler_valid_until:
            scheduler_valid_until = re.sub(
                r"\+00:00$", "Z", scheduler_valid_until.replace(tzinfo=UTC).isoformat()
            )

        seat_id = None
        if s.subscription_seat_id:
            seat_id = s.subscription_seat_id
        elif s.plan_financing_seat_id:
            seat_id = s.plan_financing_seat_id

        schedulers_payload.append({
            "id": s.id,
            "source_type": source_type,
            "source_id": source_id,
            "seat_id": seat_id,
            "service": service_item.service.slug if service_item else None,
            "service_item_id": service_item.id if service_item else None,
            "renew_at": getattr(service_item, "renew_at", None) if service_item else None,
            "renew_at_unit": getattr(service_item, "renew_at_unit", None) if service_item else None,
            "is_renewable": getattr(service_item, "is_renewable", None) if service_item else None,
            "scheduler_valid_until": scheduler_valid_until,
            "resource_linked": resource_linked,
            "consumables_count": s.consumables.count(),
            "consumables_sample": consumables_sample,
            "issues": check_scheduler_renewal_issues(s, utc_now),
        })

    if not schedulers_payload and not (
        Subscription.objects.filter(user_id=user_id, academy_id=academy_id).exists()
        or PlanFinancing.objects.filter(user_id=user_id, academy_id=academy_id).exists()
    ):
        from breathecode.payments.models import SubscriptionSeat, PlanFinancingSeat

        has_seat = (
            SubscriptionSeat.objects.filter(user_id=user_id, billing_team__subscription__academy_id=academy_id)
            .exists()
            or PlanFinancingSeat.objects.filter(user_id=user_id, team__financing__academy_id=academy_id).exists()
        )
        if not has_seat:
            return None

    payload = {
        "user": {"id": user.id, "email": user.email},
        "academy_id": academy_id,
        "schedulers": schedulers_payload,
    }

    if include_balance:
        items = Consumable.list(user=user, include_zero_balance=True)
        mentorship_services = items.filter(mentorship_service_set__isnull=False)
        cohorts = items.filter(cohort_set__isnull=False)
        event_types = items.filter(event_type_set__isnull=False)
        balance = {
            "mentorship_service_sets": get_balance_by_resource(mentorship_services, "mentorship_service_set"),
            "cohort_sets": get_balance_by_resource(cohorts, "cohort_set"),
            "event_type_sets": get_balance_by_resource(event_types, "event_type_set"),
            "voids": filter_void_consumable_balance(request, items) if request else [],
        }
        payload["consumables_balance"] = balance

    return payload


def _run_service_stock_build_task_sync(target_type: str, target_id: int, seat_id: Optional[int] = None) -> None:
    if target_type == "plan_financing":
        task_handler = tasks.build_service_stock_scheduler_from_plan_financing
    else:
        task_handler = tasks.build_service_stock_scheduler_from_subscription

    kwargs = {}
    if seat_id is not None:
        kwargs["seat_id"] = seat_id

    if hasattr(task_handler, "apply"):
        task_handler.apply(args=[target_id], kwargs=kwargs, throw=True)
        _raise_if_task_manager_failed(task_handler)
        return

    task_handler(target_id, **kwargs)


def _run_renew_consumable_task_sync(service_stock_scheduler_id: int) -> None:
    task_handler = tasks.renew_consumables

    if hasattr(task_handler, "apply"):
        task_handler.apply(args=[service_stock_scheduler_id], throw=True)
        _raise_if_task_manager_failed(task_handler)
        return

    task_handler(service_stock_scheduler_id)


def regenerate_consumable_for_service_stock_scheduler(
    academy_id: int,
    service_stock_scheduler_id: int,
) -> dict:
    from breathecode.payments.models import ServiceStockScheduler

    academy_q = (
        Q(plan_handler__subscription__academy_id=academy_id)
        | Q(plan_handler__plan_financing__academy_id=academy_id)
        | Q(subscription_handler__subscription__academy_id=academy_id)
        | Q(subscription_seat__billing_team__subscription__academy_id=academy_id)
        | Q(subscription_billing_team__subscription__academy_id=academy_id)
        | Q(plan_financing_seat__team__financing__academy_id=academy_id)
        | Q(plan_financing_team__financing__academy_id=academy_id)
    )

    scheduler = ServiceStockScheduler.objects.filter(id=service_stock_scheduler_id).filter(academy_q).first()
    if not scheduler:
        raise ValidationException(
            translation(
                en="Service stock scheduler not found in this academy",
                es="Service stock scheduler no encontrado en esta academia",
                slug="service-stock-scheduler-not-found",
            ),
            code=404,
        )

    execution_error = None
    error_stage = None
    consumables_count_before = scheduler.consumables.count()
    try:
        _run_renew_consumable_task_sync(service_stock_scheduler_id)
    except (AbortTask, RetryTask, Exception) as error:
        execution_error = str(error)
        error_stage = "renew_consumable"

    scheduler.refresh_from_db()
    consumables_count_after = scheduler.consumables.count()

    if execution_error is None and consumables_count_after <= consumables_count_before:
        issues = check_scheduler_renewal_issues(scheduler, timezone.now())
        prioritized_issue = None
        priority_tokens = [
            "needs to be paid",
            "is expired",
            "has invalid status",
            "has no linked resource",
            "does not need renewal yet",
        ]

        for token in priority_tokens:
            prioritized_issue = next((x for x in issues if token in x), None)
            if prioritized_issue:
                break

        execution_error = prioritized_issue or "No consumable was created during regeneration"
        error_stage = "post_condition"

    if execution_error:
        status = "failed"
    else:
        status = "success"

    return {
        "scheduler": {
            "id": service_stock_scheduler_id,
            "academy_id": academy_id,
        },
        "status": status,
        "error_stage": error_stage,
        "execution_error": execution_error,
        "message": (
            "Consumable regeneration executed successfully"
            if status == "success"
            else f"Failed while renewing consumables for service stock scheduler: {execution_error}"
        ),
    }


def regenerate_service_stock_for_target(
    academy_id: int,
    plan_financing_id: Optional[int] = None,
    subscription_id: Optional[int] = None,
    seat_id: Optional[int] = None,
) -> dict:
    """
    Regenerate service stock schedulers and consumables synchronously for one target.
    Returns an immediate execution payload so the client can re-fetch schedulers in a separate request.
    """
    from breathecode.payments.models import PlanFinancing, ServiceStockScheduler, Subscription

    if bool(plan_financing_id) == bool(subscription_id):
        raise ValidationException(
            translation(
                en="Provide exactly one target: plan_financing_id or subscription_id",
                es="Debes enviar exactamente un objetivo: plan_financing_id o subscription_id",
                slug="invalid-target",
            ),
            code=400,
        )

    target_type = "plan_financing" if plan_financing_id else "subscription"
    target_id = plan_financing_id if plan_financing_id else subscription_id

    if target_type == "plan_financing":
        target = PlanFinancing.objects.filter(id=target_id, academy_id=academy_id).first()
    else:
        target = Subscription.objects.filter(id=target_id, academy_id=academy_id).first()

    if not target:
        raise ValidationException(
            translation(
                en=f"{target_type} not found in this academy",
                es=f"{target_type} no encontrado en esta academia",
                slug="target-not-found",
            ),
            code=404,
        )

    user_id = target.user_id

    execution_error = None
    error_stage = None
    schedulers_count_before = (
        ServiceStockScheduler.objects.filter(plan_handler__plan_financing_id=target_id).count()
        if target_type == "plan_financing"
        else ServiceStockScheduler.objects.filter(
            Q(subscription_handler__subscription_id=target_id) | Q(plan_handler__subscription_id=target_id)
        ).count()
    )
    try:
        _run_service_stock_build_task_sync(target_type, target_id, seat_id=seat_id)
    except (AbortTask, RetryTask, Exception) as error:
        execution_error = str(error)
        error_stage = "build_service_stock_scheduler"

    schedulers_count_after = (
        ServiceStockScheduler.objects.filter(plan_handler__plan_financing_id=target_id).count()
        if target_type == "plan_financing"
        else ServiceStockScheduler.objects.filter(
            Q(subscription_handler__subscription_id=target_id) | Q(plan_handler__subscription_id=target_id)
        ).count()
    )

    if execution_error is None and schedulers_count_before == 0 and schedulers_count_after == 0:
        execution_error = "No service stock scheduler was created during regeneration"
        error_stage = "post_condition"

    if execution_error:
        status = "failed"
    else:
        status = "success"

    return {
        "target": {
            "type": target_type,
            "id": target_id,
            "academy_id": academy_id,
            "user_id": user_id,
            "seat_id": seat_id,
        },
        "status": status,
        "error_stage": error_stage,
        "execution_error": execution_error,
        "message": (
            "Service stock regeneration executed successfully"
            if status == "success"
            else f"Failed while building service stock schedulers: {execution_error}"
        ),
    }


def resolve_plan_regeneration_service_ids(*, plan_id: int, services: Any, lang: str) -> list[int]:
    """
    Parse and validate service ids or slugs for bulk plan stock regeneration.
    Every resolved service must belong to the plan via PlanServiceItem.
    """
    if services is None:
        raise ValidationException(
            translation(
                lang,
                en="services is required (list of service ids or slugs from the plan)",
                es="services es requerido (lista de ids o slugs de servicios del plan)",
                slug="missing-services",
            ),
            code=400,
        )

    if not isinstance(services, list) or not services:
        raise ValidationException(
            translation(
                lang,
                en="services must be a non-empty list",
                es="services debe ser una lista no vacía",
                slug="invalid-services",
            ),
            code=400,
        )

    service_ids: list[int] = []
    slugs: list[str] = []

    for entry in services:
        if isinstance(entry, int):
            service_ids.append(entry)
        elif isinstance(entry, str) and entry.strip().isdigit():
            service_ids.append(int(entry.strip()))
        elif isinstance(entry, str) and entry.strip():
            slugs.append(entry.strip())
        else:
            raise ValidationException(
                translation(
                    lang,
                    en="Each service must be an integer id or a slug string",
                    es="Cada servicio debe ser un id entero o un slug",
                    slug="invalid-service-entry",
                ),
                code=400,
            )

    if slugs:
        slug_rows = list(Service.objects.filter(slug__in=slugs).values("id", "slug"))
        slug_to_id = {row["slug"]: row["id"] for row in slug_rows}
        missing_slugs = sorted(set(slugs) - set(slug_to_id))
        if missing_slugs:
            raise ValidationException(
                translation(
                    lang,
                    en=f"Services not found: {', '.join(missing_slugs)}",
                    es=f"Servicios no encontrados: {', '.join(missing_slugs)}",
                    slug="service-not-found",
                ),
                code=404,
            )
        service_ids.extend(slug_to_id[slug] for slug in slugs)

    service_ids = list(dict.fromkeys(service_ids))

    plan_service_ids = set(
        PlanServiceItem.objects.filter(plan_id=plan_id)
        .values_list("service_item__service_id", flat=True)
        .distinct()
    )
    if not plan_service_ids:
        raise ValidationException(
            translation(
                lang,
                en="Plan has no services configured",
                es="El plan no tiene servicios configurados",
                slug="plan-without-services",
            ),
            code=400,
        )

    invalid_ids = sorted({sid for sid in service_ids if sid not in plan_service_ids})
    if invalid_ids:
        raise ValidationException(
            translation(
                lang,
                en=f"Services {invalid_ids} are not part of plan {plan_id}",
                es=f"Los servicios {invalid_ids} no pertenecen al plan {plan_id}",
                slug="service-not-in-plan",
            ),
            code=400,
        )

    return service_ids


def enqueue_service_stock_regeneration_for_plan(*, academy_id: int, plan_id: int, service_ids: list[int]) -> dict:
    """
    Queue async rebuild of service stock schedulers for every plan financing or subscription in
    the academy that includes this plan and is ACTIVE or FULLY_PAID.

    Only schedulers for the given service_ids are rebuilt.

    Subscription rows cannot normally be FULLY_PAID (model validation); the filter is kept
    aligned with plan financing statuses for consistency.
    """
    eligible_statuses = (PlanFinancing.Status.ACTIVE, PlanFinancing.Status.FULLY_PAID)

    plan_financing_ids = list(
        PlanFinancing.objects.filter(
            academy_id=academy_id,
            plans__id=plan_id,
            status__in=eligible_statuses,
        )
        .values_list("id", flat=True)
        .distinct()
    )
    subscription_ids = list(
        Subscription.objects.filter(
            academy_id=academy_id,
            plans__id=plan_id,
            status__in=eligible_statuses,
        )
        .values_list("id", flat=True)
        .distinct()
    )

    for pf_id in plan_financing_ids:
        tasks.build_service_stock_scheduler_from_plan_financing.delay(pf_id, service_ids=service_ids)

    for sub_id in subscription_ids:
        tasks.build_service_stock_scheduler_from_subscription.delay(sub_id, service_ids=service_ids)

    total = len(plan_financing_ids) + len(subscription_ids)

    return {
        "plan_id": plan_id,
        "academy_id": academy_id,
        "service_ids": service_ids,
        "plan_financing_ids_queued": plan_financing_ids,
        "subscription_ids_queued": subscription_ids,
        "plan_financings_queued": len(plan_financing_ids),
        "subscriptions_queued": len(subscription_ids),
        "total_queued": total,
        "message": (
            f"Queued service stock scheduler rebuild for {total} target(s)"
            if total
            else "No active or fully paid subscriptions or plan financings found for this plan in this academy"
        ),
    }


# Default configuration for coupon statistics
DEFAULT_COUPON_STATS_CONFIG = {
    "coupons": {
        "stats_hours_threshold": 24,
        "stats_top_n": 100,
        "stats_min_usage": 2,
        "stats_cleanup_threshold": 24 * 730,  # 2 years in hours
    }
}


def get_coupon_stats_config(academy_id: Optional[int] = None) -> dict:
    """
    Get coupon statistics configuration for an academy.
    
    Merges academy-specific feature_flags.coupons with defaults.
    Academy values override defaults, missing values use defaults.
    
    Args:
        academy_id: Optional academy ID. If None, returns defaults only.
    
    Returns:
        dict: Merged configuration dictionary with coupon stats settings.
    """
    config = DEFAULT_COUPON_STATS_CONFIG.copy()
    
    if academy_id is None:
        return config
    
    try:
        payment_settings = AcademyPaymentSettings.objects.filter(academy_id=academy_id).first()
        if payment_settings and payment_settings.feature_flags:
            academy_coupons_config = payment_settings.feature_flags.get("coupons", {})
            if academy_coupons_config:
                # Merge academy config into defaults (academy values override)
                config["coupons"].update(academy_coupons_config)
    except Exception:
        # If there's any error, return defaults
        pass
    
    return config


@lru_cache(maxsize=1)
def max_coupons_allowed():
    try:
        return int(os.getenv("MAX_COUPONS_ALLOWED", "1"))

    except Exception:
        return 1


def get_available_coupons(
    plan: Plan,
    coupons: Optional[list[str]] = None,
    user: Optional[User] = None,
    only_sent_coupons: bool = False,
    as_of: Optional[datetime] = None,
) -> list[Coupon]:

    def get_total_spent_coupons(coupon: Coupon) -> int:
        sub_kwargs = {"invoices__bag__coupons": coupon}
        if coupon.expires_at:
            sub_kwargs["created_at__lte"] = coupon.expires_at

        how_many_subscriptions = Subscription.objects.filter(**sub_kwargs).count()
        how_many_plan_financings = PlanFinancing.objects.filter(**sub_kwargs).count()
        total_spent_coupons = how_many_subscriptions + how_many_plan_financings

        return total_spent_coupons

    def manage_coupon(coupon: Coupon) -> None:
        # Prevent sellers from using their own coupons
        if user and coupon.seller and coupon.seller.user == user:
            founded_coupon_slugs.append(coupon.slug)
            return

        # Check if coupon is restricted to a specific user
        if coupon.allowed_user and (not user or coupon.allowed_user != user):
            founded_coupon_slugs.append(coupon.slug)
            return
        # Check if coupon is restricted to a specific plan
        if coupon.referral_type != Coupon.Referral.NO_REFERRAL:
            if coupon.plans.exists():
                if coupon.plans.filter(exclude_from_referral_program=True).exists():
                    founded_coupon_slugs.append(coupon.slug)
                    return
            else:
                if plan and plan.exclude_from_referral_program:
                    founded_coupon_slugs.append(coupon.slug)
                    return

        if coupon.slug not in founded_coupon_slugs:
            if coupon.how_many_offers == -1:
                founded_coupons.append(coupon)
                founded_coupon_slugs.append(coupon.slug)
                return

            if coupon.how_many_offers == 0:
                founded_coupon_slugs.append(coupon.slug)
                return

            total_spent_coupons = get_total_spent_coupons(coupon)
            if coupon.how_many_offers > total_spent_coupons:
                founded_coupons.append(coupon)

            founded_coupon_slugs.append(coupon.slug)

    founded_coupons = []
    founded_coupon_slugs = []
    validity_moment = as_of or timezone.now()

    cou_args = (
        Q(plans=plan) | Q(plans=None),
        Q(offered_at=None) | Q(offered_at__lte=timezone.now()),
        Q(expires_at=None) | Q(expires_at__gte=validity_moment),
    )

    cou_fields = ("id", "slug", "how_many_offers", "offered_at", "expires_at", "seller", "allowed_user")

    if not only_sent_coupons:
        special_offer = (
            Coupon.objects.filter(*cou_args, auto=True)
            .exclude(
                Q(how_many_offers=0) | Q(discount_type=Coupon.Discount.NO_DISCOUNT) | Q(allowed_user__isnull=False)
            )
            .select_related("seller__user", "allowed_user")
            .only(*cou_fields)
            .first()
        )

        if special_offer:
            manage_coupon(special_offer)

    valid_coupons = (
        Coupon.objects.filter(*cou_args, slug__in=coupons, auto=False)
        .exclude(how_many_offers=0)
        .select_related("seller__user", "allowed_user")
        .only(*cou_fields)
    )

    max = max_coupons_allowed()

    if only_sent_coupons:
        sent_coupons = Coupon.objects.filter(*cou_args, slug__in=coupons).only(*cou_fields)

        for coupon in sent_coupons:
            manage_coupon(coupon)
    else:
        for coupon in valid_coupons[0:max]:
            manage_coupon(coupon)

    return founded_coupons


def get_discounted_price(price: float, coupons: list[Coupon]) -> float:
    percent_off_coupons = [x for x in coupons if x.discount_type == Coupon.Discount.PERCENT_OFF]
    fixed_discount_coupons = [
        x for x in coupons if x.discount_type not in [Coupon.Discount.NO_DISCOUNT, Coupon.Discount.PERCENT_OFF]
    ]

    for coupon in percent_off_coupons:
        price -= price * coupon.discount_value

    for coupon in fixed_discount_coupons:
        price -= coupon.discount_value

    if price < 0:
        price = 0

    return price


def get_coupons_for_plan(plan: Plan, coupons: list[Coupon]) -> list[Coupon]:
    """
    Filter coupons that are eligible for a given plan.

    Rules:
      - If coupon.plans is empty -> global coupon, applies to all plans.
      - If coupon.plans is not empty -> applies only if the plan is in coupon.plans.
    """

    eligible: list[Coupon] = []

    for coupon in coupons:
        # scoped coupon
        if coupon.plans.exists():
            if coupon.plans.filter(id=plan.id).exists():
                eligible.append(coupon)
            continue

        # global coupon
        eligible.append(coupon)

    return eligible


def validate_and_create_proof_of_payment(
    request: dict | WSGIRequest | AsyncRequest | HttpRequest | Request,
    staff_user: User,
    academy_id: int,
    lang: Optional[str] = None,
):
    from .tasks import set_proof_of_payment_confirmation_url

    if isinstance(request, (WSGIRequest, AsyncRequest, HttpRequest, Request)):
        data = request.data

    else:
        data = request

    if lang is None:
        settings = get_user_settings(staff_user.id)
        lang = settings.lang

    provided_payment_details = data.get("provided_payment_details")
    reference = data.get("reference")
    file_id = data.get("file")

    if not file_id and not reference:
        raise ValidationException(
            translation(
                lang,
                en="At least one of 'file' or'reference' must be provided",
                es="Debe proporcionar al menos un 'file' o'reference'",
                slug="at-least-one-of-file-or-reference-must-be-provided",
            ),
            code=400,
        )

    x = ProofOfPayment()
    x.provided_payment_details = provided_payment_details
    x.reference = reference
    x.created_by = staff_user

    if file_id and (
        file := File.objects.filter(
            Q(user__id=staff_user.id) | Q(academy__id=academy_id), id=file_id, status=File.Status.CREATED
        ).first()
    ):
        file.status = File.Status.TRANSFERRING
        file.save()

        x.status = ProofOfPayment.Status.PENDING
        x.save()

        set_proof_of_payment_confirmation_url.delay(file.id, x.id)

    elif file_id:
        raise ValidationException(
            translation(
                lang,
                en="Invalid file id",
                es="ID de archivo inválido",
                slug="invalid-file-id",
            ),
            code=400,
        )

    else:
        x.status = ProofOfPayment.Status.DONE
        x.save()

    return x


def resolve_user_from_data(data: dict, lang: str) -> User:
    """Resolve user by id or email from data; raise ValidationException if missing or not found."""
    user_pk = data.get("user")
    if user_pk is None:
        raise ValidationException(
            translation(
                lang,
                en="user must be provided",
                es="user debe ser proporcionado",
                slug="user-must-be-provided",
            ),
            code=400,
        )
    args = []
    kwargs = {}
    if isinstance(user_pk, int):
        kwargs["id"] = user_pk
    else:
        args.append(Q(email=user_pk) | Q(username=user_pk))
    user = User.objects.filter(*args, **kwargs).first()
    if user is None:
        raise ValidationException(
            translation(
                lang,
                en=f"User not found: {user_pk}",
                es=f"Usuario no encontrado: {user_pk}",
                slug="user-not-found",
            ),
            code=404,
        )
    return user


def resolve_payment_method_for_staff(
    data: dict,
    academy_id: int,
    lang: str,
    allow_card_and_crypto: bool = False,
) -> PaymentMethod:
    """Resolve payment_method from data; must exist and belong to academy or global. When allow_card_and_crypto=False, raise if card or crypto."""
    payment_method = data.get("payment_method")
    if not payment_method or (
        payment_method := PaymentMethod.objects.filter(
            Q(academy__id=academy_id) | Q(academy__isnull=True), id=payment_method
        ).first()
    ) is None:
        raise ValidationException(
            translation(
                lang,
                en="Payment method not provided",
                es="Método de pago no proporcionado",
                slug="payment-method-not-provided",
            ),
            code=400,
        )
    if not allow_card_and_crypto and (payment_method.is_credit_card or payment_method.is_crypto):
        raise ValidationException(
            translation(
                lang,
                en="Payment method must not be credit card or crypto for this action",
                es="El método de pago no debe ser tarjeta de crédito ni cripto para esta acción",
                slug="payment-method-must-not-be-card-or-crypto",
            ),
            code=400,
        )
    return payment_method


def resolve_currency_for_staff_payment(
    payment_method: PaymentMethod,
    academy: Academy,
    lang: str,
) -> Currency:
    """Return payment_method.currency or academy.main_currency; raise if neither."""
    currency = payment_method.currency or academy.main_currency
    if not currency:
        raise ValidationException(
            translation(
                lang,
                en="Currency cannot be determined. Please ensure the payment method has a currency assigned or set a main currency for the academy.",
                es="No se puede determinar la moneda. Por favor, asegúrate de que el método de pago tenga una moneda asignada o establece una moneda principal para la academia.",
                slug="currency-not-found",
            ),
            code=400,
        )
    return currency


def create_externally_managed_bag_and_invoice(
    user: User,
    academy: Academy,
    currency: Currency,
    amount: float,
    payment_method: PaymentMethod,
    proof_of_payment: ProofOfPayment,
    lang: str,
    bag_type: str = Bag.Type.BAG,
    plans: Optional[QuerySet] = None,
    service_items: Optional[list] = None,
    how_many_installments: int = 1,
    chosen_period: Optional[str] = None,
    amount_breakdown: Optional[dict] = None,
    externally_managed: bool = True,
    invoice_kind: str = Invoice.InvoiceKind.GENERAL,
    **bag_extra: Any,
) -> Tuple[Bag, Invoice]:
    """Create Bag and Invoice; attach plans or service_items. Return (bag, invoice).

    Set ``externally_managed=False`` for system-generated invoices (e.g. credit-applied charges)
    that have no external payment method — the Invoice model requires a payment_method whenever
    externally_managed is True.
    """
    utc_now = timezone.now()
    bag = Bag()
    bag.type = bag_type
    bag.user = user
    bag.currency = currency
    bag.status = Bag.Status.PAID
    bag.academy = academy
    bag.is_recurrent = bool(plans)
    bag.how_many_installments = how_many_installments
    if chosen_period is not None:
        bag.chosen_period = chosen_period
    for key, value in bag_extra.items():
        if hasattr(bag, key):
            setattr(bag, key, value)
    bag.save()
    if plans is not None:
        bag.plans.set(plans)
    if service_items is not None:
        bag.service_items.set(service_items)
    if amount_breakdown is None and (bag.plans.exists() or bag.service_items.exists() or bag.plan_addons.exists()):
        try:
            amount_breakdown = calculate_invoice_breakdown(
                bag=bag,
                invoice=None,
                lang=lang,
                chosen_period=bag.chosen_period,
                how_many_installments=bag.how_many_installments,
            )
        except Exception:
            amount_breakdown = None
    invoice = Invoice(
        amount=amount,
        paid_at=utc_now,
        user=user,
        bag=bag,
        academy=academy,
        status=Invoice.Status.FULFILLED,
        currency=currency,
        externally_managed=externally_managed,
        invoice_kind=invoice_kind,
        proof=proof_of_payment,
        payment_method=payment_method,
        amount_breakdown=amount_breakdown,
    )
    if amount_breakdown is None:
        invoice.amount_breakdown = calculate_invoice_breakdown(bag, invoice, lang)
    invoice.save()
    return bag, invoice


def validate_and_create_subscriptions(
    request: dict | WSGIRequest | AsyncRequest | HttpRequest | Request,
    staff_user: User,
    proof_of_payment: ProofOfPayment,
    academy_id: int,
    lang: Optional[str] = None,
):
    if isinstance(request, (WSGIRequest, AsyncRequest, HttpRequest, Request)):
        data = request.data

    else:
        data = request

    if lang is None:
        settings = get_user_settings(staff_user.id)
        lang = settings.lang

    allowed_grace_period_units = {DAY, WEEK, MONTH, YEAR}

    try:
        how_many_installments = int(data.get("how_many_installments", 1))
    except (TypeError, ValueError):
        raise ValidationException(
            translation(
                lang,
                en="how_many_installments must be a positive integer",
                es="how_many_installments debe ser un entero positivo",
                slug="invalid-how-many-installments",
            ),
            code=400,
        )

    if how_many_installments <= 0:
        raise ValidationException(
            translation(
                lang,
                en="how_many_installments must be a positive integer",
                es="how_many_installments debe ser un entero positivo",
                slug="invalid-how-many-installments",
            ),
            code=400,
        )

    initial_payment_amount = data.get("initial_payment_amount", None)
    if initial_payment_amount is not None:
        try:
            initial_payment_amount = float(initial_payment_amount)
        except (TypeError, ValueError):
            raise ValidationException(
                translation(
                    lang,
                    en="initial_payment_amount must be a number",
                    es="initial_payment_amount debe ser un número",
                    slug="invalid-initial-payment-amount",
                ),
                code=400,
            )

        if initial_payment_amount < 0:
            raise ValidationException(
                translation(
                    lang,
                    en="initial_payment_amount must be zero or greater",
                    es="initial_payment_amount debe ser cero o mayor",
                    slug="invalid-initial-payment-amount",
                ),
                code=400,
            )

    unique_payment_negotiated_amount = data.get("unique_payment_negotiated_amount", None)
    if unique_payment_negotiated_amount is None and "negotiated_invoice_amount" in data:
        unique_payment_negotiated_amount = data.get("negotiated_invoice_amount", None)
    if unique_payment_negotiated_amount is not None:
        try:
            unique_payment_negotiated_amount = float(unique_payment_negotiated_amount)
        except (TypeError, ValueError):
            raise ValidationException(
                translation(
                    lang,
                    en="unique_payment_negotiated_amount must be a number",
                    es="unique_payment_negotiated_amount debe ser un número",
                    slug="invalid-unique-payment-negotiated-amount",
                ),
                code=400,
            )
        if unique_payment_negotiated_amount <= 0:
            raise ValidationException(
                translation(
                    lang,
                    en="unique_payment_negotiated_amount must be greater than zero",
                    es="unique_payment_negotiated_amount debe ser mayor que cero",
                    slug="invalid-unique-payment-negotiated-amount",
                ),
                code=400,
            )

    if initial_payment_amount is not None and unique_payment_negotiated_amount is not None:
        raise ValidationException(
            translation(
                lang,
                en="unique_payment_negotiated_amount cannot be combined with initial_payment_amount",
                es="unique_payment_negotiated_amount no puede combinarse con initial_payment_amount",
                slug="unique-payment-negotiated-initial-exclusive",
            ),
            code=400,
        )

    initial_payment_notes = data.get("initial_payment_notes", None)
    if initial_payment_amount is not None and not str(initial_payment_notes or "").strip():
        raise ValidationException(
            translation(
                lang,
                en="initial_payment_notes is required when using initial_payment_amount",
                es="initial_payment_notes es obligatorio al usar initial_payment_amount",
                slug="initial-payment-notes-required",
            ),
            code=400,
        )

    if (
        unique_payment_negotiated_amount is not None
        and how_many_installments == 1
        and not str(initial_payment_notes or "").strip()
    ):
        raise ValidationException(
            translation(
                lang,
                en="initial_payment_notes is required when using unique_payment_negotiated_amount for one payment plans",
                es="initial_payment_notes es obligatorio al usar unique_payment_negotiated_amount en planes de un pago",
                slug="negotiated-amount-notes-required",
            ),
            code=400,
        )
    initial_payment_notes = format_note_made_by_user(initial_payment_notes, staff_user.id)

    try:
        grace_period_duration = int(data.get("grace_period_duration", 0) or 0)
    except (TypeError, ValueError):
        raise ValidationException(
            translation(
                lang,
                en="grace_period_duration must be zero or a positive integer",
                es="grace_period_duration debe ser cero o un entero positivo",
                slug="invalid-grace-period-duration",
            ),
            code=400,
        )

    if grace_period_duration < 0:
        raise ValidationException(
            translation(
                lang,
                en="grace_period_duration must be zero or a positive integer",
                es="grace_period_duration debe ser cero o un entero positivo",
                slug="invalid-grace-period-duration",
            ),
            code=400,
        )

    grace_period_duration_unit = data.get("grace_period_duration_unit", MONTH)
    if grace_period_duration_unit not in allowed_grace_period_units:
        raise ValidationException(
            translation(
                lang,
                en="grace_period_duration_unit must be DAY, WEEK, MONTH or YEAR",
                es="grace_period_duration_unit debe ser DAY, WEEK, MONTH o YEAR",
                slug="invalid-grace-period-duration-unit",
            ),
            code=400,
        )

    cohort = data.get("cohorts", [])
    cohort_found = []

    if cohort:
        for x in cohort:
            x = Cohort.objects.filter(slug=x).first()
            if not x:
                raise ValidationException(
                    translation(
                        lang,
                        en=f"Cohort not found: {x}",
                        es=f"Cohorte no encontrada: {x}",
                        slug="cohort-not-found",
                    ),
                    code=404,
                )
            cohort_found.append(x)

    extra = {}
    if cohort_found:
        extra["cohort_set__cohorts__slug__in"] = cohort

    plans = data.get("plans", [])
    plans = Plan.objects.filter(slug__in=plans, **extra).distinct()
    if plans.count() != 1:
        raise ValidationException(
            translation(
                lang,
                en="Exactly one plan must be provided",
                es="Debe proporcionar exactamente un plan",
                slug="exactly-one-plan-must-be-provided",
            ),
            code=400,
        )

    if "coupons" in data and not isinstance(data["coupons"], list):
        raise ValidationException(
            translation(
                lang,
                en="Coupons must be a list of strings",
                es="Cupones debe ser una lista de cadenas",
                slug="invalid-coupons",
            ),
            code=400,
        )

    if "coupons" in data and len(data["coupons"]) > (max := max_coupons_allowed()):
        raise ValidationException(
            translation(
                lang,
                en=f"Too many coupons (max {max})",
                es=f"Demasiados cupones (max {max})",
                slug="too-many-coupons",
            ),
            code=400,
        )

    plan = plans[0]

    financing_option_id = data.get("financing_option_id")
    if financing_option_id is not None:
        try:
            financing_option_id = int(financing_option_id)
        except (TypeError, ValueError):
            raise ValidationException(
                translation(
                    lang,
                    en="financing_option_id must be an integer",
                    es="financing_option_id debe ser un entero",
                ),
                slug="invalid-financing-option-id",
                code=400,
            )

    option = get_plan_financing_option(
        plan,
        how_many_installments,
        financing_option_id=financing_option_id,
        lang=lang,
    )

    conversion_info = data["conversion_info"] if "conversion_info" in data else None
    validate_conversion_info(conversion_info, lang)

    academy = Academy.objects.filter(id=academy_id).first()
    if academy is None:
        raise ValidationException(
            translation(
                lang,
                en="Academy not found",
                es="Academia no encontrada",
                slug="academy-not-found",
            ),
            code=404,
        )

    user = resolve_user_from_data(data, lang)

    if PlanFinancing.objects.filter(plans=plan, user=user, valid_until__gt=timezone.now()).exists():
        raise ValidationException(
            translation(
                lang,
                en=f"User already has a valid subscription for this plan: {data.get('user')}",
                es=f"Usuario ya tiene una suscripción válida para este plan: {data.get('user')}",
                slug="user-already-has-valid-subscription",
            ),
            code=409,
        )

    # Get available coupons for this user (excluding their own coupons if they are a seller)
    coupons = get_available_coupons(plan, data.get("coupons", []), user=user)

    payment_method = resolve_payment_method_for_staff(data, academy_id, lang, allow_card_and_crypto=True)
    currency = resolve_currency_for_staff_payment(payment_method, academy, lang)

    original_price = option.monthly_price
    catalog_installment_amount = get_discounted_price(original_price, coupons)
    installment_amount = catalog_installment_amount
    if unique_payment_negotiated_amount is not None:
        installment_amount = unique_payment_negotiated_amount

    if initial_payment_amount is not None:
        amount = initial_payment_amount
    elif unique_payment_negotiated_amount is not None:
        amount = unique_payment_negotiated_amount
    else:
        amount = installment_amount

    amount_breakdown = None
    if initial_payment_amount is not None:
        amount_breakdown = {
            "plans": {
                plan.slug: {
                    "amount": amount,
                    "currency": currency.code,
                    "type": "INITIAL_PAYMENT",
                }
            },
            "service-items": {},
        }
    elif unique_payment_negotiated_amount is not None:
        amount_breakdown = {
            "plans": {
                plan.slug: {
                    "amount": amount,
                    "currency": currency.code,
                    "type": "UNIQUE_PAYMENT_NEGOTIATED",
                    "catalog_installment_amount": catalog_installment_amount,
                }
            },
            "service-items": {},
        }

    bag, invoice = create_externally_managed_bag_and_invoice(
        user=user,
        academy=academy,
        currency=currency,
        amount=amount,
        payment_method=payment_method,
        proof_of_payment=proof_of_payment,
        lang=lang,
        bag_type=Bag.Type.BAG,
        plans=plans,
        how_many_installments=how_many_installments,
        amount_breakdown=amount_breakdown,
    )
    if initial_payment_notes is not None:
        invoice.invoice_notes = initial_payment_notes
        invoice.save(update_fields=["invoice_notes"])

    # Create reward coupons for sellers if coupons were used
    if coupons and original_price > 0:
        create_seller_reward_coupons(coupons, original_price, user)

    build_kwargs: dict[str, Any] = {
        "conversion_info": conversion_info,
        "cohorts": cohort,
    }

    if grace_period_duration > 0:
        build_kwargs["grace_period_duration"] = grace_period_duration
        build_kwargs["grace_period_duration_unit"] = grace_period_duration_unit

    if initial_payment_notes is not None:
        build_kwargs["initial_payment_notes"] = initial_payment_notes

    if initial_payment_amount is not None:
        build_kwargs["principal_amount"] = catalog_installment_amount
        build_kwargs["initial_payment_amount"] = amount
    elif unique_payment_negotiated_amount is not None:
        build_kwargs["principal_amount"] = unique_payment_negotiated_amount

    tasks.build_plan_financing.delay(bag.id, invoice.id, **build_kwargs)

    return invoice, coupons


def grant_consumables_for_user(
    request: dict | WSGIRequest | AsyncRequest | HttpRequest | Request,
    proof_of_payment: ProofOfPayment,
    academy_id: int,
    lang: Optional[str] = None,
) -> Invoice:
    """
    Staff grant consumables to a user (standalone purchase/grant).
    Requires payment_method (non-card, non-crypto), proof, user, service, how_many.
    Creates Bag, Invoice (externally_managed), and Consumable(s) with standalone_invoice set.
    """
    if isinstance(request, (WSGIRequest, AsyncRequest, HttpRequest, Request)):
        data = request.data
    else:
        data = request

    if lang is None:
        if isinstance(request, (WSGIRequest, AsyncRequest, HttpRequest, Request)) and getattr(request, "user", None):
            lang = get_user_settings(request.user.id).lang
        else:
            lang = "en"

    academy = Academy.objects.filter(id=academy_id).first()
    if not academy:
        raise ValidationException(
            translation(
                lang,
                en="Academy not found",
                es="Academia no encontrada",
                slug="academy-not-found",
            ),
            code=404,
        )

    service_spec = data.get("service")
    if not service_spec:
        raise ValidationException(
            translation(
                lang,
                en="Service is required",
                es="El servicio es requerido",
                slug="service-is-required",
            ),
            code=400,
        )
    if isinstance(service_spec, int):
        service = Service.objects.filter(id=service_spec).first()
    else:
        service = Service.objects.filter(slug=service_spec).first()
    if not service:
        raise ValidationException(
            translation(
                lang,
                en="Service not found",
                es="El servicio no fue encontrado",
                slug="service-not-found",
            ),
            code=404,
        )

    if service.type not in (
        Service.Type.MENTORSHIP_SERVICE_SET,
        Service.Type.EVENT_TYPE_SET,
        Service.Type.VOID,
    ):
        raise ValidationException(
            translation(
                lang,
                en="This service type is not allowed for staff grant. Use MENTORSHIP_SERVICE_SET, EVENT_TYPE_SET, or VOID.",
                es="Este tipo de servicio no está permitido para concesión por staff.",
                slug="service-type-not-allowed-for-grant",
            ),
            code=400,
        )

    how_many = data.get("how_many")
    if not how_many or (isinstance(how_many, (int, float)) and how_many <= 0):
        raise ValidationException(
            translation(
                lang,
                en="how_many is required and must be a positive number",
                es="how_many es requerido y debe ser un número positivo",
                slug="how-many-required",
            ),
            code=400,
        )
    how_many = int(how_many)

    mentorship_service_set_id = data.get("mentorship_service_set")
    event_type_set_id = data.get("event_type_set")
    if mentorship_service_set_id and event_type_set_id:
        raise ValidationException(
            translation(
                lang,
                en="Provide only one of mentorship_service_set or event_type_set, not both",
                es="Proporcione solo uno de mentorship_service_set o event_type_set",
                slug="only-one-set-allowed",
            ),
            code=400,
        )
    if service.type == Service.Type.MENTORSHIP_SERVICE_SET and not mentorship_service_set_id:
        raise ValidationException(
            translation(
                lang,
                en="mentorship_service_set is required for this service type",
                es="mentorship_service_set es requerido para este tipo de servicio",
                slug="mentorship-service-set-required",
            ),
            code=400,
        )
    if service.type == Service.Type.EVENT_TYPE_SET and not event_type_set_id:
        raise ValidationException(
            translation(
                lang,
                en="event_type_set is required for this service type",
                es="event_type_set es requerido para este tipo de servicio",
                slug="event-type-set-required",
            ),
            code=400,
        )

    kwargs_academy = {}
    if mentorship_service_set_id:
        mentorship_service_set = MentorshipServiceSet.objects.filter(
            id=mentorship_service_set_id, academy_id=academy_id
        ).first()
        if not mentorship_service_set:
            raise ValidationException(
                translation(
                    lang,
                    en="Mentorship service set not found",
                    es="Conjunto de mentoría no encontrado",
                    slug="mentorship-service-set-not-found",
                ),
                code=404,
            )
        kwargs_academy["available_mentorship_service_sets"] = mentorship_service_set_id
    else:
        mentorship_service_set = None

    if event_type_set_id:
        event_type_set = EventTypeSet.objects.filter(id=event_type_set_id, academy_id=academy_id).first()
        if not event_type_set:
            raise ValidationException(
                translation(
                    lang,
                    en="Event type set not found",
                    es="Conjunto de tipo de evento no encontrado",
                    slug="event-type-set-not-found",
                ),
                code=404,
            )
        kwargs_academy["available_event_type_sets"] = event_type_set_id
    else:
        event_type_set = None

    academy_service = AcademyService.objects.filter(
        academy_id=academy_id, service=service, **kwargs_academy
    ).first()
    if not academy_service:
        raise ValidationException(
            translation(
                lang,
                en="Academy service not found",
                es="Servicio de academia no encontrado",
                slug="academy-service-not-found",
            ),
            code=404,
        )

    user = resolve_user_from_data(data, lang)
    payment_method = resolve_payment_method_for_staff(data, academy_id, lang, allow_card_and_crypto=False)
    currency = resolve_currency_for_staff_payment(payment_method, academy, lang)

    amount = data.get("amount")
    if amount is None:
        amount = 0.0
    else:
        amount = float(amount)

    service_item, _ = ServiceItem.get_or_create_for_service(
        service=service, how_many=how_many, is_team_allowed=False
    )

    bag, invoice = create_externally_managed_bag_and_invoice(
        user=user,
        academy=academy,
        currency=currency,
        amount=amount,
        payment_method=payment_method,
        proof_of_payment=proof_of_payment,
        lang=lang,
        bag_type=Bag.Type.CHARGE,
        service_items=[service_item],
        how_many_installments=0,
    )

    valid_until = resolve_grant_valid_until(
        data.get("duration") if "duration" in data else None,
        data.get("duration_unit") if "duration_unit" in data else None,
        lang,
        service,
    )

    consumable = Consumable(
        service_item=service_item,
        user=user,
        how_many=how_many,
        mentorship_service_set=mentorship_service_set,
        event_type_set=event_type_set,
        standalone_invoice=invoice,
        valid_until=valid_until,
    )
    consumable.save()

    if valid_until:
        schedule_standalone_consumable_deprovision(consumable.id, valid_until, service)

    return invoice


@dataclass
class DepositAllocation:
    """Describes how a single deposit amount was allocated."""

    installment_applied: bool
    credit_added: float = 0.0
    credit_entry_amount: float = 0.0
    credit_entry_type: Optional[str] = None
    credit_consumed: float = 0.0
    credit_entries: list[dict[str, Any]] = field(default_factory=list)
    invoice_amount: float = 0.0


@dataclass
class DepositResult:
    """Full result returned by register_student_deposit."""

    invoice: Invoice
    allocation: DepositAllocation
    credit_balance: float
    remaining_installments: int
    warning: Optional[str]


def get_remaining_installments(plan_financing: PlanFinancing) -> int:
    """Return the number of installments still pending on a PlanFinancing."""
    return max(plan_financing.how_many_installments - int(plan_financing.installments_paid or 0), 0)


def plan_financing_was_staff_assigned(
    plan_financing: PlanFinancing,
    first_invoice: Invoice | None = None,
) -> bool:
    """
    True when the financing was created by staff (academy subscription or student invite),
    not by self-checkout (PayView / Stripe / Coinbase webhooks).
    """
    if first_invoice is None:
        first_invoice = (
            plan_financing.invoices.select_related("bag", "proof").order_by("paid_at", "id").first()
        )

    if not first_invoice:
        return False

    if first_invoice.proof_id is not None:
        return True

    bag = first_invoice.bag
    return bag is not None and bag.type == Bag.Type.INVITED


def get_credit_balance(plan_financing: PlanFinancing) -> float:
    """Return the current credit balance for a PlanFinancing from the CreditLedgerEntry ledger.

    The filter is intentionally scoped to PLAN_FINANCING entries only, so that any future GLOBAL
    entries for the same user are not accidentally included in installment calculations.
    """
    result = CreditLedgerEntry.objects.filter(
        plan_financing=plan_financing,
        scope=CreditLedgerEntry.Scope.PLAN_FINANCING,
    ).aggregate(total=Sum("amount"))["total"]
    return float(result or 0)


def _is_credit_only_manual_deposit_invoice(invoice: Invoice) -> bool:
    breakdown = invoice.amount_breakdown or {}
    plans = breakdown.get("plans", {}) if isinstance(breakdown, dict) else {}
    if not isinstance(plans, dict):
        return False
    for item in plans.values():
        if isinstance(item, dict) and item.get("type") == "MANUAL_DEPOSIT_CREDIT":
            return True
    return False


def get_plan_financing_payment_schedule(plan_financing: PlanFinancing, *, lang: str = "en") -> dict[str, Any]:
    """
    Build dynamic payment schedule and KPI summary for a PlanFinancing.
    """
    utc_now = timezone.now()
    installments = int(plan_financing.how_many_installments or 0)
    installments_paid = min(max(int(plan_financing.installments_paid or 0), 0), max(installments, 0))
    remaining_installments = max(installments - installments_paid, 0)
    monthly_price = float(plan_financing.monthly_price or 0)

    fulfilled_invoices = list(
        plan_financing.invoices.filter(status=Invoice.Status.FULFILLED).order_by("paid_at", "id")
    )

    paid_so_far = 0.0
    for invoice in fulfilled_invoices:
        paid_so_far += max(float(invoice.amount or 0) - float(invoice.amount_refunded or 0), 0)

    initial_payment_amount = float(plan_financing.initial_payment_amount or 0)
    negotiated_total = initial_payment_amount + (monthly_price * installments)
    pending_amount = max(negotiated_total - paid_so_far, 0.0)
    credit_balance = get_credit_balance(plan_financing)
    next_payment_due = plan_financing.next_payment_at if remaining_installments > 0 else None
    primary_plan = plan_financing.plans.order_by("id").first()

    first_due_date = None
    if installments > 0 and plan_financing.next_payment_at:
        first_due_date = plan_financing.next_payment_at - relativedelta(months=installments_paid)
    elif installments > 0 and plan_financing.valid_until:
        first_due_date = plan_financing.valid_until - relativedelta(months=max(installments - 1, 0))
    elif installments > 0:
        first_due_date = plan_financing.created_at

    closure_dates: list[datetime] = []
    for invoice in fulfilled_invoices:
        if _is_credit_only_manual_deposit_invoice(invoice):
            continue
        closure_dates.append(invoice.paid_at or invoice.created_at)

    auto_credit_consumed = (
        CreditLedgerEntry.objects.filter(
            plan_financing=plan_financing,
            scope=CreditLedgerEntry.Scope.PLAN_FINANCING,
            entry_type=CreditLedgerEntry.EntryType.CREDIT_CONSUMED,
            source_invoice__isnull=True,
        )
        .order_by("created_at", "id")
    )
    for entry in auto_credit_consumed:
        if entry.notes and "Automatic charge covered by accumulated credit" in entry.notes:
            closure_dates.append(entry.created_at)

    closure_dates = sorted(closure_dates)
    if len(closure_dates) < installments_paid:
        for invoice in fulfilled_invoices:
            dt = invoice.paid_at or invoice.created_at
            if dt not in closure_dates:
                closure_dates.append(dt)
                if len(closure_dates) >= installments_paid:
                    break
        closure_dates = sorted(closure_dates)

    if first_due_date:
        while len(closure_dates) < installments_paid:
            closure_dates.append(first_due_date + relativedelta(months=len(closure_dates)))

    closure_dates = closure_dates[:installments_paid]
    schedule: list[dict[str, Any]] = []
    on_time_count = 0

    if installments > 0 and first_due_date:
        for idx in range(1, installments + 1):
            due_date = first_due_date + relativedelta(months=idx - 1)
            paid_at = closure_dates[idx - 1] if idx <= installments_paid else None

            if paid_at is not None:
                # Business rule: payment on the same calendar day counts as on time,
                # even if it was registered later than the due hour.
                is_on_time = paid_at.date() <= due_date.date()
                status = "PAID_ON_TIME" if is_on_time else "PAID_LATE"
                if is_on_time:
                    on_time_count += 1
                paid_amount = monthly_price
            else:
                status = "OVERDUE" if due_date < utc_now else "PENDING"
                paid_amount = 0.0

            schedule.append(
                {
                    "installment_number": idx,
                    "due_date": due_date,
                    "expected_amount": monthly_price,
                    "paid_amount": paid_amount,
                    "paid_at": paid_at,
                    "status": status,
                }
            )

    on_time_rate = None
    if installments_paid > 0:
        on_time_rate = round((on_time_count / installments_paid) * 100, 2)

    return {
        "summary": {
            "plan_financing_id": plan_financing.id,
            "plan_slug": primary_plan.slug if primary_plan else None,
            "paid_so_far": paid_so_far,
            "on_time_rate": on_time_rate,
            "pending_amount": pending_amount,
            "negotiated_total": negotiated_total,
            "next_payment_due": next_payment_due,
            "payments_made": installments_paid,
            "total_payments": installments,
            "current_credit": credit_balance,
            "currency": plan_financing.currency.code if plan_financing.currency else None,
        },
        "schedule": schedule,
    }


@transaction.atomic
def register_student_deposit(
    request: dict | WSGIRequest | AsyncRequest | HttpRequest | Request,
    proof_of_payment: ProofOfPayment,
    academy_id: int,
    lang: Optional[str] = None,
) -> DepositResult:
    """
    Register a manual student deposit and apply it to the next installment of a plan financing.
    """
    if isinstance(request, (WSGIRequest, AsyncRequest, HttpRequest, Request)):
        data = request.data
    else:
        data = request

    if lang is None:
        if isinstance(request, (WSGIRequest, AsyncRequest, HttpRequest, Request)) and getattr(request, "user", None):
            lang = get_user_settings(request.user.id).lang
        else:
            lang = "en"

    academy = Academy.objects.filter(id=academy_id).first()
    if not academy:
        raise ValidationException(
            translation(lang, en="Academy not found", es="Academia no encontrada", slug="academy-not-found"),
            code=404,
        )

    financing_id = data.get("plan_financing") or data.get("plan_financing_id")
    if not financing_id:
        raise ValidationException(
            translation(
                lang,
                en="plan_financing is required",
                es="plan_financing es requerido",
                slug="plan-financing-required",
            ),
            code=400,
        )

    plan_financing = (
        PlanFinancing.objects.filter(id=financing_id, academy_id=academy_id).select_related("user", "currency").first()
    )
    if not plan_financing:
        raise ValidationException(
            translation(
                lang,
                en="Plan financing not found",
                es="No existe el plan de financiamiento",
                slug="plan-financing-not-found",
            ),
            code=404,
        )

    if plan_financing.status in [
        PlanFinancing.Status.CANCELLED,
        PlanFinancing.Status.DEPRECATED,
        PlanFinancing.Status.EXPIRED,
        PlanFinancing.Status.FULLY_PAID,
    ]:
        raise ValidationException(
            translation(
                lang,
                en="Plan financing cannot receive deposits in its current status",
                es="El plan financiado no puede recibir depósitos en su estado actual",
                slug="invalid-plan-financing-status",
            ),
            code=409,
        )

    if data.get("user") and int(data["user"]) != plan_financing.user_id:
        raise ValidationException(
            translation(
                lang,
                en="Deposit user does not match the plan financing user",
                es="El usuario del depósito no coincide con el usuario del plan financiado",
                slug="user-does-not-match-plan-financing",
            ),
            code=400,
        )

    try:
        amount = float(data.get("amount"))
    except (TypeError, ValueError):
        raise ValidationException(
            translation(lang, en="amount must be a positive number", es="amount debe ser un número positivo", slug="invalid-amount"),
            code=400,
        )

    if amount <= 0:
        raise ValidationException(
            translation(lang, en="amount must be greater than zero", es="amount debe ser mayor a cero", slug="invalid-amount"),
            code=400,
        )

    notes = data.get("notes") or data.get("deposit_notes") or data.get("invoice_notes")
    if notes and len(notes) > 250:
        raise ValidationException(
            translation(
                lang,
                en="notes must be 250 characters or less",
                es="notes debe tener 250 caracteres o menos",
                slug="invalid-notes",
            ),
            code=400,
        )

    payment_method = resolve_payment_method_for_staff(data, academy_id, lang, allow_card_and_crypto=False)
    currency = resolve_currency_for_staff_payment(payment_method, academy, lang)
    plans = plan_financing.plans.all()
    monthly_price = float(plan_financing.monthly_price or 0)

    # Compute remaining installments and current credit BEFORE creating the invoice so a fully-paid
    # financing cannot accept extra deposits and incorrectly advance next_payment_at.
    remaining_installments = get_remaining_installments(plan_financing)
    if remaining_installments <= 0:
        raise ValidationException(
            translation(
                lang,
                en="No installments remaining to pay for this plan financing",
                es="No quedan cuotas por pagar en este plan de financiamiento",
                slug="no-remaining-installments",
            ),
            code=409,
        )

    credit_balance = get_credit_balance(plan_financing)
    utc_now = timezone.now()
    payment_settings = AcademyPaymentSettings.objects.filter(academy=plan_financing.academy).first()
    early_renewal_window_days = payment_settings.early_renewal_window_days if payment_settings else 0
    renewal_window_start = plan_financing.next_payment_at - timedelta(days=early_renewal_window_days)
    is_within_early_window = utc_now >= renewal_window_start

    # ── Determine allocation ──────────────────────────────────────────────────
    # For every installment: how much cash is actually needed after applying credit.
    still_owed = max(monthly_price - credit_balance, 0)

    # Total amount the plan can still absorb (all remaining installments minus existing credit).
    total_remaining = monthly_price * remaining_installments
    max_deposit = max(total_remaining - credit_balance, 0)

    if amount > max_deposit + 1e-9:
        raise ValidationException(
            translation(
                lang,
                en=f"Amount {currency.format_price(amount)} exceeds the maximum deposit allowed "
                f"of {currency.format_price(max_deposit)} for this plan "
                f"({remaining_installments} installment(s) × {currency.format_price(monthly_price)} "
                f"minus {currency.format_price(credit_balance)} existing credit).",
                es=f"El monto {currency.format_price(amount)} supera el máximo permitido "
                f"de {currency.format_price(max_deposit)} para este plan "
                f"({remaining_installments} cuota(s) × {currency.format_price(monthly_price)} "
                f"menos {currency.format_price(credit_balance)} de crédito existente).",
            ),
            slug="overpayment-exceeds-plan-total",
        )

    # At this point amount <= max_deposit, so no overpayment beyond the plan total is possible.
    # Window policy:
    # - Outside early window: always treat manual deposit as deferred credit (do not close installment).
    # - Inside early window: FIFO policy to close the current installment when possible.
    credit_consumed = 0.0
    credit_added = 0.0
    installment_applied = False

    if not is_within_early_window:
        credit_added = amount
    else:
        # FIFO policy:
        # - When closing an installment, consume existing credit first.
        # - Any deposit surplus becomes new credit.
        # - If an installment is already fully covered by existing credit and future installments remain,
        #   manual deposit stays as credit (do not close another installment in this call).
        if remaining_installments == 1:
            if amount >= still_owed - 1e-9:
                installment_applied = True
                credit_consumed = min(credit_balance, monthly_price)
            else:
                credit_added = amount
        else:
            if still_owed < 1e-9:
                credit_added = amount
            elif amount >= still_owed - 1e-9:
                installment_applied = True
                credit_consumed = min(credit_balance, monthly_price)
                deposit_used_for_installment = max(monthly_price - credit_consumed, 0.0)
                credit_added = max(amount - deposit_used_for_installment, 0.0)
            else:
                credit_added = amount

    created_credit_entries: list[dict[str, Any]] = []

    # ── Build breakdown type label ────────────────────────────────────────────
    breakdown_type = "MANUAL_DEPOSIT_INSTALLMENT" if installment_applied else "MANUAL_DEPOSIT_CREDIT"

    amount_breakdown = {
        "plans": {
            plan.slug: {
                "amount": amount,
                "currency": currency.code,
                "type": breakdown_type,
            }
            for plan in plans
        },
        "service-items": {},
    }

    bag, invoice = create_externally_managed_bag_and_invoice(
        user=plan_financing.user,
        academy=academy,
        currency=currency,
        amount=amount,
        payment_method=payment_method,
        proof_of_payment=proof_of_payment,
        lang=lang,
        bag_type=Bag.Type.CHARGE,
        plans=plans,
        how_many_installments=0,
        amount_breakdown=amount_breakdown,
        invoice_kind=Invoice.InvoiceKind.MANUAL_DEPOSIT,
    )
    staff_user_id = None
    if isinstance(request, (WSGIRequest, AsyncRequest, HttpRequest, Request)) and getattr(request, "user", None):
        if request.user.is_authenticated:
            staff_user_id = request.user.id
    invoice_notes = format_note_made_by_user(notes, staff_user_id)
    if invoice_notes:
        invoice.invoice_notes = invoice_notes
        invoice.save(update_fields=["invoice_notes"])
    bag.was_delivered = True
    bag.save()
    # Every manual deposit invoice represents real cash received for this financing.
    # Link all of them for complete payment-history/audit visibility.
    plan_financing.invoices.add(invoice)
    if installment_applied:
        # installments_paid remains the only source of truth for closed billing cycles.
        PlanFinancing.objects.filter(pk=plan_financing.pk).update(
            installments_paid=F("installments_paid") + 1
        )
        plan_financing.refresh_from_db(fields=["installments_paid"])

    # ── Persist ledger entry/entries (FIFO) ───────────────────────────────────
    if credit_consumed > 1e-9:
        amount_consumed = -credit_consumed
        CreditLedgerEntry.objects.create(
            user=plan_financing.user,
            scope=CreditLedgerEntry.Scope.PLAN_FINANCING,
            plan_financing=plan_financing,
            amount=amount_consumed,
            entry_type=CreditLedgerEntry.EntryType.CREDIT_CONSUMED,
            source_invoice=invoice,
            notes=notes,
        )
        created_credit_entries.append(
            {
                "amount": amount_consumed,
                "entry_type": CreditLedgerEntry.EntryType.CREDIT_CONSUMED,
            }
        )

    if credit_added > 1e-9:
        CreditLedgerEntry.objects.create(
            user=plan_financing.user,
            scope=CreditLedgerEntry.Scope.PLAN_FINANCING,
            plan_financing=plan_financing,
            amount=credit_added,
            entry_type=CreditLedgerEntry.EntryType.CREDIT_ADDED,
            source_invoice=invoice,
            notes=notes,
        )
        created_credit_entries.append(
            {
                "amount": credit_added,
                "entry_type": CreditLedgerEntry.EntryType.CREDIT_ADDED,
            }
        )

    # Backward-compatible compact view for callers that still expect one movement.
    if len(created_credit_entries) == 1:
        credit_entry_amount = float(created_credit_entries[0]["amount"])
        credit_entry_type = str(created_credit_entries[0]["entry_type"])
    else:
        credit_entry_amount = 0.0
        credit_entry_type = None

    # ── Build warning message ─────────────────────────────────────────────────
    new_credit_balance = credit_balance - credit_consumed + credit_added

    warning: Optional[str] = None
    if not installment_applied and new_credit_balance < monthly_price - 1e-9:
        # Total accumulated credit is still not enough to cover a full installment.
        # The next automatic charge may fail and trigger cancellation.
        warning = translation(
            lang,
            en=(
                f"Partial payment recorded. The total accumulated credit "
                f"({currency.format_price(new_credit_balance)}) is still less than the installment amount "
                f"({currency.format_price(monthly_price)}). Full payment must be received before "
                f"{plan_financing.next_payment_at.date()} to avoid cancellation."
            ),
            es=(
                f"Pago parcial registrado. El crédito acumulado total "
                f"({currency.format_price(new_credit_balance)}) aún es menor al valor de la cuota "
                f"({currency.format_price(monthly_price)}). Se requiere el pago completo antes del "
                f"{plan_financing.next_payment_at.date()} para evitar la cancelación."
            ),
        )

    # ── Advance billing cycle when installment is applied ─────────────────────
    if installment_applied:
        # Recompute remaining after the new invoice is linked.
        remaining_installments = get_remaining_installments(plan_financing)

        # Only roll next_payment_at when the due date has passed. If charge_plan_financing
        # already advanced the calendar on an unpaid staff cycle, next_payment_at may be in
        # the future — closing the installment must not push the due date forward again.
        if utc_now >= plan_financing.next_payment_at:
            delta = relativedelta(months=1)
            while utc_now >= plan_financing.next_payment_at + delta:
                delta += relativedelta(months=1)

            plan_financing.next_payment_at += delta

        plan_financing.valid_until = plan_financing.next_payment_at + relativedelta(
            months=max(remaining_installments - 1, 0)
        )
        plan_financing.status = (
            PlanFinancing.Status.ACTIVE if remaining_installments > 0 else PlanFinancing.Status.FULLY_PAID
        )
        plan_financing.status_message = None
        plan_financing.save()

        tasks.renew_plan_financing_consumables.delay(plan_financing.id)
        if remaining_installments > 0:
            reschedule_billing_tasks(plan_financing_id=plan_financing.id)
        else:
            for fn in (tasks.charge_plan_financing, tasks.notify_plan_financing_renewal):
                _cancel_pending_future_scheduled(fn, plan_financing.id, utc_now=utc_now)

    new_credit_balance = get_credit_balance(plan_financing)

    allocation = DepositAllocation(
        installment_applied=installment_applied,
        credit_added=credit_added,
        credit_entry_amount=credit_entry_amount,
        credit_entry_type=credit_entry_type,
        credit_consumed=credit_consumed,
        credit_entries=created_credit_entries,
        invoice_amount=amount,
    )

    return DepositResult(
        invoice=invoice,
        allocation=allocation,
        credit_balance=new_credit_balance,
        remaining_installments=remaining_installments,
        warning=warning,
    )


class UnitBalance(TypedDict):
    unit: int


class ConsumableItem(TypedDict):
    id: int
    how_many: int
    unit_type: str
    valid_until: Optional[datetime]


class ResourceBalance(TypedDict):
    id: int
    slug: str
    balance: UnitBalance
    items: list[ConsumableItem]


class ConsumableBalance(TypedDict):
    mentorship_service_sets: ResourceBalance
    cohort_sets: list[ResourceBalance]
    event_type_sets: list[ResourceBalance]
    voids: list[ResourceBalance]


def set_virtual_balance(balance: ConsumableBalance, user: User) -> None:
    from breathecode.admissions.actions import is_no_saas_student_up_to_date_in_any_cohort
    from breathecode.payments.data import get_virtual_consumables

    if is_no_saas_student_up_to_date_in_any_cohort(user, default=False) is False:
        return

    virtuals = get_virtual_consumables()

    event_type_set_ids = [virtual["event_type_set"]["id"] for virtual in virtuals if virtual["event_type_set"]]
    cohort_set_ids = [virtual["cohort_set"]["id"] for virtual in virtuals if virtual["cohort_set"]]
    mentorship_service_set_ids = [
        virtual["mentorship_service_set"]["id"] for virtual in virtuals if virtual["mentorship_service_set"]
    ]

    available_services = [
        virtual["service_item"]["service"]["id"]
        for virtual in virtuals
        if virtual["service_item"]["service"]["type"] == Service.Type.VOID
    ]

    available_event_type_sets = EventTypeSet.objects.filter(
        academy__profileacademy__user=user, id__in=event_type_set_ids
    ).values_list("id", flat=True)

    available_cohort_sets = CohortSet.objects.filter(cohorts__cohortuser__user=user, id__in=cohort_set_ids).values_list(
        "id", flat=True
    )

    available_mentorship_service_sets = MentorshipServiceSet.objects.filter(
        academy__profileacademy__user=user, id__in=mentorship_service_set_ids
    ).values_list("id", flat=True)

    balance_mapping: dict[str, dict[int, int]] = {
        "cohort_sets": dict(
            [(v["id"], i) for (i, v) in enumerate(balance["cohort_sets"]) if v["id"] in available_cohort_sets]
        ),
        "event_type_sets": dict(
            [(v["id"], i) for (i, v) in enumerate(balance["event_type_sets"]) if v["id"] in available_event_type_sets]
        ),
        "mentorship_service_sets": dict(
            [
                (v["id"], i)
                for (i, v) in enumerate(balance["mentorship_service_sets"])
                if v["id"] in available_mentorship_service_sets
            ]
        ),
        "voids": dict([(v["id"], i) for (i, v) in enumerate(balance["voids"]) if v["id"] in available_services]),
    }

    def append(
        key: Literal["cohort_sets", "event_type_sets", "mentorship_service_sets", "voids"],
        id: int,
        slug: str,
        how_many: int,
        unit_type: str,
        valid_until: Optional[datetime] = None,
    ):

        index = balance_mapping[key].get(id)

        # index = balance[key].append(id)
        unit_type = unit_type.lower()
        if index is None:
            balance[key].append({"id": id, "slug": slug, "balance": {unit_type: 0}, "items": []})
            index = len(balance[key]) - 1
            balance_mapping[key][id] = index

        obj = balance[key][index]

        if how_many == -1:
            obj["balance"][unit_type] = how_many

        elif obj["balance"][unit_type] != -1:
            obj["balance"][unit_type] += how_many

        obj["items"].append(
            {
                "id": None,
                "how_many": how_many,
                "unit_type": unit_type.upper(),
                "valid_until": valid_until,
                "subscription_seat": None,
                "subscription_billing_team": None,
                "user": user.id,
                "subscription": None,
                "plan_financing": None,
            }
        )

    for virtual in virtuals:
        if (
            virtual["service_item"]["service"]["type"] == Service.Type.VOID
            and virtual["service_item"]["service"]["id"] in available_services
        ):
            id = virtual["service_item"]["service"]["id"]
            slug = virtual["service_item"]["service"]["slug"]
            how_many = virtual["service_item"]["how_many"]
            unit_type = virtual["service_item"]["unit_type"]
            append("voids", id, slug, how_many, unit_type)

        if virtual["event_type_set"] and virtual["event_type_set"]["id"] in available_event_type_sets:
            id = virtual["event_type_set"]["id"]
            slug = virtual["event_type_set"]["slug"]
            how_many = virtual["service_item"]["how_many"]
            unit_type = virtual["service_item"]["unit_type"]
            append("event_type_sets", id, slug, how_many, unit_type)

        if (
            virtual["mentorship_service_set"]
            and virtual["mentorship_service_set"]["id"] in available_mentorship_service_sets
        ):
            id = virtual["mentorship_service_set"]["id"]
            slug = virtual["mentorship_service_set"]["slug"]
            how_many = virtual["service_item"]["how_many"]
            unit_type = virtual["service_item"]["unit_type"]
            append("mentorship_service_sets", id, slug, how_many, unit_type)

        if virtual["cohort_set"] and virtual["cohort_set"]["id"] in available_cohort_sets:
            id = virtual["cohort_set"]["id"]
            slug = virtual["cohort_set"]["slug"]
            how_many = virtual["service_item"]["how_many"]
            unit_type = virtual["service_item"]["unit_type"]
            append("cohort_sets", id, slug, how_many, unit_type)





def is_stripe_checkout_already_fulfilled(
    *,
    session: dict,
    exclude_stripe_event_id: int | None = None,
) -> bool:
    session_id = session.get("id")
    if not session_id:
        return False

    done_events = StripeEvent.objects.filter(status="DONE", data__object__id=session_id)
    if exclude_stripe_event_id:
        done_events = done_events.exclude(id=exclude_stripe_event_id)
    if done_events.exists():
        return True

    metadata = session.get("metadata") or {}
    is_purchase = not metadata.get("subscription_id") and not metadata.get("plan_financing_id")

    invoice = Invoice.objects.filter(stripe_id=session_id, status=Invoice.Status.FULFILLED).first()
    if not invoice:
        return False

    if raw_sub_id := metadata.get("subscription_id"):
        try:
            sub_id = int(float(raw_sub_id))
        except (TypeError, ValueError):
            return False
        return Subscription.objects.filter(id=sub_id, user=invoice.user, invoices=invoice).exists()

    if raw_pf_id := metadata.get("plan_financing_id"):
        try:
            pf_id = int(float(raw_pf_id))
        except (TypeError, ValueError):
            return False
        return PlanFinancing.objects.filter(id=pf_id, user=invoice.user, invoices=invoice).exists()

    bag = invoice.bag
    if not bag:
        return False

    if bag.was_delivered:
        return True

    if Subscription.objects.filter(invoices=invoice).exists():
        return True
    if PlanFinancing.objects.filter(invoices=invoice).exists():
        return True

    if is_purchase and bag.status == Bag.Status.PAID and not bag.was_delivered:
        # Invoice for this session exists but build_* did not finish; pending-bag supervisor owns it.
        return True

    return False


def retry_pending_bag(bag: Bag):
    """
    This function retries the delivery of bags that are paid but not delivered.
    It is intended to be called periodically by a scheduler.
    """

    if bag.status != Bag.Status.PAID:
        return "not-paid"

    if bag.was_delivered:
        return "done"

    invoice: Invoice | None = bag.invoices.first()
    if invoice is None:
        return "no-invoice"

    if bag.how_many_installments > 0:
        tasks.build_plan_financing.delay(bag.id, invoice.id)

    elif invoice.amount > 0:
        tasks.build_subscription.delay(bag.id, invoice.id)

    else:
        tasks.build_free_subscription.delay(bag.id, invoice.id)

    return "scheduled"


def get_cached_currency(code: str, cache: dict[str, Currency]) -> Currency | None:
    """
    Get a currency from the cache by code.
    """
    currency = cache.get(code.upper())
    if currency is None:
        currency = Currency.objects.filter(code__iexact=code).first()
        cache[code.upper()] = currency
    return currency


def apply_pricing_ratio(
    price: float,
    country_code: Optional[str],
    obj: Optional[Union[Plan, AcademyService, FinancingOption]] = None,
    price_attr: str = "price",
    lang: Optional[str] = None,
    cache: Optional[dict[str, Currency]] = None,
) -> Tuple[float, Optional[float], Optional[Currency]]:
    """
    Apply pricing ratio to a price based on country code and object-specific overrides.

    Args:
        price (float): The original price to apply ratio to
        country_code (Optional[str]): Two-letter country code to look up ratio for
        obj (Optional[Union[Plan, AcademyService]]): Plan or AcademyService object that may have pricing overrides
        price_attr (str): Attribute name to use for price override
        lang (Optional[str]): Language to use for translations
        cache (Optional[dict[str, Currency]]): Cache of currencies

    Returns:
        Tuple[float, Optional[float], Optional[Currency]]: A tuple containing:
            - The final price after applying any ratio
            - The ratio that was applied (None if using object's direct price override)
            - The currency that was used for the price if it was overridden

    The function applies pricing ratios in the following order:
    1. If the object has a direct price override for the country, use that price and return None as ratio
    2. If the object has a ratio override for the country, apply that ratio
    3. If there is a general ratio defined for the country, apply that ratio
    4. Otherwise return the original price with None as ratio
    """

    if not price or not country_code:
        return price, None, None

    if cache is None:
        cache = {}

    country_code = country_code.lower()

    # Check for object-specific overrides first
    if obj and hasattr(obj, "pricing_ratio_exceptions") and obj.pricing_ratio_exceptions:
        exceptions = obj.pricing_ratio_exceptions.get(country_code, {})

        currency = exceptions.get("currency", None)
        if currency:
            currency = get_cached_currency(currency, cache)

            if currency is None:
                raise ValidationException(
                    translation(
                        lang or "en", en="Currency not found", es="Moneda no encontrada", slug="currency-not-found"
                    ),
                    code=404,
                )

        # Direct price override - Check this FIRST
        if exceptions.get(price_attr) is not None:
            return exceptions[price_attr], None, currency

        # Ratio override
        if exceptions.get("ratio") is not None:
            return price * exceptions["ratio"], exceptions["ratio"], currency

    # Fall back to general ratios
    if country_code in GENERAL_PRICING_RATIOS:
        ratio = GENERAL_PRICING_RATIOS[country_code]["pricing_ratio"]
        return price * ratio, ratio, None

    return price, None, None


def create_seller_reward_coupons(coupons: list[Coupon], original_price: float, buyer_user: User) -> None:
    """
    Create reward coupons for sellers when their coupons are used in payments.

    Creates user-restricted coupons that sellers can use on any plan.

    Args:
        coupons: List of coupons used in the payment
        original_price: The original price before discounts
        buyer_user: The user who made the purchase
    """
    utc_now = timezone.now()

    for coupon in coupons:
        if not coupon.seller or not coupon.seller.user:
            continue

        seller_user = coupon.seller.user

        # Don't create reward for the buyer themselves (already prevented by validation)
        if seller_user == buyer_user:
            continue

        # Calculate reward amount based on coupon's referral settings
        reward_amount = 0
        if coupon.referral_type == Coupon.Referral.PERCENTAGE:
            reward_amount = original_price * coupon.referral_value
        elif coupon.referral_type == Coupon.Referral.FIXED_PRICE:
            reward_amount = coupon.referral_value
        else:
            # No referral reward configured
            continue

        if reward_amount <= 0:
            continue

        # Create a unique slug for the reward coupon
        base_slug = f"reward-{seller_user.id}-{coupon.slug}"
        reward_slug = base_slug
        counter = 1

        while Coupon.objects.filter(slug=reward_slug).exists():
            reward_slug = f"{base_slug}-{counter}"
            counter += 1

        # Create the reward coupon restricted to the seller
        # No plans restriction - can be used with any plan
        reward_coupon = Coupon(
            slug=reward_slug,
            discount_type=Coupon.Discount.FIXED_PRICE,
            discount_value=reward_amount,
            referral_type=Coupon.Referral.NO_REFERRAL,
            referral_value=0,
            auto=False,
            referred_buyer=buyer_user,
            how_many_offers=1,  # Single use
            allowed_user=seller_user,  # Restrict to seller only
            offered_at=utc_now,
            expires_at=utc_now + timedelta(days=90),  # 90 days to use the reward
        )
        reward_coupon.save()

        logger.info(
            f"Created user-restricted reward coupon {reward_coupon.slug} of {reward_amount} "
            f"for seller {seller_user.id} from coupon {coupon.slug}"
        )


def is_plan_paid(plan: Plan) -> bool:
    """
    Check if a plan is paid by examining its pricing structure.

    Args:
        plan: The plan to check

    Returns:
        bool: True if the plan is paid, False if it's free
    """
    if not plan.is_renewable:
        # For non-renewable plans, check if they have financing options
        return plan.financing_options.exists()

    # For renewable plans, check if any pricing field is greater than 0
    return (
        (getattr(plan, "price_per_month", 0) or 0) > 0
        or (getattr(plan, "price_per_quarter", 0) or 0) > 0
        or (getattr(plan, "price_per_half", 0) or 0) > 0
        or (getattr(plan, "price_per_year", 0) or 0) > 0
    )


def is_subscription_paid(subscription: Subscription) -> bool:
    """
    Check if a subscription is paid by examining its plans.

    Args:
        subscription: The subscription to check

    Returns:
        bool: True if the subscription is paid, False if it's free
    """
    for plan in subscription.plans.all():
        if is_plan_paid(plan):
            return True
    return False


def manage_plan_financing_add_ons(request: Request, bag: Bag, lang: str) -> float:
    """Return the sum of add-on prices from an object list in request.data.

    Expected format (always objects):
      add_ons: [
        { id: <academy_service_id>, quantity?: <int>, ... },
        ...
      ]
    Rules:
      - Only AcademyServices in plan.add_ons are considered
      - quantity defaults to 1 if missing; must be > 0
    """

    plan = bag.plans.filter().first()
    if not plan:
        return 0.0

    payload = request.data.get("add_ons")
    if not isinstance(payload, list) or not payload:
        return 0.0

    allowed_addons = {a.id: a for a in plan.add_ons.all()}

    total = 0.0
    for entry in payload:
        if not isinstance(entry, dict):
            continue

        academy_service_id = entry.get("id") if isinstance(entry.get("id"), int) else None
        if academy_service_id is None:
            continue

        add_on = allowed_addons.get(academy_service_id)
        if not add_on:
            continue

        qty = entry.get("quantity")
        if not isinstance(qty, int) or qty <= 0:
            qty = 1

        price, _, _ = add_on.get_discounted_price(qty, bag.country_code, lang)
        total += float(price or 0)

    return total


def get_plan_addons_amount(bag: Bag, lang: str) -> float:
    """
    Calculate the total one-shot amount for all plan addons in a bag.

    Rules:
      - Each addon plan must have a FinancingOption with how_many_months=1.
      - Pricing ratio is applied using bag.country_code and the FinancingOption.
      - All addons must share the same currency as the academy/bag.
      - The result is stored in bag.plan_addons_amount.
    """

    addons = bag.plan_addons.all()
    if not addons.exists():
        if bag.plan_addons_amount:
            bag.plan_addons_amount = 0
            bag.save(update_fields=["plan_addons_amount"])
        return 0.0

    main_currency = bag.currency or bag.academy.main_currency
    if not main_currency:
        raise ValidationException(
            translation(
                lang,
                en="Academy does not have a main currency configured",
                es="La academia no tiene una moneda principal configurada",
                slug="academy-without-main-currency",
            ),
            code=500,
        )

    currencies: dict[str, Currency] = {main_currency.code.upper(): main_currency}
    total = 0.0
    pricing_explanation: list[dict[str, Any]] = []

    for plan in addons:
        option = plan.financing_options.filter(how_many_months=1).first()
        if not option:
            raise ValidationException(
                translation(
                    lang,
                    en=f"Plan addon {plan.slug} does not have a one-payment financing option configured",
                    es=f"El plan addon {plan.slug} no tiene configurada una opción de financiamiento de un solo pago",
                    slug="plan-addon-without-one-payment-option",
                ),
                code=400,
            )

        base_price = option.monthly_price or 0

        if bag.country_code:
            adjusted_price, ratio, c = apply_pricing_ratio(base_price, bag.country_code, option, lang=lang)

            if c:
                currencies[c.code.upper()] = c

            if adjusted_price != base_price and base_price > 0 and ratio:
                pricing_explanation.append({"plan": plan.slug, "ratio": ratio})

            price = adjusted_price
        else:
            price = base_price

        total += float(price or 0)

    if len(currencies.keys()) > 1:
        raise ValidationException(
            translation(
                lang,
                en="Multiple currencies found, it means that the pricing ratio exceptions have a wrong configuration",
                es="Múltiples monedas encontradas, lo que significa que las excepciones de ratio de precios tienen una configuración incorrecta",
                slug="multiple-currencies-found",
            ),
            code=500,
        )

    # Update pricing ratio explanation for plan_addons without touching plans/service_items keys
    explanation = bag.pricing_ratio_explanation or {"plans": [], "service_items": [], "plan_addons": []}
    if "plan_addons" not in explanation:
        explanation["plan_addons"] = []

    if pricing_explanation:
        explanation["plan_addons"] = pricing_explanation
        bag.pricing_ratio_explanation = explanation

    bag.plan_addons_amount = total
    bag.save(update_fields=["pricing_ratio_explanation", "plan_addons_amount"])

    return total


def get_plan_addons_amounts_with_coupons(
    bag: Bag, coupons: list[Coupon], lang: str
) -> tuple[float, float]:
    """
    Calculate the total one-shot amount for all plan addons in a bag,
    returning both:
      - total_before: sum before coupons
      - total_after: sum after applying eligible coupons per addon

    Coupons are filtered per addon using get_coupons_for_plan, so a coupon
    only discounts an addon if it is configured to work with that plan.
    """

    addons = bag.plan_addons.all()
    if not addons.exists():
        return 0.0, 0.0

    main_currency = bag.currency or bag.academy.main_currency
    if not main_currency:
        raise ValidationException(
            translation(
                lang,
                en="Academy does not have a main currency configured",
                es="La academia no tiene una moneda principal configurada",
                slug="academy-without-main-currency",
            ),
            code=500,
        )

    currencies: dict[str, Currency] = {main_currency.code.upper(): main_currency}
    total_before = 0.0
    total_after = 0.0

    for plan in addons:
        option = plan.financing_options.filter(how_many_months=1).first()
        if not option:
            raise ValidationException(
                translation(
                    lang,
                    en=f"Plan addon {plan.slug} does not have a one-payment financing option configured",
                    es=f"El plan addon {plan.slug} no tiene configurada una opción de financiamiento de un solo pago",
                    slug="plan-addon-without-one-payment-option",
                ),
                code=400,
            )

        base_price = option.monthly_price or 0

        if bag.country_code:
            base_price, _, c = apply_pricing_ratio(base_price, bag.country_code, option, lang=lang)

            if c:
                currencies[c.code.upper()] = c

        total_before += float(base_price or 0)

        addon_coupons = get_coupons_for_plan(plan, coupons)
        price_after = get_discounted_price(base_price, addon_coupons)
        total_after += price_after

    if len(currencies.keys()) > 1:
        raise ValidationException(
            translation(
                lang,
                en="Multiple currencies found, it means that the pricing ratio exceptions have a wrong configuration",
                es="Múltiples monedas encontradas, lo que significa que las excepciones de ratio de precios tienen una configuración incorrecta",
                slug="multiple-currencies-found",
            ),
            code=500,
        )

    return total_before, total_after


# Keep old function name for backward compatibility
def calculate_invoice_amount_breakdown(
    bag: Bag,
    main_plan_amount: float = 0.0,
    main_plan_amount_before_discount: float = 0.0,
    service_items_amount: float = 0.0,
    plan_addons_amount: float = 0.0,
    plan_addons_amount_before_discount: float = 0.0,
    seat_costs: float = 0.0,
    lang: str = "en",
    invoice: Invoice | None = None,
) -> dict[str, Any]:
    """
    Legacy function for backward compatibility.
    Now delegates to calculate_invoice_breakdown which calculates everything from scratch.
    """
    return calculate_invoice_breakdown(bag=bag, invoice=invoice, lang=lang)


def _invoice_breakdown_has_line_items(breakdown: dict[str, Any] | None) -> bool:
    if not breakdown:
        return False
    return bool(breakdown.get("plans")) or bool(breakdown.get("service-items"))


def ensure_invoice_amount_breakdown(invoice: Invoice, lang: str) -> None:
    """
    Populate invoice.amount_breakdown when missing, using the invoice bag (same logic as admin bulk action).
    """
    if _invoice_breakdown_has_line_items(invoice.amount_breakdown):
        return

    if not invoice.bag_id:
        return

    bag = invoice.bag
    try:
        breakdown = calculate_invoice_breakdown(bag, invoice, lang)
        invoice.amount_breakdown = breakdown
        invoice.save(update_fields=["amount_breakdown"])
    except Exception as e:
        logger.warning(
            "Failed to recalculate amount_breakdown for invoice %s: %s",
            invoice.id,
            e,
        )


def calculate_refund_breakdown(
    invoice: Invoice, refund_amount: float, items_to_refund: dict[str, float], lang: str = "en"
) -> dict[str, Any]:
    """
    Calculate which components of the invoice should be refunded based on the refund amount and items to refund.

    Args:
        invoice: The invoice to refund
        refund_amount: Total amount to refund (must match sum of items_to_refund values)
        items_to_refund: Dictionary mapping slugs to refund amounts (e.g., {'plan-slug': 100, 'service-slug': 50}). Required.
        lang: Language code

    Returns:
        Dictionary with breakdown of what to refund (plans, service-items)
    """
    if not invoice.amount_breakdown:
        raise ValidationException(
            translation(
                lang,
                en="Invoice does not have amount_breakdown. Cannot calculate refund breakdown.",
                es="La factura no tiene amount_breakdown. No se puede calcular el breakdown del reembolso.",
                slug="invoice-no-breakdown",
            ),
            code=400,
        )

    breakdown = invoice.amount_breakdown
    total_invoice = invoice.amount
    already_refunded = invoice.amount_refunded or 0
    available_to_refund = total_invoice - already_refunded

    if refund_amount <= 0:
        raise ValidationException(
            translation(
                lang,
                en="Refund amount must be greater than 0",
                es="El monto del reembolso debe ser mayor que 0",
                slug="invalid-refund-amount",
            ),
            code=400,
        )

    # Check if refund amount exceeds available amount
    if refund_amount > available_to_refund:
        raise ValidationException(
            translation(
                lang,
                en=f"Refund amount ({refund_amount}) exceeds available amount to refund ({available_to_refund}). "
                f"Already refunded: {already_refunded}, Invoice total: {total_invoice}",
                es=f"El monto del reembolso ({refund_amount}) excede el monto disponible para reembolsar ({available_to_refund}). "
                f"Ya reembolsado: {already_refunded}, Total de la factura: {total_invoice}",
                slug="refund-amount-exceeds-available",
            ),
            code=400,
        )

    refund_breakdown: dict[str, Any] = {
        "plans": {},
        "service-items": {},
    }

    # First, validate that ALL slugs exist in the breakdown before processing anything
    available_plan_slugs = set(breakdown.get("plans", {}).keys())
    available_service_slugs = set(breakdown.get("service-items", {}).keys())
    all_available_slugs = available_plan_slugs | available_service_slugs

    # Find slugs that don't exist in the breakdown
    items_to_refund_slugs = set(items_to_refund.keys())
    invalid_slugs = items_to_refund_slugs - all_available_slugs

    if invalid_slugs:
        available_slugs = []
        if breakdown.get("plans"):
            available_slugs.append(f"plans: {list(breakdown['plans'].keys())}")
        if breakdown.get("service-items"):
            available_slugs.append(f"service-items: {list(breakdown['service-items'].keys())}")

        raise ValidationException(
            translation(
                lang,
                en=f"Invalid slugs provided: {list(invalid_slugs)}. These slugs do not exist in the invoice breakdown. "
                f"Available slugs: {', '.join(available_slugs)}",
                es=f"Slugs inválidos proporcionados: {list(invalid_slugs)}. Estos slugs no existen en el breakdown de la factura. "
                f"Slugs disponibles: {', '.join(available_slugs)}",
                slug="invalid-slugs-in-breakdown",
            ),
            code=400,
        )

    # Validate that refund amounts for each item don't exceed their original amounts
    # and calculate total refund amount from items_to_refund
    total_refund_from_items = 0.0

    # Check plans
    if "plans" in breakdown and breakdown["plans"]:
        for plan_slug, refund_amount_for_plan in items_to_refund.items():
            if plan_slug in breakdown["plans"]:
                original_amount = breakdown["plans"][plan_slug].get("amount", 0)
                if refund_amount_for_plan > original_amount:
                    raise ValidationException(
                        translation(
                            lang,
                            en=f"Refund amount for '{plan_slug}' ({refund_amount_for_plan}) exceeds its original amount ({original_amount})",
                            es=f"El monto del reembolso para '{plan_slug}' ({refund_amount_for_plan}) excede su monto original ({original_amount})",
                            slug="refund-amount-exceeds-item-amount",
                        ),
                        code=400,
                    )
                total_refund_from_items += refund_amount_for_plan

    # Check service items
    if "service-items" in breakdown and breakdown["service-items"]:
        for service_slug, refund_amount_for_service in items_to_refund.items():
            if service_slug in breakdown["service-items"]:
                original_amount = breakdown["service-items"][service_slug].get("amount", 0)
                if refund_amount_for_service > original_amount:
                    raise ValidationException(
                        translation(
                            lang,
                            en=f"Refund amount for '{service_slug}' ({refund_amount_for_service}) exceeds its original amount ({original_amount})",
                            es=f"El monto del reembolso para '{service_slug}' ({refund_amount_for_service}) excede su monto original ({original_amount})",
                            slug="refund-amount-exceeds-item-amount",
                        ),
                        code=400,
                    )
                total_refund_from_items += refund_amount_for_service

    # Validate that total refund amount matches the sum of items_to_refund amounts
    if abs(refund_amount - total_refund_from_items) > 0.01:  # Allow small floating point differences
        raise ValidationException(
            translation(
                lang,
                en=f"Refund amount ({refund_amount}) does not match the sum of items_to_refund amounts ({total_refund_from_items}). "
                f"Items to refund: {items_to_refund}",
                es=f"El monto del reembolso ({refund_amount}) no coincide con la suma de los montos de items_to_refund ({total_refund_from_items}). "
                f"Items a reembolsar: {items_to_refund}",
                slug="refund-amount-mismatch",
            ),
            code=400,
        )

    # Apply refund amounts directly from items_to_refund (no proportional calculation needed)
    # Check plans
    if "plans" in breakdown and breakdown["plans"]:
        for plan_slug, refund_amount_for_plan in items_to_refund.items():
            if plan_slug in breakdown["plans"]:
                plan_data = breakdown["plans"][plan_slug]
                if refund_amount_for_plan > 0:
                    refund_breakdown["plans"][plan_slug] = {
                        **plan_data,
                        "amount": refund_amount_for_plan,
                    }

    # Check service items
    if "service-items" in breakdown and breakdown["service-items"]:
        for service_slug, refund_amount_for_service in items_to_refund.items():
            if service_slug in breakdown["service-items"]:
                service_data = breakdown["service-items"][service_slug]
                if refund_amount_for_service > 0:
                    refund_breakdown["service-items"][service_slug] = {
                        **service_data,
                        "amount": refund_amount_for_service,
                    }

    return refund_breakdown


def _validate_refund_request(invoice: Invoice, amount: float | None, lang: str) -> float:
    already_refunded = invoice.amount_refunded or 0
    available_to_refund = invoice.amount - already_refunded

    if already_refunded >= invoice.amount:
        raise ValidationException(
            translation(
                lang,
                en=f"Invoice has already been fully refunded. Total refunded: {already_refunded}, Invoice amount: {invoice.amount}",
                es=f"La factura ya ha sido completamente reembolsada. Total reembolsado: {already_refunded}, Monto de la factura: {invoice.amount}",
                slug="invoice-already-fully-refunded",
            ),
            code=400,
        )

    if amount is None:
        raise ValidationException(
            translation(
                lang,
                en="Refund amount is required and must be greater than 0",
                es="El monto del reembolso es requerido y debe ser mayor que 0",
                slug="refund-amount-required",
            ),
            code=400,
        )

    if amount <= 0:
        raise ValidationException(
            translation(
                lang,
                en="Refund amount must be greater than 0",
                es="El monto del reembolso debe ser mayor que 0",
                slug="invalid-refund-amount",
            ),
            code=400,
        )

    if amount > available_to_refund:
        raise ValidationException(
            translation(
                lang,
                en=f"Refund amount ({amount}) exceeds available amount to refund ({available_to_refund}). "
                f"Already refunded: {already_refunded}, Invoice total: {invoice.amount}",
                es=f"El monto del reembolso ({amount}) excede el monto disponible para reembolsar ({available_to_refund}). "
                f"Ya reembolsado: {already_refunded}, Total de la factura: {invoice.amount}",
                slug="refund-amount-exceeds-available",
            ),
            code=400,
        )

    if invoice.status not in [
        Invoice.Status.FULFILLED,
        Invoice.Status.PARTIALLY_REFUNDED,
        Invoice.Status.REFUNDED,
    ]:
        raise ValidationException(
            translation(
                lang,
                en="Only fulfilled or partially refunded invoices can be refunded",
                es="Solo las facturas cumplidas o parcialmente reembolsadas pueden ser reembolsadas",
                slug="invoice-not-fulfilled",
            ),
            code=400,
        )

    return amount


def _apply_invoice_refund_balance(invoice: Invoice, amount: float) -> None:
    invoice.amount_refunded = (invoice.amount_refunded or 0) + amount
    if invoice.amount_refunded >= invoice.amount:
        invoice.status = Invoice.Status.REFUNDED
        invoice.refunded_at = timezone.now()
    elif invoice.amount_refunded > 0:
        invoice.status = Invoice.Status.PARTIALLY_REFUNDED
    invoice.save()


def _bag_plan_slugs(bag: Bag) -> set[str]:
    slugs = set(bag.plans.values_list("slug", flat=True))
    slugs.update(bag.plan_addons.values_list("slug", flat=True))
    return slugs


PLAN_ENTITLEMENT_ACTION_CANCEL_IMMEDIATELY = "cancel_immediately"
PLAN_ENTITLEMENT_ACTION_CANCEL_AT_PERIOD_END = "cancel_at_period_end"
PLAN_ENTITLEMENT_ACTION_KEEP = "keep"

VALID_PLAN_ENTITLEMENT_ACTIONS = frozenset(
    {
        PLAN_ENTITLEMENT_ACTION_CANCEL_IMMEDIATELY,
        PLAN_ENTITLEMENT_ACTION_CANCEL_AT_PERIOD_END,
        PLAN_ENTITLEMENT_ACTION_KEEP,
    }
)


def _plan_slugs_in_refund_items(invoice: Invoice, items_to_refund: dict[str, float]) -> list[str]:
    bag = invoice.bag
    original_breakdown = invoice.amount_breakdown or {}
    plan_slugs_in_invoice: set[str] = set()

    if original_breakdown.get("plans"):
        plan_slugs_in_invoice = set(original_breakdown["plans"].keys())
    elif bag:
        plan_slugs_in_invoice = _bag_plan_slugs(bag)

    if not plan_slugs_in_invoice:
        return []

    return [
        plan_slug
        for plan_slug, refund_amount_for_plan in items_to_refund.items()
        if plan_slug in plan_slugs_in_invoice and refund_amount_for_plan > 0
    ]


def _target_status_for_plan_entitlement_action(plan_entitlement_action: str) -> str | None:
    if plan_entitlement_action == PLAN_ENTITLEMENT_ACTION_CANCEL_IMMEDIATELY:
        return AbstractIOweYou.Status.EXPIRED
    if plan_entitlement_action == PLAN_ENTITLEMENT_ACTION_CANCEL_AT_PERIOD_END:
        return AbstractIOweYou.Status.CANCELLED
    return None


def _apply_plan_entitlement_action_to_iou(iou, target_status: str, invoice: Invoice) -> None:
    entity = "Subscription" if isinstance(iou, Subscription) else "Plan financing"
    iou.status = target_status
    iou.status_message = f"{entity} {target_status.lower()} due to refund of invoice {invoice.id}"
    iou.save()


def _apply_refund_entitlements(
    invoice: Invoice,
    items_to_refund: dict[str, float],
    plan_entitlement_action: str = PLAN_ENTITLEMENT_ACTION_CANCEL_IMMEDIATELY,
) -> None:
    from breathecode.payments.models import PlanServiceItemHandler, SubscriptionServiceItem

    bag = invoice.bag
    user = invoice.user

    plans_to_update: list[str] = []
    service_items_to_remove: list[int] = []

    if items_to_refund:
        if plan_entitlement_action != PLAN_ENTITLEMENT_ACTION_KEEP:
            plans_to_update = _plan_slugs_in_refund_items(invoice, items_to_refund)

        original_breakdown = invoice.amount_breakdown or {}
        service_slugs_in_invoice: set[str] = set()
        if original_breakdown.get("service-items"):
            service_slugs_in_invoice = set(original_breakdown["service-items"].keys())
        elif bag:
            service_slugs_in_invoice = set(
                bag.service_items.select_related("service").values_list("service__slug", flat=True)
            )

        if service_slugs_in_invoice and bag:
            for service_slug, refund_amount_for_service in items_to_refund.items():
                if service_slug in service_slugs_in_invoice and refund_amount_for_service > 0:
                    service_items = bag.service_items.filter(service__slug=service_slug)
                    for service_item in service_items:
                        service_items_to_remove.append(service_item.id)

    target_status = _target_status_for_plan_entitlement_action(plan_entitlement_action)
    if plans_to_update and target_status:
        plans = Plan.objects.filter(slug__in=plans_to_update)
        for plan in plans:
            subscription = Subscription.objects.filter(invoices=invoice, plans=plan).first()
            if subscription:
                _apply_plan_entitlement_action_to_iou(subscription, target_status, invoice)
            else:
                for subscription in Subscription.objects.filter(user=user, plans__in=[plan]):
                    _apply_plan_entitlement_action_to_iou(subscription, target_status, invoice)

            plan_financing = PlanFinancing.objects.filter(invoices=invoice, plans=plan).first()
            if plan_financing:
                _apply_plan_entitlement_action_to_iou(plan_financing, target_status, invoice)
            else:
                for plan_financing in PlanFinancing.objects.filter(user=user, plans__in=[plan]):
                    _apply_plan_entitlement_action_to_iou(plan_financing, target_status, invoice)

    if service_items_to_remove:
        SubscriptionServiceItem.objects.filter(
            subscription__user=user, service_item_id__in=service_items_to_remove
        ).delete()

        PlanServiceItemHandler.objects.filter(
            plan_financing__user=user,
            handler__service_item_id__in=service_items_to_remove,
        ).delete()


def _reverse_credit_for_refunded_invoice(invoice: Invoice) -> None:
    """
    Reverse remaining credit that originated from a refunded invoice.
    """
    # New source of truth: entries tied directly to the invoice.
    invoice_added_entries = (
        CreditLedgerEntry.objects.filter(
            source_invoice=invoice,
            scope=CreditLedgerEntry.Scope.PLAN_FINANCING,
            entry_type=CreditLedgerEntry.EntryType.CREDIT_ADDED,
        )
        .values("plan_financing_id")
        .annotate(total_added=Sum("amount"))
    )

    totals_by_plan: dict[int, float] = {}
    for row in list(invoice_added_entries):
        plan_id = row["plan_financing_id"]
        if not plan_id:
            continue
        totals_by_plan[plan_id] = float(totals_by_plan.get(plan_id, 0.0) + float(row["total_added"] or 0.0))

    for plan_id, total_added in totals_by_plan.items():
        plan_financing = PlanFinancing.objects.filter(id=plan_id).first()
        if not plan_financing or total_added <= 1e-9:
            continue

        current_balance = get_credit_balance(plan_financing)
        reversible = min(total_added, current_balance)
        if reversible <= 1e-9:
            continue

        CreditLedgerEntry.objects.create(
            user=invoice.user,
            scope=CreditLedgerEntry.Scope.PLAN_FINANCING,
            plan_financing=plan_financing,
            amount=-reversible,
            entry_type=CreditLedgerEntry.EntryType.CREDIT_CONSUMED,
            source_invoice=invoice,
            notes=f"Credit reversal for refunded invoice #{invoice.id}",
        )


def process_refund(
    invoice: Invoice,
    amount: float | None,
    items_to_refund: dict[str, float],
    breakdown: dict[str, Any] | None = None,
    reason: str = "",
    country_code: str | None = None,
    legal_text: str | None = None,
    lang: str = "en",
    plan_entitlement_action: str = PLAN_ENTITLEMENT_ACTION_CANCEL_IMMEDIATELY,
) -> "CreditNote":
    """
    Process a refund for an invoice.

    Args:
        invoice: The invoice to refund
        amount: Total amount to refund (required, must match sum of items_to_refund values)
        breakdown: Breakdown of what to refund (plans, service-items)
        items_to_refund: Dictionary mapping slugs to refund amounts (e.g., {'plan-slug': 100, 'service-slug': 50}). Required.
        reason: Reason for the refund
        country_code: Country code for legal compliance
        legal_text: Country-specific legal text
        lang: Language code
        plan_entitlement_action: What to do with linked subscription/plan financing when refunding plans

    Returns:
        CreditNote object created for the refund
    """
    ensure_invoice_amount_breakdown(invoice, lang)
    amount = _validate_refund_request(invoice, amount, lang)
    if breakdown is None:
        breakdown = invoice.amount_breakdown or {}

    if _plan_slugs_in_refund_items(invoice, items_to_refund):
        breakdown = {**breakdown, "plan_entitlement_action": plan_entitlement_action}

    refund_stripe_id = None
    if invoice.stripe_id:
        from breathecode.payments.services.stripe import Stripe

        stripe_service = Stripe(academy=invoice.academy)
        stripe_service.set_language(lang)
        try:
            refund_result = stripe_service.refund_payment(invoice, amount=amount)
            refund_stripe_id = refund_result["refund"]["id"]
            invoice.refresh_from_db()
        except Exception as e:
            logger.error(f"Error processing Stripe refund: {str(e)}")
            raise

    if not invoice.stripe_id:
        _apply_invoice_refund_balance(invoice, amount)

    credit_note = CreditNote.objects.create(
        invoice=invoice,
        amount=amount,
        currency=invoice.currency,
        reason=reason,
        status=CreditNote.Status.ISSUED,
        legal_text=legal_text,
        country_code=country_code or invoice.bag.country_code,
        breakdown=breakdown,
        refund_stripe_id=refund_stripe_id,
    )

    _apply_refund_entitlements(invoice, items_to_refund, plan_entitlement_action=plan_entitlement_action)
    _reverse_credit_for_refunded_invoice(invoice)
    return credit_note


def process_refund_record_external(
    invoice: Invoice,
    amount: float | None,
    items_to_refund: dict[str, float],
    external_reference: str,
    stripe_refund_id: str | None = None,
    breakdown: dict[str, Any] | None = None,
    reason: str = "",
    country_code: str | None = None,
    legal_text: str | None = None,
    lang: str = "en",
    plan_entitlement_action: str = PLAN_ENTITLEMENT_ACTION_CANCEL_IMMEDIATELY,
) -> "CreditNote":
    """
    Record a refund that happened outside this API without calling Stripe.
    """
    ensure_invoice_amount_breakdown(invoice, lang)
    amount = _validate_refund_request(invoice, amount, lang)
    _apply_invoice_refund_balance(invoice, amount)

    refund_breakdown = breakdown.copy() if isinstance(breakdown, dict) else (invoice.amount_breakdown or {}).copy()
    refund_breakdown["external-refund"] = {
        "recorded_externally": True,
        "external_reference": external_reference,
    }
    if _plan_slugs_in_refund_items(invoice, items_to_refund):
        refund_breakdown["plan_entitlement_action"] = plan_entitlement_action

    credit_note = CreditNote.objects.create(
        invoice=invoice,
        amount=amount,
        currency=invoice.currency,
        reason=reason,
        status=CreditNote.Status.ISSUED,
        legal_text=legal_text,
        country_code=country_code or invoice.bag.country_code,
        breakdown=refund_breakdown,
        refund_stripe_id=stripe_refund_id,
    )

    _apply_refund_entitlements(invoice, items_to_refund, plan_entitlement_action=plan_entitlement_action)
    _reverse_credit_for_refunded_invoice(invoice)
    return credit_note


def calculate_invoice_breakdown(
    bag: Bag,
    invoice: Invoice,
    lang: str,
    chosen_period: str | None = None,
    how_many_installments: int | None = None,
    financing_option_id: int | None = None,
) -> dict[str, Any]:
    """
    Calculate the breakdown of how the invoice amount is divided across plans, plan addons, and service items.

    Args:
        bag: The bag containing plans, plan_addons, and service_items
        invoice: The invoice to calculate breakdown for
        lang: Language code for error messages
        chosen_period: Optional chosen period (MONTH, QUARTER, HALF, YEAR). If not provided, uses bag.chosen_period
        how_many_installments: Optional number of installments. If not provided, uses bag.how_many_installments
        financing_option_id: Optional financing option id when multiple options share the same installment count

    Returns a dictionary with the following structure:
    {
        "plans": {
            "plan-slug": {
                "amount": float,
                "currency": str
            }
        },
        "service-items": {
            "service-slug": {
                "amount": float,
                "currency": str,
                "how-many": int,
                "unit-type": str
            }
        }
    }

    Note: Plan addons are included in the "plans" section with their plan slug.
    """
    breakdown: dict[str, Any] = {"plans": {}, "service-items": {}}

    currency = invoice.currency or bag.currency or bag.academy.main_currency
    if not currency:
        raise ValidationException(
            translation(
                lang,
                en="Currency not found for invoice breakdown calculation",
                es="Moneda no encontrada para el cálculo del desglose de la factura",
                slug="currency-not-found-for-breakdown",
            ),
            code=500,
        )

    currency_code = currency.code.upper()
    coupons = list(bag.coupons.all())

    # Use provided values or fall back to bag values
    effective_chosen_period = chosen_period if chosen_period is not None else bag.chosen_period
    effective_how_many_installments = how_many_installments if how_many_installments is not None else bag.how_many_installments

    # Ensure we have all plans loaded - use select_related/prefetch_related if needed
    plans = list(bag.plans.all())
    if not plans:
        return breakdown

    for plan in plans:
        base_price = 0.0

        if effective_how_many_installments > 0:
            option = None
            try:
                option = get_plan_financing_option(
                    plan,
                    effective_how_many_installments,
                    financing_option_id=financing_option_id,
                    lang=lang,
                )
            except ValidationException:
                pass

            if not option:
                continue

            base_price = option.monthly_price or 0

            if base_price > 0:
                if bag.country_code:
                    adjusted_price, _, c = apply_pricing_ratio(base_price, bag.country_code, option, lang=lang)
                    if c:
                        currency_code = c.code.upper()
                    base_price = adjusted_price

                if bag.seat_service_item and bag.seat_service_item.how_many > 0:
                    academy_service = AcademyService.objects.filter(
                        service=bag.seat_service_item.service, academy=bag.academy
                    ).first()
                    if academy_service:
                        seat_cost = academy_service.price_per_unit * bag.seat_service_item.how_many
                        base_price += seat_cost

                add_ons_amount = 0
                for add_on in plan.add_ons.filter(currency=currency):
                    service_item = bag.service_items.filter(service=add_on.service).first()
                    if service_item:
                        add_on_price, _, _ = add_on.get_discounted_price(service_item.how_many, bag.country_code, lang)
                        add_ons_amount += add_on_price

                base_price += add_ons_amount

                plan_coupons = get_coupons_for_plan(plan, coupons)
                final_price = get_discounted_price(base_price, plan_coupons)

                if final_price > 0:
                    breakdown["plans"][plan.slug] = {
                        "amount": round(final_price, 2),
                        "currency": currency_code,
                    }

        elif effective_chosen_period and effective_chosen_period != "NO_SET":
            if effective_chosen_period == "MONTH":
                base_price = plan.price_per_month or 0
                price_attr = "price_per_month"
            elif effective_chosen_period == "QUARTER":
                base_price = plan.price_per_quarter or 0
                price_attr = "price_per_quarter"
            elif effective_chosen_period == "HALF":
                base_price = plan.price_per_half or 0
                price_attr = "price_per_half"
            elif effective_chosen_period == "YEAR":
                base_price = plan.price_per_year or 0
                price_attr = "price_per_year"
            else:
                base_price = 0
                price_attr = None

            if base_price > 0 and price_attr:
                # Apply pricing ratio if country code is available
                if bag.country_code:
                    adjusted_price, _, c = apply_pricing_ratio(base_price, bag.country_code, plan, lang=lang, price_attr=price_attr)
                    if c:
                        currency_code = c.code.upper()
                    base_price = adjusted_price

                if bag.seat_service_item and bag.seat_service_item.how_many > 0:
                    academy_service = AcademyService.objects.filter(
                        service=bag.seat_service_item.service, academy=bag.academy
                    ).first()
                    if academy_service:
                        if effective_chosen_period == "MONTH":
                            seat_cost = academy_service.price_per_unit * bag.seat_service_item.how_many
                        elif effective_chosen_period == "QUARTER":
                            seat_cost = academy_service.price_per_unit * bag.seat_service_item.how_many * 3
                        elif effective_chosen_period == "HALF":
                            seat_cost = academy_service.price_per_unit * bag.seat_service_item.how_many * 6
                        elif effective_chosen_period == "YEAR":
                            seat_cost = academy_service.price_per_unit * bag.seat_service_item.how_many * 12
                        else:
                            seat_cost = 0
                        base_price += seat_cost

                # Apply coupons to get the final discounted price
                plan_coupons = get_coupons_for_plan(plan, coupons)
                final_price = get_discounted_price(base_price, plan_coupons)

                if final_price > 0:
                    breakdown["plans"][plan.slug] = {
                        "amount": round(final_price, 2),
                        "currency": currency_code,
                    }

    for plan_addon in bag.plan_addons.all():
        option = plan_addon.financing_options.filter(how_many_months=1).first()
        if not option:
            continue

        base_price = option.monthly_price or 0

        if base_price > 0:
            if bag.country_code:
                adjusted_price, _, c = apply_pricing_ratio(base_price, bag.country_code, option, lang=lang)
                if c:
                    currency_code = c.code.upper()
                base_price = adjusted_price

            # Apply coupons
            addon_coupons = get_coupons_for_plan(plan_addon, coupons)
            final_price = get_discounted_price(base_price, addon_coupons)

            if final_price > 0:
                breakdown["plans"][plan_addon.slug] = {
                    "amount": round(final_price, 2),
                    "currency": currency_code,
                }

    # Track which services are already included as plan add-ons to avoid duplication
    plans = bag.plans.all()
    add_ons: dict[int, AcademyService] = {}
    services_in_plan_addons: set[int] = set()
    
    for plan in plans:
        for add_on in plan.add_ons.filter(currency=currency):
            if add_on.service.id not in add_ons:
                add_ons[add_on.service.id] = add_on
                services_in_plan_addons.add(add_on.service.id)

    for service_item in bag.service_items.all():
        if service_item.service.id in services_in_plan_addons:
            continue

        service_slug = service_item.service.slug

        academy_service = AcademyService.objects.filter(
            service=service_item.service, academy=bag.academy, currency=currency
        ).first()

        if not academy_service:
            continue

        amount, c, _ = academy_service.get_discounted_price(service_item.how_many, bag.country_code, lang)
        if c:
            currency_code = c.code.upper()

        if amount > 0:
            breakdown["service-items"][service_slug] = {
                "amount": round(amount, 2),
                "currency": currency_code,
                "how-many": service_item.how_many,
                "unit-type": service_item.unit_type,
            }

    return breakdown


def build_plan_addons_financings(bag: Bag, invoice: Invoice, lang: str, conversion_info: str | None = "") -> None:
    """
    Create a PlanFinancing (one payment) for each plan addon in the bag.

    This is used when plan addons are sold either standalone or together with a main plan.
    """

    addons = bag.plan_addons.all()
    if not addons.exists():
        return

    utc_now = timezone.now()
    coupons = list(bag.coupons.all())

    for plan in addons:
        option = plan.financing_options.filter(how_many_months=1).first()
        if not option:
            raise ValidationException(
                translation(
                    lang,
                    en=f"Plan addon {plan.slug} does not have a one-payment financing option configured",
                    es=f"El plan addon {plan.slug} no tiene configurada una opción de financiamiento de un solo pago",
                    slug="plan-addon-without-one-payment-option",
                ),
                code=400,
            )

        base_price = option.monthly_price or 0

        if bag.country_code:
            base_price, _, _ = apply_pricing_ratio(base_price, bag.country_code, option, lang=lang)

        addon_coupons = get_coupons_for_plan(plan, coupons)
        price = get_discounted_price(base_price, addon_coupons)

        if plan.time_of_life and plan.time_of_life_unit:
            delta = calculate_relative_delta(plan.time_of_life, plan.time_of_life_unit)
            plan_expires_at = invoice.paid_at + delta
        else:
            plan_expires_at = invoice.paid_at

        financing = PlanFinancing.objects.create(
            user=bag.user,
            how_many_installments=1,
            installments_paid=1,
            next_payment_at=utc_now + relativedelta(months=1),
            academy=bag.academy,
            selected_cohort_set=plan.cohort_set,
            selected_event_type_set=plan.event_type_set,
            selected_mentorship_service_set=plan.mentorship_service_set,
            valid_until=invoice.paid_at,
            plan_expires_at=plan_expires_at,
            monthly_price=price,
            status=PlanFinancing.Status.ACTIVE,
            currency=invoice.currency or bag.currency or bag.academy.main_currency,
        )

        financing.plans.set([plan])

        bag_coupons = bag.coupons.all()
        if bag_coupons.exists():
            financing.coupons.set(bag_coupons)
            # Increment usage counters for coupons
            now = timezone.now()
            Coupon.objects.filter(id__in=[c.id for c in bag_coupons]).update(
                times_used=F("times_used") + 1, last_used_at=now
            )

        financing.invoices.add(invoice)
        
        if financing.how_many_installments == 1 and invoice.status == Invoice.Status.FULFILLED:
            financing.status = PlanFinancing.Status.FULLY_PAID
        
        financing.save()

        tasks.build_service_stock_scheduler_from_plan_financing.delay(plan_financing_id=financing.id)


def get_plan_addons_amount(bag: Bag, lang: str) -> float:
    """
    Calculate the total one-shot amount for all plan addons in a bag.

    Rules:
      - Each addon plan must have a FinancingOption with how_many_months=1.
      - Pricing ratio is applied using bag.country_code and the FinancingOption.
      - All addons must share the same currency as the academy/bag.
      - The result is stored in bag.plan_addons_amount.
    """

    addons = bag.plan_addons.all()
    if not addons.exists():
        if bag.plan_addons_amount:
            bag.plan_addons_amount = 0
            bag.save(update_fields=["plan_addons_amount"])
        return 0.0

    main_currency = bag.currency or bag.academy.main_currency
    if not main_currency:
        raise ValidationException(
            translation(
                lang,
                en="Academy does not have a main currency configured",
                es="La academia no tiene una moneda principal configurada",
                slug="academy-without-main-currency",
            ),
            code=500,
        )

    currencies: dict[str, Currency] = {main_currency.code.upper(): main_currency}
    total = 0.0
    pricing_explanation: list[dict[str, Any]] = []

    for plan in addons:
        option = plan.financing_options.filter(how_many_months=1).first()
        if not option:
            raise ValidationException(
                translation(
                    lang,
                    en=f"Plan addon {plan.slug} does not have a one-payment financing option configured",
                    es=f"El plan addon {plan.slug} no tiene configurada una opción de financiamiento de un solo pago",
                    slug="plan-addon-without-one-payment-option",
                ),
                code=400,
            )

        base_price = option.monthly_price or 0

        if bag.country_code:
            adjusted_price, ratio, c = apply_pricing_ratio(base_price, bag.country_code, option, lang=lang)

            if c:
                currencies[c.code.upper()] = c

            if adjusted_price != base_price and base_price > 0 and ratio:
                pricing_explanation.append({"plan": plan.slug, "ratio": ratio})

            price = adjusted_price
        else:
            price = base_price

        total += float(price or 0)

    if len(currencies.keys()) > 1:
        raise ValidationException(
            translation(
                lang,
                en="Multiple currencies found, it means that the pricing ratio exceptions have a wrong configuration",
                es="Múltiples monedas encontradas, lo que significa que las excepciones de ratio de precios tienen una configuración incorrecta",
                slug="multiple-currencies-found",
            ),
            code=500,
        )

    # Update pricing ratio explanation for plan_addons without touching plans/service_items keys
    explanation = bag.pricing_ratio_explanation or {"plans": [], "service_items": [], "plan_addons": []}
    if "plan_addons" not in explanation:
        explanation["plan_addons"] = []

    if pricing_explanation:
        explanation["plan_addons"] = pricing_explanation
        bag.pricing_ratio_explanation = explanation

    bag.plan_addons_amount = total
    bag.save(update_fields=["pricing_ratio_explanation", "plan_addons_amount"])

    return total


def is_plan_financing_paid(plan_financing: PlanFinancing) -> bool:
    """
    Check if a plan financing is paid by examining its plans.

    Args:
        plan_financing: The plan financing to check

    Returns:
        bool: True if the plan financing is paid, False if it's free
    """
    for plan in plan_financing.plans.all():
        if plan.financing_options.exists():
            return True
    return False


def user_has_active_paid_plans(user: User) -> bool:
    """
    Check if a user has any active paid subscriptions or plan financings.

    Args:
        user: The user to check

    Returns:
        bool: True if the user has active paid plans, False otherwise
    """
    owned_subscriptions = Subscription.objects.filter(user=user, status=Subscription.Status.ACTIVE)
    seated_subscription_ids = SubscriptionSeat.objects.filter(user=user).values_list(
        "billing_team__subscription_id", flat=True
    )
    seat_subscriptions = Subscription.objects.filter(id__in=seated_subscription_ids, status=Subscription.Status.ACTIVE)

    for subscription in owned_subscriptions.union(seat_subscriptions):
        if is_subscription_paid(subscription):
            return True

    return False


def user_has_active_4geeks_plus_plans(user: User) -> bool:
    """
    Check if a user has any active paid subscriptions or plan financings for 4Geeks Plus.

    Args:
        user: The user to check

    Returns:
        bool: True if the user has active paid plans, False otherwise
    """
    # Check for active subscriptions with 4Geeks Plus
    for subscription in Subscription.objects.filter(user=user, status=Subscription.Status.ACTIVE):
        if subscription.plans.filter(slug="4geeks-plus-subscription").exists():
            return True
    # Check for active plan financings with 4Geeks Plus
    for plan_financing in PlanFinancing.objects.filter(user=user, status=PlanFinancing.Status.ACTIVE):
        if plan_financing.plans.filter(slug="4geeks-plus-planfinancing").exists():
            return True

    return False


# ------------------------------
# Team member consumables (per-member issuance from JSON)
# ------------------------------

type SeatLogAction = Literal["ADDED", "REMOVED", "REPLACED"]


class SeatLogEntry(TypedDict):
    email: str
    action: SeatLogAction
    created_at: str


def create_seat_log_entry(seat: SubscriptionSeat, action: SeatLogAction) -> SeatLogEntry:
    utc_now = timezone.now()
    entry = {
        "email": (seat.email or "").strip().lower(),
        "action": action,
        "created_at": utc_now.isoformat().replace("+00:00", "Z"),
    }
    return entry


# seats management


class SeatDict(TypedDict, total=False):
    email: str
    user: int | None
    first_name: str | None
    last_name: str | None
    role: str | None
    cohort: Cohort


class AddSeat(TypedDict):
    email: str
    user: int | None
    first_name: str
    last_name: str
    role: str | None
    cohort_id: int | None


class ReplaceSeat(TypedDict):
    from_email: str
    to_email: str
    to_user: int | None
    first_name: str
    last_name: str
    role: str | None


def notify_user_was_added_to_subscription_team(
    subscription: Subscription, subscription_seat: SubscriptionSeat, lang: str
):
    """
    Send a notification email to an existing user that was added to a subscription team.

    This function notifies users who already exist in the platform and were directly assigned
    to a subscription team seat. It sends a welcome notification informing them they've been
    added to the team with immediate access to consumables and services.

    Args:
        subscription: The Subscription the user is being added to
        subscription_seat: The SubscriptionSeat with an assigned user (must have user != None)
        lang: Language code for email localization (e.g., 'en', 'es')

    Returns:
        None. Returns early without sending email if subscription_seat.user is None.

    Note:
        This function is the opposite of invite_user_to_subscription_team:
        - This handles seats WITH users (existing platform users)
        - invite_user_to_subscription_team handles seats WITHOUT users (pending invitations)

    See Also:
        invite_user_to_subscription_team: For inviting non-existent users
    """
    if subscription_seat.user is None:
        return

    billing_team_name = subscription_seat.billing_team.name if subscription_seat.billing_team else "team"
    notify_actions.send_email_message(
        "welcome_academy",
        subscription_seat.email,
        {
            "email": subscription_seat.email,
            "FIRST_NAME": subscription_seat.user.first_name or "",
            "subject": translation(
                lang,
                en=f"You've been added to {billing_team_name} at {subscription.academy.name}",
                es=f"Has sido agregado a {billing_team_name} en {subscription.academy.name}",
            ),
            "LINK": get_app_url(),
        },
        academy=subscription.academy,
    )


def _get_student_role() -> Role | None:
    return Role.objects.filter(slug="student").first()


def invite_user_to_subscription_team(
    obj: SeatDict, subscription: Subscription, subscription_seat: SubscriptionSeat, lang: str
):
    """
    Create and send an invitation for a non-existent user to join a subscription team.

    This function handles the invitation flow for users who don't exist in the platform yet.
    It creates a UserInvite record and sends a welcome email with an invitation link. When the
    user accepts the invite, the related consumables (created with user=None) will be automatically
    assigned to them via the handle_seat_invite_accepted receiver.

    Args:
        obj: Dictionary containing user information (email, first_name, last_name)
        subscription: The Subscription the user is being invited to
        subscription_seat: The SubscriptionSeat reserved for this user (user=None until accepted)
        lang: Language code for email localization (e.g., 'en', 'es')

    Behavior:
        - Creates a UserInvite if one doesn't exist, or reuses existing pending invite
        - Sends welcome email only if invite is newly created or still pending
        - The subscription_seat remains with user=None until the invite is accepted
        - Upon acceptance, consumables are automatically assigned via signal receiver

    Related:
        - See handle_seat_invite_accepted in receivers.py for post-acceptance logic
        - See Issue #9973 for the complete invitation flow
    """
    student_role = _get_student_role()
    cohort = obj.get("cohort")

    invite, created = UserInvite.objects.get_or_create(
        email=obj.get("email", ""),
        academy=subscription.academy,
        subscription_seat=subscription_seat,
        role=student_role,
        defaults={
            "status": "PENDING",
            "author": subscription.user,
            "role": student_role,
            "token": str(uuid.uuid4()),
            "sent_at": timezone.now(),
            "first_name": obj.get("first_name", ""),
            "last_name": obj.get("last_name", ""),
            "cohort": cohort,
        },
    )
    if not created and cohort and invite.cohort_id is None:
        invite.cohort = cohort
        invite.save(update_fields=["cohort"])
    if created or invite.status == "PENDING":
        billing_team_name = subscription_seat.billing_team.name if subscription_seat.billing_team else "team"
        callback_url = get_app_url(academy=subscription.academy)
        invite_link = get_invite_url(invite.token, academy=subscription.academy, callback_url=callback_url)

        email_data = {
            "email": subscription_seat.email,
            "FIRST_NAME": obj.get("first_name", "") or "",
            "subject": translation(
                lang,
                en=f"You've been added to {billing_team_name} at {subscription.academy.name}",
                es=f"Has sido agregado a {billing_team_name} en {subscription.academy.name}",
            ),
            "LINK": invite_link,
        }
        
        # Add welcome video if available
        if invite.welcome_video:
            email_data["WELCOME_VIDEO"] = invite.welcome_video

        notify_actions.send_email_message(
            "welcome_academy",
            subscription_seat.email,
            email_data,
            academy=subscription.academy,
        )


def _validate_email(email: str, lang: str):
    email_status = validate_email_local(email, lang)
    if email_status["score"] <= 0.60:
        raise ValidationException(
            translation(
                lang,
                en="The email address seems to have poor quality. Are you able to provide a different email address?",
                es="El correo electrónico que haz especificado parece de mala calidad. ¿Podrías especificarnos otra dirección?",
                slug="poor-quality-email",
            ),
            data=email_status,
        )


def create_seat(
    email: str,
    user: User | None,
    billing_team: SubscriptionBillingTeam,
    lang: str,
    cohort: Cohort,
):
    _validate_email(email, lang)

    if SubscriptionSeat.objects.filter(billing_team=billing_team, email=email).exists():
        raise ValidationException(
            translation(
                lang,
                en="User already has a seat for this team",
                es="El usuario ya tiene un asiento para esta equipo",
                slug="duplicate-team-seat",
            ),
            code=400,
        )

    seat = SubscriptionSeat(
        billing_team=billing_team,
        user=user,
        email=email,
    )
    seat_log_entry = create_seat_log_entry(seat, "ADDED")
    seat.seat_log.append(seat_log_entry)
    seat.is_active = True
    seat.save()

    if not user:
        invite_user_to_subscription_team(
            {"email": email, "first_name": None, "last_name": None, "cohort": cohort},
            seat.billing_team.subscription,
            seat,
            lang,
        )

    else:
        notify_user_was_added_to_subscription_team(
            seat.billing_team.subscription,
            seat,
            lang,
        )
        for plan in seat.billing_team.subscription.plans.all():
            grant_student_capabilities(user, plan, selected_cohort=cohort.slug)

    # create consumables unless shared per team
    strategy = getattr(
        billing_team,
        "consumption_strategy",
        SubscriptionBillingTeam.ConsumptionStrategy.PER_SEAT,
    )

    # if strategy is not per team, create the individual consumables
    if strategy != SubscriptionBillingTeam.ConsumptionStrategy.PER_TEAM:
        tasks.build_service_stock_scheduler_from_subscription.delay(billing_team.subscription.id, seat_id=seat.id)

    return seat


def notify_user_was_added_to_plan_financing_team(team: PlanFinancingTeam, seat: PlanFinancingSeat, lang: str):
    if seat.user is None:
        return

    financing = team.financing
    notify_actions.send_email_message(
        "welcome_academy",
        seat.email,
        {
            "email": seat.email,
            "FIRST_NAME": seat.user.first_name or "",
            "subject": translation(
                lang,
                en=f"You've been added to {team.name} at {financing.academy.name}",
                es=f"Has sido agregado a {team.name} en {financing.academy.name}",
            ),
            "LINK": get_app_url(),
        },
        academy=financing.academy,
    )


def invite_user_to_plan_financing_team(
    obj: SeatDict, team: PlanFinancingTeam, plan_financing_seat: PlanFinancingSeat, lang: str
):
    financing = team.financing
    student_role = _get_student_role()
    cohort = obj.get("cohort")

    invite, created = UserInvite.objects.get_or_create(
        email=obj.get("email", ""),
        academy=financing.academy,
        plan_financing_seat=plan_financing_seat,
        role=student_role,
        defaults={
            "status": "PENDING",
            "author": financing.user,
            "role": student_role,
            "token": str(uuid.uuid4()),
            "sent_at": timezone.now(),
            "first_name": obj.get("first_name", ""),
            "last_name": obj.get("last_name", ""),
            "cohort": cohort,
        },
    )
    if not created and cohort and invite.cohort_id is None:
        invite.cohort = cohort
        invite.save(update_fields=["cohort"])

    if created or invite.status == "PENDING":
        callback_url = get_app_url(academy=financing.academy)
        invite_link = get_invite_url(invite.token, academy=financing.academy, callback_url=callback_url)

        email_data = {
            "email": plan_financing_seat.email,
            "FIRST_NAME": obj.get("first_name", "") or "",
            "subject": translation(
                lang,
                en=f"You've been invited to {team.name} at {financing.academy.name}",
                es=f"Has sido invitado a {team.name} en {financing.academy.name}",
            ),
            "LINK": invite_link,
        }
        
        # Add welcome video if available
        if invite.welcome_video:
            email_data["WELCOME_VIDEO"] = invite.welcome_video

        notify_actions.send_email_message(
            "welcome_academy",
            plan_financing_seat.email,
            email_data,
            academy=financing.academy,
        )


def _conversion_info_for_build_plan_financing_task(conversion_info: Any) -> str | None:
    if conversion_info is None:
        return None
    if isinstance(conversion_info, str):
        return conversion_info
    return json.dumps(conversion_info)


def format_note_made_by_user(note: str | None, user_id: int | None) -> str | None:
    """
    Normalize notes to: "Note made by user <user_id>: <note>".
    """
    normalized = str(note or "").strip()
    if not normalized:
        return None

    if normalized.startswith("Note made by user "):
        return normalized[:250]

    if user_id is None:
        return normalized[:250]

    return f"Note made by user {user_id}: {normalized}"[:250]


def get_plan_financing_option(
    plan: Plan,
    how_many_installments: int,
    financing_option_id: int | None = None,
    lang: str = "en",
) -> FinancingOption:
    """
    Resolve a plan's financing option for a given installment count.

    When multiple financing options share the same ``how_many_months``, callers must pass
    ``financing_option_id`` to avoid picking an arbitrary option via ``.first()``.
    """
    if financing_option_id is not None:
        option = plan.financing_options.filter(id=financing_option_id).first()
        if option is None:
            raise ValidationException(
                translation(
                    lang,
                    en=f"Financing option {financing_option_id} is not linked to plan {plan.slug}",
                    es=f"La opción de financiamiento {financing_option_id} no está vinculada al plan {plan.slug}",
                ),
                slug="financing-option-not-found",
                code=404,
            )
        if option.how_many_months != how_many_installments:
            raise ValidationException(
                translation(
                    lang,
                    en=(
                        f"Financing option {financing_option_id} has {option.how_many_months} installments, "
                        f"expected {how_many_installments}"
                    ),
                    es=(
                        f"La opción de financiamiento {financing_option_id} tiene {option.how_many_months} cuotas, "
                        f"se esperaban {how_many_installments}"
                    ),
                ),
                slug="financing-option-installment-mismatch",
                code=400,
            )
        return option

    options = plan.financing_options.filter(how_many_months=how_many_installments)
    count = options.count()
    if count == 0:
        raise ValidationException(
            translation(
                lang,
                en=f"Financing option not found for {how_many_installments} installments (plan {plan.slug})",
                es=f"No hay opción de financiamiento para {how_many_installments} cuotas (plan {plan.slug})",
            ),
            slug="financing-option-not-found",
            code=404,
        )
    if count > 1:
        raise ValidationException(
            translation(
                lang,
                en=(
                    f"Multiple financing options found for {how_many_installments} installments on plan {plan.slug}. "
                    "Pass financing_option_id."
                ),
                es=(
                    f"Hay varias opciones de financiamiento para {how_many_installments} cuotas en el plan {plan.slug}. "
                    "Envía financing_option_id."
                ),
            ),
            slug="ambiguous-financing-option",
            code=400,
        )
    return options.first()


def validate_student_invite_plan_access_config(
    *,
    plans: list[Plan],
    how_many_installments: int,
    initial_payment_amount: float | None,
    initial_payment_notes: str | None,
    unique_payment_negotiated_amount: float | None = None,
    grace_period_duration: int,
    grace_period_duration_unit: str,
    financing_option_id: int | None = None,
    lang: str,
    note_author_user_id: int | None = None,
) -> dict[str, Any]:
    """
    Validate optional plan-access fields for POST /v1/auth/academy/student (same financing rules as staff subscription).
    Returns a JSON-serializable dict to persist on UserInvite.student_plan_access.
    """
    if not plans:
        raise ValidationException(
            translation(lang, en="At least one plan is required", es="Se requiere al menos un plan"),
            slug="plans-required-for-plan-access",
            code=400,
        )

    if how_many_installments <= 0:
        raise ValidationException(
            translation(
                lang,
                en="how_many_installments must be a positive integer",
                es="how_many_installments debe ser un entero positivo",
            ),
            slug="invalid-how-many-installments",
            code=400,
        )

    allowed_grace_period_units = {DAY, WEEK, MONTH, YEAR}
    if grace_period_duration_unit not in allowed_grace_period_units:
        raise ValidationException(
            translation(
                lang,
                en="grace_period_duration_unit must be DAY, WEEK, MONTH or YEAR",
                es="grace_period_duration_unit debe ser DAY, WEEK, MONTH o YEAR",
            ),
            slug="invalid-grace-period-duration-unit",
            code=400,
        )

    if grace_period_duration < 0:
        raise ValidationException(
            translation(
                lang,
                en="grace_period_duration must be zero or a positive integer",
                es="grace_period_duration debe ser cero o un entero positivo",
            ),
            slug="invalid-grace-period-duration",
            code=400,
        )

    if initial_payment_amount is not None:
        try:
            initial_payment_amount = float(initial_payment_amount)
        except (TypeError, ValueError):
            raise ValidationException(
                translation(
                    lang,
                    en="initial_payment_amount must be a number",
                    es="initial_payment_amount debe ser un número",
                ),
                slug="invalid-initial-payment-amount",
                code=400,
            )
        if initial_payment_amount < 0:
            raise ValidationException(
                translation(
                    lang,
                    en="initial_payment_amount must be zero or greater",
                    es="initial_payment_amount debe ser cero o mayor",
                ),
                slug="invalid-initial-payment-amount",
                code=400,
            )

    if unique_payment_negotiated_amount is not None:
        try:
            unique_payment_negotiated_amount = float(unique_payment_negotiated_amount)
        except (TypeError, ValueError):
            raise ValidationException(
                translation(
                    lang,
                    en="unique_payment_negotiated_amount must be a number",
                    es="unique_payment_negotiated_amount debe ser un número",
                ),
                slug="invalid-unique-payment-negotiated-amount",
                code=400,
            )
        if unique_payment_negotiated_amount <= 0:
            raise ValidationException(
                translation(
                    lang,
                    en="unique_payment_negotiated_amount must be greater than zero",
                    es="unique_payment_negotiated_amount debe ser mayor que cero",
                ),
                slug="invalid-unique-payment-negotiated-amount",
                code=400,
            )

    if initial_payment_amount is not None and unique_payment_negotiated_amount is not None:
        raise ValidationException(
            translation(
                lang,
                en="unique_payment_negotiated_amount cannot be combined with initial_payment_amount",
                es="unique_payment_negotiated_amount no puede combinarse con initial_payment_amount",
            ),
            slug="unique-payment-negotiated-initial-exclusive",
            code=400,
        )

    if initial_payment_amount is not None and not str(initial_payment_notes or "").strip():
        raise ValidationException(
            translation(
                lang,
                en="initial_payment_notes is required when using initial_payment_amount",
                es="initial_payment_notes es obligatorio al usar initial_payment_amount",
            ),
            slug="initial-payment-notes-required",
            code=400,
        )

    if (
        unique_payment_negotiated_amount is not None
        and how_many_installments == 1
        and not str(initial_payment_notes or "").strip()
    ):
        raise ValidationException(
            translation(
                lang,
                en="initial_payment_notes is required when using unique_payment_negotiated_amount for one payment plans",
                es="initial_payment_notes es obligatorio al usar unique_payment_negotiated_amount en planes de un pago",
            ),
            slug="negotiated-amount-notes-required",
            code=400,
        )

    for p in plans:
        get_plan_financing_option(
            p,
            how_many_installments,
            financing_option_id=financing_option_id,
            lang=lang,
        )

    initial_payment_notes = format_note_made_by_user(initial_payment_notes, note_author_user_id)
    payload: dict[str, Any] = {
        "how_many_installments": how_many_installments,
        "initial_payment_amount": initial_payment_amount,
        "initial_payment_notes": initial_payment_notes,
        "unique_payment_negotiated_amount": unique_payment_negotiated_amount,
        "grace_period_duration": grace_period_duration,
        "grace_period_duration_unit": grace_period_duration_unit,
    }
    if financing_option_id is not None:
        payload["financing_option_id"] = financing_option_id
    return payload


def resolve_student_plan_access_from_invite(user_invite: UserInvite) -> dict[str, Any]:
    """Defaults match legacy invite behaviour (single installment, no grace, no initial split)."""
    raw: dict[str, Any] = {}
    spa = getattr(user_invite, "student_plan_access", None)
    if isinstance(spa, dict) and spa:
        raw = spa
    elif isinstance(user_invite.conversion_info, dict):
        # Compat: invitaciones creadas cuando el payload vivía bajo __bc_student_plan_access
        legacy = user_invite.conversion_info.get("__bc_student_plan_access")
        if isinstance(legacy, dict):
            raw = legacy
    unit = raw.get("grace_period_duration_unit") or MONTH
    if unit not in {DAY, WEEK, MONTH, YEAR}:
        unit = MONTH
    unique_raw = raw.get("unique_payment_negotiated_amount")
    if unique_raw is None:
        unique_raw = raw.get("negotiated_invoice_amount")
    financing_option_id = raw.get("financing_option_id")
    if financing_option_id is not None:
        try:
            financing_option_id = int(financing_option_id)
        except (TypeError, ValueError):
            financing_option_id = None

    resolved: dict[str, Any] = {
        "how_many_installments": int(raw.get("how_many_installments") or 1),
        "initial_payment_amount": raw.get("initial_payment_amount"),
        "initial_payment_notes": raw.get("initial_payment_notes"),
        "unique_payment_negotiated_amount": unique_raw,
        "grace_period_duration": int(raw.get("grace_period_duration") or 0),
        "grace_period_duration_unit": unit,
    }
    if financing_option_id is not None:
        resolved["financing_option_id"] = financing_option_id
    return resolved


def create_invited_plan_financing_for_user(
    user: User,
    plan: Plan,
    academy: Academy,
    cohort: Cohort | None = None,
    payment_method: PaymentMethod | None = None,
    author: User | None = None,
    lang: str = "en",
    *,
    joined_cohorts: list[Cohort] | None = None,
    how_many_installments: int = 1,
    initial_payment_amount: float | None = None,
    initial_payment_notes: str | None = None,
    unique_payment_negotiated_amount: float | None = None,
    grace_period_duration: int = 0,
    grace_period_duration_unit: str = MONTH,
    financing_option_id: int | None = None,
    conversion_info: Any = None,
) -> None:
    """
    Create PlanFinancing for an existing user (staff-assigned / bulk upload / invite acceptance).
    Mirrors staff subscription financing: optional installments, initial payment, grace period.
    ``cohort`` / ``joined_cohorts``: optional; when omitted, financing is created without ``joined_cohorts``.
    """
    if plan.status == Plan.Status.DRAFT:
        raise ValidationException(
            translation(
                lang,
                en="Cannot assign draft plans to students. Publish the plan first.",
                es="No se pueden asignar planes en borrador a estudiantes. Publica el plan primero.",
            ),
            slug="plan-draft-not-assignable",
            code=400,
        )

    seen_ids: set[int] = set()
    all_cohorts: list[Cohort] = []
    for c in ([cohort] if cohort is not None else []) + list(joined_cohorts or []):
        if c.id not in seen_ids:
            seen_ids.add(c.id)
            all_cohorts.append(c)

    for c in all_cohorts:
        if not plan.cohort_set or not plan.cohort_set.cohorts.filter(id=c.id).exists():
            raise ValidationException(
                translation(
                    lang,
                    en="Plan does not include this cohort. The plan's cohort_set must contain the cohort.",
                    es="El plan no incluye este cohort. El cohort_set del plan debe contener el cohort.",
                ),
                slug="plan-cohort-mismatch",
                code=400,
            )

    if not academy.main_currency_id:
        raise ValidationException(
            translation(
                lang,
                en="Academy must have main_currency set to assign plans",
                es="La academia debe tener main_currency configurado para asignar planes",
            ),
            slug="academy-main-currency-required",
            code=400,
        )

    for c in all_cohorts:
        if not (
            c.available_as_saas is True
            or (c.available_as_saas is None and academy.available_as_saas is True)
        ):
            raise ValidationException(
                translation(
                    lang,
                    en="Cohort or academy must have available_as_saas=true for plan assignment",
                    es="El cohort o la academia deben tener available_as_saas=true para asignar planes",
                ),
                slug="cohort-not-available-as-saas",
                code=400,
            )

    financing_option = get_plan_financing_option(
        plan,
        how_many_installments,
        financing_option_id=financing_option_id,
        lang=lang,
    )

    if initial_payment_amount is not None and unique_payment_negotiated_amount is not None:
        raise ValidationException(
            translation(
                lang,
                en="unique_payment_negotiated_amount cannot be combined with initial_payment_amount",
                es="unique_payment_negotiated_amount no puede combinarse con initial_payment_amount",
            ),
            slug="unique-payment-negotiated-initial-exclusive",
            code=400,
        )

    catalog_installment_amount = float(financing_option.monthly_price)

    uniq_negotiated: float | None = None
    if unique_payment_negotiated_amount is not None:
        uniq_negotiated = float(unique_payment_negotiated_amount)
        if uniq_negotiated <= 0:
            raise ValidationException(
                translation(
                    lang,
                    en="unique_payment_negotiated_amount must be greater than zero",
                    es="unique_payment_negotiated_amount debe ser mayor que cero",
                ),
                slug="invalid-unique-payment-negotiated-amount",
                code=400,
            )

    if (
        uniq_negotiated is not None
        and how_many_installments == 1
        and not str(initial_payment_notes or "").strip()
    ):
        raise ValidationException(
            translation(
                lang,
                en="initial_payment_notes is required when using unique_payment_negotiated_amount for one payment plans",
                es="initial_payment_notes es obligatorio al usar unique_payment_negotiated_amount en planes de un pago",
            ),
            slug="negotiated-amount-notes-required",
            code=400,
        )
    if initial_payment_amount is not None and not str(initial_payment_notes or "").strip():
        raise ValidationException(
            translation(
                lang,
                en="initial_payment_notes is required when using initial_payment_amount",
                es="initial_payment_notes es obligatorio al usar initial_payment_amount",
            ),
            slug="initial-payment-notes-required",
            code=400,
        )
    initial_payment_notes = format_note_made_by_user(initial_payment_notes, author.id if author else user.id)

    installment_amount = catalog_installment_amount
    if uniq_negotiated is not None:
        installment_amount = uniq_negotiated

    amount = float(initial_payment_amount) if initial_payment_amount is not None else installment_amount
    is_free = installment_amount == 0
    externally_managed = payment_method is not None

    if payment_method and not payment_method.is_crypto and not author:
        raise ValidationException(
            translation(
                lang,
                en="Author is required when payment method is set for staff-assigned plans.",
                es="El autor es requerido cuando se establece un método de pago para planes asignados por staff.",
            ),
            slug="invite-author-required-for-payment-method",
            code=400,
        )

    utc_now = timezone.now()

    bag = Bag()
    bag.chosen_period = "NO_SET"
    bag.status = "PAID"
    bag.type = "INVITED"
    bag.how_many_installments = how_many_installments
    bag.academy = academy
    bag.user = user
    bag.is_recurrent = False
    bag.was_delivered = False
    bag.token = None
    bag.currency = academy.main_currency
    bag.expires_at = None
    bag.save()
    bag.plans.add(plan)

    proof = None
    if payment_method and not payment_method.is_crypto and author:
        proof = ProofOfPayment(
            created_by=author,
            status=ProofOfPayment.Status.DONE,
            provided_payment_details=f"Staff-assigned plan via {payment_method.title}",
            reference=f"STAFF-ASSIGNED-{user.id}-{plan.id}",
        )
        proof.save()

    invoice_kw: dict[str, Any] = {
        "amount": amount,
        "paid_at": utc_now,
        "user": user,
        "bag": bag,
        "academy": academy,
        "status": "FULFILLED",
        "currency": academy.main_currency,
        "payment_method": payment_method,
        "externally_managed": externally_managed,
        "proof": proof,
        "invoice_notes": initial_payment_notes,
    }
    if uniq_negotiated is not None:
        invoice_kw["amount_breakdown"] = {
            "plans": {
                plan.slug: {
                    "amount": amount,
                    "currency": academy.main_currency.code if academy.main_currency else None,
                    "type": "UNIQUE_PAYMENT_NEGOTIATED",
                    "catalog_installment_amount": catalog_installment_amount,
                }
            },
            "service-items": {},
        }

    invoice = Invoice(**invoice_kw)
    invoice.save()

    conv_str = _conversion_info_for_build_plan_financing_task(conversion_info)

    use_extended = (
        initial_payment_amount is not None
        or uniq_negotiated is not None
        or (initial_payment_notes is not None and str(initial_payment_notes).strip() != "")
        or grace_period_duration > 0
        or how_many_installments != 1
    )

    cohort_slugs = [c.slug for c in all_cohorts]

    if use_extended:
        build_kwargs: dict[str, Any] = {
            "conversion_info": conv_str,
            "cohorts": cohort_slugs,
            "grace_period_duration": grace_period_duration,
            "grace_period_duration_unit": grace_period_duration_unit,
        }
        if initial_payment_notes is not None:
            build_kwargs["initial_payment_notes"] = initial_payment_notes
        if initial_payment_amount is not None:
            build_kwargs["principal_amount"] = catalog_installment_amount
            build_kwargs["initial_payment_amount"] = amount
        else:
            build_kwargs["principal_amount"] = installment_amount
        tasks.build_plan_financing.delay(bag.id, invoice.id, is_free=is_free, **build_kwargs)
    elif cohort_slugs:
        tasks.build_plan_financing.delay(bag.id, invoice.id, is_free=is_free, cohorts=cohort_slugs)
    else:
        tasks.build_plan_financing.delay(bag.id, invoice.id, is_free=is_free)


def create_plan_financing_seat(
    email: str,
    user: User | None,
    team: PlanFinancingTeam,
    lang: str,
    cohort: Cohort,
    first_name: str = "",
    last_name: str = "",
):
    _validate_email(email, lang)

    if PlanFinancingSeat.objects.filter(team=team, email=email).exists():
        raise ValidationException(
            translation(
                lang,
                en="User already has a seat for this financing",
                es="El usuario ya tiene un asiento para este financiamiento",
                slug="duplicate-financing-seat",
            ),
            code=400,
        )

    seat = PlanFinancingSeat(
        team=team,
        user=user,
        email=email,
    )
    seat_log_entry = create_seat_log_entry(seat, "ADDED")
    seat.seat_log.append(seat_log_entry)
    seat.is_active = True
    seat.save()

    if user:
        for plan in team.financing.plans.all():
            grant_student_capabilities(user, plan, selected_cohort=cohort.slug)
        notify_user_was_added_to_plan_financing_team(team, seat, lang)
    else:
        invite_user_to_plan_financing_team(
            {"email": email, "first_name": first_name or "", "last_name": last_name or "", "cohort": cohort},
            team,
            seat,
            lang,
        )

    if team.consumption_strategy == PlanFinancingTeam.ConsumptionStrategy.PER_TEAM:
        tasks.build_service_stock_scheduler_from_plan_financing.delay(team.financing.id)
    else:
        tasks.build_service_stock_scheduler_from_plan_financing.delay(team.financing.id, seat_id=seat.id)

    return seat


def replace_seat(
    from_email: str,
    to_email: str,
    to_user: User | None,
    subscription_seat: SubscriptionSeat,
    lang: str,
):
    _validate_email(to_email, lang)

    seat = SubscriptionSeat.objects.filter(billing_team=subscription_seat.billing_team, email=from_email).first()
    if not seat:
        raise ValidationException(
            translation(
                lang,
                en=f"There is no seat with this email {from_email}",
                es=f"No hay un asiento con este email {from_email}",
                slug="no-seat-with-this-email",
            ),
            code=400,
        )

    if SubscriptionSeat.objects.filter(billing_team=subscription_seat.billing_team, email=to_email).exists():
        raise ValidationException(
            translation(
                lang,
                en=f"There is already a seat with this email {to_email}",
                es=f"Ya hay un asiento con este email {to_email}",
                slug="seat-with-this-email-already-exists",
            ),
            code=400,
        )

    seat.email = to_user.email if to_user else to_email
    seat.user = to_user
    seat.is_active = True
    seat_log_entry = create_seat_log_entry(seat, "REPLACED")
    seat.seat_log.append(seat_log_entry)
    seat.save(update_fields=["seat_log", "is_active", "email", "user"])

    if not to_user:
        invite_user_to_subscription_team(
            {"email": to_email, "first_name": None, "last_name": None},
            subscription_seat.billing_team.subscription,
            subscription_seat,
            lang,
        )

    else:
        notify_user_was_added_to_subscription_team(
            seat.billing_team.subscription,
            seat,
            lang,
        )

        for plan in subscription_seat.billing_team.subscription.plans.all():
            grant_student_capabilities(to_user, plan)

    # create consumables unless shared per team
    strategy = getattr(
        subscription_seat.billing_team,
        "consumption_strategy",
        SubscriptionBillingTeam.ConsumptionStrategy.PER_SEAT,
    )

    # if strategy is not per team, reassign consumables from the seat to the new user (or None if pending invite)
    if strategy != SubscriptionBillingTeam.ConsumptionStrategy.PER_TEAM:
        # Set user to the new user if exists, otherwise None (waiting for invitation acceptance)
        Consumable.objects.filter(subscription_seat=seat).update(user=to_user)

    return seat


def replace_plan_financing_seat(
    from_email: str,
    to_email: str,
    to_user: User | None,
    financing_seat: PlanFinancingSeat,
    lang: str,
    first_name: str = "",
    last_name: str = "",
):
    _validate_email(to_email, lang)

    seat = PlanFinancingSeat.objects.filter(team=financing_seat.team, email=from_email).first()
    if not seat:
        raise ValidationException(
            translation(
                lang,
                en=f"There is no seat with this email {from_email}",
                es=f"No hay un asiento con este email {from_email}",
                slug="no-seat-with-this-email",
            ),
            code=404,
        )

    if PlanFinancingSeat.objects.filter(team=financing_seat.team, email=to_email).exists():
        raise ValidationException(
            translation(
                lang,
                en=f"There is already a seat with this email {to_email}",
                es=f"Ya hay un asiento con este email {to_email}",
                slug="seat-with-this-email-already-exists",
            ),
            code=400,
        )

    seat.email = to_user.email if to_user else to_email
    seat.user = to_user
    seat.is_active = True
    seat_log_entry = create_seat_log_entry(seat, "REPLACED")
    seat.seat_log.append(seat_log_entry)
    seat.save(update_fields=["seat_log", "is_active", "email", "user"])

    if to_user:
        for plan in seat.team.financing.plans.all():
            grant_student_capabilities(to_user, plan)
        notify_user_was_added_to_plan_financing_team(seat.team, seat, lang)
    else:
        invite_user_to_plan_financing_team(
            {"email": to_email, "first_name": first_name or "", "last_name": last_name or ""},
            seat.team,
            seat,
            lang,
        )

    if seat.team.consumption_strategy != PlanFinancingTeam.ConsumptionStrategy.PER_TEAM:
        Consumable.objects.filter(plan_financing_seat=seat).update(user=to_user)

    tasks.build_service_stock_scheduler_from_plan_financing.delay(seat.team.financing.id, seat_id=seat.id)

    return seat


def deactivate_plan_financing_seat(financing_seat: PlanFinancingSeat):
    financing_seat.user = None
    financing_seat.is_active = False
    financing_seat.seat_log.append(create_seat_log_entry(financing_seat, "REMOVED"))
    financing_seat.save(update_fields=["is_active", "user", "seat_log"])

    Consumable.objects.filter(plan_financing_seat_id=financing_seat.id).update(user=None)
    tasks.build_service_stock_scheduler_from_plan_financing.delay(financing_seat.team.financing.id)


def normalize_email(email: str):
    return email.strip().lower()


def _normalize_role(role: Any) -> str | None:
    if role is None:
        return None
    if isinstance(role, str):
        return role.strip().lower() or None
    return str(role).strip().lower()


def _normalize_user_value(user_value: Any) -> int | None:
    if user_value is None:
        return None
    if isinstance(user_value, int):
        return user_value
    if isinstance(user_value, str) and user_value.isdigit():
        return int(user_value)
    return None


def normalize_add_seats(add_seats: list[dict[str, Any]]) -> list[AddSeat]:
    l: list[AddSeat] = []
    for seat in add_seats:
        cohort_id = seat.get("cohort_id") or seat.get("cohort")
        if isinstance(cohort_id, dict):
            cohort_id = cohort_id.get("id")
        serialized = {
            "email": normalize_email(seat["email"]),
            "user": _normalize_user_value(seat.get("user")),
            "first_name": seat.get("first_name", ""),
            "last_name": seat.get("last_name", ""),
            "role": _normalize_role(seat.get("role")),
            "cohort_id": int(cohort_id) if cohort_id is not None else None,
        }
        l.append(serialized)
    return l


def normalize_replace_seat(replace_seats: list[dict[str, Any]]) -> ReplaceSeat:
    l: list[AddSeat] = []
    for seat in replace_seats:
        serialized = {
            "from_email": normalize_email(seat["from_email"]),
            "to_email": normalize_email(seat["to_email"]),
            "to_user": _normalize_user_value(seat.get("to_user")),
            "first_name": seat.get("first_name", ""),
            "last_name": seat.get("last_name", ""),
            "role": _normalize_role(seat.get("role")),
        }
        l.append(serialized)
    return l


def validate_seats_limit(
    team: SubscriptionBillingTeam | PlanFinancingTeam,
    add_seats: list[AddSeat],
    replace_seats: list[ReplaceSeat],
    lang: str,
):
    seats = {}
    if isinstance(team, SubscriptionBillingTeam):
        queryset = SubscriptionSeat.objects.filter(billing_team=team)
    else:
        queryset = PlanFinancingSeat.objects.filter(team=team)

    for seat in queryset:
        seats[seat.email] = 1

    for seat in add_seats:
        # seat is a dict-like (TypedDict)
        seats[seat["email"]] = 1

    for seat in replace_seats:
        # carry forward the existing multiplier when replacing an email
        prev = seats.pop(seat["from_email"], None)
        if prev is not None:
            seats[seat["to_email"]] = prev

    value = 0
    for seat in seats.values():
        value += seat

    if team.additional_seats and value > team.seats_limit:
        raise ValidationException(
            translation(
                lang,
                en=f"Seats limit exceeded: {value} > {team.seats_limit}",
                es=f"Límite de asientos excedido: {value} > {team.seats_limit}",
                slug="seats-limit-exceeded",
            ),
            code=400,
        )


def validate_seat_cohort_for_owner(
    owner: User,
    plan: Plan | None,
    resource: Subscription | PlanFinancing,
    cohort_id: int | None,
    lang: str,
) -> Cohort:
    if not cohort_id:
        raise ValidationException(
            translation(
                lang,
                en="You must select a cohort for the invited member",
                es="Debes seleccionar una cohorte para el miembro invitado",
                slug="seat-cohort-required",
            ),
            code=400,
        )

    if plan is None:
        raise ValidationException(
            translation(
                lang,
                en="Plan not found for this subscription",
                es="No se encontró el plan para esta suscripción",
                slug="plan-not-found",
            ),
            code=404,
        )

    bad_stages = ["DELETED", "ENDED"]
    cohort = Cohort.objects.filter(id=cohort_id).exclude(stage__in=bad_stages).first()
    if not cohort:
        raise ValidationException(
            translation(
                lang,
                en="Cohort not found",
                es="Cohorte no encontrada",
                slug="cohort-not-found",
            ),
            code=404,
        )

    if not CohortUser.objects.filter(user=owner, cohort=cohort).exists():
        raise ValidationException(
            translation(
                lang,
                en="You can only invite members to cohorts you belong to",
                es="Solo puedes invitar miembros a cohortes en las que estás inscrito",
                slug="owner-not-in-cohort",
            ),
            code=400,
        )

    if plan.cohort_set_id:
        in_scope = plan.cohort_set.cohorts.filter(id=cohort.id).exists()
    elif resource.selected_cohort_set_id:
        in_scope = resource.selected_cohort_set.cohorts.filter(id=cohort.id).exists()
    else:
        in_scope = False

    if not in_scope:
        raise ValidationException(
            translation(
                lang,
                en="This cohort is not included in your plan",
                es="Esta cohorte no está incluida en tu plan",
                slug="cohort-not-in-plan",
            ),
            code=400,
        )

    return cohort


def grant_student_capabilities(user: User, plan: Plan, selected_cohort: Optional[str] = None):
    if plan.owner:
        admissions_tasks.build_profile_academy.delay(plan.owner.id, user.id)

    if not plan.cohort_set or not selected_cohort:
        return

    cohort = plan.cohort_set.cohorts.filter(slug=selected_cohort).first()
    if not cohort:
        return

    admissions_tasks.build_cohort_user.delay(cohort.id, user.id)

    if plan.owner != cohort.academy:
        admissions_tasks.build_profile_academy.delay(cohort.academy.id, user.id)


def get_user_from_consumable_to_be_charged(
    instance: Consumable,
) -> User | None:
    """
    Resolve the user that should be considered the consumer for charging/notifications.

    Rules:
    - For `PlanFinancing` (always individual) or when the service is not team‑allowed,
      the user is the resource owner (`resource.user`).
    - For team‑allowed services with PER_SEAT strategy, it is the seat user if present,
      otherwise it falls back to the resource owner.

    Parameters:
    - instance: The `Consumable` linked to either a `Subscription` or `PlanFinancing`.

    Returns:
    - A `User` instance or `None` when team‑shared without a specific user.
    """
    resource: Subscription | PlanFinancing | None = instance.subscription or instance.plan_financing
    is_team_allowed = instance.service_item.is_team_allowed

    seat = instance.subscription_seat or instance.plan_financing_seat

    team: SubscriptionBillingTeam | PlanFinancingTeam | None = instance.subscription_billing_team
    if not team and seat:
        team = getattr(seat, "billing_team", None)
    if not team:
        team = getattr(instance, "plan_financing_team", None)

    strategy = getattr(team, "consumption_strategy", None)

    if is_team_allowed is False:
        return resource.user

    if isinstance(resource, PlanFinancing) and team is None:
        return resource.user

    if strategy in (
        SubscriptionBillingTeam.ConsumptionStrategy.PER_TEAM
        if isinstance(team, SubscriptionBillingTeam)
        else PlanFinancingTeam.ConsumptionStrategy.PER_TEAM
        if isinstance(team, PlanFinancingTeam)
        else None
    ):
        return None

    if strategy in (
        SubscriptionBillingTeam.ConsumptionStrategy.PER_SEAT
        if isinstance(team, SubscriptionBillingTeam)
        else PlanFinancingTeam.ConsumptionStrategy.PER_SEAT
        if isinstance(team, PlanFinancingTeam)
        else None
    ):
        return seat.user if (seat and seat.user) else resource.user

    return resource.user


def validate_auto_recharge_service_units(
    instance: Consumable,
) -> tuple[float, int, str | None]:  # price, amount, error
    """
    Decide whether an auto‑recharge should happen and, if so, how many units to buy.

    The decision takes into account:
    - Auto‑recharge enablement on the owning resource (`Subscription` or `PlanFinancing`).
    - Whether a seat is inactive (no recharge for inactive seats).
    - Presence of a main currency in the academy (required to price the units).
    - The effective user to consider for spending (derived from
      `get_user_from_consumable_to_be_charged`).
    - Current period spend for the service/user/team and configured thresholds/limits
      (`recharge_threshold_amount`, `max_period_spend`).
    - Academy price per unit for the service.
    - Remaining balance heuristics (e.g., more than 20% left).

    Parameters:
    - instance: The `Consumable` being consumed.

    Returns:
    - (price_per_unit, units_to_buy, None) when allowed.
    - (0.0, 0, "<slug>") when not allowed, where the slug explains the reason
      (e.g., "main-currency-not-found", "auto-recharge-threshold-reached",
      "max-period-spend-reached", "price-per-unit-not-found").
    """
    resource: Subscription | PlanFinancing | None = instance.subscription or instance.plan_financing
    if (
        resource is None
        or resource.auto_recharge_enabled is False
        or (instance.subscription_seat and instance.subscription_seat.is_active is False)
        or (instance.plan_financing_seat and instance.plan_financing_seat.is_active is False)
    ):
        return 0.0, 0, None

    if resource.academy.main_currency is None:
        return 0.0, 0, "main-currency-not-found"

    user = get_user_from_consumable_to_be_charged(instance)
    service = instance.service_item.service

    # Normalize spends to Decimal
    _user_spend = resource.get_current_period_spend(service, user)
    user_spend: Decimal = Decimal(str(_user_spend)) if _user_spend is not None else Decimal("0")

    team_spend: Decimal = user_spend
    if user:
        _team_spend = resource.get_current_period_spend(service)
        team_spend = Decimal(str(_team_spend)) if _team_spend is not None else Decimal("0")

    # Thresholds may come as DecimalField (DB) or float in stubs; normalize to Decimal
    threshold_dec = (
        Decimal(str(resource.recharge_threshold_amount))
        if resource.recharge_threshold_amount is not None
        else Decimal("0")
    )

    if team_spend >= threshold_dec:
        return 0.0, 0, "auto-recharge-threshold-reached"

    max_spend_dec = Decimal(str(resource.max_period_spend)) if getattr(resource, "max_period_spend", None) else None

    recharge_amount: Decimal = Decimal(str(resource.recharge_amount))

    if max_spend_dec and (team_spend >= max_spend_dec or team_spend + recharge_amount >= max_spend_dec):
        return 0.0, 0, "max-period-spend-reached"

    if max_spend_dec and team_spend + recharge_amount > max_spend_dec:
        recharge_amount = max_spend_dec - team_spend

    price_qs = AcademyService.objects.filter(service=service, academy=resource.academy)
    if (price := price_qs.first()) is None:
        return 0.0, 0, "academy-service-not-found"

    if price.price_per_unit is None:
        return 0.0, 0, "price-per-unit-not-found"

    price_per_unit_dec = Decimal(str(price.price_per_unit))
    if price_per_unit_dec <= 0:
        return 0.0, 0, "price-per-unit-not-found"

    if price_per_unit_dec > recharge_amount:
        return 0.0, 0, "price-per-unit-exceeded"

    consumables = Consumable.list(user=user, service=instance.service_item.service)
    total = 0
    available = 0
    for consumable in consumables:
        if consumable.how_many == -1:
            return 0.0, 0, None

        available += consumable.how_many
        total += consumable.service_item.how_many

    # Use Decimal for ratio comparison to avoid float mixing
    if len(consumables) > 0 and available > 1 and (Decimal(total) / Decimal(available) > Decimal("0.2")):
        return 0.0, 0, "more-than-20-percent-left"

    if Decimal(available) * price_per_unit_dec > threshold_dec:
        return 0.0, 0, None

    # Compute units using Decimal and return price as float for compatibility
    units = int((Decimal(str(recharge_amount)) / price_per_unit_dec).to_integral_value(rounding=ROUND_FLOOR))
    return float(price.price_per_unit), units, None


def process_auto_recharge(
    consumable: Consumable,
):
    """
    Execute the auto‑recharge workflow for the resource that owns a consumable.

    This is an ACTION (not a Celery task). The Celery entry point that calls this is
    `breathecode.payments.tasks.process_auto_recharge`. This function:

    1) Resolves the owning resource from the `consumable` (either `Subscription` or `PlanFinancing`).
    2) Acquires a Redis lock to avoid concurrent recharges per resource.
    3) Validates the recharge using `validate_auto_recharge_service_units` which returns
       the unit price and number of units to buy or an error slug.
    4) Performs the payment (Stripe) by creating a temporary `Bag` and charging the
       subscription owner. The charged user in emails can be the seat holder depending on the
       service/team strategy.
    5) Sends notification emails to the resource owner and, when applicable, the charged user.

    Parameters:
    - consumable: The `Consumable` instance that triggered the recharge path.

    Returns:
    - None. Side‑effects include DB writes (Bag/Invoice), Stripe charge and notifications.

    Raises:
    - AbortTask: When the flow cannot proceed (e.g., configuration, payment or validation issues).

    Concurrency:
    - Guarded by a Redis lock named `process_auto_recharge:<ResourceClass>:<resource_id>`.
    """

    resource: Subscription | PlanFinancing | None = consumable.subscription or consumable.plan_financing
    if not resource:
        return

    currency: Currency | None = resource.academy.main_currency
    if not currency:
        return

    # Connect to Redis
    redis_client = get_redis_connection("default")
    team = (
        consumable.subscription_billing_team
        or getattr(consumable, "plan_financing_team", None)
        or (consumable.subscription_seat.billing_team if consumable.subscription_seat else None)
        or (consumable.plan_financing_seat.team if getattr(consumable, "plan_financing_seat", None) else None)
    )
    seat = consumable.subscription_seat or getattr(consumable, "plan_financing_seat", None)

    lock_key = f"process_auto_recharge:{resource.__class__.__name__}:{resource.id}"
    lock_timeout = 300  # 5 minutes max lock time

    # Try to acquire lock
    lock: redis.lock.Lock | None = redis_client.lock(lock_key, timeout=lock_timeout, blocking_timeout=5)
    # lock.release()

    if lock.acquire(blocking=False) is False:
        raise RetryTask(f"Auto-recharge already in progress for {resource.__class__.__name__} {resource.id}")

    try:
        logger.info(f"Processing auto-recharge for {resource.__class__.__name__} {resource.id}")

        price, amount, error = validate_auto_recharge_service_units(consumable)
        if error:
            logger.warning(f"Auto-recharge not allowed for consumable {consumable.id}: {error}")
            return

        if amount <= 0:
            logger.warning(f"Auto-recharge not allowed for consumable {consumable.id}: amount is zero or negative")
            return

        try:
            with transaction.atomic():
                # Create invoice via Stripe payment
                from .services.stripe import Stripe

                charged_user = get_user_from_consumable_to_be_charged(consumable)

                # Create a temporary bag for the auto-recharge
                bag = Bag.objects.create(
                    user=resource.user,  # it must be charged to the owner
                    academy=resource.academy,
                    currency=currency,
                    type="CHARGE",
                    status="PAID",
                    was_delivered=True,
                )

                # Process payment via Stripe
                # If this fails, the entire transaction will rollback
                s = Stripe(academy=resource.academy)
                context_desc = f"auto-recharge for {charged_user.email}"
                stripe_team = team if isinstance(team, SubscriptionBillingTeam) else None
                stripe_seat = consumable.subscription_seat

                s.pay(
                    resource.user,  # it must be charged to the owner
                    bag,
                    price * amount,
                    currency=currency.code,
                    description=f"Auto-recharge for {context_desc}",
                    subscription_billing_team=stripe_team,
                    subscription_seat=stripe_seat,
                )

                emails = [resource.user.email]
                if charged_user.email not in resource.user.email:
                    if charged_user:
                        emails.append(charged_user.email)

                if charged_user is None:
                    charged_user = resource.user

                user_settings = get_user_settings(charged_user)
                lang = user_settings.lang

                subject = translation(
                    lang,
                    en=f"Consumables Auto-Recharged for {charged_user.email}",
                    es=f"Consumibles Auto-Recargados para {charged_user.email}",
                )
                message = translation(
                    lang,
                    en=f"The consumables have been auto-recharged for {charged_user.email}",
                    es=f"Los consumibles han sido auto-recargados para {charged_user.email}",
                )

                for email in emails:
                    notify_actions.send_email_message(
                        "message",
                        email,
                        {
                            "SUBJECT": subject,
                            "MESSAGE": message,
                        },
                        academy=resource.academy,
                    )

                # Clone the existing ServiceItem with a different how_many
                original = consumable.service_item
                si, _ = ServiceItem.get_or_create_for_service(
                    service=original.service,
                    how_many=amount,
                    unit_type=original.unit_type,
                    is_renewable=original.is_renewable,
                    is_team_allowed=original.is_team_allowed,
                    renew_at=original.renew_at,
                    renew_at_unit=original.renew_at_unit,
                    sort_priority=original.sort_priority,
                )

                attrs = consumable.__dict__.copy()
                attrs.pop("id")
                attrs.pop("_state")
                attrs.pop("service_item")

                Consumable.objects.create(**attrs, service_item=si)

        except Exception as e:
            raise AbortTask(f"Consumable auto-recharge failed for {resource.__class__.__name__} {resource.id}: {e}")

    finally:
        # Always release the lock
        lock.release()


def calculate_single_coupon_stats(coupon: Coupon) -> dict:
    """
    Calculate detailed statistics for a single coupon.
    
    Args:
        coupon: Coupon instance to calculate stats for
    
    Returns:
        dict: Statistics dictionary with revenue, users, plans, referral, time_periods, payment_methods
    """
    from datetime import timedelta
    from django.db.models import Count, Min, Max, Sum, Avg
    
    now = timezone.now()
    stats = {
        "times_used": coupon.times_used,
        "last_used_at": coupon.last_used_at.isoformat() if coupon.last_used_at else None,
    }
    
    # Get all invoices that used this coupon (via subscriptions and plan financings)
    # The relationship is: Subscription/PlanFinancing -> invoices (ManyToMany) -> bag -> coupons
    # So we query invoices where the subscription/planfinancing has this coupon
    # and the invoice's bag also has this coupon (to ensure it was used in that transaction)
    sub_invoices = Invoice.objects.filter(
        subscription__coupons=coupon,
        bag__coupons=coupon,
        status=Invoice.Status.FULFILLED,
    ).select_related("currency", "payment_method", "bag__user").distinct()
    
    pf_invoices = Invoice.objects.filter(
        planfinancing__coupons=coupon,
        bag__coupons=coupon,
        status=Invoice.Status.FULFILLED,
    ).select_related("currency", "payment_method", "bag__user").distinct()
    
    # Combine both querysets
    all_invoices = list(sub_invoices) + list(pf_invoices)
    
    if not all_invoices:
        # Return minimal stats if no usage
        stats.update({
            "first_used_at": None,
            "revenue": {
                "total_revenue_generated": 0.0,
                "total_discount_given": 0.0,
                "average_order_value": 0.0,
                "currency": None,
            },
            "users": {
                "unique_users": 0,
                "repeat_users": 0,
                "new_users": 0,
            },
            "plans": {},
            "referral": None,
            "time_periods": {
                "last_7_days": {"times_used": 0, "revenue_generated": 0.0},
                "last_30_days": {"times_used": 0, "revenue_generated": 0.0},
                "last_90_days": {"times_used": 0, "revenue_generated": 0.0},
            },
            "payment_methods": {},
        })
        return stats
    
    # Calculate first_used_at (earliest invoice paid_at)
    first_used_at = min(inv.paid_at for inv in all_invoices)
    stats["first_used_at"] = first_used_at.isoformat()
    
    # Revenue calculations
    total_revenue = sum(inv.amount for inv in all_invoices)
    # Calculate discount given (this is approximate - would need original price)
    # For now, we'll calculate based on coupon discount type and value
    total_discount = 0.0
    if coupon.discount_type == Coupon.Discount.PERCENT_OFF:
        # Approximate: assume average discount
        total_discount = total_revenue * coupon.discount_value / (1 - coupon.discount_value)
    elif coupon.discount_type == Coupon.Discount.FIXED_PRICE:
        total_discount = coupon.discount_value * len(all_invoices)
    
    avg_order_value = total_revenue / len(all_invoices) if all_invoices else 0.0
    primary_currency = all_invoices[0].currency.code if all_invoices else None
    
    stats["revenue"] = {
        "total_revenue_generated": round(total_revenue, 2),
        "total_discount_given": round(total_discount, 2),
        "average_order_value": round(avg_order_value, 2),
        "currency": primary_currency,
    }
    
    # User statistics
    user_ids = [inv.bag.user_id for inv in all_invoices if inv.bag and inv.bag.user_id]
    unique_users = len(set(user_ids))
    user_counts = {}
    for user_id in user_ids:
        user_counts[user_id] = user_counts.get(user_id, 0) + 1
    repeat_users = sum(1 for count in user_counts.values() if count > 1)
    
    stats["users"] = {
        "unique_users": unique_users,
        "repeat_users": repeat_users,
        "new_users": unique_users - repeat_users,  # Approximation
    }
    
    # Plan breakdown
    plan_stats = {}
    for inv in all_invoices:
        if not inv.bag:
            continue
        bag_plans = inv.bag.plans.all()
        for plan in bag_plans:
            plan_id = str(plan.id)
            if plan_id not in plan_stats:
                plan_stats[plan_id] = {
                    "times_used": 0,
                    "last_used_at": None,
                    "revenue_generated": 0.0,
                    "discount_given": 0.0,
                }
            plan_stats[plan_id]["times_used"] += 1
            plan_stats[plan_id]["revenue_generated"] += inv.amount
            if inv.paid_at:
                if plan_stats[plan_id]["last_used_at"] is None or inv.paid_at > plan_stats[plan_id]["last_used_at"]:
                    plan_stats[plan_id]["last_used_at"] = inv.paid_at.isoformat()
    
    # Calculate discount per plan
    for plan_id, plan_stat in plan_stats.items():
        if coupon.discount_type == Coupon.Discount.PERCENT_OFF:
            plan_stat["discount_given"] = round(
                plan_stat["revenue_generated"] * coupon.discount_value / (1 - coupon.discount_value), 2
            )
        elif coupon.discount_type == Coupon.Discount.FIXED_PRICE:
            plan_stat["discount_given"] = round(coupon.discount_value * plan_stat["times_used"], 2)
        plan_stat["revenue_generated"] = round(plan_stat["revenue_generated"], 2)
    
    stats["plans"] = plan_stats
    
    # Referral statistics (if applicable)
    if coupon.referral_type != Coupon.Referral.NO_REFERRAL:
        # Calculate commissions paid
        if coupon.referral_type == Coupon.Referral.PERCENTAGE:
            total_commissions = total_revenue * coupon.referral_value
        else:  # FIXED_PRICE
            total_commissions = coupon.referral_value * len(all_invoices)
        
        unique_sellers = 1 if coupon.seller else 0
        unique_buyers = unique_users
        
        stats["referral"] = {
            "total_commissions_paid": round(total_commissions, 2),
            "unique_sellers": unique_sellers,
            "unique_buyers": unique_buyers,
        }
    else:
        stats["referral"] = None
    
    # Time period breakdowns
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)
    ninety_days_ago = now - timedelta(days=90)
    
    last_7_days = [inv for inv in all_invoices if inv.paid_at >= seven_days_ago]
    last_30_days = [inv for inv in all_invoices if inv.paid_at >= thirty_days_ago]
    last_90_days = [inv for inv in all_invoices if inv.paid_at >= ninety_days_ago]
    
    stats["time_periods"] = {
        "last_7_days": {
            "times_used": len(last_7_days),
            "revenue_generated": round(sum(inv.amount for inv in last_7_days), 2),
        },
        "last_30_days": {
            "times_used": len(last_30_days),
            "revenue_generated": round(sum(inv.amount for inv in last_30_days), 2),
        },
        "last_90_days": {
            "times_used": len(last_90_days),
            "revenue_generated": round(sum(inv.amount for inv in last_90_days), 2),
        },
    }
    
    # Payment method distribution
    payment_methods = {}
    for inv in all_invoices:
        if inv.payment_method:
            method_name = inv.payment_method.name or "unknown"
            payment_methods[method_name] = payment_methods.get(method_name, 0) + 1
        else:
            payment_methods["unknown"] = payment_methods.get("unknown", 0) + 1
    
    stats["payment_methods"] = payment_methods

    return stats


def validate_payment_method_for_checkout(payment_method: PaymentMethod, bag: Bag, lang: str) -> None:
    if payment_method.deprecated:
        raise ValidationException(
            translation(
                lang,
                en="Payment method is deprecated",
                es="El método de pago está deprecado",
                slug="payment-method-deprecated",
            ),
            code=400,
        )

    if payment_method.visibility != PaymentMethod.Visibility.PUBLIC:
        raise ValidationException(
            translation(
                lang,
                en="Payment method is not available for checkout",
                es="El método de pago no está disponible para checkout",
                slug="payment-method-not-public",
            ),
            code=400,
        )

    if payment_method.academy_id and payment_method.academy_id != bag.academy_id:
        raise ValidationException(
            translation(
                lang,
                en="Payment method not found for this academy",
                es="Método de pago no encontrado para esta academia",
                slug="payment-method-not-found",
            ),
            code=404,
        )

    stripe_types = payment_method.get_stripe_payment_method_types()
    if stripe_types:
        allowed = ", ".join(sorted(PaymentMethod.StripeCheckoutPaymentMethodType.values))
        for value in stripe_types:
            if value not in PaymentMethod.StripeCheckoutPaymentMethodType.values:
                raise ValidationException(
                    translation(
                        lang,
                        en=f"Unsupported Stripe checkout payment method type: {value}. Allowed: {allowed}",
                        es=f"Tipo de método de pago de Stripe Checkout no soportado: {value}. Permitidos: {allowed}",
                        slug="unsupported-stripe-payment-method-type",
                    ),
                    code=400,
                )

        plan = bag.plans.first()
        if not plan:
            raise ValidationException(
                translation(lang, en="Bag has no plan", es="La bolsa no tiene plan", slug="bag-has-no-plan"),
                code=400,
            )

        if payment_method.plans.exists() and not payment_method.plans.filter(id=plan.id).exists():
            raise ValidationException(
                translation(
                    lang,
                    en="Payment method is not available for this plan",
                    es="El método de pago no está disponible para este plan",
                    slug="payment-method-not-available-for-plan",
                ),
                code=400,
            )

        return

    if payment_method.is_crypto or payment_method.is_credit_card:
        return

    raise ValidationException(
        translation(
            lang,
            en="Payment method not supported for checkout",
            es="Método de pago no soportado para checkout",
            slug="payment-method-not-supported",
        ),
        code=400,
    )


def resolve_plan_for_academy(
    plan_identifier,
    academy_id: int,
    lang: str,
    *,
    require_academy_owned: bool = False,
    allow_global: bool = True,
) -> "Plan":
    from breathecode.payments.models import Plan

    plan_kwargs = {}
    if isinstance(plan_identifier, int):
        plan_kwargs["id"] = plan_identifier
    elif isinstance(plan_identifier, str):
        if plan_identifier.isdigit():
            plan_kwargs["id"] = int(plan_identifier)
        else:
            plan_kwargs["slug"] = plan_identifier
    else:
        raise ValidationException(
            translation(
                lang,
                en="Invalid plan identifier. Must be an ID or slug",
                es="Identificador de plan inválido. Debe ser un ID o slug",
                slug="invalid-plan-identifier",
            ),
            code=400,
        )

    plan = Plan.objects.filter(**plan_kwargs).exclude(status="DELETED").first()
    if not plan:
        raise ValidationException(
            translation(
                lang,
                en=f"Plan not found: {plan_identifier}",
                es=f"Plan no encontrado: {plan_identifier}",
                slug="plan-not-found",
            ),
            code=404,
        )

    if require_academy_owned:
        if plan.owner_id != academy_id:
            raise ValidationException(
                translation(
                    lang,
                    en=f"Plan {plan_identifier} does not belong to this academy",
                    es=f"El plan {plan_identifier} no pertenece a esta academia",
                    slug="plan-not-belonging-to-academy",
                ),
                code=403,
            )
    elif plan.owner_id is not None and plan.owner_id != academy_id:
        raise ValidationException(
            translation(
                lang,
                en=f"Plan {plan_identifier} does not belong to this academy",
                es=f"El plan {plan_identifier} no pertenece a esta academia",
                slug="plan-not-belonging-to-academy",
            ),
            code=403,
        )

    if not allow_global and plan.owner_id is None:
        raise ValidationException(
            translation(
                lang,
                en=f"Plan {plan_identifier} must belong to this academy",
                es=f"El plan {plan_identifier} debe pertenecer a esta academia",
                slug="plan-not-belonging-to-academy",
            ),
            code=403,
        )

    return plan
