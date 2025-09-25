import calendar
import logging
from typing import Any

from task_manager.django.decorators import task
from task_manager.core.exceptions import AbortTask, RetryTask
from breathecode.utils.decorators import TaskPriority

logger = logging.getLogger(__name__)

from breathecode.commission.models import (
    GeekCreatorReferralCommission,
    GeekCreatorCommission,
    GeekCreatorPayment,
    UserUsageCommission,
)
from breathecode.payments.models import Invoice, Coupon
from breathecode.authenticate.models import ProfileAcademy
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime
from django.db.models import Sum, Count
from .actions import (
    get_geek_creator_academy_ids,
    get_eligible_cohort_ids,
    filter_invoices_by_plans_and_cohorts,
    compute_usage_rows_and_total,
)


@task(priority=TaskPriority.WEB_SERVICE_PAYMENT.value)
def register_referral_from_invoice(invoice_id: int, **_: Any) -> None:
    """Create a GeekCreatorReferralCommission if the invoice used a referral coupon and the seller is geek creator."""
    invoice = (
        Invoice.objects.select_related("bag", "currency", "academy", "user")
        .filter(id=invoice_id, status=Invoice.Status.FULFILLED, refunded_at__isnull=True)
        .first()
    )
    if not invoice:
        raise AbortTask(f"Invoice with id {invoice_id} not found or not fulfilled")

    bag = invoice.bag
    if not bag:
        raise AbortTask(f"Invoice {invoice_id} has no associated bag")

    coupon = bag.coupons.exclude(referral_type=Coupon.Referral.NO_REFERRAL).select_related("seller__user").first()
    if not coupon or not coupon.seller or not coupon.seller.user:
        raise AbortTask(f"No valid referral coupon found for invoice {invoice_id}")

    geek_creator = coupon.seller.user

    if not ProfileAcademy.objects.filter(
        user=geek_creator, academy_id=invoice.academy_id, role__slug="geek_creator", status="ACTIVE"
    ).exists():
        raise AbortTask(f"User {geek_creator.id} is not an active geek creator in academy {invoice.academy_id}")

    def add_months(dt, months=1):
        year = dt.year + (dt.month - 1 + months) // 12
        month = (dt.month - 1 + months) % 12 + 1
        day = min(dt.day, calendar.monthrange(year, month)[1])
        return dt.replace(year=year, month=month, day=day)

    available_at = add_months(invoice.paid_at, 1)
    status_text = None

    GeekCreatorReferralCommission.objects.get_or_create(
        invoice_id=invoice.id,
        defaults={
            "geek_creator_id": geek_creator.id,
            "academy_id": invoice.academy_id,
            "buyer_id": invoice.user_id,
            "amount": float(invoice.amount) * 0.5,
            "currency_id": invoice.currency_id,
            "available_at": available_at,
            "status_text": status_text,
        },
    )


@task(priority=TaskPriority.BACKGROUND.value)
def build_user_engagement_for_user_month(influencer_id: int, user_id: int, year: int, month: int, **_: Any) -> None:
    influencer = User.objects.filter(id=influencer_id).first()
    if not influencer:
        raise AbortTask(f"Influencer with id {influencer_id} not found")

    tz = timezone.get_current_timezone()
    start_dt = datetime(year, month, 1, 0, 0, 0, tzinfo=tz)
    next_year = year + (month // 12)
    next_mon = 1 if month == 12 else month + 1
    end_dt = datetime(next_year if month == 12 else year, next_mon, 1, 0, 0, 0, tzinfo=tz)

    # Exclude users that used referral for this influencer in the same month
    has_referral = GeekCreatorReferralCommission.objects.filter(
        geek_creator_id=influencer_id,
        buyer_id=user_id,
        created_at__gte=start_dt,
        created_at__lt=end_dt,
    ).exists()
    if has_referral:
        raise AbortTask(
            f"User {user_id} already has referral commission for influencer {influencer_id} in {year}-{month:02d}"
        )

    academy_ids = get_geek_creator_academy_ids(influencer)
    eligible_cohort_ids = get_eligible_cohort_ids(influencer, academy_ids)
    if not eligible_cohort_ids:
        raise AbortTask(f"No eligible cohorts found for influencer {influencer_id}")

    usage_invoices = Invoice.objects.select_related("bag", "currency", "academy", "user").filter(
        user_id=user_id,
        status=Invoice.Status.FULFILLED,
        refunded_at__isnull=True,
        paid_at__gte=start_dt,
        paid_at__lt=end_dt,
    )
    if not usage_invoices.exists():
        raise AbortTask(f"No usage invoices found for user {user_id} in {year}-{month:02d}")

    try:
        rows, _total, user_breakdown_by_cohort = compute_usage_rows_and_total(
            influencer, start_dt, end_dt, usage_invoices, eligible_cohort_ids
        )
    except Exception as e:
        logger.error(f"BigQuery computation failed for user {user_id}, influencer {influencer_id}: {e}")
        raise RetryTask("BigQuery computation failed, retrying in 300 seconds", countdown=300)

    for row in rows:
        if row["user_id"] != user_id:
            continue
        currency_obj = next((inv.currency for inv in usage_invoices if inv.currency.code == row["currency"]), None)
        if not currency_obj:
            logger.warning(f"No currency found for user {user_id}, currency code: {row['currency']}")
            continue
        user_breakdown = user_breakdown_by_cohort.get(user_id, {})

        usage_commission, created = UserUsageCommission.objects.update_or_create(
            influencer_id=influencer_id,
            user_id=user_id,
            cohort_id=row["cohort_id"],
            month=start_dt.date().replace(day=1),
            currency=currency_obj,
            defaults={
                "academy_id": Invoice.objects.filter(user_id=user_id).values_list("academy_id", flat=True).first(),
                "user_total_points": float(row["total_points"]),
                "cohort_points": float(row["cohort_points"]),
                "paid_amount": float(row["paid_amount"]),
                "commission_amount": float(row["commission"]),
                "details": {"breakdown": user_breakdown},
            },
        )

        geek_creator_commission = GeekCreatorCommission.objects.filter(
            influencer_id=influencer_id,
            cohort_id=row["cohort_id"],
            month=start_dt.date().replace(day=1),
            currency=currency_obj,
            commission_type=GeekCreatorCommission.CommissionType.USAGE,
        ).first()

        if geek_creator_commission:
            usage_commission.geek_creator_commission = geek_creator_commission
            usage_commission.save()

        logger.info(
            f"Successfully processed commission for user {user_id}, influencer {influencer_id}, cohort {row['cohort_id']}"
        )


@task(priority=TaskPriority.BACKGROUND.value)
def build_commissions_for_month(influencer_id: int, year: int, month: int, **_: Any) -> None:
    print(
        f"\033[33m[COMMISSION PROCESS] 🚀 Starting commission build for influencer {influencer_id}, month {year}-{month:02d}\033[0m"
    )

    tz = timezone.get_current_timezone()
    start_dt = datetime(year, month, 1, 0, 0, 0, tzinfo=tz)
    end_dt = datetime(year + (month // 12), 1 if month == 12 else month + 1, 1, 0, 0, 0, tzinfo=tz)

    usage_invoices = Invoice.objects.filter(
        status=Invoice.Status.FULFILLED,
        amount__gt=0,
        refunded_at__isnull=True,
        paid_at__gte=start_dt,
        paid_at__lt=end_dt,
    ).exclude(
        user_id__in=GeekCreatorReferralCommission.objects.filter(
            geek_creator_id=influencer_id, created_at__gte=start_dt, created_at__lt=end_dt
        ).values_list("buyer_id", flat=True)
    )

    influencer = User.objects.filter(id=influencer_id).first()
    if not influencer:
        raise AbortTask(f"Couldn't find influencer with id {influencer_id}")

    academy_ids = get_geek_creator_academy_ids(influencer)
    eligible_cohort_ids = get_eligible_cohort_ids(influencer, academy_ids)
    if not eligible_cohort_ids:
        raise AbortTask(f"No eligible cohorts found for influencer {influencer_id}")

    usage_invoices = filter_invoices_by_plans_and_cohorts(usage_invoices, None, None, eligible_cohort_ids)

    user_ids = list(usage_invoices.values_list("user_id", flat=True).distinct())

    if not user_ids:
        raise AbortTask(
            f"No users found for commission processing for influencer {influencer_id} in {year}-{month:02d}"
        )

    batch_size = 100
    for i in range(0, len(user_ids), batch_size):
        batch_user_ids = user_ids[i : i + batch_size]

        process_user_batch.delay(
            influencer_id=influencer_id,
            user_ids=batch_user_ids,
            year=year,
            month=month,
            batch_number=i // batch_size + 1,
            total_batches=(len(user_ids) + batch_size - 1) // batch_size,
        )

    final_aggregation_delay = max(300, len(user_ids) // 10)
    aggregate_commissions_for_month.apply_async(args=[influencer_id, year, month], countdown=final_aggregation_delay)

    print(
        f"\033[33m[COMMISSION PROCESS] 📋 Scheduled {len(user_ids)} users in {(len(user_ids) + batch_size - 1) // batch_size} batches for influencer {influencer_id}, final aggregation in {final_aggregation_delay}s\033[0m"
    )


@task(priority=TaskPriority.BACKGROUND.value)
def process_user_batch(
    influencer_id: int, user_ids: list[int], year: int, month: int, batch_number: int, total_batches: int, **_: Any
) -> None:
    """Process a batch of users for commission calculation."""
    if not user_ids:
        raise AbortTask(f"Empty user batch {batch_number}/{total_batches} for influencer {influencer_id}")

    print(
        f"\033[33m[COMMISSION BATCH] 🚀 Starting batch {batch_number}/{total_batches} for influencer {influencer_id} - {len(user_ids)} users\033[0m"
    )

    logger.info(
        f"Processing batch {batch_number}/{total_batches} for influencer {influencer_id}, users: {len(user_ids)}"
    )

    failed_users = []
    for user_id in user_ids:
        try:
            build_user_engagement_for_user_month.delay(influencer_id, user_id, year, month)
        except Exception as e:
            logger.error(f"Failed to schedule user {user_id} for influencer {influencer_id}: {e}")
            failed_users.append(user_id)

    if failed_users:
        logger.warning(
            f"Batch {batch_number}/{total_batches} completed with {len(failed_users)} failed users: {failed_users}"
        )
    else:
        logger.info(f"Batch {batch_number}/{total_batches} completed successfully for all {len(user_ids)} users")

    print(
        f"\033[33m[COMMISSION BATCH] ✅ Batch {batch_number}/{total_batches} completed for influencer {influencer_id} - {len(user_ids)} users processed\033[0m"
    )


@task(priority=TaskPriority.BACKGROUND.value)
def aggregate_commissions_for_month(influencer_id: int, year: int, month: int, **_: Any) -> None:
    """Aggregate all user commissions into TeacherInfluencerCommission records."""
    tz = timezone.get_current_timezone()
    start_dt = datetime(year, month, 1, 0, 0, 0, tzinfo=tz)
    month_date = start_dt.date().replace(day=1)
    end_dt = datetime(year + (month // 12), 1 if month == 12 else month + 1, 1, 0, 0, 0, tzinfo=tz)

    usage_agg = (
        UserUsageCommission.objects.filter(influencer_id=influencer_id, month=month_date)
        .values("cohort_id", "currency_id")
        .annotate(total_amount=Sum("commission_amount"), users=Count("id"))
    )

    for x in usage_agg:
        inst, _ = GeekCreatorCommission.objects.get_or_create(
            influencer_id=influencer_id,
            cohort_id=x["cohort_id"],
            month=month_date,
            commission_type=GeekCreatorCommission.CommissionType.USAGE,
            currency_id=x["currency_id"],
        )
        inst.amount_paid = float(x["total_amount"] or 0)
        inst.num_users = int(x["users"] or 0)
        inst.save()

        usage_records = UserUsageCommission.objects.filter(
            influencer_id=influencer_id, cohort_id=x["cohort_id"], month=month_date, currency_id=x["currency_id"]
        )
        inst.usage_commissions.set(usage_records)

    referrals_created_in_month = GeekCreatorReferralCommission.objects.filter(
        geek_creator_id=influencer_id, created_at__gte=start_dt, created_at__lt=end_dt
    ).select_related("invoice")

    referrals_without_refunds = [r for r in referrals_created_in_month if not r.invoice.refunded_at]

    current_time = timezone.now()
    effective_referrals = [r for r in referrals_without_refunds if current_time >= r.available_at]

    matured = {}
    for r in effective_referrals:
        currency_id = r.currency_id
        if currency_id not in matured:
            matured[currency_id] = {"total_amount": 0, "users": set()}
        matured[currency_id]["total_amount"] += r.amount
        matured[currency_id]["users"].add(r.buyer_id)

    # Convert to list format
    matured_list = [
        {"currency_id": currency_id, "total_amount": data["total_amount"], "users": len(data["users"])}
        for currency_id, data in matured.items()
    ]

    for x in matured_list:
        inst, _ = GeekCreatorCommission.objects.get_or_create(
            influencer_id=influencer_id,
            cohort=None,
            month=month_date,
            commission_type=GeekCreatorCommission.CommissionType.REFERRAL,
            currency_id=x["currency_id"],
        )
        inst.amount_paid = float(x["total_amount"] or 0)  # amount already includes 50% commission
        inst.num_users = int(x["users"] or 0)
        inst.save()

        effective_referral_ids_for_currency = [r.id for r in effective_referrals if r.currency_id == x["currency_id"]]
        referral_records = GeekCreatorReferralCommission.objects.filter(id__in=effective_referral_ids_for_currency)
        inst.referral_commissions.set(referral_records)

    currency_ids = list(
        GeekCreatorCommission.objects.filter(influencer_id=influencer_id, month=month_date)
        .values_list("currency_id", flat=True)
        .distinct()
    )

    for currency_id in currency_ids:
        total = (
            GeekCreatorCommission.objects.filter(
                influencer_id=influencer_id, month=month_date, currency_id=currency_id
            ).aggregate(total=Sum("amount_paid"))["total"]
            or 0.0
        )

        bill, _ = GeekCreatorPayment.objects.get_or_create(
            influencer_id=influencer_id, month=month_date, currency_id=currency_id, defaults={"total_amount": 0.0}
        )
        bill.total_amount = round(float(total), 2)
        bill.save()
        bill.commissions.set(
            GeekCreatorCommission.objects.filter(influencer_id=influencer_id, month=month_date, currency_id=currency_id)
        )

    logger.info(f"Completed aggregation for influencer {influencer_id}, month {year}-{month:02d}")

    print(
        f"\033[33m[COMMISSION AGGREGATION] 🎉 Completed ALL aggregation for influencer {influencer_id}, month {year}-{month:02d}\033[0m"
    )
