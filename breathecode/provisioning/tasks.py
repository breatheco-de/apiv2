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

from breathecode.payments.services.stripe import Stripe
from breathecode.provisioning import actions
from breathecode.provisioning.models import ProvisioningBill, ProvisioningConsumptionEvent, ProvisioningUserConsumption
from breathecode.services.google_cloud.storage import Storage
from breathecode.utils.decorators import TaskPriority
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
