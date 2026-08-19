from __future__ import annotations

from collections import defaultdict
from logging import getLogger

from django.core.management.base import BaseCommand
from django.db.models import Count

from breathecode.admissions.models import Cohort, CohortUser

logger = getLogger(__name__)


def collect_macro_micro_ids() -> dict[int, set[int]]:
    macros = Cohort.objects.annotate(micro_count=Count("micro_cohorts")).filter(micro_count__gt=0).prefetch_related(
        "micro_cohorts"
    )
    return {macro.id: {micro.id for micro in macro.micro_cohorts.all()} for macro in macros}


def fill_source_macro_cohort(*, commit: bool = False) -> dict[str, int]:
    logger.info("fill_source_macro_cohort start commit=%s", commit)
    micro_ids_by_macro = collect_macro_micro_ids()
    macro_id_set = set(micro_ids_by_macro)
    by_user: dict[int, list[CohortUser]] = defaultdict(list)

    for cohort_user in CohortUser.objects.only("id", "user_id", "cohort_id", "source_macro_cohort_id"):
        by_user[cohort_user.user_id].append(cohort_user)

    filled = 0
    skipped_overlap = 0
    skipped_existing = 0

    for user_id, cohort_users in by_user.items():
        user_macro_ids = [cu.cohort_id for cu in cohort_users if cu.cohort_id in macro_id_set]
        if not user_macro_ids:
            continue

        for macro_id in user_macro_ids:
            micros_m = micro_ids_by_macro[macro_id]
            other: set[int] = set()
            for other_macro_id in user_macro_ids:
                if other_macro_id != macro_id:
                    other |= micro_ids_by_macro[other_macro_id]

            if micros_m & other:
                skipped_overlap += 1
                logger.info(
                    "fill_source_macro_cohort skip overlap user_id=%s macro_id=%s shared=%s",
                    user_id,
                    macro_id,
                    sorted(micros_m & other),
                )
                continue

            for cohort_user in cohort_users:
                if cohort_user.cohort_id not in micros_m:
                    continue
                if cohort_user.source_macro_cohort_id is not None:
                    skipped_existing += 1
                    continue

                logger.info(
                    "fill_source_macro_cohort fill user_id=%s cohort_user_id=%s macro_id=%s",
                    user_id,
                    cohort_user.id,
                    macro_id,
                )
                if commit:
                    CohortUser.objects.filter(id=cohort_user.id).update(source_macro_cohort_id=macro_id)
                    cohort_user.source_macro_cohort_id = macro_id
                filled += 1

    logger.info(
        "fill_source_macro_cohort done commit=%s filled=%s skipped_overlap=%s skipped_existing=%s",
        commit,
        filled,
        skipped_overlap,
        skipped_existing,
    )
    return {
        "filled": filled,
        "skipped_overlap": skipped_overlap,
        "skipped_existing": skipped_existing,
    }


class Command(BaseCommand):
    help = (
        "Fill CohortUser.source_macro_cohort when the user's macros do not share micros. "
        "Dry-run by default; pass --commit to write."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--commit",
            action="store_true",
            help="Persist source_macro_cohort. Without this flag the command only reports what it would fill.",
        )

    def handle(self, *args, **options):
        commit = bool(options.get("commit"))
        stats = fill_source_macro_cohort(commit=commit)
        mode = "commit" if commit else "dry-run"
        self.stdout.write(
            self.style.SUCCESS(
                f"[{mode}] filled={stats['filled']} skipped_overlap={stats['skipped_overlap']} "
                f"skipped_existing={stats['skipped_existing']}"
            )
        )
