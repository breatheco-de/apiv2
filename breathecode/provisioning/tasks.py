import logging
import math
import os
from datetime import datetime
from decimal import Decimal
from io import BytesIO
from typing import Any

import pandas as pd
import pytz
from dateutil.relativedelta import relativedelta
from django.db.models import DecimalField, F, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from task_manager.core.exceptions import AbortTask, RetryTask
from task_manager.django.decorators import task

from breathecode.authenticate.models import User
from breathecode.payments.models import Consumable, Service
from breathecode.payments.services.stripe import Stripe
from breathecode.payments.signals import consume_service, reimburse_service_units
from breathecode.provisioning import actions
from breathecode.provisioning.utils.llm_client import LLMClientError, get_llm_client
from breathecode.provisioning.models import (
    ProvisioningAcademy,
    ProvisioningBill,
    ProvisioningConsumptionEvent,
    ProvisioningLLM,
    ProvisioningUserConsumption,
    ProvisioningVPS,
)
from breathecode.provisioning.utils.vps_client import VPSProvisioningError, get_vps_client
from breathecode.services.google_cloud.storage import Storage
from breathecode.utils.decorators import TaskPriority
from breathecode.utils.encryption import encrypt
from breathecode.utils.io.file import cut_csv

logger = logging.getLogger(__name__)


def get_provisioning_credit_price():
    return Decimal(os.getenv("PROVISIONING_CREDIT_PRICE", "10"))


def get_stripe_price_id():
    return os.getenv("STRIPE_PRICE_ID", None)


MONTHS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]

PANDAS_ROWS_LIMIT = 100
DELETE_LIMIT = 10000


@task(priority=TaskPriority.BILL.value)
def calculate_bill_amounts(hash: str, *, force: bool = False, **_: Any):
    logger.info(f"Starting calculate_bill_amounts for hash {hash}")

    bills_query = ProvisioningBill.objects.filter(hash=hash)

    if force:
        bills_query = bills_query.exclude(status="PAID")

    else:
        bills_query = bills_query.exclude(status__in=["DISPUTED", "IGNORED", "PAID"])

    if not bills_query.exists():
        raise RetryTask(f"Does not exists bills for hash {hash}")

    first_bill = bills_query.first()  # Get one bill to determine vendor and dates

    if first_bill.vendor.name == "Gitpod":
        fields = ["id", "credits", "startTime", "endTime", "kind", "userName", "contextURL"]
        start_field, end_field = "startTime", "startTime"

    elif first_bill.vendor.name == "Codespaces":
        fields = [
            "username",
            "date",
            "product",
            "sku",
            "quantity",
            "unit_type",
            "applied_cost_per_quantity",
        ]
        start_field, end_field = "date", "date"

    elif first_bill.vendor.name == "Rigobot":
        fields = [
            "organization",
            "consumption_period_id",
            "consumption_period_start",
            "consumption_period_end",
            "billing_status",
            "total_spent_period",
            "consumption_item_id",
            "user_id",
            "email",
            "consumption_type",
            "pricing_type",
            "total_spent",
            "total_tokens",
            "model",
            "purpose_id",
            "purpose_slug",
            "purpose",
            "created_at",
            "github_username",
        ]
        start_field, end_field = "consumption_period_start", "consumption_period_end"

    else:
        raise AbortTask(f"Unsupported vendor: {first_bill.vendor.name}")

    storage = Storage()
    cloud_file = storage.file(os.getenv("PROVISIONING_BUCKET", None), hash)
    if not cloud_file.exists():
        raise AbortTask(f"File {hash} not found")

    csv_string_io = BytesIO()
    cloud_file.download(csv_string_io)
    csv_string_io = cut_csv(csv_string_io, first=1)
    csv_string_io.seek(0)
    df1 = pd.read_csv(csv_string_io, sep=",", usecols=fields)
    first_date_str = df1[start_field][0].split("T")[0]
    first = datetime.strptime(first_date_str, "%Y-%m-%d").replace(tzinfo=pytz.UTC)

    csv_string_io = BytesIO()
    cloud_file.download(csv_string_io)
    csv_string_io = cut_csv(csv_string_io, last=1)
    csv_string_io.seek(0)
    df2 = pd.read_csv(csv_string_io, sep=",", usecols=fields)
    last_date_str = df2[end_field][0].split("T")[0]
    last = datetime.strptime(last_date_str, "%Y-%m-%d").replace(tzinfo=pytz.UTC)

    if first > last:
        x = first
        first = last
        last = x

    month = MONTHS[first.month - 1]

    annotated_bills = bills_query.annotate(
        aggregated_amount=Coalesce(
            Sum(
                F("provisioninguserconsumption__events__quantity")
                * F("provisioninguserconsumption__events__price__price_per_unit")
                * F("provisioninguserconsumption__events__price__multiplier"),
                output_field=DecimalField(),
            ),
            Decimal("0.0"),
            output_field=DecimalField(),
        )
    )

    for bill in annotated_bills:
        amount = bill.aggregated_amount.quantize(Decimal("0.000000001"))

        for activity in ProvisioningUserConsumption.objects.filter(bills=bill, status__in=["PERSISTED", "WARNING"]):
            activity_agg = activity.events.aggregate(
                total_amount=Coalesce(
                    Sum(
                        F("quantity") * F("price__price_per_unit") * F("price__multiplier"),
                        output_field=DecimalField(),
                    ),
                    Decimal("0.0"),
                    output_field=DecimalField(),
                ),
                total_quantity=Coalesce(Sum(F("quantity"), output_field=DecimalField()), Decimal("0.0")),
            )

            activity.amount = activity_agg["total_amount"].quantize(Decimal("0.000000001"))
            activity.quantity = activity_agg["total_quantity"].quantize(Decimal("0.000000001"))
            activity.save()

        bill.status = "DUE" if amount else "PAID"

        if amount:
            credit_price = get_provisioning_credit_price()
            quantity = math.ceil(amount / credit_price)
            new_price = (Decimal(str(quantity)) * credit_price).quantize(Decimal("0.000000001"))

            try:
                s = Stripe()
                bill.stripe_id, bill.stripe_url = s.create_payment_link(get_stripe_price_id(), quantity)
                bill.fee = (new_price - amount).quantize(Decimal("0.000000001"))
                bill.total_amount = new_price.quantize(Decimal("0.000000001"))
                bill.paid_at = None

            except Exception as e:
                logger.error(f"Stripe error for bill {bill.id}: {e}")
                bill.status = "ERROR"
                bill.status_details = f"Stripe error: {e}"
                bill.total_amount = amount
                bill.fee = Decimal("0.0")
                bill.stripe_id = None
                bill.stripe_url = None

        else:
            bill.total_amount = Decimal("0.0").quantize(Decimal("0.000000001"))
            bill.fee = Decimal("0.0").quantize(Decimal("0.000000001"))
            bill.paid_at = timezone.now() if bill.status == "PAID" else None
            bill.stripe_id = None
            bill.stripe_url = None

        bill.started_at = first
        bill.ended_at = last
        bill.title = f"{month} {first.year}"
        bill.save()


def reverse_upload(hash: str, **_: Any):
    logger.info(f"Canceling upload for hash {hash}")

    ProvisioningConsumptionEvent.objects.filter(provisioninguserconsumption__hash=hash).delete()
    ProvisioningUserConsumption.objects.filter(hash=hash).delete()
    ProvisioningBill.objects.filter(hash=hash).delete()


@task(reverse=reverse_upload, priority=TaskPriority.BILL.value)
def upload(hash: str, *, page: int = 0, force: bool = False, task_manager_id: int = 0, **_: Any):
    logger.info(f"Starting upload for hash {hash}")

    limit = PANDAS_ROWS_LIMIT
    start = page * limit
    end = start + limit
    context = {
        "provisioning_bills": {},
        "provisioning_vendors": {},
        "github_academy_user_logs": {},
        "provisioning_activity_prices": {},
        "provisioning_activity_kinds": {},
        "provisioning_multiplier": actions.get_multiplier(),
        "currencies": {},
        "profile_academies": {},
        "hash": hash,
        "limit": timezone.now(),
        "logs": {},
    }

    storage = Storage()
    cloud_file = storage.file(os.getenv("PROVISIONING_BUCKET", None), hash)
    if not cloud_file.exists():
        raise RetryTask(f"File {hash} not found")

    bills = ProvisioningBill.objects.filter(hash=hash).exclude(status="PENDING")
    if bills.exists() and not force:
        raise AbortTask(f"File {hash} already processed")

    pending_bills = bills.exclude(status__in=["DISPUTED", "IGNORED", "PAID"])

    if force and pending_bills.count() != bills.count():
        raise AbortTask("Cannot force upload because there are bills with status DISPUTED, IGNORED or PAID")

    if force:
        event_pks_to_delete = ProvisioningConsumptionEvent.objects.filter(
            provisioninguserconsumption__bills__in=pending_bills
        ).values_list("pk", flat=True)

        chunk_size = 1000
        for i in range(0, len(event_pks_to_delete), chunk_size):
            chunk = list(event_pks_to_delete[i : i + chunk_size])
            ProvisioningConsumptionEvent.objects.filter(pk__in=chunk).delete()

        ProvisioningUserConsumption.objects.filter(bills__in=pending_bills).delete()

        pending_bills.delete()

    csv_string_io = BytesIO()
    cloud_file.download(csv_string_io)
    csv_string_io = cut_csv(csv_string_io, start=start, end=end)
    csv_string_io.seek(0)

    df = pd.read_csv(csv_string_io, sep=",", low_memory=False)

    handler = None
    vendor_name = None

    gitpod_fields = ["id", "credits", "startTime", "endTime", "kind", "userName", "contextURL"]
    if len(df.keys().intersection(gitpod_fields)) == len(gitpod_fields):
        handler = actions.add_gitpod_activity
        vendor_name = "Gitpod"

    if not handler:
        codespaces_fields = [
            "username",
            "date",
            "product",
            "sku",
            "quantity",
            "unit_type",
        ]
        if len(df.keys().intersection(codespaces_fields)) >= len(codespaces_fields) - 1:
            handler = actions.add_codespaces_activity
            vendor_name = "Codespaces"

    if not handler:
        rigobot_fields = [
            "organization",
            "consumption_period_id",
            "consumption_period_start",
            "consumption_period_end",
            "billing_status",
            "total_spent_period",
            "consumption_item_id",
            "user_id",
            "email",
            "consumption_type",
            "pricing_type",
            "total_spent",
            "total_tokens",
            "model",
            "purpose_id",
            "purpose_slug",
            "purpose",
            "created_at",
            "github_username",
        ]
        if len(df.keys().intersection(rigobot_fields)) == len(rigobot_fields):
            handler = actions.add_rigobot_activity
            vendor_name = "Rigobot"

    if not handler:
        raise AbortTask(
            f"File {hash} has an unsupported origin or the provider had changed the file format. Detected columns: {list(df.columns)}"
        )

    if vendor_name:
        context["vendor_name"] = vendor_name

    prev_bill = ProvisioningBill.objects.filter(hash=hash).first()
    if prev_bill:
        context["limit"] = prev_bill.created_at

    try:
        i = 0
        for position in range(start, end):
            if i >= len(df):
                break
            try:
                handler(context, df.iloc[i].to_dict(), position)
                i += 1

            except IndexError:
                logger.warning(
                    f"IndexError while processing row {i} (position {position}) in file {hash}. Reached end of DataFrame chunk."
                )
                break
            except Exception as inner_exc:
                logger.error(
                    f"Error processing row {i} (position {position}) in file {hash}: {inner_exc}", exc_info=True
                )
                i += 1

    except Exception as e:
        import traceback

        traceback.print_exc()
        ProvisioningBill.objects.filter(hash=hash).update(status="ERROR", status_details=f"Task-level error: {e}")
        raise AbortTask(f"File {hash} cannot be processed due to task-level error: {str(e)}")

    for bill in context["provisioning_bills"].values():
        if bill.pk and not ProvisioningUserConsumption.objects.filter(bills=bill).exists():
            logger.warning(f"Deleting bill {bill.id} for hash {hash} because it has no related consumptions.")
            bill.delete()

    if len(df) == limit:
        upload.delay(hash, page=page + 1, task_manager_id=task_manager_id)

    elif not ProvisioningUserConsumption.objects.filter(hash=hash, status="ERROR").exists():
        calculate_bill_amounts.delay(hash)

    elif ProvisioningUserConsumption.objects.filter(hash=hash, status="ERROR").exists():
        ProvisioningBill.objects.filter(hash=hash).update(
            status="ERROR", status_details="Errors found in consumption records."
        )


@task(priority=TaskPriority.BACKGROUND.value)
def archive_provisioning_bill(bill_id: int, **_: Any):
    logger.info(f"Starting archive_provisioning_bills for bill id {bill_id}")

    now = timezone.now()
    bill = ProvisioningBill.objects.filter(
        id=bill_id, status="PAID", paid_at__lte=now - relativedelta(months=1), archived_at__isnull=True
    ).first()

    if not bill:
        raise AbortTask(f"Bill {bill_id} not found or requirements not met for archiving.")

    event_pks_to_delete = ProvisioningConsumptionEvent.objects.filter(
        provisioninguserconsumption__hash=bill.hash
    ).values_list("pk", flat=True)

    chunk_size = 1000
    for i in range(0, len(event_pks_to_delete), chunk_size):
        chunk = list(event_pks_to_delete[i : i + chunk_size])
        ProvisioningConsumptionEvent.objects.filter(pk__in=chunk).delete()

    bill.archived_at = now
    bill.save()
    logger.info(f"Successfully archived bill {bill_id}")


@task(priority=TaskPriority.STUDENT.value)
def provision_vps_task(provisioning_vps_id: int, vendor_selection: dict | None = None, **_: Any):
    """
    Provision a VPS via the vendor API. On success: update model, encrypt password, send email.
    On failure: reimburse consumable and set status ERROR.
    """
    vps = ProvisioningVPS.objects.filter(id=provisioning_vps_id).select_related("vendor", "academy", "user").first()
    if not vps:
        logger.warning("ProvisioningVPS id=%s not found", provisioning_vps_id)
        return
    if vps.status not in (ProvisioningVPS.VPS_STATUS_PENDING, ProvisioningVPS.VPS_STATUS_PROVISIONING):
        logger.info("ProvisioningVPS id=%s already in status %s, skipping", provisioning_vps_id, vps.status)
        return

    vps.status = ProvisioningVPS.VPS_STATUS_PROVISIONING
    vps.save(update_fields=["status", "updated_at"])

    provisioning_academy = ProvisioningAcademy.objects.filter(academy=vps.academy, vendor=vps.vendor).first()
    if not provisioning_academy:
        _vps_fail(vps, "No ProvisioningAcademy for this academy and vendor")
        return

    credentials = {"token": provisioning_academy.credentials_token or ""}
    if provisioning_academy.credentials_key:
        credentials["key"] = provisioning_academy.credentials_key
    if provisioning_academy.vendor_settings:
        credentials.update(provisioning_academy.vendor_settings)
    if vendor_selection:
        credentials.update(vendor_selection)
    credentials["provisioning_vps_id"] = provisioning_vps_id
    client = get_vps_client(vps.vendor)
    if not client:
        _vps_fail(vps, "No VPS client registered for vendor %s", vps.vendor.name if vps.vendor else "?")
        return

    try:
        result = client.create_vps(credentials, plan_slug=vps.plan_slug or None)
    except VPSProvisioningError as e:
        _vps_fail(vps, str(e))
        return

    external_id = result.get("external_id") or ""
    ip_address = result.get("ip_address")
    hostname = result.get("hostname") or ""
    ssh_user = result.get("ssh_user") or "root"
    ssh_port = result.get("ssh_port") or 22
    root_password = result.get("root_password")

    vps.external_id = external_id
    vps.ip_address = ip_address
    vps.hostname = hostname
    vps.ssh_user = ssh_user
    vps.ssh_port = ssh_port
    if root_password:
        try:
            vps.root_password_encrypted = encrypt(root_password)
        except Exception as enc_err:
            logger.exception("Encrypting VPS root password failed: %s", enc_err)
            _vps_fail(vps, "Failed to store password")
            return
    vps.status = ProvisioningVPS.VPS_STATUS_ACTIVE
    vps.provisioned_at = timezone.now()
    vps.error_message = ""
    vps.save(
        update_fields=[
            "external_id",
            "ip_address",
            "hostname",
            "ssh_user",
            "ssh_port",
            "root_password_encrypted",
            "status",
            "provisioned_at",
            "error_message",
            "updated_at",
        ]
    )

    vps.refresh_from_db(fields=None)
    actions.apply_early_vps_billing_alignment(vps)

    try:
        from breathecode.notify.actions import send_email_message

        to = vps.user.email if getattr(vps.user, "email", None) else None
        if to:
            data = {
                "hostname": hostname,
                "ip_address": ip_address or "",
                "ssh_user": ssh_user,
                "ssh_port": ssh_port,
                "root_password": root_password or "",
            }
            send_email_message("vps_connection_details", to, data=data, academy=vps.academy)
    except Exception as email_err:
        logger.warning("Failed to send VPS connection email: %s", email_err)


def _vps_fail(vps: ProvisioningVPS, message: str, *args) -> None:
    if args:
        message = message % args
    if vps.consumed_consumable_id:
        try:
            reimburse_service_units.send_robust(sender=Consumable, instance=vps.consumed_consumable, how_many=1)
        except Exception as e:
            logger.exception("Reimburse consumable failed: %s", e)
    vps.status = ProvisioningVPS.VPS_STATUS_ERROR
    vps.error_message = message[:255] if len(message) > 255 else message
    vps.save(update_fields=["status", "error_message", "updated_at"])


@task(priority=TaskPriority.STUDENT.value)
def renew_or_deprovision_vps_task(provisioning_vps_id: int, **_: Any):
    """
    For one ACTIVE VPS: if user has vps_server consumable, consume 1 to renew; else deprovision (destroy_vps, set DELETED).
    """
    vps = (
        ProvisioningVPS.objects.filter(id=provisioning_vps_id, status=ProvisioningVPS.VPS_STATUS_ACTIVE)
        .select_related("vendor", "academy", "user")
        .first()
    )
    if not vps:
        return
    consumables = Consumable.list(
        user=vps.user,
        include_zero_balance=False,
        extra={"service_item__service__consumer": Service.Consumer.VPS_SERVER},
    ).filter(how_many__gt=0)
    if consumables.exists():
        consumable = consumables.first()
        consume_service.send(sender=Consumable, instance=consumable, how_many=1)
        logger.info("Renewed VPS %s: consumed 1 vps_server", provisioning_vps_id)
        return
    deprovision_vps_task(provisioning_vps_id)


@task(priority=TaskPriority.STUDENT.value)
def deprovision_vps_task(provisioning_vps_id: int, **_: Any):
    """
    Deprovision a VPS via the vendor API (e.g. academy delete or monthly renewal).
    Sets status to DELETED. Optionally send vps_deprovisioned email.
    """
    vps = ProvisioningVPS.objects.filter(id=provisioning_vps_id).select_related("vendor", "academy", "user").first()
    if not vps:
        logger.warning("ProvisioningVPS id=%s not found for deprovision", provisioning_vps_id)
        return
    if vps.status == ProvisioningVPS.VPS_STATUS_DELETED:
        return
    provisioning_academy = ProvisioningAcademy.objects.filter(academy=vps.academy, vendor=vps.vendor).first()
    if not provisioning_academy or not vps.external_id:
        vps.status = ProvisioningVPS.VPS_STATUS_DELETED
        vps.deleted_at = timezone.now()
        vps.save(update_fields=["status", "deleted_at", "updated_at"])
        return
    credentials = {"token": provisioning_academy.credentials_token or ""}
    client = get_vps_client(vps.vendor)
    if client:
        try:
            client.destroy_vps(credentials, vps.external_id)
        except VPSProvisioningError as e:
            logger.warning("Deprovision VPS %s failed: %s", provisioning_vps_id, e)
    vps.status = ProvisioningVPS.VPS_STATUS_DELETED
    vps.deleted_at = timezone.now()
    vps.save(update_fields=["status", "deleted_at", "updated_at"])
    try:
        from breathecode.notify.actions import send_email_message

        to = vps.user.email if getattr(vps.user, "email", None) else None
        if to:
            send_email_message(
                "vps_deprovisioned",
                to,
                data={"hostname": vps.hostname or ""},
                academy=vps.academy,
            )
    except Exception as email_err:
        logger.warning("Failed to send VPS deprovisioned email: %s", email_err)


@task(priority=TaskPriority.SCHEDULER.value)
def monthly_vps_renewal_dispatcher(**_: Any):
    """
    Run at start of each month (e.g. Celery beat crontab 0 0 1 * *).
    Enqueues renew_or_deprovision_vps_task for each ACTIVE ProvisioningVPS.
    """
    active_ids = list(
        ProvisioningVPS.objects.filter(status=ProvisioningVPS.VPS_STATUS_ACTIVE).values_list("id", flat=True)
    )
    for vps_id in active_ids:
        renew_or_deprovision_vps_task.delay(vps_id)
    logger.info("Monthly VPS renewal: enqueued %s tasks", len(active_ids))


@task(priority=TaskPriority.STUDENT.value)
def deprovision_litellm_user_task(user_id: int, academy_id: int | None = None, **_: Any):
    """
    Deprovision a user from Litellm by deleting the external user and its API keys.

    This is triggered when the user loses `free_monthly_llm_budget`.
    """
    user = User.objects.filter(id=user_id).first()
    if not user:
        raise AbortTask(f"User {user_id} not found")

    if academy_id:
        try:
            academy_id = int(academy_id)
        except Exception:
            academy_id = None

    if academy_id:
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
            logger.info(
                "User %s still has free-monthly-llm-budget for academy %s, skipping deprovision",
                user_id,
                academy_id,
            )
            return
    else:
        if Consumable.list(user=user, service="free-monthly-llm-budget").exists():
            logger.info("User %s still has free-monthly-llm-budget, skipping deprovision", user_id)
            return

    provisioning_llms_qs = ProvisioningLLM.objects.filter(user=user).select_related("academy", "vendor").all()
    if academy_id:
        provisioning_llms_qs = provisioning_llms_qs.filter(academy_id=academy_id)

    # Group external users by (academy_id, vendor_id) so each deletion call
    # uses the correct ProvisioningAcademy credentials/base_url.
    provisioning_academy_groups: dict[tuple[int, int], set[str]] = {}
    for provisioning_llm in provisioning_llms_qs:
        if not provisioning_llm.vendor_id or not provisioning_llm.external_user_id:
            continue
        key = (provisioning_llm.academy_id, provisioning_llm.vendor_id)
        provisioning_academy_groups.setdefault(key, set()).add(str(provisioning_llm.external_user_id))

    if not provisioning_academy_groups:
        return

    now = timezone.now()

    # For each tenant/config (academy + vendor), call Litellm to delete the external user(s),
    # and persist our internal status accordingly.
    for (academy_id, vendor_id), external_user_ids in provisioning_academy_groups.items():
        provisioning_academy = (
            ProvisioningAcademy.objects.select_related("vendor")
            .filter(
                academy_id=academy_id,
                vendor_id=vendor_id,
            )
            .first()
        )

        if not provisioning_academy or not provisioning_academy.vendor:
            continue

        client = get_llm_client(provisioning_academy)
        if client is None:
            continue

        user_id_list = list(external_user_ids)
        try:
            client.delete_user(user_ids=user_id_list)
        except LLMClientError as exc:
            ProvisioningLLM.objects.filter(
                user=user,
                academy_id=academy_id,
                vendor_id=vendor_id,
                external_user_id__in=user_id_list,
            ).update(
                status=ProvisioningLLM.STATUS_ERROR,
                error_message=str(exc),
                updated_at=timezone.now(),
            )
            raise RetryTask(f"deprovision_litellm_user_task failed: {exc}") from exc

        # Success: mark affected records as deprovisioned.
        ProvisioningLLM.objects.filter(
            user=user,
            academy_id=academy_id,
            vendor_id=vendor_id,
            external_user_id__in=user_id_list,
        ).update(
            status=ProvisioningLLM.STATUS_DEPROVISIONED,
            deprovisioned_at=now,
            error_message="",
            updated_at=timezone.now(),
        )
        logger.info(f"Deprovisioned user {user_id} from Litellm for academy {academy_id} and vendor {vendor_id}")
