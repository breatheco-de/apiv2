from __future__ import annotations

import csv
from datetime import date, datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from breathecode.admissions.models import CohortUser
from breathecode.payments.models import Invoice


def parse_month(month_str: str) -> date:
    return datetime.strptime(month_str + "-01", "%Y-%m-%d").date()


class Command(BaseCommand):
    help = (
        "Export a CSV with 50% referral commissions for all users in a cohort for a given month. "
        "Assumes every user in the cohort is attributed to the influencer for that month."
    )

    def add_arguments(self, parser):
        parser.add_argument("--cohort-id", type=int, required=True)
        parser.add_argument("--month", type=str, required=True, help="Month in YYYY-MM format")
        parser.add_argument("--out", type=str, required=True, help="Output CSV path")
        parser.add_argument(
            "--plan-slug",
            action="append",
            dest="plan_slugs",
            default=None,
            help=("Plan slug to include (can be passed multiple times). If omitted, all invoices are considered."),
        )

    def handle(self, *args, **options):
        cohort_id: int = options["cohort_id"]
        month_str: str = options["month"]
        out_path: str = options["out"]

        month_date = parse_month(month_str)
        # Build timezone-aware bounds for the month
        tz = timezone.get_current_timezone()
        month_start = timezone.make_aware(datetime(month_date.year, month_date.month, 1), tz)
        if month_date.month == 12:
            month_end = timezone.make_aware(datetime(month_date.year + 1, 1, 1), tz)
        else:
            month_end = timezone.make_aware(datetime(month_date.year, month_date.month + 1, 1), tz)

        cohort_user_ids = CohortUser.objects.filter(cohort_id=cohort_id).values_list("user_id", flat=True)

        qs = (
            Invoice.objects.select_related("currency", "bag", "user")
            .prefetch_related("bag__plans")
            .filter(
                user_id__in=cohort_user_ids,
                status=Invoice.Status.FULFILLED,
                refunded_at__isnull=True,
                paid_at__gte=month_start,
                paid_at__lt=month_end,
            )
        )

        plan_slugs = options.get("plan_slugs")
        if plan_slugs:
            qs = qs.filter(bag__plans__slug__in=plan_slugs)

        invoices = qs.order_by("paid_at").distinct()

        fieldnames = [
            "cohort_id",
            "user_id",
            "user_email",
            "invoice_id",
            "paid_at",
            "amount",
            "currency",
            "bag_id",
            "plan_slugs",
            "commission_rate",
            "commission_amount",
            "effective",
            "effective_comment",
            # summary fields (filled only in summary rows)
            "summary",
            "summary_count",
            "summary_amount",
            "summary_commission",
        ]

        with open(out_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            now = timezone.now()

            # Accumulators
            eff_count = 0
            eff_amount_sum = 0.0
            eff_commission_sum = 0.0
            noeff_count = 0
            noeff_amount_sum = 0.0
            noeff_commission_sum = 0.0

            invoices = list(invoices)

            for inv in invoices:
                commission_rate = 0.5
                commission_amount = float(inv.amount) * commission_rate

                effective_date = inv.paid_at + timezone.timedelta(days=30)
                is_effective = now >= effective_date
                effective_comment = (
                    "Effective"
                    if is_effective
                    else f"Effective when the user completes month {effective_date.date().isoformat()}"
                )

                plans = sorted({p.slug for p in getattr(inv.bag, "plans", []).all()}) if inv.bag_id else []

                writer.writerow(
                    {
                        "cohort_id": cohort_id,
                        "user_id": inv.user_id,
                        "user_email": inv.user.email,
                        "invoice_id": inv.id,
                        "paid_at": inv.paid_at.isoformat(),
                        "amount": f"{inv.amount:.2f}",
                        "currency": inv.currency.code,
                        "bag_id": inv.bag_id,
                        "plan_slugs": ",".join(plans),
                        "commission_rate": commission_rate,
                        "commission_amount": f"{commission_amount:.2f}",
                        "effective": "yes" if is_effective else "no",
                        "effective_comment": effective_comment,
                        "summary": "",
                        "summary_count": "",
                        "summary_amount": "",
                        "summary_commission": "",
                    }
                )

                if is_effective:
                    eff_count += 1
                    eff_amount_sum += float(inv.amount)
                    eff_commission_sum += commission_amount
                else:
                    noeff_count += 1
                    noeff_amount_sum += float(inv.amount)
                    noeff_commission_sum += commission_amount

            # Summary rows
            writer.writerow(
                {
                    "cohort_id": "",
                    "user_id": "",
                    "user_email": "",
                    "invoice_id": "",
                    "paid_at": "",
                    "amount": "",
                    "currency": "",
                    "bag_id": "",
                    "plan_slugs": "",
                    "commission_rate": "",
                    "commission_amount": "",
                    "effective": "",
                    "effective_comment": "",
                    "summary": "effective",
                    "summary_count": eff_count,
                    "summary_amount": f"{eff_amount_sum:.2f}",
                    "summary_commission": f"{eff_commission_sum:.2f}",
                }
            )

            writer.writerow(
                {
                    "cohort_id": "",
                    "user_id": "",
                    "user_email": "",
                    "invoice_id": "",
                    "paid_at": "",
                    "amount": "",
                    "currency": "",
                    "bag_id": "",
                    "plan_slugs": "",
                    "commission_rate": "",
                    "commission_amount": "",
                    "effective": "",
                    "effective_comment": "",
                    "summary": "not_effective",
                    "summary_count": noeff_count,
                    "summary_amount": f"{noeff_amount_sum:.2f}",
                    "summary_commission": f"{noeff_commission_sum:.2f}",
                }
            )

        self.stdout.write(self.style.SUCCESS(f"Exported {len(invoices)} rows to {out_path}"))
