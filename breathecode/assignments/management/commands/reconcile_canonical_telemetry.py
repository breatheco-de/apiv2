import logging
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from breathecode.assignments.models import AssignmentTelemetry, Task
from breathecode.registry.models import Asset

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Reconcile assignment telemetry to canonical translation slug (lowest-id asset in group)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show planned telemetry reconciliation without writing changes",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        self.stdout.write(self.style.WARNING("Running in DRY-RUN mode") if dry_run else self.style.SUCCESS("Applying reconciliation"))

        summary = {
            "groups": 0,
            "users_with_changes": 0,
            "telemetry_repointed": 0,
            "telemetry_deleted": 0,
            "tasks_repointed": 0,
        }

        processed_asset_ids = set()
        groups = self._collect_translation_groups(processed_asset_ids)

        for group in groups:
            summary["groups"] += 1
            group_changes = self._reconcile_group(group, dry_run=dry_run)
            for key in summary:
                if key in group_changes:
                    summary[key] += group_changes[key]

        self.stdout.write("\nReconciliation summary:")
        for key, value in summary.items():
            self.stdout.write(f"- {key}: {value}")

    def _collect_translation_groups(self, processed_asset_ids: set[int]) -> list[list[Asset]]:
        groups = []
        assets = Asset.objects.all().only("id", "slug")

        for asset in assets:
            if asset.id in processed_asset_ids:
                continue

            group = [asset]
            group.extend(list(asset.all_translations.all().only("id", "slug")))

            # Deduplicate by id and keep only valid ids
            unique_group_by_id = {}
            for elem in group:
                if elem and elem.id is not None:
                    unique_group_by_id[elem.id] = elem

            deduped_group = list(unique_group_by_id.values())
            for elem in deduped_group:
                processed_asset_ids.add(elem.id)

            groups.append(deduped_group)

        return groups

    def _reconcile_group(self, group: list[Asset], *, dry_run: bool) -> dict[str, int]:
        if not group:
            return {}

        canonical_asset = min(group, key=lambda x: x.id)
        canonical_slug = canonical_asset.slug
        group_slugs = [x.slug for x in group]

        telemetries = AssignmentTelemetry.objects.filter(asset_slug__in=group_slugs).order_by("-updated_at", "-id")
        if not telemetries.exists():
            return {}

        by_user = defaultdict(list)
        for telemetry in telemetries:
            by_user[telemetry.user_id].append(telemetry)

        result = {
            "users_with_changes": 0,
            "telemetry_repointed": 0,
            "telemetry_deleted": 0,
            "tasks_repointed": 0,
        }

        for user_id, rows in by_user.items():
            canonical_rows = [r for r in rows if r.asset_slug == canonical_slug]

            target = canonical_rows[0] if canonical_rows else rows[0]
            source_latest = rows[0]
            rows_to_merge = [r for r in rows if r.id != target.id]

            changed = False
            if target.asset_slug != canonical_slug:
                changed = True

            # Ensure target keeps freshest payload and metrics in deterministic way.
            for field in [
                "telemetry",
                "engagement_score",
                "frustration_score",
                "metrics_algo_version",
                "metrics",
                "total_time",
                "completion_rate",
            ]:
                source_value = getattr(source_latest, field)
                target_value = getattr(target, field)
                if source_value is not None and source_value != target_value:
                    changed = True

            if not changed and len(rows_to_merge) == 0:
                continue

            result["users_with_changes"] += 1

            if not dry_run:
                with transaction.atomic():
                    target.asset_slug = canonical_slug
                    for field in [
                        "telemetry",
                        "engagement_score",
                        "frustration_score",
                        "metrics_algo_version",
                        "metrics",
                        "total_time",
                        "completion_rate",
                    ]:
                        source_value = getattr(source_latest, field)
                        if source_value is not None:
                            setattr(target, field, source_value)
                    target.save()

                    telemetry_ids = [r.id for r in rows]
                    affected_tasks = Task.objects.filter(telemetry_id__in=telemetry_ids).exclude(telemetry_id=target.id)
                    repointed_count = affected_tasks.count()
                    if repointed_count:
                        affected_tasks.update(telemetry=target)
                        result["tasks_repointed"] += repointed_count

                    if rows_to_merge:
                        merged_count = len(rows_to_merge)
                        AssignmentTelemetry.objects.filter(id__in=[r.id for r in rows_to_merge]).delete()
                        result["telemetry_deleted"] += merged_count

            result["telemetry_repointed"] += 1

        return result
