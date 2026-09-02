from logging import getLogger

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from task_manager.django.models import TaskManager

from breathecode.payments import tasks
from breathecode.payments.models import Plan, PlanFinancing

logger = getLogger(__name__)

CHARGEABLE_STATUSES = {
    PlanFinancing.Status.ACTIVE,
    PlanFinancing.Status.PAYMENT_ISSUE,
    PlanFinancing.Status.ERROR,
}

MAX_CATCH_UP_CYCLES = 36


def parse_plan_slugs(raw: str | None) -> list[str] | None:
    if raw is None:
        return None
    slugs = [slug.strip() for slug in raw.split(",") if slug.strip()]
    if not slugs:
        raise CommandError("--plans cannot be empty")
    return slugs


def run_task_now(celery_task, *args):
    """Run a task_manager @task in-process.

    ``.apply()`` / first ``delay()`` hop only creates a TaskManager row and
    ``apply_async``; it does not execute the charge on a Heroku one-off dyno.
    Passing ``task_manager_id`` skips that schedule-only path.

    Callers must be ``bind=True`` tasks: the wrapper treats ``args[0]`` as
    the Celery task instance.
    """
    wrapper = getattr(celery_task, "__wrapped__", None)
    if wrapper is None:
        logger.warning(
            "Task %s has no __wrapped__; falling back to delay() and will not wait for the charge",
            getattr(celery_task, "__name__", celery_task),
        )
        celery_task.delay(*args)
        return None

    task_manager = TaskManager.objects.create(
        task_module=celery_task.__module__,
        task_name=celery_task.__name__,
        arguments={"args": list(args), "kwargs": {}},
        status="SCHEDULED",
        last_run=timezone.now(),
        current_page=0,
        total_pages=1,
        attempts=1,
    )
    wrapper(celery_task, *args, task_manager_id=task_manager.id)
    task_manager.refresh_from_db()
    logger.info(
        "Ran %s in-process args=%s task_manager_id=%s status=%s message=%s",
        celery_task.__name__,
        args,
        task_manager.id,
        task_manager.status,
        task_manager.status_message,
    )
    return task_manager


class Command(BaseCommand):
    help = (
        "Set created_by_admin=True on plan financings that have at least one invoice "
        "with proof of payment, and run charge_plan_financing in-process for overdue "
        "chargeable ones. With --plans, mark every financing of those plan slugs and "
        "catch up ACTIVE overdue charges plus consumables until next_payment_at is in "
        "the future."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List affected plan financings without updating or running charges",
        )
        parser.add_argument("--email", type=str, default=None, help="Limit to a user email")
        parser.add_argument(
            "--plan-financing-id",
            type=int,
            default=None,
            help="Limit to a single PlanFinancing id",
        )
        parser.add_argument(
            "--plans",
            type=str,
            default=None,
            help="Comma-separated plan slugs. Marks those financings as created_by_admin "
            "and catch-up charges ACTIVE overdue ones until next_payment_at > now.",
        )

    def handle(self, *args, **options):
        utc_now = timezone.now()
        dry_run = options["dry_run"]
        plan_slugs = parse_plan_slugs(options.get("plans"))
        logger.info(
            "Starting backfill_plan_financing_created_by_admin dry_run=%s email=%s "
            "plan_financing_id=%s plans=%s",
            dry_run,
            options["email"],
            options["plan_financing_id"],
            plan_slugs,
        )

        if plan_slugs:
            qs = self._queryset_for_plans(plan_slugs)
        else:
            qs = (
                PlanFinancing.objects.filter(
                    created_by_admin=False,
                    invoices__proof_id__isnull=False,
                )
                .distinct()
                .select_related("user", "academy")
                .prefetch_related("plans")
                .order_by("id")
            )

        if options["email"]:
            qs = qs.filter(user__email__iexact=options["email"])
        if options["plan_financing_id"]:
            qs = qs.filter(pk=options["plan_financing_id"])

        marked = 0
        charged = 0
        charge_targets = []
        for plan_financing in qs:
            overdue = plan_financing.next_payment_at is not None and plan_financing.next_payment_at <= utc_now
            remaining = plan_financing.how_many_installments > (plan_financing.installments_paid or 0)
            if plan_slugs:
                should_charge = plan_financing.status == PlanFinancing.Status.ACTIVE and overdue and remaining
            else:
                should_charge = plan_financing.status in CHARGEABLE_STATUSES and overdue and remaining

            plan_slugs_label = ",".join(plan_financing.plans.values_list("slug", flat=True))
            self.stdout.write(
                f"id={plan_financing.id} user={plan_financing.user.email} "
                f"status={plan_financing.status} plans={plan_slugs_label} "
                f"next_payment_at={plan_financing.next_payment_at} "
                f"installments_paid={plan_financing.installments_paid}/"
                f"{plan_financing.how_many_installments} "
                f"charge={'yes' if should_charge else 'no'}"
            )

            if not dry_run:
                if not plan_financing.created_by_admin:
                    plan_financing.created_by_admin = True
                    plan_financing.save(update_fields=["created_by_admin"])
                    logger.info("Marked plan_financing_id=%s created_by_admin=True", plan_financing.id)
                if should_charge:
                    if plan_slugs:
                        self._catch_up_overdue(plan_financing, utc_now)
                    else:
                        task_manager = run_task_now(tasks.charge_plan_financing, plan_financing.id)
                        logger.info(
                            "Ran charge_plan_financing plan_financing_id=%s task_status=%s",
                            plan_financing.id,
                            getattr(task_manager, "status", None),
                        )

            marked += 1
            if should_charge:
                charged += 1
                charge_targets.append((plan_financing.id, plan_financing.user.email))

        action = "Would mark" if dry_run else "Marked"
        charge_action = "would charge" if dry_run else "ran charge for"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} {marked} plan financing(s) as created_by_admin; {charge_action} {charged}."
            )
        )
        if charge_targets:
            self.stdout.write("")
            self.stdout.write(f"Emails to charge ({len(charge_targets)}):")
            for financing_id, email in charge_targets:
                self.stdout.write(f"  id={financing_id} {email}")
        logger.info(
            "Finished backfill_plan_financing_created_by_admin dry_run=%s marked=%s charged=%s emails=%s",
            dry_run,
            marked,
            charged,
            [email for _, email in charge_targets],
        )

    def _queryset_for_plans(self, plan_slugs: list[str]):
        found = set(Plan.objects.filter(slug__in=plan_slugs).values_list("slug", flat=True))
        missing = [slug for slug in plan_slugs if slug not in found]
        if missing:
            raise CommandError(f"Unknown plan slug(s): {', '.join(missing)}")

        logger.info("Selecting plan financings for plans=%s", plan_slugs)
        return (
            PlanFinancing.objects.filter(plans__slug__in=plan_slugs)
            .distinct()
            .select_related("user", "academy")
            .prefetch_related("plans")
            .order_by("id")
        )

    def _catch_up_overdue(self, plan_financing: PlanFinancing, utc_now) -> None:
        """Charge and renew until next_payment_at is in the future or the financing stops being ACTIVE."""
        cycles = 0
        remaining_cap = max(
            (plan_financing.how_many_installments or 0) - (plan_financing.installments_paid or 0),
            1,
        )
        max_cycles = min(MAX_CATCH_UP_CYCLES, remaining_cap)

        logger.info(
            "Catching up plan_financing_id=%s next_payment_at=%s max_cycles=%s",
            plan_financing.id,
            plan_financing.next_payment_at,
            max_cycles,
        )

        while cycles < max_cycles:
            plan_financing.refresh_from_db()
            overdue = plan_financing.next_payment_at is not None and plan_financing.next_payment_at <= utc_now
            remaining = plan_financing.how_many_installments > (plan_financing.installments_paid or 0)
            if plan_financing.status != PlanFinancing.Status.ACTIVE or not overdue or not remaining:
                break

            before = (
                plan_financing.next_payment_at,
                plan_financing.installments_paid,
                plan_financing.status,
            )
            logger.info(
                "Catch-up charge cycle=%s plan_financing_id=%s next_payment_at=%s installments_paid=%s",
                cycles + 1,
                plan_financing.id,
                plan_financing.next_payment_at,
                plan_financing.installments_paid,
            )
            try:
                task_manager = run_task_now(tasks.charge_plan_financing, plan_financing.id)
            except Exception:
                logger.exception("Catch-up charge failed plan_financing_id=%s", plan_financing.id)
                self.stdout.write(self.style.ERROR(f"charge failed plan_financing_id={plan_financing.id}"))
                break

            plan_financing.refresh_from_db()
            after = (
                plan_financing.next_payment_at,
                plan_financing.installments_paid,
                plan_financing.status,
            )
            cycles += 1
            if after == before:
                message = task_manager.status_message if task_manager else "unknown"
                logger.warning(
                    "Catch-up made no progress plan_financing_id=%s task_manager_status=%s message=%s",
                    plan_financing.id,
                    getattr(task_manager, "status", None),
                    message,
                )
                self.stdout.write(
                    self.style.WARNING(
                        f"charge made no progress id={plan_financing.id} "
                        f"task_status={getattr(task_manager, 'status', None)} {message}"
                    )
                )
                break

        plan_financing.refresh_from_db()
        if plan_financing.next_payment_at is not None and plan_financing.next_payment_at > utc_now:
            run_task_now(tasks.renew_plan_financing_consumables, plan_financing.id)
            logger.info(
                "Renewed consumables in-process plan_financing_id=%s after %s catch-up cycle(s)",
                plan_financing.id,
                cycles,
            )
        else:
            logger.warning(
                "Catch-up finished still overdue plan_financing_id=%s next_payment_at=%s status=%s cycles=%s",
                plan_financing.id,
                plan_financing.next_payment_at,
                plan_financing.status,
                cycles,
            )
