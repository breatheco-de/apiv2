from __future__ import annotations

from logging import getLogger

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from breathecode.admissions.models import Academy, Cohort, CohortUser, Syllabus, SyllabusVersion
from breathecode.assignments.models import Task
from breathecode.authenticate.models import Token
from breathecode.registry.models import Asset

logger = getLogger(__name__)

PREFIX = "source-macro-override-demo"
DEFAULT_ACADEMY_ID = 47
KEEP_SLUG = f"{PREFIX}-keep-project"
DROP_SLUG = f"{PREFIX}-drop-project"


class Command(BaseCommand):
    help = (
        "Create a macro+micro demo where the macro syllabus override deletes one mandatory project. "
        "Enroll --user, set source_macro_cohort, leave tasks PENDING, and print a temporal token."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--user",
            type=str,
            required=True,
            help="Existing user id, email or username to enroll and issue a token for.",
        )
        parser.add_argument(
            "--academy",
            type=int,
            default=DEFAULT_ACADEMY_ID,
            help=f"Academy that owns the demo syllabuses and cohorts (default: {DEFAULT_ACADEMY_ID}).",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete previous demo syllabuses, cohorts, tasks and enrollments for this prefix.",
        )
        parser.add_argument(
            "--hours-length",
            type=int,
            default=24,
            help="Lifetime of the temporal token in hours (default: 24).",
        )

    def handle(self, *args, **options):
        academy = Academy.objects.filter(id=options["academy"]).first()
        if academy is None:
            raise CommandError(f"Academy {options['academy']} was not found")

        user = self._resolve_user(options["user"])
        if options["clear"]:
            self._clear(user)

        keep_slug, drop_slug = self._resolve_project_slugs()
        micro_syllabus = self._upsert_syllabus(f"{PREFIX}-micro", "Override demo micro", academy)
        micro_version = self._upsert_micro_syllabus_version(micro_syllabus, academy, keep_slug, drop_slug)
        macro_syllabus = self._upsert_syllabus(f"{PREFIX}-macro", "Override demo macro", academy)
        macro_version = self._upsert_macro_syllabus_version(macro_syllabus, academy, micro_syllabus.slug, keep_slug)

        micro_cohort = self._upsert_cohort(academy, micro_version, f"{PREFIX}-micro", "Override demo micro")
        macro_cohort = self._upsert_cohort(academy, macro_version, f"{PREFIX}-macro", "Override demo macro")
        macro_cohort.micro_cohorts.set([micro_cohort])
        Cohort.objects.filter(id=macro_cohort.id).update(cohorts_order=str(micro_cohort.id))

        self._upsert_cohort_user(user, macro_cohort, source_macro=None)
        micro_cu = self._upsert_cohort_user(user, micro_cohort, source_macro=macro_cohort)
        self._upsert_pending_projects(user, micro_cohort, keep_slug, drop_slug)

        token, created = Token.get_or_create(user, token_type="temporal", hours_length=options["hours_length"])
        logger.info(
            "seed_source_macro_override_demo done user_id=%s micro_cohort_id=%s macro_cohort_id=%s "
            "micro_cu_id=%s token_created=%s",
            user.id,
            micro_cohort.id,
            macro_cohort.id,
            micro_cu.id,
            created,
        )

        self.stdout.write(self.style.SUCCESS("Demo listo. Completa SOLO el proyecto KEEP (revision APPROVED)."))
        self.stdout.write(f"user_id={user.id} email={user.email} username={user.username}")
        self.stdout.write(f"token={token.key}")
        self.stdout.write(f"Authorization: Token {token.key}")
        self.stdout.write(f"macro_cohort id={macro_cohort.id} slug={macro_cohort.slug}")
        self.stdout.write(f"micro_cohort id={micro_cohort.id} slug={micro_cohort.slug}")
        self.stdout.write(f"source_macro_cohort_id={micro_cu.source_macro_cohort_id}")
        self.stdout.write(f"KEEP project (override, required) slug={keep_slug}")
        self.stdout.write(f"DROP project (base only, deleted by override) slug={drop_slug}")
        self.stdout.write(
            f"GET /v1/admissions/academy/cohort/{micro_cohort.id}/user/{user.id} "
            "(con token de staff) para ver completion.used_macro_override"
        )
        self.stdout.write(
            "Legacy pide KEEP+DROP. Con source_macro_cohort basta KEEP. "
            "Sin completar DROP no deberías graduarte por el pase legacy."
        )

    def _resolve_user(self, raw: str) -> User:
        user = None
        if raw.isdigit():
            user = User.objects.filter(id=int(raw)).first()
        if user is None:
            user = User.objects.filter(email__iexact=raw).first()
        if user is None:
            user = User.objects.filter(username__iexact=raw).first()
        if user is None:
            raise CommandError(f"User {raw!r} was not found")
        return user

    def _resolve_project_slugs(self) -> tuple[str, str]:
        slugs = list(Asset.objects.filter(asset_type="PROJECT").order_by("id").values_list("slug", flat=True)[:2])
        if len(slugs) >= 2:
            return slugs[0], slugs[1]
        return KEEP_SLUG, DROP_SLUG

    def _clear(self, user: User) -> None:
        logger.info("seed_source_macro_override_demo clear user_id=%s", user.id)
        cohort_slugs = [f"{PREFIX}-micro", f"{PREFIX}-macro"]
        cohorts = Cohort.objects.filter(slug__in=cohort_slugs)
        Task.objects.filter(user=user, cohort__in=cohorts).delete()
        CohortUser.objects.filter(user=user, cohort__in=cohorts).delete()
        Cohort.objects.filter(slug__in=cohort_slugs).delete()
        SyllabusVersion.objects.filter(syllabus__slug__in=[f"{PREFIX}-micro", f"{PREFIX}-macro"]).delete()
        Syllabus.objects.filter(slug__in=[f"{PREFIX}-micro", f"{PREFIX}-macro"]).delete()

    def _upsert_syllabus(self, slug: str, name: str, academy: Academy) -> Syllabus:
        syllabus, _ = Syllabus.objects.update_or_create(
            slug=slug,
            defaults={"name": name, "academy_owner": academy, "private": False},
        )
        return syllabus

    def _upsert_micro_syllabus_version(
        self, syllabus: Syllabus, academy: Academy, keep_slug: str, drop_slug: str
    ) -> SyllabusVersion:
        syllabus_json = {
            "slug": syllabus.slug,
            "status": "PUBLISHED",
            "profile": syllabus.slug,
            "version": 1,
            "academy_author": academy.id,
            "days": [
                {
                    "id": 1,
                    "label": "Day 1",
                    "lessons": [],
                    "quizzes": [],
                    "replits": [],
                    "assignments": [
                        {"slug": keep_slug, "title": "Keep project", "mandatory": True, "task_type": "PROJECT"},
                        {"slug": drop_slug, "title": "Drop project", "mandatory": True, "task_type": "PROJECT"},
                    ],
                }
            ],
        }
        return self._upsert_version(syllabus, syllabus_json)

    def _upsert_macro_syllabus_version(
        self, syllabus: Syllabus, academy: Academy, micro_slug: str, keep_slug: str
    ) -> SyllabusVersion:
        syllabus_json = {
            "slug": syllabus.slug,
            "status": "PUBLISHED",
            "profile": syllabus.slug,
            "version": 1,
            "academy_author": academy.id,
            "days": [],
            f"{micro_slug}.v1": {
                "days": [
                    {
                        "assignments": [
                            {"slug": keep_slug, "title": "Keep project", "mandatory": True, "task_type": "PROJECT"},
                            {"status": "DELETED"},
                        ]
                    }
                ]
            },
        }
        return self._upsert_version(syllabus, syllabus_json)

    def _upsert_version(self, syllabus: Syllabus, syllabus_json: dict) -> SyllabusVersion:
        version = SyllabusVersion.objects.filter(syllabus=syllabus, version=1).first()
        if version is None:
            return SyllabusVersion.objects.create(syllabus=syllabus, version=1, json=syllabus_json, status="PUBLISHED")
        SyllabusVersion.objects.filter(id=version.id).update(json=syllabus_json, status="PUBLISHED")
        return SyllabusVersion.objects.get(id=version.id)

    def _upsert_cohort(self, academy: Academy, syllabus_version: SyllabusVersion, slug: str, name: str) -> Cohort:
        defaults = {
            "name": name,
            "academy": academy,
            "syllabus_version": syllabus_version,
            "kickoff_date": timezone.now(),
            "stage": "STARTED",
            "never_ends": True,
            "available_as_saas": True,
            "language": "en",
        }
        cohort = Cohort.objects.filter(slug=slug).first()
        if cohort is None:
            return Cohort.objects.create(slug=slug, **defaults)
        Cohort.objects.filter(id=cohort.id).update(**defaults)
        return Cohort.objects.get(id=cohort.id)

    def _upsert_cohort_user(self, user: User, cohort: Cohort, *, source_macro: Cohort | None) -> CohortUser:
        cohort_user = CohortUser.objects.filter(user=user, cohort=cohort, role="STUDENT").first()
        defaults = {
            "educational_status": "ACTIVE",
            "finantial_status": "FULLY_PAID",
            "source_macro_cohort": source_macro,
        }
        if cohort_user is None:
            return CohortUser.objects.create(user=user, cohort=cohort, role="STUDENT", **defaults)

        CohortUser.objects.filter(id=cohort_user.id).update(**defaults)
        return CohortUser.objects.get(id=cohort_user.id)

    def _upsert_pending_projects(self, user: User, cohort: Cohort, keep_slug: str, drop_slug: str) -> None:
        for slug, title in ((keep_slug, "Keep project"), (drop_slug, "Drop project")):
            asset = Asset.objects.filter(slug=slug).first()
            Task.objects.update_or_create(
                user=user,
                cohort=cohort,
                task_type="PROJECT",
                associated_slug=slug,
                defaults={
                    "title": asset.title if asset and asset.title else title,
                    "task_status": "PENDING",
                    "revision_status": "PENDING",
                },
            )
