"""
Migrate legacy `academy_features.features` into the new segmented top-level structure
(`events`, `mentorship`, `feedback`, `community`, `marketing`, `commerce`).

Goal:
- Remove `features` key entirely from persisted academy_features JSON.
- Preserve existing per-academy configuration (do not overwrite segment values already set).

Usage:
    python manage.py migrate_academy_features_segments --dry-run
    python manage.py migrate_academy_features_segments
    python manage.py migrate_academy_features_segments --allow-unknown
    python manage.py migrate_academy_features_segments --academy 1 --academy 2
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from breathecode.admissions.models import Academy


MAPPING: dict[str, tuple[str, ...]] = {
    "allow_events": ("events", "enabled"),
    "allow_other_academy_events": ("events", "allow_other_academy_events"),
    "allow_mentoring": ("mentorship", "enabled"),
    "allow_feedback_widget": ("feedback", "widget", "enabled"),
    "allow_community_widget": ("community", "widget", "enabled"),
    "allow_referral_program": ("marketing", "referral_program", "enabled"),
    "allow_other_academy_courses": ("marketing", "dashboard", "allow_other_academy_courses"),
    "reseller": ("commerce", "reseller"),
}


def _get_nested(data: dict, path: tuple[str, ...]):
    current = data
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None, False
        current = current[key]
    return current, True


def _set_nested(data: dict, path: tuple[str, ...], value):
    current = data
    for key in path[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]

    current[path[-1]] = value


class Command(BaseCommand):
    help = "Migrate academy_features.features -> segmented top-level keys and remove the legacy key"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without actually saving",
        )
        parser.add_argument(
            "--allow-unknown",
            action="store_true",
            help="If legacy `features` contains unknown keys, move them to `custom_features` instead of failing",
        )
        parser.add_argument(
            "--academy",
            action="append",
            type=int,
            default=[],
            help="Limit to specific academy IDs (can be passed multiple times)",
        )

    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]
        allow_unknown: bool = options["allow_unknown"]
        academy_ids: list[int] = options["academy"] or []

        qs = Academy.objects.all()
        if academy_ids:
            qs = qs.filter(id__in=academy_ids)

        total = qs.count()
        updated = 0
        skipped = 0
        unknown_total = 0

        self.stdout.write(f"Found {total} academies to process")

        for academy in qs.iterator():
            raw = academy.academy_features or {}
            if not isinstance(raw, dict):
                skipped += 1
                continue

            legacy = raw.get("features")
            if not isinstance(legacy, dict):
                skipped += 1
                continue

            unknown_keys = sorted([k for k in legacy.keys() if k not in MAPPING])
            if unknown_keys:
                unknown_total += len(unknown_keys)
                if not allow_unknown:
                    raise CommandError(
                        f"Academy {academy.id} ({academy.slug}) has unknown legacy feature keys: {unknown_keys}. "
                        "Re-run with --allow-unknown to move them into custom_features."
                    )

            # Work on a copy so we can compare and avoid writing if no changes
            new = dict(raw)

            # Move known keys into segmented top-level structure (do not overwrite if already set)
            for old_key, path in MAPPING.items():
                if old_key not in legacy:
                    continue

                _, exists = _get_nested(new, path)
                if exists:
                    continue

                _set_nested(new, path, legacy[old_key])

            # Move unknown keys (optional)
            if unknown_keys and allow_unknown:
                custom_path = ("custom_features",)
                custom, exists = _get_nested(new, custom_path)
                if not exists or not isinstance(custom, dict):
                    _set_nested(new, custom_path, {})
                    custom, _ = _get_nested(new, custom_path)

                for k in unknown_keys:
                    custom[k] = legacy[k]

            # Remove legacy key
            new.pop("features", None)

            if new == raw:
                skipped += 1
                continue

            updated += 1
            if dry_run:
                self.stdout.write(self.style.WARNING(f"[DRY RUN] Would update academy {academy.id} ({academy.slug})"))
            else:
                academy.academy_features = new
                academy.save(update_fields=["academy_features"])
                self.stdout.write(self.style.SUCCESS(f"Updated academy {academy.id} ({academy.slug})"))

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"\n[DRY RUN] Would update {updated} academies, skipped {skipped}. "
                    f"Unknown legacy keys found: {unknown_total}."
                )
            )
            self.stdout.write(self.style.WARNING("Run again without --dry-run to apply changes."))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nSuccessfully updated {updated} academies, skipped {skipped}. "
                    f"Unknown legacy keys found: {unknown_total}."
                )
            )


