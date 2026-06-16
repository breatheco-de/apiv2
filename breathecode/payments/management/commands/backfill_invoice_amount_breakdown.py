from dateutil.relativedelta import relativedelta
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from breathecode.payments.actions import _invoice_breakdown_has_line_items, calculate_invoice_breakdown
from breathecode.payments.models import Invoice, PlanFinancing


class Command(BaseCommand):
    help = "Backfill amount_breakdown for fulfilled invoices missing breakdown within a time window"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without making changes",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Number of invoices to process per batch (default: 100)",
        )
        parser.add_argument(
            "--years",
            type=float,
            default=1,
            help="Only process invoices paid within this many years (default: 1)",
        )
        parser.add_argument(
            "--academy-id",
            type=int,
            default=None,
            help="Only process invoices for this academy",
        )
        parser.add_argument(
            "--invoice-id",
            type=int,
            default=None,
            help="Process a single invoice by id",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        batch_size = options["batch_size"]
        years = options["years"]
        academy_id = options.get("academy_id")
        invoice_id = options.get("invoice_id")
        utc_now = timezone.now()
        paid_since = utc_now - relativedelta(years=years)

        invoices = (
            Invoice.objects.select_related("bag", "currency", "academy")
            .filter(
                status=Invoice.Status.FULFILLED,
                bag_id__isnull=False,
                paid_at__gte=paid_since,
                amount__gt=0,
            )
            .filter(Q(amount_breakdown__isnull=True) | Q(amount_breakdown={}))
            .order_by("id")
        )

        if academy_id:
            invoices = invoices.filter(academy_id=academy_id)

        if invoice_id:
            invoices = invoices.filter(id=invoice_id)

        total_count = invoices.count()
        if total_count == 0:
            self.stdout.write(self.style.SUCCESS("No invoices need amount_breakdown backfill"))
            return

        self.stdout.write(f"Found {total_count} invoice(s) to process (paid since {paid_since.isoformat()})")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be saved"))

        updated_count = 0
        skipped_count = 0
        error_count = 0
        errors = []

        for offset in range(0, total_count, batch_size):
            batch = list(invoices[offset : offset + batch_size])
            for invoice in batch:
                if _invoice_breakdown_has_line_items(invoice.amount_breakdown):
                    skipped_count += 1
                    continue

                bag = invoice.bag
                if not bag:
                    skipped_count += 1
                    continue

                how_many_installments = bag.how_many_installments or 0
                if how_many_installments <= 0:
                    plan_financing = PlanFinancing.objects.filter(invoices=invoice).first()
                    if plan_financing and plan_financing.how_many_installments:
                        how_many_installments = plan_financing.how_many_installments

                try:
                    breakdown = calculate_invoice_breakdown(
                        bag,
                        invoice,
                        lang="en",
                        chosen_period=bag.chosen_period,
                        how_many_installments=how_many_installments if how_many_installments > 0 else None,
                    )
                except Exception as e:
                    error_count += 1
                    errors.append((invoice.id, str(e)))
                    self.stdout.write(self.style.ERROR(f"Invoice {invoice.id}: {e}"))
                    continue

                if dry_run:
                    self.stdout.write(
                        f"Would update invoice {invoice.id} (bag {bag.id}, amount {invoice.amount})"
                    )
                    updated_count += 1
                    continue

                invoice.amount_breakdown = breakdown
                invoice.save(update_fields=["amount_breakdown"])
                updated_count += 1

        self.stdout.write("")
        self.stdout.write(f"Updated: {updated_count}")
        self.stdout.write(f"Skipped: {skipped_count}")
        self.stdout.write(f"Errors: {error_count}")
        if errors:
            self.stdout.write(self.style.ERROR("Failed invoice IDs:"))
            for inv_id, message in errors:
                self.stdout.write(f"  - {inv_id}: {message}")
