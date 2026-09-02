from logging import getLogger

from django.core.management.base import BaseCommand
from django.utils import timezone

from breathecode.payments import tasks
from breathecode.payments.models import PlanFinancing

logger = getLogger(__name__)

CHARGEABLE_STATUSES = {
    PlanFinancing.Status.ACTIVE,
    PlanFinancing.Status.PAYMENT_ISSUE,
    PlanFinancing.Status.ERROR,
}


class Command(BaseCommand):
    help = (
        "Set created_by_admin=True on every plan financing that has at least one invoice "
        "with proof of payment, and enqueue charge_plan_financing for overdue chargeable ones."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List affected plan financings without updating or enqueueing charges",
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
        logger.info(
            "Starting backfill_plan_financing_created_by_admin dry_run=%s email=%s plan_financing_id=%s",
            dry_run,
            options["email"],
            options["plan_financing_id"],
        )
        qs = (
            PlanFinancing.objects.filter(
                created_by_admin=False,
                invoices__proof_id__isnull=False,
            )
            .distinct()
            .select_related("user", "academy")
            .order_by("id")
        )

        if options["email"]:
            qs = qs.filter(user__email__iexact=options["email"])
        if options["plan_financing_id"]:
            qs = qs.filter(pk=options["plan_financing_id"])

        marked = 0
        charged = 0
        for plan_financing in qs.iterator():
            overdue = plan_financing.next_payment_at is not None and plan_financing.next_payment_at <= utc_now
            remaining = plan_financing.how_many_installments > (plan_financing.installments_paid or 0)
            should_charge = plan_financing.status in CHARGEABLE_STATUSES and overdue and remaining

            self.stdout.write(
                f"id={plan_financing.id} user={plan_financing.user.email} "
                f"status={plan_financing.status} next_payment_at={plan_financing.next_payment_at} "
                f"installments_paid={plan_financing.installments_paid}/"
                f"{plan_financing.how_many_installments} "
                f"charge={'yes' if should_charge else 'no'}"
            )

            if not dry_run:
                plan_financing.created_by_admin = True
                plan_financing.save(update_fields=["created_by_admin"])
                logger.info("Marked plan_financing_id=%s created_by_admin=True", plan_financing.id)
                if should_charge:
                    tasks.charge_plan_financing.delay(plan_financing.id)
                    logger.info("Queued charge_plan_financing plan_financing_id=%s", plan_financing.id)

            marked += 1
            if should_charge:
                charged += 1

        action = "Would mark" if dry_run else "Marked"
        charge_action = "would charge" if dry_run else "queued charge for"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} {marked} plan financing(s) as created_by_admin; {charge_action} {charged}."
            )
        )
        logger.info(
            "Finished backfill_plan_financing_created_by_admin dry_run=%s marked=%s charged=%s",
            dry_run,
            marked,
            charged,
        )
