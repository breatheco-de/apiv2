from __future__ import annotations

import io
from datetime import datetime

import pandas as pd
from capyc.core.i18n import translation
from capyc.rest_framework.exceptions import ValidationException
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Sum, Count, Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from breathecode.authenticate.actions import get_user_language
from breathecode.admissions.models import Cohort
from breathecode.commission.models import (
    GeekCreatorReferralCommission,
    GeekCreatorCommission,
    GeekCreatorPayment,
    UserUsageCommission,
)
import breathecode.commission.tasks as influencer_tasks
from breathecode.payments.models import Invoice
from .actions import (
    get_geek_creator_academy_ids,
    get_eligible_cohort_ids,
    filter_invoices_by_plans_and_cohorts,
    compute_usage_rows_and_total,
)
from .serializers import (
    CommissionReportResponseSerializer,
    AsyncCommissionResponseSerializer,
    GeekCreatorPaymentSerializer,
    GeekCreatorCommissionSerializer,
    UserUsageCommissionSerializer,
    GeekCreatorReferralCommissionSerializer,
)
from breathecode.utils.decorators import capable_of
from breathecode.utils import HeaderLimitOffsetPagination


class InfluencerPayoutReportView(APIView):
    """CSV report of referral (matured and pending) and usage for an influencer in a date range."""

    @capable_of("crud_commission")
    def get(self, request, academy_id=None, extension=None):
        lang = get_user_language(request)
        creator_id = request.GET.get("creator_id")
        month_str = request.GET.get("month")
        async_param = request.GET.get("async")
        include_plans = request.GET.get("include_plans")
        exclude_plans = request.GET.get("exclude_plans")
        is_async_requested = str(async_param).lower() in ("1", "true", "yes")
        is_preview = request.GET.get("preview", "").lower() in ("1", "true", "yes")

        if not creator_id:
            raise ValidationException(
                translation(lang, en="Missing creator_id", es="Falta creator_id", slug="missing-creator-id"),
                code=400,
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

        try:
            influencer = User.objects.get(id=int(creator_id))
        except Exception:
            raise ValidationException(
                translation(lang, en="Creator not found", es="Creator no encontrado", slug="creator-not-found"),
                code=404,
            )

        # Calculate date range
        tz = timezone.get_current_timezone()
        start_dt = datetime(year, mon, 1, 0, 0, 0, tzinfo=tz)
        next_year = year + (mon // 12)
        next_mon = 1 if mon == 12 else mon + 1
        end_dt = datetime(next_year if mon == 12 else year, next_mon, 1, 0, 0, 0, tzinfo=tz)
        month_date = start_dt.date().replace(day=1)
        current_time = timezone.now()

        if not is_preview:
            current_month = current_time.date().replace(day=1)
            if mon == 12:
                next_month_year = year + 1
                next_month = 1
            else:
                next_month_year = year
                next_month = mon + 1

            if current_month <= datetime(next_month_year, next_month, 1).date():
                raise ValidationException(
                    translation(
                        lang,
                        en=f"Cannot create commission report for {year}-{mon:02d}. Reports are only available after the next month ends "
                        f"to ensure all referrals have matured. Use ?preview=true to see current status.",
                        es=f"No se puede crear el reporte de comisiones para {year}-{mon:02d}. Los reportes solo están disponibles después de que termine el mes siguiente "
                        f"para asegurar que todos los referrals hayan madurado. Use ?preview=true para ver el estado actual.",
                        slug="month-not-complete",
                    ),
                    code=400,
                )

        if is_async_requested:
            return self._handle_async_mode(influencer, year, mon, start_dt, end_dt, include_plans, exclude_plans)

        referral_data = self._get_referral_data(influencer, start_dt, end_dt, current_time)
        usage_data = self._get_usage_data(
            influencer, start_dt, end_dt, include_plans, exclude_plans, referral_data["user_ids"]
        )

        # Process usage commissions
        usage_rows, usage_total, user_breakdown_by_cohort = (
            usage_data["rows"],
            usage_data["total"],
            usage_data["breakdown"],
        )

        # Create/update UserUsageCommission records
        self._create_usage_commissions(
            influencer, usage_rows, user_breakdown_by_cohort, start_dt, usage_data["currency_map"]
        )

        # Build TeacherInfluencerCommission records
        usage_commissions = self._build_usage_teacher_commissions(influencer, month_date)
        referral_commissions = self._build_referral_teacher_commissions(
            influencer, month_date, referral_data["effective_ids"]
        )

        # Create TeacherInfluencerPayment records
        self._create_teacher_payments(influencer, month_date, usage_commissions, referral_commissions, is_preview)

        # Generate CSV data
        all_rows = self._generate_csv_rows(
            usage_rows, referral_data["matured_referrals"], referral_data["effective_ids"], start_dt
        )
        matured_total = sum(x["commission_amount"] for x in all_rows if x["type"] == "referral" and x["is_effective"])

        # Handle CSV extension like TechnologyView handles .txt
        if extension == "csv":
            df = pd.DataFrame(all_rows)
            buffer = io.StringIO()
            df.to_csv(buffer, index=False)
            buffer.seek(0)

            response = HttpResponse(buffer.getvalue(), content_type="text/csv")
            response["Content-Disposition"] = (
                f'attachment; filename="commission_report_{influencer.email}_{year}_{mon:02d}.csv"'
            )
            return response

        response_data = {
            "influencer": influencer.email,
            "month": f"{year}-{mon:02d}",
            "matured_referral_total": round(matured_total, 2),
            "usage_total": round(usage_total, 2),
        }

        if is_preview:
            response_data["is_preview"] = True
            response_data["warning"] = "This is a preview. The month is not complete and amounts may change."

        serializer = CommissionReportResponseSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)

    def _handle_async_mode(
        self,
        influencer: User,
        year: int,
        mon: int,
        start_dt: datetime,
        end_dt: datetime,
        include_plans: str,
        exclude_plans: str,
    ) -> Response:
        """Handle async mode by scheduling tasks."""
        # Get usage invoices for scheduling
        invoices_in_range = Invoice.objects.filter(
            status=Invoice.Status.FULFILLED,
            amount__gt=0,
            refunded_at__isnull=True,
            paid_at__gte=start_dt,
            paid_at__lt=end_dt,
        ).select_related("currency")

        # Get referral user IDs to exclude
        referral_user_ids = set(
            GeekCreatorReferralCommission.objects.filter(
                geek_creator=influencer, created_at__gte=start_dt, created_at__lt=end_dt
            ).values_list("buyer_id", flat=True)
        )

        # Filter invoices and get eligible cohorts
        usage_invoices = invoices_in_range.exclude(user_id__in=referral_user_ids)
        influencer_academy_ids = get_geek_creator_academy_ids(influencer)
        eligible_cohort_ids = (
            get_eligible_cohort_ids(influencer, influencer_academy_ids) if influencer_academy_ids else set()
        )

        usage_invoices = filter_invoices_by_plans_and_cohorts(
            usage_invoices, include_plans, exclude_plans, eligible_cohort_ids
        )

        # Get candidate user IDs for reporting
        candidate_user_ids = set(usage_invoices.values_list("user_id", flat=True).distinct())

        # Schedule batch processing instead of individual tasks
        influencer_tasks.build_commissions_for_month.delay(influencer.id, year, mon)

        response_data = {
            "influencer": influencer.email,
            "month": f"{year}-{mon:02d}",
            "scheduled_user_engagements": len(candidate_user_ids),
            "scheduled_commissions": True,
            "mode": "async",
        }

        serializer = AsyncCommissionResponseSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=202)

    def _get_referral_data(
        self, influencer: User, start_dt: datetime, end_dt: datetime, current_time: datetime
    ) -> dict:
        """Get all referral"""
        referrals_created = GeekCreatorReferralCommission.objects.filter(
            geek_creator=influencer, created_at__gte=start_dt, created_at__lt=end_dt
        ).select_related("invoice", "currency", "buyer")

        referrals_without_refunds = [r for r in referrals_created if not r.invoice.refunded_at]
        effective_referrals = [r for r in referrals_without_refunds if current_time >= r.available_at]

        return {
            "matured_referrals": referrals_created,
            "effective_referrals": effective_referrals,
            "effective_ids": {r.id for r in effective_referrals},
            "user_ids": {r.buyer_id for r in referrals_created},
        }

    def _get_usage_data(
        self,
        influencer: User,
        start_dt: datetime,
        end_dt: datetime,
        include_plans: str,
        exclude_plans: str,
        referral_user_ids: set,
    ) -> dict:
        """Get usage data"""
        invoices_in_range = (
            Invoice.objects.filter(
                status=Invoice.Status.FULFILLED,
                amount__gt=0,
                refunded_at__isnull=True,
                paid_at__gte=start_dt,
                paid_at__lt=end_dt,
            )
            .exclude(user_id__in=referral_user_ids)
            .select_related("bag", "currency", "academy", "user")
        )

        # Get eligible cohorts
        influencer_academy_ids = get_geek_creator_academy_ids(influencer)
        if not influencer_academy_ids:
            raise ValidationException(
                translation(
                    "en",
                    en="This user is not an active geek creator in any academy",
                    es="Este usuario no es un geek creator activo en ninguna academia",
                    slug="not-geek-creator",
                ),
                code=400,
            )

        eligible_cohort_ids = get_eligible_cohort_ids(influencer, influencer_academy_ids)

        # Filter invoices by plans and cohorts
        usage_invoices = filter_invoices_by_plans_and_cohorts(
            invoices_in_range, include_plans, exclude_plans, eligible_cohort_ids
        )

        # Compute usage data
        usage_rows, usage_total, user_breakdown_by_cohort = compute_usage_rows_and_total(
            influencer, start_dt, end_dt, usage_invoices, eligible_cohort_ids
        )

        # Create currency map
        currency_map = {inv.currency_id: inv.currency for inv in usage_invoices}

        return {
            "rows": usage_rows,
            "total": usage_total,
            "breakdown": user_breakdown_by_cohort,
            "currency_map": currency_map,
            "invoices": usage_invoices,
        }

    def _create_usage_commissions(
        self, influencer: User, usage_rows: list, user_breakdown_by_cohort: dict, start_dt: datetime, currency_map: dict
    ) -> None:
        """Create or update UserUsageCommission records."""
        cohort_ids = {row["cohort_id"] for row in usage_rows}
        cohort_academy_map = {
            cohort["id"]: cohort["academy_id"]
            for cohort in Cohort.objects.filter(id__in=cohort_ids).values("id", "academy_id")
        }

        with transaction.atomic():
            for row in usage_rows:
                uid = row["user_id"]
                cid = row["cohort_id"]
                currency_code = row["currency"]
                currency_obj = next((c for c in currency_map.values() if c.code == currency_code), None)
                if not currency_obj:
                    continue

                user_breakdown = user_breakdown_by_cohort.get(uid, {})
                academy_id = cohort_academy_map.get(cid)

                obj, created = UserUsageCommission.objects.get_or_create(
                    influencer=influencer,
                    user_id=uid,
                    cohort_id=cid,
                    month=start_dt.date().replace(day=1),
                    currency=currency_obj,
                    defaults={
                        "academy_id": academy_id,
                        "user_total_points": float(row["total_points"]),
                        "cohort_points": float(row["cohort_points"]),
                        "paid_amount": float(row["paid_amount"]),
                        "commission_amount": float(row["commission"]),
                        "details": {"breakdown": user_breakdown},
                    },
                )

                if not created:
                    current_total = float(row["total_points"])
                    current_paid = float(row["paid_amount"])

                    if abs(obj.user_total_points - current_total) > 0.01 or abs(obj.paid_amount - current_paid) > 0.01:
                        obj.user_total_points = current_total
                        obj.cohort_points = float(row["cohort_points"])
                        obj.paid_amount = current_paid
                        obj.commission_amount = float(row["commission"])
                        obj.details = {"breakdown": user_breakdown}
                        obj.save()

    def _build_usage_teacher_commissions(self, influencer: User, month_date: datetime) -> list:
        """Build TeacherInfluencerCommission records for usage."""
        usage_agg = (
            UserUsageCommission.objects.filter(influencer=influencer, month=month_date)
            .values("cohort_id", "currency_id")
            .annotate(total_amount=Sum("commission_amount"), users=Count("id"))
        )

        usage_commissions = []
        for x in usage_agg:
            inst, _ = GeekCreatorCommission.objects.get_or_create(
                influencer=influencer,
                cohort_id=x["cohort_id"],
                month=month_date,
                commission_type=GeekCreatorCommission.CommissionType.USAGE,
                currency_id=x["currency_id"],
            )
            inst.amount_paid = float(x["total_amount"] or 0)
            inst.num_users = int(x["users"] or 0)
            inst.save()
            usage_commissions.append(inst)

            usage_records = UserUsageCommission.objects.filter(
                influencer=influencer, cohort_id=x["cohort_id"], month=month_date, currency_id=x["currency_id"]
            )
            inst.usage_commissions.set(usage_records)

        return usage_commissions

    def _build_referral_teacher_commissions(
        self, influencer: User, month_date: datetime, effective_referral_ids: set
    ) -> list:
        """Build TeacherInfluencerCommission records for referrals."""
        matured = (
            GeekCreatorReferralCommission.objects.filter(id__in=effective_referral_ids)
            .values("currency_id")
            .annotate(total_amount=Sum("amount"), users=Count("buyer_id", distinct=True))
            .values("currency_id", "total_amount", "users")
        )

        referral_commissions = []
        for x in matured:
            inst, _ = GeekCreatorCommission.objects.get_or_create(
                influencer=influencer,
                cohort=None,
                month=month_date,
                commission_type=GeekCreatorCommission.CommissionType.REFERRAL,
                currency_id=x["currency_id"],
            )
            inst.amount_paid = float(x["total_amount"] or 0)
            inst.num_users = int(x["users"] or 0)
            inst.details = {
                "invoices": list(
                    GeekCreatorReferralCommission.objects.filter(
                        id__in=effective_referral_ids, currency_id=x["currency_id"]
                    ).values_list("invoice_id", flat=True)
                )
            }
            inst.save()
            referral_commissions.append(inst)

            referral_records = GeekCreatorReferralCommission.objects.filter(
                id__in=effective_referral_ids, currency_id=x["currency_id"]
            )
            inst.referral_commissions.set(referral_records)

        return referral_commissions

    def _create_teacher_payments(
        self,
        influencer: User,
        month_date: datetime,
        usage_commissions: list,
        referral_commissions: list,
        is_preview: bool = False,
    ) -> list:
        """Create TeacherInfluencerPayment records."""
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

            if is_preview:
                default_status = GeekCreatorPayment.Status.PREVIEW
                default_status_text = "This is a preview. The month is not complete and amounts may change. This is why this payment cannot change status."
            else:
                default_status = GeekCreatorPayment.Status.PENDING
                default_status_text = None

            bill, created = GeekCreatorPayment.objects.get_or_create(
                influencer=influencer,
                month=month_date,
                currency_id=currency_id,
                defaults={"total_amount": 0.0, "status": default_status, "status_text": default_status_text},
            )

            if not created and is_preview:
                bill.status = GeekCreatorPayment.Status.PREVIEW
                bill.status_text = "This is a preview. The month is not complete and amounts may change. This is why this payment cannot change status."

            bill.total_amount = round(total, 2)
            bill.save()

            bill.commissions.set(
                GeekCreatorCommission.objects.filter(influencer=influencer, month=month_date, currency_id=currency_id)
            )
            bills.append({"currency_id": currency_id, "total": bill.total_amount})

        return bills

    def _generate_csv_rows(
        self, usage_rows: list, matured_referrals: list, effective_referral_ids: set, start_dt: datetime
    ) -> list:
        """Generate CSV rows for both usage and referral commissions."""
        all_rows = []

        # Add usage commission rows
        for row in usage_rows:
            all_rows.append(
                {
                    "type": "usage",
                    "invoice_id": "",
                    "user_id": row["user_id"],
                    "cohort_id": row["cohort_id"],
                    "currency": row["currency"],
                    "status": "PENDING",
                    "created_at": start_dt.date().replace(day=1),
                    "available_at": start_dt.date().replace(day=1),
                    "is_effective": True,
                    "total_points": row["total_points"],
                    "cohort_points": row["cohort_points"],
                    "paid_amount": row["paid_amount"],
                    "commission_amount": row["commission"],
                }
            )

        # Add referral commission rows
        for r in matured_referrals:
            all_rows.append(
                {
                    "type": "referral",
                    "invoice_id": r.invoice_id,
                    "user_id": r.buyer_id,
                    "cohort_id": "",
                    "currency": r.currency.code,
                    "status": r.status,
                    "created_at": r.created_at,
                    "available_at": r.available_at,
                    "is_effective": r.id in effective_referral_ids,
                    "total_points": "",
                    "cohort_points": "",
                    "paid_amount": r.invoice.amount if r.invoice else "",
                    "commission_amount": r.amount,
                }
            )

        return all_rows


class GeekCreatorPaymentView(APIView, HeaderLimitOffsetPagination):
    """Administrative view for managing GeekCreatorPayment records."""

    @capable_of("crud_commission")
    def get(self, request, academy_id=None):
        """List payments with filters."""
        lang = get_user_language(request)

        queryset = GeekCreatorPayment.objects.filter(
            Q(commissions__cohort__academy__id=academy_id)
            | Q(commissions__referral_commissions__academy__id=academy_id)
        ).distinct()

        lookup = {}

        if "creator_id" in request.GET:
            try:
                lookup["influencer_id"] = int(request.GET.get("creator_id"))
            except ValueError:
                raise ValidationException(
                    translation(lang, en="Invalid creator_id", es="creator_id inválido", slug="invalid-creator-id"),
                    code=400,
                )

        if "status" in request.GET:
            status_param = request.GET.get("status")
            status_list = [s.strip().upper() for s in status_param.split(",")]
            valid_statuses = [choice[0] for choice in GeekCreatorPayment.Status.choices]

            invalid_statuses = [s for s in status_list if s not in valid_statuses]
            if invalid_statuses:
                raise ValidationException(
                    translation(
                        lang,
                        en=f"Invalid statuses: {', '.join(invalid_statuses)}",
                        es=f"Estados inválidos: {', '.join(invalid_statuses)}",
                        slug="invalid-statuses",
                    ),
                    code=400,
                )
            lookup["status__in"] = status_list

        if "month" in request.GET:
            try:
                month = request.GET.get("month")
                year, mon = month.split("-")
                month_date = datetime(int(year), int(mon), 1).date()
                lookup["month"] = month_date
            except (ValueError, TypeError):
                raise ValidationException(
                    translation(
                        lang,
                        en="Invalid month format (YYYY-MM)",
                        es="Formato de mes inválido (YYYY-MM)",
                        slug="invalid-month-format",
                    ),
                    code=400,
                )

        if "currency_id" in request.GET:
            try:
                lookup["currency_id"] = int(request.GET.get("currency_id"))
            except ValueError:
                raise ValidationException(
                    translation(lang, en="Invalid currency_id", es="currency_id inválido", slug="invalid-currency-id"),
                    code=400,
                )

        queryset = queryset.filter(**lookup)

        page = self.paginate_queryset(queryset, request)
        payment_data = [GeekCreatorPaymentSerializer(payment).data for payment in page]

        if self.is_paginate(request):
            return self.get_paginated_response(payment_data)
        else:
            return Response(payment_data)

    @capable_of("crud_commission")
    def patch(self, request, payment_id, academy_id=None):
        """Update payment status."""
        lang = get_user_language(request)

        try:
            payment = GeekCreatorPayment.objects.get(id=payment_id)
        except GeekCreatorPayment.DoesNotExist:
            raise ValidationException(
                translation(lang, en="Payment not found", es="Pago no encontrado", slug="payment-not-found"),
                code=404,
            )

        new_status = request.data.get("status")
        if not new_status:
            raise ValidationException(
                translation(lang, en="Missing status", es="Falta status", slug="missing-status"),
                code=400,
            )

        if new_status not in dict(GeekCreatorPayment.Status.choices):
            raise ValidationException(
                translation(lang, en="Invalid status", es="Estado inválido", slug="invalid-status"),
                code=400,
            )

        if payment.status == GeekCreatorPayment.Status.PREVIEW:
            raise ValidationException(
                translation(
                    lang,
                    en="Cannot change status of PREVIEW payments. Preview payments are for informational purposes only.",
                    es="No se puede cambiar el estado de los pagos PREVIEW. Los pagos en preview son solo para fines informativos.",
                    slug="preview-status-change-not-allowed",
                ),
                code=400,
            )

        payment.status = new_status

        if new_status == "PAID" and payment.payment_date is None:
            payment.payment_date = timezone.now()

            referral_commissions = GeekCreatorReferralCommission.objects.filter(
                aggregated_referral_commissions__in=payment.commissions.filter(commission_type="REFERRAL")
            ).distinct()

            if referral_commissions.exists():
                referral_commissions.update(status="PAID")

        payment.save()

        return Response(GeekCreatorPaymentSerializer(payment).data)


class GeekCreatorCommissionView(APIView, HeaderLimitOffsetPagination):
    """Administrative view for managing GeekCreatorCommission records."""

    @capable_of("crud_commission")
    def get(self, request, academy_id=None):
        """List commissions with filters."""
        lang = get_user_language(request)

        queryset = GeekCreatorCommission.objects.filter(
            Q(cohort__academy__id=academy_id) | Q(commission_type=GeekCreatorCommission.CommissionType.REFERRAL)
        ).distinct()
        lookup = {}

        if "creator_id" in request.GET:
            try:
                lookup["influencer_id"] = int(request.GET.get("creator_id"))
            except ValueError:
                raise ValidationException(
                    translation(lang, en="Invalid creator_id", es="creator_id inválido", slug="invalid-creator-id"),
                    code=400,
                )

        if "commission_type" in request.GET:
            commission_type = request.GET.get("commission_type")
            if commission_type not in dict(GeekCreatorCommission.CommissionType.choices):
                raise ValidationException(
                    translation(
                        lang,
                        en="Invalid commission_type",
                        es="Tipo de comisión inválido",
                        slug="invalid-commission-type",
                    ),
                    code=400,
                )
            lookup["commission_type"] = commission_type

        if "month" in request.GET:
            try:
                month = request.GET.get("month")
                year, mon = month.split("-")
                month_date = datetime(int(year), int(mon), 1).date()
                lookup["month"] = month_date
            except (ValueError, TypeError):
                raise ValidationException(
                    translation(
                        lang,
                        en="Invalid month format (YYYY-MM)",
                        es="Formato de mes inválido (YYYY-MM)",
                        slug="invalid-month-format",
                    ),
                    code=400,
                )

        if "cohort_id" in request.GET:
            try:
                lookup["cohort_id"] = int(request.GET.get("cohort_id"))
            except ValueError:
                raise ValidationException(
                    translation(lang, en="Invalid cohort_id", es="cohort_id inválido", slug="invalid-cohort-id"),
                    code=400,
                )

        if "currency_id" in request.GET:
            try:
                lookup["currency_id"] = int(request.GET.get("currency_id"))
            except ValueError:
                raise ValidationException(
                    translation(lang, en="Invalid currency_id", es="currency_id inválido", slug="invalid-currency-id"),
                    code=400,
                )

        if "payment_id" in request.GET:
            try:
                payment_id = int(request.GET.get("payment_id"))
                payment = GeekCreatorPayment.objects.get(id=payment_id)
                queryset = payment.commissions.all()
            except GeekCreatorPayment.DoesNotExist:
                raise ValidationException(
                    translation(lang, en="Payment not found", es="Pago no encontrado", slug="payment-not-found"),
                    code=404,
                )
            except ValueError:
                raise ValidationException(
                    translation(lang, en="Invalid payment_id", es="payment_id inválido", slug="invalid-payment-id"),
                    code=400,
                )

        queryset = queryset.filter(**lookup)

        page = self.paginate_queryset(queryset, request)
        commission_data = [GeekCreatorCommissionSerializer(commission).data for commission in page]

        if self.is_paginate(request):
            return self.get_paginated_response(commission_data)
        else:
            return Response(commission_data)


class UserUsageCommissionView(APIView, HeaderLimitOffsetPagination):
    """Administrative view for managing UserUsageCommission records."""

    @capable_of("crud_commission")
    def get(self, request, academy_id=None):
        """List usage commissions with filters."""
        lang = get_user_language(request)

        queryset = UserUsageCommission.objects.filter(academy__id=academy_id)
        lookup = {}

        if "creator_id" in request.GET:
            try:
                lookup["influencer_id"] = int(request.GET.get("creator_id"))
            except ValueError:
                raise ValidationException(
                    translation(lang, en="Invalid creator_id", es="creator_id inválido", slug="invalid-creator-id"),
                    code=400,
                )

        if "user_id" in request.GET:
            try:
                lookup["user_id"] = int(request.GET.get("user_id"))
            except ValueError:
                raise ValidationException(
                    translation(lang, en="Invalid user_id", es="user_id inválido", slug="invalid-user-id"),
                    code=400,
                )

        if "cohort_id" in request.GET:
            try:
                lookup["cohort_id"] = int(request.GET.get("cohort_id"))
            except ValueError:
                raise ValidationException(
                    translation(lang, en="Invalid cohort_id", es="cohort_id inválido", slug="invalid-cohort-id"),
                    code=400,
                )

        if "month" in request.GET:
            try:
                month = request.GET.get("month")
                year, mon = month.split("-")
                month_date = datetime(int(year), int(mon), 1).date()
                lookup["month"] = month_date
            except (ValueError, TypeError):
                raise ValidationException(
                    translation(
                        lang,
                        en="Invalid month format (YYYY-MM)",
                        es="Formato de mes inválido (YYYY-MM)",
                        slug="invalid-month-format",
                    ),
                    code=400,
                )

        if "currency_id" in request.GET:
            try:
                lookup["currency_id"] = int(request.GET.get("currency_id"))
            except ValueError:
                raise ValidationException(
                    translation(lang, en="Invalid currency_id", es="currency_id inválido", slug="invalid-currency-id"),
                    code=400,
                )

        if "commission_id" in request.GET:
            try:
                commission_id = int(request.GET.get("commission_id"))
                queryset = queryset.filter(aggregated_usage_commissions__id=commission_id)
            except ValueError:
                raise ValidationException(
                    translation(
                        lang, en="Invalid commission_id", es="commission_id inválido", slug="invalid-commission-id"
                    ),
                    code=400,
                )

        queryset = queryset.filter(**lookup)

        page = self.paginate_queryset(queryset, request)
        commission_data = [UserUsageCommissionSerializer(commission).data for commission in page]

        if self.is_paginate(request):
            return self.get_paginated_response(commission_data)
        else:
            return Response(commission_data)


class GeekCreatorReferralCommissionView(APIView, HeaderLimitOffsetPagination):
    """Administrative view for managing GeekCreatorReferralCommission records."""

    @capable_of("crud_commission")
    def get(self, request, academy_id=None):
        """List referral commissions with filters."""
        lang = get_user_language(request)

        queryset = GeekCreatorReferralCommission.objects.filter(academy__id=academy_id)
        lookup = {}

        if "geek_creator_id" in request.GET:
            try:
                lookup["geek_creator_id"] = int(request.GET.get("geek_creator_id"))
            except ValueError:
                raise ValidationException(
                    translation(
                        lang,
                        en="Invalid geek_creator_id",
                        es="geek_creator_id inválido",
                        slug="invalid-geek-creator-id",
                    ),
                    code=400,
                )

        if "buyer_id" in request.GET:
            try:
                lookup["buyer_id"] = int(request.GET.get("buyer_id"))
            except ValueError:
                raise ValidationException(
                    translation(lang, en="Invalid buyer_id", es="buyer_id inválido", slug="invalid-buyer-id"),
                    code=400,
                )

        if "invoice_id" in request.GET:
            try:
                lookup["invoice_id"] = int(request.GET.get("invoice_id"))
            except ValueError:
                raise ValidationException(
                    translation(lang, en="Invalid invoice_id", es="invoice_id inválido", slug="invalid-invoice-id"),
                    code=400,
                )

        if "status" in request.GET:
            status = request.GET.get("status")
            if status not in dict(GeekCreatorReferralCommission.Status.choices):
                raise ValidationException(
                    translation(lang, en="Invalid status", es="Estado inválido", slug="invalid-status"),
                    code=400,
                )
            lookup["status"] = status

        if "currency_id" in request.GET:
            try:
                lookup["currency_id"] = int(request.GET.get("currency_id"))
            except ValueError:
                raise ValidationException(
                    translation(lang, en="Invalid currency_id", es="currency_id inválido", slug="invalid-currency-id"),
                    code=400,
                )

        if "commission_id" in request.GET:
            try:
                commission_id = int(request.GET.get("commission_id"))
                # Filter referral commissions that belong to the specified aggregated commission
                queryset = queryset.filter(aggregated_referral_commissions__id=commission_id)
            except ValueError:
                raise ValidationException(
                    translation(
                        lang, en="Invalid commission_id", es="commission_id inválido", slug="invalid-commission-id"
                    ),
                    code=400,
                )

        queryset = queryset.filter(**lookup)

        page = self.paginate_queryset(queryset, request)
        commission_data = [GeekCreatorReferralCommissionSerializer(commission).data for commission in page]

        if self.is_paginate(request):
            return self.get_paginated_response(commission_data)
        else:
            return Response(commission_data)

    @capable_of("crud_commission")
    def patch(self, request, commission_id, academy_id=None):
        """Update referral commission status or available_at date."""
        lang = get_user_language(request)

        try:
            commission = GeekCreatorReferralCommission.objects.get(id=commission_id)
        except GeekCreatorReferralCommission.DoesNotExist:
            raise ValidationException(
                translation(
                    lang,
                    en="Referral commission not found",
                    es="Comisión de referral no encontrada",
                    slug="referral-commission-not-found",
                ),
                code=404,
            )

        new_status = request.data.get("status")
        new_available_at = request.data.get("available_at")

        if new_status:
            if new_status not in dict(GeekCreatorReferralCommission.Status.choices):
                raise ValidationException(
                    translation(lang, en="Invalid status", es="Estado inválido", slug="invalid-status"),
                    code=400,
                )
            commission.status = new_status

        if new_available_at:
            try:
                commission.available_at = datetime.fromisoformat(new_available_at.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                raise ValidationException(
                    translation(
                        lang,
                        en="Invalid available_at format",
                        es="Formato de available_at inválido",
                        slug="invalid-available-at-format",
                    ),
                    code=400,
                )

        commission.save()

        return Response(
            {
                "id": commission.id,
                "status": commission.status,
                "available_at": commission.available_at.isoformat() if commission.available_at else None,
                "is_matured": commission.is_matured,
                "updated_at": commission.updated_at.isoformat(),
            }
        )
