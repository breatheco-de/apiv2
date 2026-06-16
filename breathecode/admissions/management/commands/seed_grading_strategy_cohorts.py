from __future__ import annotations

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from breathecode.admissions.models import Academy, City, Cohort, CohortUser, Country, Syllabus, SyllabusVersion
from breathecode.assignments.models import Task
from breathecode.certificate.models import LayoutDesign, Specialty
from breathecode.payments.models import CohortSet, CohortSetCohort, Currency, FinancingOption, Plan, PlanFinancing


PREFIX = "grading-strategy-demo"


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

    def handle(self, *args, **options):
        if options["clear"]:
            self._clear()

        country, _ = Country.objects.get_or_create(code="GS", defaults={"name": "Grading"})
        city, _ = City.objects.get_or_create(name="Grading City", country=country)
        academy = self._upsert_academy(country, city)
        currency, _ = Currency.objects.get_or_create(code="USD", defaults={"name": "US Dollar", "decimals": 2})
        country.currencies.add(currency)
        Academy.objects.filter(id=academy.id).update(main_currency=currency)
        academy = Academy.objects.get(id=academy.id)

        teacher, _ = User.objects.get_or_create(
            username=f"{PREFIX}-teacher",
            defaults={"email": f"{PREFIX}-teacher@example.com", "first_name": "Demo", "last_name": "Teacher"},
        )
        complete_student, _ = User.objects.get_or_create(
            username=f"{PREFIX}-complete",
            defaults={"email": f"{PREFIX}-complete@example.com", "first_name": "Complete", "last_name": "Student"},
        )
        incomplete_student, _ = User.objects.get_or_create(
            username=f"{PREFIX}-incomplete",
            defaults={"email": f"{PREFIX}-incomplete@example.com", "first_name": "Incomplete", "last_name": "Student"},
        )
        target_user = self._get_target_user(options["user"]) if options["user"] else None

        LayoutDesign.objects.update_or_create(
            slug=f"{PREFIX}-layout",
            defaults={
                "name": "Grading Demo",
                "academy": academy,
                "is_default": True,
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
        for slug, name, strategy, required_types in scenarios:
            syllabus = self._upsert_syllabus(slug, name)
            syllabus_version = self._upsert_syllabus_version(syllabus, slug, strategy)
            cohort = self._upsert_cohort(academy, syllabus_version, slug, name)
            cohorts.append(cohort)
            self._upsert_specialty(academy, syllabus)
            self._upsert_cohort_user(teacher, cohort, "TEACHER", "ACTIVE")
            complete_cu = self._upsert_cohort_user(complete_student, cohort, "STUDENT", "ACTIVE")
            incomplete_cu = self._upsert_cohort_user(incomplete_student, cohort, "STUDENT", "ACTIVE")
            if target_user:
                self._upsert_cohort_user(target_user, cohort, "STUDENT", "ACTIVE")
            self._upsert_tasks(complete_student, cohort, slug, required_types, complete=True)
            self._upsert_tasks(incomplete_student, cohort, slug, required_types, complete=False)
            created.append((cohort.slug, complete_cu.id, incomplete_cu.id))

        cohort_set = self._upsert_cohort_set(academy, cohorts)
        plan = self._upsert_plan(academy, currency, cohort_set)
        if target_user:
            financing = self._upsert_plan_financing(target_user, academy, currency, plan, cohort_set, cohorts)
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
        self.stdout.write(self.style.SUCCESS(f"Created plan {plan.slug} with cohort_set {cohort_set.slug}"))

    def _get_target_user(self, value: str) -> User:
        query = {"id": int(value)} if value.isdigit() else {"email": value}
        user = User.objects.filter(**query).first()
        if user is None and not value.isdigit():
            user = User.objects.filter(username=value).first()
        if user is None:
            raise CommandError(f"User {value} was not found by id, email or username")
        return user

    def _upsert_academy(self, country: Country, city: City) -> Academy:
        defaults = {
            "name": "Grading Strategy Demo",
            "logo_url": "https://example.com/logo.png",
            "street_address": "Demo street",
            "city": city,
            "country": country,
            "available_as_saas": True,
        }
        academy = Academy.objects.filter(slug=PREFIX).first()
        if academy is None:
            Academy.objects.bulk_create([Academy(slug=PREFIX, **defaults)])
            return Academy.objects.get(slug=PREFIX)

        Academy.objects.filter(id=academy.id).update(**defaults)
        return Academy.objects.get(id=academy.id)

    def _clear(self):
        PlanFinancing.objects.filter(plans__slug=f"{PREFIX}-plan").delete()
        Plan.objects.filter(slug=f"{PREFIX}-plan").delete()
        CohortSet.objects.filter(slug=f"{PREFIX}-cohort-set").delete()
        Cohort.objects.filter(slug__startswith=PREFIX).delete()
        Specialty.objects.filter(slug__startswith=PREFIX).delete()
        Syllabus.objects.filter(slug__startswith=PREFIX).delete()
        LayoutDesign.objects.filter(slug=f"{PREFIX}-layout").delete()
        User.objects.filter(username__startswith=PREFIX).delete()
        Academy.objects.filter(slug=PREFIX).delete()
        City.objects.filter(name="Grading City", country_id="GS").delete()
        Country.objects.filter(code="GS").delete()

    def _upsert_syllabus(self, slug: str, name: str) -> Syllabus:
        defaults = {
            "name": f"Demo {name}",
            "duration_in_days": 2,
            "duration_in_hours": 2,
            "week_hours": 2,
        }
        syllabus_slug = f"{PREFIX}-{slug}"
        syllabus = Syllabus.objects.filter(slug=syllabus_slug).first()
        if syllabus is None:
            Syllabus.objects.bulk_create([Syllabus(slug=syllabus_slug, **defaults)])
            return Syllabus.objects.get(slug=syllabus_slug)

        Syllabus.objects.filter(id=syllabus.id).update(**defaults)
        return Syllabus.objects.get(id=syllabus.id)

    def _upsert_syllabus_version(self, syllabus: Syllabus, slug: str, strategy: dict) -> SyllabusVersion:
        syllabus_json = {
            **strategy,
            "days": [
                {
                    "label": "Day 1",
                    "lessons": [{"slug": f"{PREFIX}-{slug}-lesson-1", "mandatory": True}],
                    "replits": [{"slug": f"{PREFIX}-{slug}-exercise-1", "mandatory": True}],
                },
                {
                    "label": "Day 2",
                    "quizzes": [{"slug": f"{PREFIX}-{slug}-quiz-1", "mandatory": True}],
                    "assignments": [{"slug": f"{PREFIX}-{slug}-project-1", "mandatory": True}],
                },
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

    def _upsert_cohort(self, academy: Academy, syllabus_version: SyllabusVersion, slug: str, name: str) -> Cohort:
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
        cohort_slug = f"{PREFIX}-{slug}"
        cohort = Cohort.objects.filter(slug=cohort_slug).first()
        if cohort is None:
            Cohort.objects.bulk_create([Cohort(slug=cohort_slug, **defaults)])
            return Cohort.objects.get(slug=cohort_slug)

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

    def _upsert_tasks(self, user: User, cohort: Cohort, slug: str, required_types: list[str], *, complete: bool):
        task_data = [
            ("LESSON", f"{PREFIX}-{slug}-lesson-1"),
            ("EXERCISE", f"{PREFIX}-{slug}-exercise-1"),
            ("QUIZ", f"{PREFIX}-{slug}-quiz-1"),
            ("PROJECT", f"{PREFIX}-{slug}-project-1"),
        ]
        for task_type, associated_slug in task_data:
            should_complete = complete or task_type not in required_types
            revision_status = "PENDING"
            task_status = "PENDING"
            if should_complete:
                task_status = "DONE"
                revision_status = "APPROVED" if task_type != "PROJECT" else "APPROVED"

            defaults = {
                "title": associated_slug.replace("-", " ").title(),
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
