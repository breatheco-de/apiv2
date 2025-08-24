import calendar
from typing import Any

from task_manager.django.decorators import task
from breathecode.utils.decorators import TaskPriority

from breathecode.commission.models import (
    TeacherInfluencerReferralCommission,
    TeacherInfluencerCommission,
    TeacherInfluencerPayment,
    UserCohortEngagement,
)
from breathecode.payments.models import Invoice, Coupon
from breathecode.authenticate.models import ProfileAcademy
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime
from django.db.models import Sum, Count
from .actions import (
    get_teacher_influencer_academy_ids,
    get_eligible_cohort_ids,
    compute_usage_rows_and_total,
)


@task(priority=TaskPriority.WEB_SERVICE_PAYMENT.value)
def register_referral_from_invoice(invoice_id: int, **_: Any) -> None:
    """Create a TeacherInfluencerReferralCommission if the invoice used a referral coupon and the seller is teacher influencer."""
    invoice = (
        Invoice.objects.select_related("bag", "currency", "academy", "user")
        .filter(id=invoice_id, status=Invoice.Status.FULFILLED, refunded_at__isnull=True)
        .first()
    )
    if not invoice:
        return

    bag = invoice.bag
    coupon = bag.coupons.exclude(referral_type=Coupon.Referral.NO_REFERRAL).select_related("seller__user").first()
    if not coupon or not coupon.seller or not coupon.seller.user:
        return

    teacher_influencer = coupon.seller.user

    if not ProfileAcademy.objects.filter(
        user=teacher_influencer, academy_id=invoice.academy_id, role__slug="teacher_influencer", status="ACTIVE"
    ).exists():
        return

    def add_months(dt, months=1):
        year = dt.year + (dt.month - 1 + months) // 12
        month = (dt.month - 1 + months) % 12 + 1
        day = min(dt.day, calendar.monthrange(year, month)[1])
        return dt.replace(year=year, month=month, day=day)

    available_at = add_months(invoice.paid_at, 1)
    status_text = None

    TeacherInfluencerReferralCommission.objects.get_or_create(
        invoice_id=invoice.id,
        defaults={
            "teacher_influencer_id": teacher_influencer.id,
            "academy_id": invoice.academy_id,
            "buyer_id": invoice.user_id,
            "amount": float(invoice.amount),
            "currency_id": invoice.currency_id,
            "available_at": available_at,
            "status_text": status_text,
        },
    )


@task(priority=TaskPriority.BACKGROUND.value)
def build_user_engagement_for_user_month(influencer_id: int, user_id: int, year: int, month: int, **_: Any) -> None:
    influencer = User.objects.filter(id=influencer_id).first()
    if not influencer:
        return

    tz = timezone.get_current_timezone()
    start_dt = datetime(year, month, 1, 0, 0, 0, tzinfo=tz)
    next_year = year + (month // 12)
    next_mon = 1 if month == 12 else month + 1
    end_dt = datetime(next_year if month == 12 else year, next_mon, 1, 0, 0, 0, tzinfo=tz)

    # Exclude users that used referral for this influencer in the same month
    has_referral = TeacherInfluencerReferralCommission.objects.filter(
        teacher_influencer_id=influencer_id,
        buyer_id=user_id,
        created_at__gte=start_dt,
        created_at__lt=end_dt,
    ).exists()
    if has_referral:
        return

    academy_ids = get_teacher_influencer_academy_ids(influencer)
    eligible_cohort_ids = get_eligible_cohort_ids(influencer, academy_ids)
    if not eligible_cohort_ids:
        return

    usage_invoices = Invoice.objects.select_related("bag", "currency", "academy", "user").filter(
        user_id=user_id,
        status=Invoice.Status.FULFILLED,
        refunded_at__isnull=True,
        paid_at__gte=start_dt,
        paid_at__lt=end_dt,
    )
    if not usage_invoices.exists():
        return

    rows, _total, breakdown_by_kind = compute_usage_rows_and_total(
        influencer, start_dt, end_dt, usage_invoices, eligible_cohort_ids
    )

    for row in rows:
        if row["user_id"] != user_id:
            continue
        currency_obj = next((inv.currency for inv in usage_invoices if inv.currency.code == row["currency"]), None)
        if not currency_obj:
            continue
        kind_breakdown = breakdown_by_kind.get((user_id, row["cohort_id"]), {})

        UserCohortEngagement.objects.update_or_create(
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
                "details": {"breakdown": kind_breakdown},
            },
        )


@task(priority=TaskPriority.BACKGROUND.value)
def build_commissions_for_month(influencer_id: int, year: int, month: int, **_: Any) -> None:
    tz = timezone.get_current_timezone()
    start_dt = datetime(year, month, 1, 0, 0, 0, tzinfo=tz)
    month_date = start_dt.date().replace(day=1)
    end_dt = datetime(year + (month // 12), 1 if month == 12 else month + 1, 1, 0, 0, 0, tzinfo=tz)

    usage_agg = (
        UserCohortEngagement.objects.filter(influencer_id=influencer_id, month=month_date)
        .values("cohort_id", "currency_id")
        .annotate(total_amount=Sum("commission_amount"), users=Count("id"))
    )

    for x in usage_agg:
        inst, _ = TeacherInfluencerCommission.objects.get_or_create(
            influencer_id=influencer_id,
            cohort_id=x["cohort_id"],
            month=month_date,
            commission_type=TeacherInfluencerCommission.CommissionType.USAGE,
            currency_id=x["currency_id"],
        )
        inst.amount_paid = float(x["total_amount"] or 0)
        inst.num_users = int(x["users"] or 0)
        inst.save()

    matured = (
        TeacherInfluencerReferralCommission.objects.filter(
            teacher_influencer_id=influencer_id, status="MATURED", matured_at__gte=start_dt, matured_at__lt=end_dt
        )
        .values("currency_id")
        .annotate(total_amount=Sum("amount"), users=Count("buyer_id", distinct=True))
        .values("currency_id", "total_amount", "users")
    )

    for x in matured:
        inst, _ = TeacherInfluencerCommission.objects.get_or_create(
            influencer_id=influencer_id,
            cohort=None,
            month=month_date,
            commission_type=TeacherInfluencerCommission.CommissionType.REFERRAL,
            currency_id=x["currency_id"],
        )
        inst.amount_paid = float(x["total_amount"] or 0) * 0.5
        inst.num_users = int(x["users"] or 0)
        inst.save()

    currency_ids = list(
        TeacherInfluencerCommission.objects.filter(influencer_id=influencer_id, month=month_date)
        .values_list("currency_id", flat=True)
        .distinct()
    )

    for currency_id in currency_ids:
        total = (
            TeacherInfluencerCommission.objects.filter(
                influencer_id=influencer_id, month=month_date, currency_id=currency_id
            ).aggregate(total=Sum("amount_paid"))["total"]
            or 0.0
        )

        bill, _ = TeacherInfluencerPayment.objects.get_or_create(
            influencer_id=influencer_id, month=month_date, currency_id=currency_id, defaults={"total_amount": 0.0}
        )
        bill.total_amount = round(float(total), 2)
        bill.save()
        bill.commissions.set(
            TeacherInfluencerCommission.objects.filter(
                influencer_id=influencer_id, month=month_date, currency_id=currency_id
            )
        )
