"""
Macro cohort certificate workflow: eligibility report per micro cohort, optional generation.

Only micro-cohort STUDENT rows with educational_status GRADUATED are considered (diagnostic + optional
--generate). Other enrollments on the micro are skipped.

This is intentionally not named diagnose_* — commands under that prefix are read-only here.
With --generate this command persists certificate state like generate_certificate.
--dry-run never writes; combine with --generate to simulate issuance, or use alone to get the
final list after the full diagnostics.
"""

from __future__ import annotations

from capyc.rest_framework.exceptions import ValidationException
from django.core.management.base import BaseCommand, CommandError

from breathecode.admissions.models import GRADUATED, STUDENT, Cohort, CohortUser
from breathecode.certificate.actions import generate_certificate
from breathecode.certificate.diagnostics import print_certificate_diagnostic


def ordered_micro_cohorts(macro: Cohort) -> list[Cohort]:
    """Micro cohorts excluding DELETED, ordered by cohorts_order then remaining ids."""
    qs = macro.micro_cohorts.exclude(stage="DELETED").all()
    micros_by_id: dict[int, Cohort] = {c.id: c for c in qs}
    if not micros_by_id:
        return []

    raw = (macro.cohorts_order or "").strip()
    if not raw:
        return sorted(micros_by_id.values(), key=lambda c: c.id)

    ids: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            cid = int(part)
        except ValueError:
            continue
        if cid in micros_by_id and cid not in ids:
            ids.append(cid)

    for cid in sorted(micros_by_id.keys()):
        if cid not in ids:
            ids.append(cid)

    return [micros_by_id[cid] for cid in ids]


class Command(BaseCommand):
    help = (
        "For STUDENT rows on a macro cohort, print certificate eligibility per micro cohort "
        "only when that user's micro CohortUser is GRADUATED (same checks as generate_certificate). "
        "Use --generate to issue certificates. Use --dry-run to never write and list who would get a cert."
    )

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--macro-cohort-id", type=int, help="Macro cohort primary key")
        group.add_argument("--macro-cohort-slug", type=str, help="Macro cohort slug")

        parser.add_argument(
            "--generate",
            action="store_true",
            help="After eligibility passes, call generate_certificate (writes to the database).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Never persist certificates. With --generate: run checks and print what would be issued. "
            "Always prints a final list of cohort_user rows that would receive generate_certificate.",
        )
        parser.add_argument(
            "--layout-slug",
            type=str,
            default=None,
            help="Layout slug passed to generate_certificate (only with --generate).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Max macro-cohort STUDENT rows to process.",
        )

    def handle(self, *args, **options):
        cohort_id = options.get("macro_cohort_id")
        slug = options.get("macro_cohort_slug")
        do_generate = options.get("generate", False)
        dry_run = options.get("dry_run", False)
        will_write = do_generate and not dry_run
        layout_slug = options.get("layout_slug")
        limit = options.get("limit")

        if cohort_id is not None:
            macro = Cohort.objects.filter(id=cohort_id).first()
            if macro is None:
                raise CommandError(f"No cohort found with id={cohort_id}")
        else:
            s = slug.strip()
            macro = Cohort.objects.filter(slug=s).first()
            if macro is None:
                raise CommandError(f"No cohort found with slug={s!r}")

        micros = ordered_micro_cohorts(macro)
        if not micros:
            raise CommandError(
                f"Cohort '{macro.slug}' has no linked micro cohorts "
                "(or all are DELETED). Link micro cohorts via Cohort.micro_cohorts."
            )

        students_qs = (
            CohortUser.objects.filter(cohort=macro, role=STUDENT)
            .exclude(cohort__stage="DELETED")
            .select_related("user", "cohort", "cohort__academy")
            .order_by("id")
        )
        if limit is not None:
            students_qs = students_qs[: limit]

        macro_students = list(students_qs)
        total_pairs = len(macro_students) * len(micros)

        self.stdout.write(self.style.SUCCESS(f"\n{'='*72}"))
        self.stdout.write(self.style.SUCCESS(f"Macro cohort: {macro.name} (id={macro.id}, slug={macro.slug})"))
        self.stdout.write(
            self.style.SUCCESS(f"Micro cohorts ({len(micros)}): {', '.join(f'{m.slug}#{m.id}' for m in micros)}")
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Macro STUDENT CohortUsers: {len(macro_students)} "
                f"(micro pairs to scan ≤ {total_pairs}; only micro rows with educational_status={GRADUATED})"
            )
        )
        if will_write:
            self.stdout.write(self.style.WARNING("Mode: report + generate (writes DB when eligible)"))
        elif do_generate and dry_run:
            self.stdout.write(
                self.style.WARNING("Mode: DRY RUN — same as --generate but no DB writes; see summary below")
            )
        elif dry_run:
            self.stdout.write(self.style.WARNING("Mode: report only (no writes); end lists who would get --generate"))
        else:
            self.stdout.write(self.style.SUCCESS("Mode: report only (no writes)"))
        self.stdout.write(self.style.SUCCESS(f"{'='*72}\n"))

        skipped_no_micro_cu = 0
        skipped_micro_not_graduated = 0
        eligibility_ok = 0
        eligibility_fail = 0
        generated_ok = 0
        generated_fail = 0
        would_generate_rows: list[str] = []

        for mc_row in macro_students:
            user = mc_row.user
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n──────── Macro student: {user.email} (user_id={user.id}, cohort_user_id={mc_row.id}) ────────"
                )
            )

            for micro in micros:
                self.stdout.write(self.style.WARNING(f"\n  ▶ Micro: {micro.name} (id={micro.id}, slug={micro.slug})"))

                cu = (
                    CohortUser.objects.filter(
                        user_id=user.id,
                        cohort=micro,
                        role=STUDENT,
                        educational_status=GRADUATED,
                    )
                    .exclude(cohort__stage="DELETED")
                    .select_related("user", "cohort", "cohort__academy")
                    .first()
                )
                if cu is None:
                    other = (
                        CohortUser.objects.filter(user_id=user.id, cohort=micro, role=STUDENT)
                        .exclude(cohort__stage="DELETED")
                        .only("id", "educational_status")
                        .first()
                    )
                    if other is None:
                        self.stdout.write(
                            self.style.ERROR(
                                f"  ⚠ SKIP: No STUDENT CohortUser for user {user.id} on micro cohort {micro.slug}"
                            )
                        )
                        skipped_no_micro_cu += 1
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  ⚠ SKIP: Micro CohortUser is not GRADUATED "
                                f"(educational_status={other.educational_status!r}); no cert check."
                            )
                        )
                        skipped_micro_not_graduated += 1
                    continue

                result = print_certificate_diagnostic(self.stdout, self.style, cu)
                if result.get("issues"):
                    eligibility_fail += 1
                    continue

                eligibility_ok += 1
                would_generate_rows.append(
                    f"  user={user.email!r} user_id={user.id} micro={micro.slug!r} (id={micro.id}) "
                    f"cohort_user_id={cu.id}"
                )
                if not do_generate:
                    continue

                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(
                            "  ◆ DRY RUN — would call generate_certificate "
                            f"(layout_slug={layout_slug!r}) for this micro cohort_user"
                        )
                    )
                    continue

                try:
                    generate_certificate(user, micro, layout_slug)
                    self.stdout.write(self.style.SUCCESS("  ✓ generate_certificate succeeded"))
                    generated_ok += 1
                except ValidationException as e:
                    self.stdout.write(self.style.ERROR(f"  ✗ generate_certificate failed: {e}"))
                    generated_fail += 1

        if dry_run and would_generate_rows:
            self.stdout.write(self.style.SUCCESS(f"\n{'='*72}"))
            self.stdout.write(
                self.style.WARNING(
                    f"Dry run — would issue certificate for {len(would_generate_rows)} micro CohortUser row(s):"
                )
            )
            for line in would_generate_rows:
                self.stdout.write(self.style.SUCCESS(line))
            self.stdout.write(self.style.SUCCESS(f"{'='*72}"))

        summary = (
            f"Summary — skipped_missing_micro_cu={skipped_no_micro_cu}, "
            f"skipped_micro_not_graduated={skipped_micro_not_graduated}, "
            f"eligibility_failed={eligibility_fail}, eligibility_ok={eligibility_ok}"
        )
        if do_generate:
            if dry_run:
                summary += ", generate=dry-run (no DB writes)"
            else:
                summary += f", generate_ok={generated_ok}, generate_failed={generated_fail}"
        self.stdout.write(self.style.SUCCESS(f"\n{'='*72}"))
        self.stdout.write(self.style.SUCCESS(summary))
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"{'='*72}\n"))
