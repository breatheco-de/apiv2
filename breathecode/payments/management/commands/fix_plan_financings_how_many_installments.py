from django.core.management.base import BaseCommand

from ...models import PlanFinancing


# renew the subscriptions every 1 hours
class Command(BaseCommand):
    help = "Add how_many_installments to old plan_financings"

    def handle(self, *args, **options):
        plan_financings = PlanFinancing.objects.all()
        for plan_financing in plan_financings:
            invoice = plan_financing.invoices.all()[0]
            plan_financing.how_many_installments = invoice.bag.how_many_installments
            plan_financing.save()
