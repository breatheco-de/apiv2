from __future__ import annotations

import io
from datetime import datetime

import pandas as pd
from capyc.core.i18n import translation
from capyc.rest_framework.exceptions import ValidationException
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from breathecode.authenticate.actions import get_user_language
from breathecode.influencer.models import (
    TeacherInfluencerReferralCommission,
    TeacherInfluencerCommission,
    TeacherInfluencerPayment,
)
import breathecode.influencer.tasks as influencer_tasks
from breathecode.payments.models import Invoice
from breathecode.admissions.models import Cohort
from .actions import (
    get_teacher_influencer_academy_ids,
    get_eligible_cohort_ids,
    compute_usage_rows_and_total,
)


class InfluencerPayoutReportView(APIView):
    """CSV report of referral (matured and pending) and usage for an influencer in a date range."""

    def get(self, request):
        lang = get_user_language(request)

        influencer_id = request.GET.get("influencer_id")
        month_str = request.GET.get("month")
        async_param = request.GET.get("async")
        is_async_requested = str(async_param).lower() in ("1", "true", "yes")

        if not influencer_id:
            raise ValidationException(
                translation(lang, en="Missing influencer_id", es="Falta influencer_id", slug="missing-influencer-id"),
                code=400,
            )

        try:
            influencer = User.objects.get(id=int(influencer_id))
        except Exception:
            raise ValidationException(
                translation(
                    lang, en="Influencer not found", es="Influencer no encontrado", slug="influencer-not-found"
                ),
                code=404,
            )

        if not month_str:
            raise ValidationException(
                translation(lang, en="Missing month (YYYY-MM)", es="Falta month (YYYY-MM)", slug="missing-month"),
                code=400,
            )

        try:
            year_s, mon_s = month_str.split("-")
            year, mon = int(year_s), int(mon_s)
            if not (1 <= mon <= 12):
                raise ValueError()
        except Exception:
            raise ValidationException(
                translation(
                    lang,
                    en="Invalid month format (YYYY-MM)",
                    es="Formato de month inválido (YYYY-MM)",
                    slug="invalid-month",
                ),
                code=400,
            )

        tz = timezone.get_current_timezone()
        start_dt = datetime(year, mon, 1, 0, 0, 0, tzinfo=tz)
        # next month
        next_year = year + (mon // 12)
        next_mon = 1 if mon == 12 else mon + 1
        end_dt = datetime(next_year if mon == 12 else year, next_mon, 1, 0, 0, 0, tzinfo=tz)

        all_referrals = TeacherInfluencerReferralCommission.objects.filter(
            teacher_influencer=influencer, created_at__gte=start_dt, created_at__lt=end_dt
        ).select_related("invoice", "currency")

        matured_referrals = TeacherInfluencerReferralCommission.objects.filter(
            teacher_influencer=influencer, status="MATURED", matured_at__gte=start_dt, matured_at__lt=end_dt
        ).select_related("invoice", "currency")

        invoices_in_range = Invoice.objects.filter(
            status=Invoice.Status.FULFILLED, refunded_at__isnull=True, paid_at__gte=start_dt, paid_at__lt=end_dt
        ).select_related("bag", "currency", "academy", "user")

        users_with_referral = set(all_referrals.values_list("buyer_id", flat=True))

        # Exclude invoices that comes from referrals to avoid double counting
        usage_invoices = invoices_in_range.exclude(user_id__in=users_with_referral)

        influencer_academy_ids = get_teacher_influencer_academy_ids(influencer)
        if not influencer_academy_ids:
            raise ValidationException(
                translation(
                    lang,
                    en="This user is not an active teacher influencer in any academy",
                    es="Este usuario no es un teacher influencer activo en ninguna academia",
                    slug="not-teacher-influencer",
                ),
                code=400,
            )
        eligible_cohort_ids = get_eligible_cohort_ids(influencer, influencer_academy_ids)

        if is_async_requested:
            scheduled_users = 0
            candidate_user_ids = list(usage_invoices.values_list("user_id", flat=True).distinct())
            for candidate_user_id in candidate_user_ids:
                influencer_tasks.build_user_engagement_for_user_month.delay(influencer.id, candidate_user_id, year, mon)
                scheduled_users += 1

            # schedule commissions build with a short delay to allow user tasks to finish
            influencer_tasks.build_commissions_for_month.apply_async(args=[influencer.id, year, mon], countdown=120)

            return Response(
                {
                    "influencer": influencer.email,
                    "month": f"{year}-{mon:02d}",
                    "scheduled_user_engagements": scheduled_users,
                    "scheduled_commissions": True,
                    "mode": "async",
                },
                status=202,
            )

        usage_rows, usage_total, breakdown_by_kind = compute_usage_rows_and_total(
            influencer, start_dt, end_dt, usage_invoices, eligible_cohort_ids
        )

        # Persist UserCohortEngagement rows for auditability
        from django.db import transaction
        from .models import UserCohortEngagement
        from django.db.models import Sum

        # map currency ids to code
        currency_map = {inv.currency_id: inv.currency for inv in usage_invoices}

        # sum paid per user/currency in range
        paid_by_user_currency = usage_invoices.values("user_id", "currency_id").annotate(total_amount=Sum("amount"))
        paid_map = {}
        for x in paid_by_user_currency:
            paid_map[(x["user_id"], x["currency_id"])] = float(x["total_amount"] or 0)

        with transaction.atomic():
            for row in usage_rows:
                uid = row["user_id"]
                cid = row["cohort_id"]
                currency_code = row["currency"]
                currency_obj = next((c for c in currency_map.values() if c.code == currency_code), None)
                if not currency_obj:
                    continue

                # compute details breakdown for this user/cohort
                kind_breakdown = breakdown_by_kind.get((uid, cid), {})

                obj, _ = UserCohortEngagement.objects.update_or_create(
                    influencer=influencer,
                    user_id=uid,
                    cohort_id=cid,
                    month=start_dt.date().replace(day=1),
                    currency=currency_obj,
                    defaults={
                        "academy_id": Cohort.objects.filter(id=cid).values_list("academy_id", flat=True).first(),
                        "user_total_points": float(row["total_points"]),
                        "cohort_points": float(row["cohort_points"]),
                        "paid_amount": float(row["paid_amount"]),
                        "commission_amount": float(row["commission"]),
                        "details": {"breakdown": kind_breakdown},
                    },
                )

        # Build TeacherInfluencerCommission (USAGE) from UserCohortEngagement
        from .models import UserCohortEngagement

        month_date = start_dt.date().replace(day=1)

        usage_commissions = []
        from django.db.models import Sum, Count

        usage_agg = (
            UserCohortEngagement.objects.filter(influencer=influencer, month=month_date)
            .values("cohort_id", "currency_id")
            .annotate(total_amount=Sum("commission_amount"), users=Count("id"))
        )

        for x in usage_agg:
            inst, _ = TeacherInfluencerCommission.objects.get_or_create(
                influencer=influencer,
                cohort_id=x["cohort_id"],
                month=month_date,
                commission_type=TeacherInfluencerCommission.CommissionType.USAGE,
                currency_id=x["currency_id"],
            )
            inst.amount_paid = float(x["total_amount"] or 0)
            inst.num_users = int(x["users"] or 0)
            inst.save()
            usage_commissions.append(inst)

        referral_commissions = []
        matured = (
            matured_referrals.values("currency_id")
            .annotate(total_amount=Sum("amount"), users=Count("buyer_id", distinct=True))
            .values("currency_id", "total_amount", "users")
        )

        for x in matured:
            inst, _ = TeacherInfluencerCommission.objects.get_or_create(
                influencer=influencer,
                cohort=None,
                month=month_date,
                commission_type=TeacherInfluencerCommission.CommissionType.REFERRAL,
                currency_id=x["currency_id"],
            )
            inst.amount_paid = float(x["total_amount"] or 0) * 0.5
            inst.num_users = int(x["users"] or 0)
            inst.details = {
                "invoices": list(
                    matured_referrals.filter(currency_id=x["currency_id"]).values_list("invoice_id", flat=True)
                )
            }
            inst.save()
            referral_commissions.append(inst)

        # Create or update TeacherInfluencerPayment (bill) per currency
        bills = []
        for currency_id in set(
            [c.currency_id for c in usage_commissions] + [c.currency_id for c in referral_commissions]
        ):
            total = 0.0
            for c in usage_commissions:
                if c.currency_id == currency_id:
                    total += c.amount_paid
            for c in referral_commissions:
                if c.currency_id == currency_id:
                    total += c.amount_paid

            bill, _ = TeacherInfluencerPayment.objects.get_or_create(
                influencer=influencer,
                month=month_date,
                currency_id=currency_id,
                defaults={"total_amount": 0.0},
            )
            bill.total_amount = round(total, 2)
            bill.save()
            # ensure m2m contains current commissions of this month/currency
            bill.commissions.set(
                TeacherInfluencerCommission.objects.filter(
                    influencer=influencer, month=month_date, currency_id=currency_id
                )
            )
            bills.append({"currency_id": currency_id, "total": bill.total_amount})

        referral_created_rows = [
            {
                "type": "referral_created",
                "invoice_id": r.invoice_id,
                "user_id": r.buyer_id,
                "amount": r.amount,
                "currency": r.currency.code,
                "status": r.status,
                "available_at": r.available_at,
            }
            for r in all_referrals
        ]

        referral_matured_rows = [
            {
                "type": "referral_matured",
                "invoice_id": r.invoice_id,
                "user_id": r.buyer_id,
                "amount": r.amount,
                "currency": r.currency.code,
                "status": r.status,
                "matured_at": r.matured_at,
            }
            for r in matured_referrals
        ]

        df = pd.DataFrame(referral_created_rows + referral_matured_rows + usage_rows)

        matured_total = sum(x["amount"] * 0.5 for x in referral_matured_rows)

        buffer = io.StringIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)

        return Response(
            {
                "influencer": influencer.email,
                "month": f"{year}-{mon:02d}",
                "matured_referral_total": round(matured_total, 2),
                "usage_total": round(usage_total, 2),
                "csv": buffer.getvalue(),
            }
        )
