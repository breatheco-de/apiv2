from logging import getLogger

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from breathecode.payments.actions import (
    consumable_valid_until_exceeds_next_payment,
    consumable_valid_until_is_expired,
    plan_financing_caps_consumables_at_next_payment,
    plan_financing_consumable_prune_cutoff_date,
)
from breathecode.payments.models import Consumable, Plan, PlanFinancing, ServiceStockScheduler

logger = getLogger(__name__)

# Django ``delete()`` totals include cascade rows; map labels for the summary.
CASCADE_MODEL_LABELS = {
    "payments.ConsumptionSession": "ConsumptionSession (sesiones de uso ligadas al consumible)",
    "payments.servicestockscheduler_consumables": "enlace ServiceStockScheduler ↔ Consumable (tabla M2M)",
}


class Command(BaseCommand):
    help = (
        "List consumables of a catalog plan and delete those whose valid_until is more than "
        "one calendar day after each PlanFinancing.next_payment_at, but only for financings "
        "that still have unpaid installments. Asks y/n before deleting."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--plan-id",
            type=int,
            default=None,
            help="Catalog Plan id. Consumables come from PlanFinancing rows of this plan.",
        )
        parser.add_argument(
            "--plan-slug",
            type=str,
            default=None,
            help="Catalog Plan slug (alternative to --plan-id).",
        )
        parser.add_argument("--email", type=str, default=None, help="Limit to a user email")
        parser.add_argument(
            "--plan-financing-id",
            type=int,
            default=None,
            help="Limit to a single PlanFinancing id",
        )
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Delete without asking y/n",
        )

    def handle(self, *args, **options):
        plan = self._resolve_plan(options["plan_id"], options["plan_slug"])
        qs = PlanFinancing.objects.filter(plans=plan).select_related("user").order_by("id")
        if options["email"]:
            qs = qs.filter(user__email__iexact=options["email"])
        if options["plan_financing_id"]:
            qs = qs.filter(pk=options["plan_financing_id"])

        self.stdout.write(f"Plan id={plan.id} slug={plan.slug}")
        self.stdout.write("")

        utc_now = timezone.now()
        skipped = 0
        to_delete: list[Consumable] = []
        schedulers_to_reset: dict[int, ServiceStockScheduler] = {}

        for plan_financing in qs:
            if not plan_financing_caps_consumables_at_next_payment(plan_financing):
                skipped += 1
                continue

            all_consumables = list(
                Consumable.objects.filter(plan_financing=plan_financing)
                .select_related("service_item__service", "user")
                .order_by("valid_until", "id")
            )
            consumables = [
                consumable
                for consumable in all_consumables
                if not consumable_valid_until_is_expired(consumable.valid_until, utc_now)
            ]
            expired_count = len(all_consumables) - len(consumables)
            extras = [
                consumable
                for consumable in consumables
                if consumable_valid_until_exceeds_next_payment(
                    consumable.valid_until,
                    plan_financing.next_payment_at,
                )
            ]

            self.stdout.write(
                f"PlanFinancing id={plan_financing.id} user={plan_financing.user.email} "
                f"status={plan_financing.status} "
                f"installments_paid={plan_financing.installments_paid}/"
                f"{plan_financing.how_many_installments} "
                f"next_payment_at={plan_financing.next_payment_at}"
            )
            if expired_count:
                self.stdout.write(
                    self.style.WARNING(f"  Skipped {expired_count} expired consumable(s) (not listed).")
                )
            if not consumables:
                self.stdout.write("  (no active consumables)")
                self.stdout.write("")
                continue

            keep = self._sort_by_valid_until([c for c in consumables if c not in extras])
            for consumable in keep:
                self._write_consumable_line(consumable, "KEEP")
            for consumable in self._sort_by_valid_until(extras):
                self._write_consumable_line(consumable, "DELETE")

            if extras:
                cutoff_date = plan_financing_consumable_prune_cutoff_date(plan_financing.next_payment_at)
                self.stdout.write(
                    self.style.ERROR(
                        f"  Would delete {len(extras)} consumable(s) with valid_until after {cutoff_date}."
                    )
                )
                to_delete.extend(extras)
                for scheduler in ServiceStockScheduler.objects.filter(
                    plan_handler__plan_financing=plan_financing,
                    valid_until__date__gt=cutoff_date,
                ):
                    schedulers_to_reset[scheduler.id] = scheduler

            self.stdout.write("")

        self.stdout.write(
            f"Skipped {skipped} plan financing(s) that are FULLY_PAID or have all installments paid."
        )
        self.stdout.write("")

        if not to_delete:
            self.stdout.write(self.style.SUCCESS("Nothing to delete."))
            return

        ids = [consumable.id for consumable in to_delete]
        self.stdout.write(self.style.WARNING(f"Will delete {len(ids)} consumable(s): {ids}"))

        if not options["yes"]:
            confirm = input("Delete these consumables? [y/N]: ").strip().lower()
            if confirm not in {"y", "yes"}:
                self.stdout.write(self.style.WARNING("Cancelled. No consumables were deleted."))
                return

        deleted_total, per_model = Consumable.objects.filter(id__in=ids).delete()
        consumables_deleted = per_model.get("payments.Consumable", 0)
        cascade_deleted = deleted_total - consumables_deleted
        for scheduler in schedulers_to_reset.values():
            scheduler.refresh_from_db()
            plan_financing = scheduler.plan_handler.plan_financing
            if plan_financing and plan_financing.next_payment_at and scheduler.valid_until:
                if consumable_valid_until_exceeds_next_payment(
                    scheduler.valid_until,
                    plan_financing.next_payment_at,
                ):
                    scheduler.valid_until = plan_financing.next_payment_at
                    scheduler.save(update_fields=["valid_until"])
                    logger.info(
                        "Reset scheduler id=%s valid_until to next_payment_at=%s",
                        scheduler.id,
                        plan_financing.next_payment_at,
                    )

        logger.info(
            "Deleted extra plan consumables ids=%s consumables=%s cascade_rows=%s per_model=%s",
            ids,
            consumables_deleted,
            cascade_deleted,
            per_model,
        )
        self.stdout.write(self.style.SUCCESS(f"Deleted {consumables_deleted} consumable(s)."))
        cascade_lines = self._format_cascade_breakdown(per_model)
        if cascade_lines:
            self.stdout.write("  Cascade (otras filas que Django borró automáticamente):")
            for line in cascade_lines:
                self.stdout.write(f"    {line}")

    def _format_cascade_breakdown(self, per_model: dict) -> list[str]:
        lines = []
        for model_label, count in sorted(per_model.items()):
            if model_label == "payments.Consumable" or count <= 0:
                continue
            label = CASCADE_MODEL_LABELS.get(model_label, model_label)
            lines.append(f"- {count}× {label}")
        return lines

    def _sort_by_valid_until(self, consumables: list[Consumable]) -> list[Consumable]:
        sentinel = timezone.now()
        return sorted(consumables, key=lambda c: (c.valid_until is None, c.valid_until or sentinel, c.id))

    def _write_consumable_line(self, consumable: Consumable, action: str) -> None:
        service_slug = getattr(getattr(consumable.service_item, "service", None), "slug", None)
        line = (
            f"  [{action}] id={consumable.id} service={service_slug} "
            f"how_many={consumable.how_many} valid_until={consumable.valid_until}"
        )
        if action == "KEEP":
            self.stdout.write(self.style.SUCCESS(line))
        else:
            self.stdout.write(self.style.ERROR(line))

    def _resolve_plan(self, plan_id: int | None, plan_slug: str | None) -> Plan:
        if not plan_id and not plan_slug:
            raise CommandError("Pass --plan-id or --plan-slug")
        if plan_id and plan_slug:
            raise CommandError("Pass only one of --plan-id or --plan-slug")

        if plan_id:
            plan = Plan.objects.filter(id=plan_id).first()
            if not plan:
                raise CommandError(f"Plan id={plan_id} not found")
            return plan

        plan = Plan.objects.filter(slug=plan_slug).first()
        if not plan:
            raise CommandError(f"Plan slug={plan_slug} not found")
        return plan
