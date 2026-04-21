from django.core.management.base import BaseCommand

from breathecode.assignments.models import LearnPackWebhook


class Command(BaseCommand):
    help = "Backfill LearnPackWebhook asset/package fields from payload"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show the number of records that would be updated without writing changes",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Overwrite existing values when payload has a valid value",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        overwrite = options["overwrite"]

        updated = 0
        scanned = 0

        webhooks = LearnPackWebhook.objects.exclude(payload__isnull=True)

        for webhook in webhooks.iterator():
            scanned += 1
            payload = webhook.payload or {}

            parsed_asset_id = self._to_int(payload.get("asset_id"))
            parsed_package_id = self._to_int(payload.get("package_id"))
            parsed_package_slug = payload.get("package_slug") or payload.get("slug")

            next_asset_id = self._pick_value(webhook.asset_id, parsed_asset_id, overwrite=overwrite)
            next_package_id = self._pick_value(
                webhook.learnpack_package_id,
                parsed_package_id,
                overwrite=overwrite,
            )
            next_package_slug = self._pick_slug(
                webhook.package_slug,
                parsed_package_slug,
                overwrite=overwrite,
            )

            has_change = (
                next_asset_id != webhook.asset_id
                or next_package_id != webhook.learnpack_package_id
                or next_package_slug != webhook.package_slug
            )
            if not has_change:
                continue

            updated += 1
            if dry_run:
                continue

            webhook.asset_id = next_asset_id
            webhook.learnpack_package_id = next_package_id
            webhook.package_slug = next_package_slug
            webhook.save()

        mode = "DRY-RUN" if dry_run else "APPLY"
        self.stdout.write(f"[{mode}] scanned={scanned} updated={updated}")

    @staticmethod
    def _to_int(value):
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _pick_value(current, parsed, *, overwrite=False):
        if overwrite and parsed is not None:
            return parsed
        if current is None and parsed is not None:
            return parsed
        return current

    @staticmethod
    def _pick_slug(current, parsed, *, overwrite=False):
        if parsed is None or parsed == "":
            return current
        if overwrite:
            return parsed
        if current is None or current == "":
            return parsed
        return current
