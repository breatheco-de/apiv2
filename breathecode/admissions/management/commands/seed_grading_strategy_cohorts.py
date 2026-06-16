from __future__ import annotations

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from breathecode.admissions.models import Academy, Cohort, CohortUser, Syllabus, SyllabusVersion
from breathecode.assignments.models import Task
from breathecode.certificate.models import LayoutDesign, Specialty
from breathecode.payments.models import CohortSet, CohortSetCohort, Currency, FinancingOption, Plan, PlanFinancing
from breathecode.registry.models import Asset


PREFIX = "grading-strategy-demo"
DEFAULT_ACADEMY_ID = 47
DEFAULT_TEACHER_USER_ID = 1

PREFERRED_ASSET_SLUGS = {
    "LESSON": ["intro-to-numpy", "intro-to-python-pandas"],
    "EXERCISE": ["numpy-exercises-tutorial", "introduction-to-telemetry-en"],
    "QUIZ": [],
    "PROJECT": [],
}


class Command(BaseCommand):
    help = "Create short demo cohorts and syllabuses for completion grading strategies."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete previous grading strategy demo data before creating it again.",
        )
        parser.add_argument(
            "--user",
            type=str,
            default=None,
            help="Existing user id, email or username to enroll in the demo plan and cohorts.",
        )
        parser.add_argument(
            "--academy",
            type=int,
            default=DEFAULT_ACADEMY_ID,
            help=f"Academy that owns the demo syllabuses and cohorts (default: {DEFAULT_ACADEMY_ID}).",
        )
        parser.add_argument(
            "--teacher",
            type=int,
            default=DEFAULT_TEACHER_USER_ID,
            help=f"Existing user id to assign as TEACHER on each demo cohort (default: {DEFAULT_TEACHER_USER_ID}).",
        )

    def handle(self, *args, **options):
        academy = Academy.objects.filter(id=options["academy"]).first()
        if academy is None:
            raise CommandError(f"Academy {options['academy']} was not found")

        teacher = User.objects.filter(id=options["teacher"]).first()
        if teacher is None:
            raise CommandError(f"Teacher user {options['teacher']} was not found")

        if options["clear"]:
            self._clear()

        currency = academy.main_currency or Currency.objects.filter(code="USD").first()
        if currency is None:
            raise CommandError("Academy has no main currency and USD is not configured")

        complete_student, _ = User.objects.get_or_create(
            username=f"{PREFIX}-complete",
            defaults={"email": f"{PREFIX}-complete@example.com", "first_name": "Complete", "last_name": "Student"},
        )
        incomplete_student, _ = User.objects.get_or_create(
            username=f"{PREFIX}-incomplete",
            defaults={"email": f"{PREFIX}-incomplete@example.com", "first_name": "Incomplete", "last_name": "Student"},
        )
        target_user = self._get_target_user(options["user"]) if options["user"] else None
        demo_assets = self._resolve_demo_assets()

        LayoutDesign.objects.update_or_create(
            slug=f"{PREFIX}-layout",
            defaults={
                "name": "Grading Demo",
                "academy": academy,
                "is_default": False,
                "background_url": "https://example.com/certificate-bg.png",
            },
        )

        scenarios = [
            (
                "full",
                "Full Completion",
                {"grading_strategy": {"completion": {"type": "FULL_COMPLETION"}}},
                ["PROJECT", "EXERCISE", "LESSON", "QUIZ"],
            ),
            (
                "partial-projects",
                "Partial Projects",
                {
                    "grading_strategy": {
                        "completion": {
                            "type": "PARTIAL_COMPLETION",
                            "requirements": {"PROJECT": {"min_percent": 100}},
                        }
                    }
                },
                ["PROJECT"],
            ),
            (
                "partial-exercises",
                "Partial Exercises",
                {
                    "grading_strategy": {
                        "completion": {
                            "type": "PARTIAL_COMPLETION",
                            "requirements": {"EXERCISE": {"min_percent": 100}},
                        }
                    }
                },
                ["EXERCISE"],
            ),
            (
                "partial-projects-exercises",
                "Partial Projects Exercises",
                {
                    "grading_strategy": {
                        "completion": {
                            "type": "PARTIAL_COMPLETION",
                            "requirements": {
                                "PROJECT": {"min_percent": 100},
                                "EXERCISE": {"min_percent": 100},
                            },
                        }
                    }
                },
                ["PROJECT", "EXERCISE"],
            ),
            (
                "partial-lessons-quizzes",
                "Partial Lessons Quizzes",
                {
                    "grading_strategy": {
                        "completion": {
                            "type": "PARTIAL_COMPLETION",
                            "requirements": {
                                "LESSON": {"min_percent": 100},
                                "QUIZ": {"min_percent": 100},
                            },
                        }
                    }
                },
                ["LESSON", "QUIZ"],
            ),
        ]

        created = []
        cohorts = []
        micro_syllabus_slugs: list[str] = []
        for slug, name, strategy, required_types in scenarios:
            syllabus = self._upsert_syllabus(slug, name, academy)
            micro_syllabus_slugs.append(syllabus.slug)
            syllabus_version = self._upsert_syllabus_version(syllabus, slug, strategy, academy, demo_assets)
            cohort = self._upsert_cohort(academy, syllabus_version, slug, name)
            cohorts.append(cohort)
            self._upsert_specialty(academy, syllabus)
            self._upsert_cohort_user(teacher, cohort, "TEACHER", "ACTIVE")
            complete_cu = self._upsert_cohort_user(complete_student, cohort, "STUDENT", "ACTIVE")
            incomplete_cu = self._upsert_cohort_user(incomplete_student, cohort, "STUDENT", "ACTIVE")
            if target_user:
                self._upsert_cohort_user(target_user, cohort, "STUDENT", "ACTIVE")
            self._upsert_tasks(complete_student, cohort, demo_assets, required_types, complete=True)
            self._upsert_tasks(incomplete_student, cohort, demo_assets, required_types, complete=False)
            created.append((cohort.slug, complete_cu.id, incomplete_cu.id))

        macro_cohort = self._upsert_macro_cohort(academy, cohorts, micro_syllabus_slugs)
        self._upsert_cohort_user(teacher, macro_cohort, "TEACHER", "ACTIVE")
        self._upsert_cohort_user(complete_student, macro_cohort, "STUDENT", "ACTIVE")
        self._upsert_cohort_user(incomplete_student, macro_cohort, "STUDENT", "ACTIVE")
        if target_user:
            self._upsert_cohort_user(target_user, macro_cohort, "STUDENT", "ACTIVE")

        cohorts_with_macro = [macro_cohort, *cohorts]
        cohort_set = self._upsert_cohort_set(academy, cohorts_with_macro)
        plan = self._upsert_plan(academy, currency, cohort_set)
        if target_user:
            financing = self._upsert_plan_financing(target_user, academy, currency, plan, cohort_set, cohorts_with_macro)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Assigned user {target_user.id} ({target_user.email}) to plan {plan.slug} "
                    f"with plan_financing={financing.id}"
                )
            )

        for cohort_slug, complete_cu_id, incomplete_cu_id in created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created {cohort_slug}: complete cohort_user={complete_cu_id}, "
                    f"incomplete cohort_user={incomplete_cu_id}"
                )
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Created macro cohort {macro_cohort.slug} with micro_cohorts="
                f"{','.join(c.slug for c in cohorts)}"
            )
        )
        self.stdout.write(self.style.SUCCESS(f"Created plan {plan.slug} with cohort_set {cohort_set.slug}"))

    def _get_target_user(self, value: str) -> User:
        query = {"id": int(value)} if value.isdigit() else {"email": value}
        user = User.objects.filter(**query).first()
        if user is None and not value.isdigit():
            user = User.objects.filter(username=value).first()
        if user is None:
            raise CommandError(f"User {value} was not found by id, email or username")
        return user

    def _resolve_demo_assets(self) -> dict[str, str]:
        asset_type_map = {
            "LESSON": "LESSON",
            "EXERCISE": "EXERCISE",
            "QUIZ": "QUIZ",
            "PROJECT": "PROJECT",
        }
        resolved: dict[str, str] = {}

        for key, asset_type in asset_type_map.items():
            preferred = PREFERRED_ASSET_SLUGS.get(key, [])
            asset = None
            if preferred:
                asset = Asset.objects.filter(slug__in=preferred, status="PUBLISHED").order_by("id").first()

            if asset is None:
                asset = Asset.objects.filter(asset_type=asset_type, status="PUBLISHED").order_by("id").first()

            if asset is None:
                resolved[key] = f"{PREFIX}-asset-{key.lower()}"
                self.stdout.write(
                    self.style.WARNING(
                        f"No published {asset_type} asset found in registry; using synthetic slug {resolved[key]}"
                    )
                )
                continue

            resolved[key] = asset.slug
            self.stdout.write(self.style.SUCCESS(f"Using {asset_type} asset: {asset.slug}"))

        return resolved

    def _asset_entry(self, slug: str) -> dict:
        asset = Asset.objects.filter(slug=slug).first()
        title = asset.title if asset and asset.title else slug.replace("-", " ").title()
        entry = {
            "slug": slug,
            "title": title,
            "mandatory": True,
            "translations": {
                "us": {"slug": slug, "title": title},
                "es": {"slug": slug, "title": title},
            },
        }
        return entry

    def _build_day(
        self,
        day_id: int,
        label_en: str,
        label_es: str,
        position: int,
        *,
        lessons: list | None = None,
        replits: list | None = None,
        quizzes: list | None = None,
        assignments: list | None = None,
    ) -> dict:
        return {
            "id": day_id,
            "label": {"en": label_en, "es": label_es},
            "lessons": lessons or [],
            "quizzes": quizzes or [],
            "replits": replits or [],
            "homework": "",
            "position": position,
            "profiles": [],
            "assignments": assignments or [],
            "description": {"en": label_en, "es": label_es},
            "key-concepts": [],
            "technologies": [],
            "asset_requests": [],
            "duration_in_days": 1,
            "teacher_instructions": {"en": "", "es": ""},
        }

    def _clear(self):
        PlanFinancing.objects.filter(plans__slug=f"{PREFIX}-plan").delete()
        Plan.objects.filter(slug=f"{PREFIX}-plan").delete()
        CohortSet.objects.filter(slug=f"{PREFIX}-cohort-set").delete()
        Cohort.objects.filter(slug__startswith=PREFIX).delete()
        Specialty.objects.filter(slug__startswith=PREFIX).delete()
        Syllabus.objects.filter(slug__startswith=PREFIX).delete()
        LayoutDesign.objects.filter(slug=f"{PREFIX}-layout").delete()
        User.objects.filter(username__in=[f"{PREFIX}-complete", f"{PREFIX}-incomplete"]).delete()

    def _upsert_syllabus(self, slug: str, name: str, academy: Academy) -> Syllabus:
        defaults = {
            "name": f"Demo {name}",
            "duration_in_days": 2,
            "duration_in_hours": 2,
            "week_hours": 2,
            "academy_owner": academy,
            "private": False,
        }
        syllabus_slug = f"{PREFIX}-{slug}"
        syllabus = Syllabus.objects.filter(slug=syllabus_slug).first()
        if syllabus is None:
            Syllabus.objects.bulk_create([Syllabus(slug=syllabus_slug, **defaults)])
            return Syllabus.objects.get(slug=syllabus_slug)

        Syllabus.objects.filter(id=syllabus.id).update(**defaults)
        return Syllabus.objects.get(id=syllabus.id)

    def _upsert_syllabus_version(
        self,
        syllabus: Syllabus,
        slug: str,
        strategy: dict,
        academy: Academy,
        demo_assets: dict[str, str],
    ) -> SyllabusVersion:
        lesson = self._asset_entry(demo_assets["LESSON"])
        exercise = self._asset_entry(demo_assets["EXERCISE"])
        quiz = self._asset_entry(demo_assets["QUIZ"])
        project = self._asset_entry(demo_assets["PROJECT"])

        syllabus_json = {
            **strategy,
            "slug": syllabus.slug,
            "status": "PUBLISHED",
            "profile": syllabus.slug,
            "version": 1,
            "academy_author": academy.id,
            "duration_in_days": 2,
            "duration_in_hours": 2,
            "days": [
                self._build_day(
                    1,
                    "Day 1",
                    "Día 1",
                    1,
                    lessons=[lesson],
                    replits=[exercise],
                ),
                self._build_day(
                    2,
                    "Day 2",
                    "Día 2",
                    2,
                    quizzes=[quiz],
                    assignments=[project],
                ),
            ],
        }
        syllabus_version = SyllabusVersion.objects.filter(syllabus=syllabus, version=1).first()
        if syllabus_version is None:
            SyllabusVersion.objects.bulk_create(
                [SyllabusVersion(syllabus=syllabus, version=1, json=syllabus_json, status="PUBLISHED")]
            )
            return SyllabusVersion.objects.get(syllabus=syllabus, version=1)

        SyllabusVersion.objects.filter(id=syllabus_version.id).update(json=syllabus_json, status="PUBLISHED")
        return SyllabusVersion.objects.get(id=syllabus_version.id)

    def _upsert_macro_syllabus_version(
        self,
        syllabus: Syllabus,
        academy: Academy,
        micro_syllabus_slugs: list[str],
    ) -> SyllabusVersion:
        syllabus_json = {
            "slug": syllabus.slug,
            "status": "PUBLISHED",
            "profile": syllabus.slug,
            "version": 1,
            "academy_author": academy.id,
            "duration_in_days": len(micro_syllabus_slugs),
            "duration_in_hours": len(micro_syllabus_slugs) * 2,
            "days": [],
        }
        for index, micro_slug in enumerate(micro_syllabus_slugs):
            syllabus_json[f"{index}:{micro_slug}.v1"] = {"days": []}

        syllabus_version = SyllabusVersion.objects.filter(syllabus=syllabus, version=1).first()
        if syllabus_version is None:
            SyllabusVersion.objects.bulk_create(
                [SyllabusVersion(syllabus=syllabus, version=1, json=syllabus_json, status="PUBLISHED")]
            )
            return SyllabusVersion.objects.get(syllabus=syllabus, version=1)

        SyllabusVersion.objects.filter(id=syllabus_version.id).update(json=syllabus_json, status="PUBLISHED")
        return SyllabusVersion.objects.get(id=syllabus_version.id)

    def _upsert_macro_cohort(
        self,
        academy: Academy,
        micro_cohorts: list[Cohort],
        micro_syllabus_slugs: list[str],
    ) -> Cohort:
        macro_syllabus = self._upsert_syllabus("macro", "Grading Strategies", academy)
        macro_syllabus_version = self._upsert_macro_syllabus_version(macro_syllabus, academy, micro_syllabus_slugs)
        macro_cohort = self._upsert_cohort(
            academy,
            macro_syllabus_version,
            "macro",
            "Grading Strategies",
            cohort_slug=f"{PREFIX}-macro",
        )
        macro_cohort.micro_cohorts.set(micro_cohorts)
        cohorts_order = ",".join(str(cohort.id) for cohort in micro_cohorts)
        Cohort.objects.filter(id=macro_cohort.id).update(cohorts_order=cohorts_order)
        return Cohort.objects.get(id=macro_cohort.id)

    def _upsert_cohort(
        self,
        academy: Academy,
        syllabus_version: SyllabusVersion,
        slug: str,
        name: str,
        *,
        cohort_slug: str | None = None,
    ) -> Cohort:
        defaults = {
            "name": f"Demo {name}",
            "academy": academy,
            "syllabus_version": syllabus_version,
            "kickoff_date": timezone.now(),
            "stage": "ENDED",
            "current_day": 2,
            "never_ends": True,
            "available_as_saas": True,
            "language": "en",
        }
        resolved_slug = cohort_slug or f"{PREFIX}-{slug}"
        cohort = Cohort.objects.filter(slug=resolved_slug).first()
        if cohort is None:
            Cohort.objects.bulk_create([Cohort(slug=resolved_slug, **defaults)])
            return Cohort.objects.get(slug=resolved_slug)

        Cohort.objects.filter(id=cohort.id).update(**defaults)
        return Cohort.objects.get(id=cohort.id)

    def _upsert_specialty(self, academy: Academy, syllabus: Syllabus):
        specialty, _ = Specialty.objects.update_or_create(
            slug=syllabus.slug,
            defaults={"name": syllabus.name, "academy": academy, "status": "ACTIVE"},
        )
        specialty.syllabuses.set([syllabus])

    def _upsert_cohort_set(self, academy: Academy, cohorts: list[Cohort]) -> CohortSet:
        cohort_set, _ = CohortSet.objects.update_or_create(slug=f"{PREFIX}-cohort-set", defaults={"academy": academy})
        CohortSetCohort.objects.filter(cohort_set=cohort_set).exclude(cohort__in=cohorts).delete()
        for cohort in cohorts:
            CohortSetCohort.objects.get_or_create(cohort_set=cohort_set, cohort=cohort)
        return cohort_set

    def _upsert_plan(self, academy: Academy, currency: Currency, cohort_set: CohortSet) -> Plan:
        plan, _ = Plan.objects.update_or_create(
            slug=f"{PREFIX}-plan",
            defaults={
                "title": "Grading Strategy Demo Plan",
                "owner": academy,
                "currency": currency,
                "cohort_set": cohort_set,
                "status": "ACTIVE",
                "is_renewable": False,
                "time_of_life": 1,
                "time_of_life_unit": "MONTH",
            },
        )
        financing_option, _ = FinancingOption.objects.get_or_create(
            academy=academy,
            how_many_months=1,
            monthly_price=1,
            currency=currency,
        )
        plan.financing_options.set([financing_option])
        return plan

    def _upsert_plan_financing(
        self,
        user: User,
        academy: Academy,
        currency: Currency,
        plan: Plan,
        cohort_set: CohortSet,
        cohorts: list[Cohort],
    ) -> PlanFinancing:
        now = timezone.now()
        financing, _ = PlanFinancing.objects.update_or_create(
            user=user,
            academy=academy,
            selected_cohort_set=cohort_set,
            defaults={
                "next_payment_at": now,
                "valid_until": now + timezone.timedelta(days=30),
                "plan_expires_at": now + timezone.timedelta(days=30),
                "monthly_price": 0,
                "currency": currency,
                "how_many_installments": 1,
                "installments_paid": 1,
                "status": "ACTIVE",
                "externally_managed": True,
            },
        )
        financing.plans.set([plan])
        financing.joined_cohorts.set(cohorts)
        return financing

    def _upsert_cohort_user(self, user: User, cohort: Cohort, role: str, educational_status: str) -> CohortUser:
        defaults = {
            "educational_status": educational_status,
            "finantial_status": "FULLY_PAID",
        }
        cohort_user = CohortUser.objects.filter(user=user, cohort=cohort, role=role).first()
        if cohort_user is None:
            CohortUser.objects.bulk_create([CohortUser(user=user, cohort=cohort, role=role, **defaults)])
            return CohortUser.objects.get(user=user, cohort=cohort, role=role)

        CohortUser.objects.filter(id=cohort_user.id).update(**defaults)
        return CohortUser.objects.get(id=cohort_user.id)

    def _upsert_tasks(
        self,
        user: User,
        cohort: Cohort,
        demo_assets: dict[str, str],
        required_types: list[str],
        *,
        complete: bool,
    ):
        task_data = [
            ("LESSON", demo_assets["LESSON"]),
            ("EXERCISE", demo_assets["EXERCISE"]),
            ("QUIZ", demo_assets["QUIZ"]),
            ("PROJECT", demo_assets["PROJECT"]),
        ]
        for task_type, associated_slug in task_data:
            should_complete = complete or task_type not in required_types
            revision_status = "PENDING"
            task_status = "PENDING"
            if should_complete:
                task_status = "DONE"
                revision_status = "APPROVED"

            asset = Asset.objects.filter(slug=associated_slug).first()
            title = asset.title if asset and asset.title else associated_slug.replace("-", " ").title()

            defaults = {
                "title": title,
                "task_status": task_status,
                "revision_status": revision_status,
            }
            task = Task.objects.filter(
                user=user,
                cohort=cohort,
                task_type=task_type,
                associated_slug=associated_slug,
            ).first()
            if task is None:
                Task.objects.bulk_create(
                    [
                        Task(
                            user=user,
                            cohort=cohort,
                            task_type=task_type,
                            associated_slug=associated_slug,
                            **defaults,
                        )
                    ]
                )
            else:
                Task.objects.filter(id=task.id).update(**defaults)
