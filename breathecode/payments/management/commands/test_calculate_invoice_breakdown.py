import json
import sys

from django.core.management.base import BaseCommand, CommandError

from breathecode.payments.actions import calculate_invoice_breakdown
from breathecode.payments.models import Invoice


class Command(BaseCommand):
    help = "Test calculate_invoice_breakdown function with a specific invoice"

    def add_arguments(self, parser):
        parser.add_argument(
            "invoice_id",
            type=int,
            help="ID of the invoice to calculate breakdown for",
        )
        parser.add_argument(
            "--bag-id",
            type=int,
            default=None,
            help="ID of the bag to use (optional, will use invoice.bag if not provided)",
        )
        parser.add_argument(
            "--lang",
            type=str,
            default="en",
            help="Language code for error messages (default: en)",
        )
        parser.add_argument(
            "--json-only",
            action="store_true",
            help="Output only the JSON breakdown without additional information",
        )

    def handle(self, *args, **options):
        invoice_id = options["invoice_id"]
        bag_id = options.get("bag_id")
        lang = options["lang"]
        json_only = options.get("json_only", False)

        try:
            # Use only() to exclude amount_breakdown in case migration hasn't been run yet
            invoice = (
                Invoice.objects.select_related("bag", "currency", "academy")
                .only(
                    "id",
                    "amount",
                    "currency",
                    "bag",
                    "academy",
                    "paid_at",
                    "status",
                    "user",
                )
                .get(id=invoice_id)
            )
        except Invoice.DoesNotExist:
            raise CommandError(f"Invoice with id {invoice_id} does not exist")

        if bag_id:
            from breathecode.payments.models import Bag

            try:
                bag = Bag.objects.get(id=bag_id)
            except Bag.DoesNotExist:
                raise CommandError(f"Bag with id {bag_id} does not exist")
        else:
            if not invoice.bag:
                raise CommandError(f"Invoice {invoice_id} does not have a bag associated")
            bag = invoice.bag

        if not json_only:
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(f"Invoice ID: {invoice.id}")
            self.stdout.write(f"Bag ID: {bag.id}")
            self.stdout.write(f"Invoice Amount: {invoice.amount} {invoice.currency.code if invoice.currency else 'N/A'}")
            self.stdout.write(f"Bag chosen_period: {bag.chosen_period}")
            self.stdout.write(f"Bag how_many_installments: {bag.how_many_installments}")
            self.stdout.write(f"{'='*60}\n")

        try:
            breakdown = calculate_invoice_breakdown(bag, invoice, lang)

            if json_only:
                # Output only JSON to stdout (useful for piping to other commands)
                self.stdout.write(json.dumps(breakdown, indent=2, ensure_ascii=False))
            else:
                self.stdout.write(self.style.SUCCESS("\n✓ Breakdown calculated successfully!\n"))
                self.stdout.write("Breakdown JSON:")
                self.stdout.write(json.dumps(breakdown, indent=2, ensure_ascii=False))

                # Calculate total from breakdown
                total_plans = sum(item["amount"] for item in breakdown.get("plans", {}).values())
                total_service_items = sum(item["amount"] for item in breakdown.get("service-items", {}).values())
                total_breakdown = total_plans + total_service_items

                self.stdout.write(f"\n{'='*60}")
                self.stdout.write(f"Total from plans: {total_plans}")
                self.stdout.write(f"Total from service-items: {total_service_items}")
                self.stdout.write(f"Total breakdown: {total_breakdown}")
                self.stdout.write(f"Invoice amount: {invoice.amount}")
                self.stdout.write(f"Difference: {abs(invoice.amount - total_breakdown)}")
                self.stdout.write(f"{'='*60}\n")

        except Exception as e:
            if json_only:
                # On error, output error as JSON
                error_output = {"error": str(e)}
                self.stdout.write(json.dumps(error_output, indent=2, ensure_ascii=False))
                sys.exit(1)
            else:
                self.stdout.write(self.style.ERROR(f"\n✗ Error calculating breakdown: {str(e)}"))
                import traceback

                self.stdout.write(traceback.format_exc())
                raise CommandError(f"Failed to calculate breakdown: {str(e)}")

