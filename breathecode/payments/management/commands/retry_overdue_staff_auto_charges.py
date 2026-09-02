from django.core.management.base import BaseCommand
from django.db.models import F
from django.utils import timezone

from breathecode.payments import tasks
from breathecode.payments.models import PlanFinancing


class Command(BaseCommand):
    help = (
        "Re-queue charge_plan_financing for overdue admin-managed plan financings. "
        "Those charges close the installment without Stripe."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List affected plan financings without enqueueing charges",
        )
        parser.add_argument("--email", type=str, default=None, help="Limit to a user email")
        parser.add_argument(
            "--plan-financing-id",
            type=int,
            default=None,
            help="Limit to a single PlanFinancing id",
        )

    def handle(self, *args, **options):
        utc_now = timezone.now()
        dry_run = options["dry_run"]
        qs = PlanFinancing.objects.filter(
            status__in=[
                PlanFinancing.Status.ACTIVE,
                PlanFinancing.Status.PAYMENT_ISSUE,
                PlanFinancing.Status.ERROR,
            ],
            next_payment_at__lte=utc_now,
            how_many_installments__gt=F("installments_paid"),
            created_by_admin=True,
        ).select_related("user", "academy")

        if options["email"]:
            qs = qs.filter(user__email__iexact=options["email"])
        if options["plan_financing_id"]:
            qs = qs.filter(pk=options["plan_financing_id"])

        queued = 0
        for plan_financing in qs:
            self.stdout.write(
                f"id={plan_financing.id} user={plan_financing.user.email} "
                f"status={plan_financing.status} next_payment_at={plan_financing.next_payment_at} "
                f"installments_paid={plan_financing.installments_paid}/"
                f"{plan_financing.how_many_installments}"
            )
            if not dry_run:
                tasks.charge_plan_financing.delay(plan_financing.id)
            queued += 1

        action = "Would queue" if dry_run else "Queued"
        self.stdout.write(self.style.SUCCESS(f"{action} {queued} plan financing charge(s)."))
