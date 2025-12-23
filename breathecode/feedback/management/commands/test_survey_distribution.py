"""
Management command to test survey distribution system.

This command simulates users completing modules and shows how surveys are distributed
based on priority probabilities.

Usage:
    python manage.py test_survey_distribution --study-id 1 --users 100 --module 1
    python manage.py test_survey_distribution --create-study --cohort-id 1183 --users 50
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from breathecode.feedback.models import (
    SurveyConfiguration,
    SurveyStudy,
    SurveyResponse,
    SurveyQuestionTemplate,
)
from breathecode.admissions.models import Cohort, CohortUser
from breathecode.authenticate.models import User
from breathecode.feedback.utils.survey_manager import SurveyManager
import random


class Command(BaseCommand):
    help = "Test survey distribution system with simulated user completions"

    def add_arguments(self, parser):
        parser.add_argument(
            "--study-id",
            type=int,
            help="ID of the SurveyStudy to test (if not provided, will create a new one)",
        )
        parser.add_argument(
            "--create-study",
            action="store_true",
            help="Create a new study for testing",
        )
        parser.add_argument(
            "--cohort-id",
            type=int,
            help="Cohort ID to use for creating test study",
        )
        parser.add_argument(
            "--users",
            type=int,
            default=50,
            help="Number of users to simulate (default: 50)",
        )
        parser.add_argument(
            "--module",
            type=int,
            help="Specific module to test (if not provided, tests all modules in configs)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would happen without creating surveys",
        )
        parser.add_argument(
            "--clear-existing",
            action="store_true",
            help="Clear existing survey responses for the study before testing",
        )

    def handle(self, *args, **options):
        study_id = options.get("study_id")
        create_study = options.get("create_study")
        cohort_id = options.get("cohort_id")
        num_users = options.get("users")
        module = options.get("module")
        dry_run = options.get("dry_run")
        clear_existing = options.get("clear_existing")

        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN MODE - No surveys will be created"))

        # Get or create study
        if create_study:
            if not cohort_id:
                self.stdout.write(
                    self.style.ERROR("❌ --cohort-id is required when using --create-study")
                )
                return
            study = self._create_test_study(cohort_id, dry_run)
            if not study:
                return
        elif study_id:
            try:
                study = SurveyStudy.objects.get(id=study_id)
            except SurveyStudy.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"❌ Study with ID {study_id} not found"))
                return
        else:
            self.stdout.write(
                self.style.ERROR("❌ Must provide either --study-id or --create-study")
            )
            return

        # Clear existing responses if requested
        if clear_existing and not dry_run:
            deleted = SurveyResponse.objects.filter(survey_study=study).delete()[0]
            self.stdout.write(
                self.style.SUCCESS(f"🗑️  Deleted {deleted} existing survey responses")
            )

        # Get configs for this study
        configs = study.survey_configurations.filter(is_active=True)
        if not configs.exists():
            self.stdout.write(
                self.style.ERROR(f"❌ Study {study.id} has no active configurations")
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"\n📊 Testing Study: {study.title} (ID: {study.id})\n"
            )
        )

        # Display configs
        self.stdout.write("📋 Configurations:")
        for config in configs:
            module_info = ""
            if config.syllabus:
                config_module = config.syllabus.get("module")
                if config_module is not None:
                    module_info = f" | Module: {config_module}"
            
            priority = config.priority if config.priority is not None else 100.0
            self.stdout.write(
                f"  • Config {config.id}: priority={priority}%{module_info} | trigger={config.trigger_type}"
            )

        # Get cohort for context
        cohort = None
        if cohort_id:
            try:
                cohort = Cohort.objects.get(id=cohort_id)
            except Cohort.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"⚠️  Cohort {cohort_id} not found, using first available")
                )

        if not cohort and configs.first().cohorts.exists():
            cohort = configs.first().cohorts.first()

        if not cohort:
            self.stdout.write(
                self.style.ERROR("❌ No cohort found. Cannot simulate module completion.")
            )
            return

        # Get users from cohort
        cohort_users = CohortUser.objects.filter(cohort=cohort, role="STUDENT")
        available_users = list(cohort_users.values_list("user_id", flat=True))

        if len(available_users) < num_users:
            self.stdout.write(
                self.style.WARNING(
                    f"⚠️  Only {len(available_users)} users available in cohort, using all of them"
                )
            )
            num_users = len(available_users)

        # Select users to simulate
        test_users = random.sample(available_users, min(num_users, len(available_users)))
        users = User.objects.filter(id__in=test_users)

        self.stdout.write(f"\n👥 Simulating {len(users)} users completing modules\n")

        # Determine which modules to test
        modules_to_test = []
        if module is not None:
            modules_to_test = [module]
        else:
            # Get all modules from configs
            for config in configs:
                if config.syllabus:
                    config_module = config.syllabus.get("module")
                    if config_module is not None and config_module not in modules_to_test:
                        modules_to_test.append(config_module)
            
            if not modules_to_test:
                modules_to_test = [0]  # Default to module 0

        # Simulate completions
        results = {}
        created_count = 0
        skipped_count = 0

        for user in users:
            for test_module in modules_to_test:
                # Create context for module completion
                context = {
                    "academy": cohort.academy,
                    "cohort": cohort,
                    "cohort_id": cohort.id,
                    "cohort_slug": cohort.slug,
                    "syllabus_slug": cohort.syllabus_version.syllabus.slug if cohort.syllabus_version else None,
                    "syllabus_version": cohort.syllabus_version.version if cohort.syllabus_version else None,
                    "module": test_module,
                    "completed_at": timezone.now().isoformat(),
                }

                # Trigger survey
                if not dry_run:
                    manager = SurveyManager(
                        user=user,
                        trigger_type=SurveyConfiguration.TriggerType.MODULE_COMPLETION,
                        context=context,
                    )
                    survey_response = manager.trigger_survey_for_user()
                    
                    if survey_response:
                        created_count += 1
                        config_id = survey_response.survey_config.id
                        if config_id not in results:
                            results[config_id] = {
                                "count": 0,
                                "users": [],
                                "module": test_module,
                            }
                        results[config_id]["count"] += 1
                        results[config_id]["users"].append(user.id)
                    else:
                        skipped_count += 1
                else:
                    # Dry run: simulate the logic
                    for config in configs:
                        config_module = (config.syllabus or {}).get("module")
                        if config_module is not None and config_module != test_module:
                            continue
                        
                        priority = config.priority if config.priority is not None else 100.0
                        hash_input = f"{user.id}_{config.id}_{test_module}"
                        hash_value = hash(hash_input)
                        random_value = abs(hash_value) % 100
                        
                        if random_value < priority:
                            if config.id not in results:
                                results[config.id] = {
                                    "count": 0,
                                    "users": [],
                                    "module": test_module,
                                }
                            results[config.id]["count"] += 1
                            results[config.id]["users"].append(user.id)
                        else:
                            skipped_count += 1

        # Display results
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("📊 RESULTS"))
        self.stdout.write("=" * 80 + "\n")

        if dry_run:
            self.stdout.write(self.style.WARNING("(DRY RUN - No surveys were actually created)\n"))

        total_expected = len(users) * len(modules_to_test)
        total_created = sum(r["count"] for r in results.values())

        self.stdout.write(f"Total users simulated: {len(users)}")
        self.stdout.write(f"Modules tested: {modules_to_test}")
        self.stdout.write(f"Total completion events: {total_expected}")
        self.stdout.write(f"Surveys created: {total_created}")
        self.stdout.write(f"Surveys skipped: {skipped_count}")
        self.stdout.write(f"Coverage: {(total_created/total_expected*100):.1f}%\n")

        self.stdout.write("\n📈 Distribution by Configuration:\n")
        for config in configs:
            config_id = config.id
            priority = config.priority if config.priority is not None else 100.0
            module_info = ""
            if config.syllabus:
                config_module = config.syllabus.get("module")
                if config_module is not None:
                    module_info = f" (Module {config_module})"
            
            result = results.get(config_id, {"count": 0, "users": []})
            count = result["count"]
            expected = len(users) * (priority / 100.0) if config_id in results else 0
            
            percentage = (count / len(users) * 100) if len(users) > 0 else 0
            expected_percentage = priority
            
            status = "✅" if abs(percentage - expected_percentage) < 10 else "⚠️"
            
            self.stdout.write(
                f"  {status} Config {config_id}{module_info}:"
            )
            self.stdout.write(
                f"    Priority: {priority}% | Created: {count}/{len(users)} ({percentage:.1f}%) | Expected: ~{expected_percentage:.1f}%"
            )

        # Show actual vs expected
        self.stdout.write("\n📊 Priority vs Actual Distribution:\n")
        for config in configs:
            config_id = config.id
            priority = config.priority if config.priority is not None else 100.0
            result = results.get(config_id, {"count": 0})
            actual = (result["count"] / len(users) * 100) if len(users) > 0 else 0
            diff = actual - priority
            
            bar_length = 40
            priority_bar = "█" * int(priority / 100 * bar_length)
            actual_bar = "█" * int(actual / 100 * bar_length)
            
            self.stdout.write(f"  Config {config_id}:")
            self.stdout.write(f"    Expected: [{priority_bar:<{bar_length}}] {priority:.1f}%")
            self.stdout.write(f"    Actual:   [{actual_bar:<{bar_length}}] {actual:.1f}% (diff: {diff:+.1f}%)")

        self.stdout.write("\n" + "=" * 80 + "\n")

    def _create_test_study(self, cohort_id: int, dry_run: bool) -> SurveyStudy | None:
        """Create a test study with sample configurations."""
        try:
            cohort = Cohort.objects.get(id=cohort_id)
        except Cohort.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"❌ Cohort {cohort_id} not found"))
            return None

        if not cohort.syllabus_version:
            self.stdout.write(
                self.style.ERROR(f"❌ Cohort {cohort_id} has no syllabus_version")
            )
            return None

        syllabus_slug = cohort.syllabus_version.syllabus.slug
        syllabus_version = cohort.syllabus_version.version

        self.stdout.write(
            self.style.SUCCESS(
                f"📝 Creating test study for cohort {cohort_id} (syllabus: {syllabus_slug} v{syllabus_version})"
            )
        )

        if dry_run:
            self.stdout.write(self.style.WARNING("  (DRY RUN - Would create study and configs)"))
            return None

        # Create study
        study = SurveyStudy.objects.create(
            slug=f"test-survey-{cohort_id}-{timezone.now().timestamp()}",
            title=f"Test Survey Study - Cohort {cohort_id}",
            description="Automatically generated test study",
            academy=cohort.academy,
        )

        # Create template (minimal)
        template = SurveyQuestionTemplate.objects.filter(
            academy=cohort.academy, lang="en"
        ).first()

        if not template:
            template = SurveyQuestionTemplate.objects.create(
                slug=f"test-template-{cohort_id}",
                title="Test Template",
                lang="en",
                academy=cohort.academy,
                questions={"questions": [{"id": "q1", "type": "text", "title": "Test question"}]},
            )

        # Create configs with different priorities
        configs_data = [
            {"module": 0, "priority": 100.0, "name": "Module 0 - 100%"},
            {"module": 1, "priority": 50.0, "name": "Module 1 - 50%"},
            {"module": 2, "priority": 30.0, "name": "Module 2 - 30%"},
        ]

        created_configs = []
        for config_data in configs_data:
            config = SurveyConfiguration.objects.create(
                trigger_type=SurveyConfiguration.TriggerType.MODULE_COMPLETION,
                syllabus={
                    "syllabus": syllabus_slug,
                    "version": syllabus_version,
                    "module": config_data["module"],
                },
                questions={"questions": []},
                is_active=True,
                academy=cohort.academy,
                priority=config_data["priority"],
                created_by=cohort.academy.owner if hasattr(cohort.academy, "owner") else None,
            )
            config.cohorts.add(cohort)
            study.survey_configurations.add(config)
            created_configs.append(config)
            self.stdout.write(
                self.style.SUCCESS(
                    f"  ✅ Created config {config.id}: {config_data['name']}"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(f"\n✅ Created study {study.id} with {len(created_configs)} configurations\n")
        )

        return study

