"""
Management command to test survey distribution system.

This command simulates users completing modules and shows how surveys are distributed
based on priority probabilities.

Usage:
    python manage.py test_survey_distribution --study-id 1 --users 100 --module 1
    python manage.py test_survey_distribution --create-study --cohort-id 1183 --users 50
    python manage.py test_survey_distribution --study-id 1 --users 100 --gradual-join --join-period-days 30

Realistic Simulation (--gradual-join):
    By default, all users are assumed to join the cohort at the study start.
    In reality, users join gradually over time. Use --gradual-join to simulate this:
    
    - Users are distributed across a join period (--join-period-days, default: 30 days)
    - Users who join earlier complete modules earlier
    - Users who join later may not have completed all modules by the current time
    - This affects survey distribution as users complete modules at different times
    
    Example:
        --gradual-join --join-period-days 30 --module-completion-days 7
        This simulates users joining over 30 days, taking 7 days on average per module.

2. New Users During Study (--new-users-during-study):
    Simulates a realistic scenario where:
    - Initial users (--users) join at the study start
    - New users (--new-users-during-study) join during the study
    - This tests how Cumulative Hazard-Based Sampling handles users joining at different times
    
    Example:
        --users 50 --new-users-during-study 50 --new-users-join-period-days 30
        This simulates 50 initial users + 50 new users joining over 30 days during the study.
        This is useful to test if the priority system correctly distributes surveys among
        both initial and new users.

How Priority Values Work:
    The system uses Conditional Hazard-Based Sampling with cumulative targets.
    Priority values are cumulative percentages, not direct probabilities.
    
    IMPORTANT LIMITATION:
    The system checks if a user already has a survey BEFORE evaluating probabilities.
    This means users who receive a survey in module 0 won't be evaluated for modules 1 or 2.
    Therefore, we CANNOT achieve exactly equal distribution (33% in each module).
    
    For EQUITABLE distribution (closest to ~33% per module):
        Module 0: priority = 33%  → ~33% of ALL users get survey
        Module 1: priority = 66% → ~33% of ALL users get survey (from remaining 67%)
        Module 2: priority = 100% → ~34% of ALL users get survey (from remaining 34%)
        Result: ~33%, ~33%, ~34% distribution
    
    For MORE EQUITABLE (slightly favoring later modules):
        Module 0: priority = 30% → ~30% of ALL users
        Module 1: priority = 60% → ~30% of ALL users (from remaining 70%)
        Module 2: priority = 100% → ~40% of ALL users (from remaining 40%)
        Result: ~30%, ~30%, ~40% distribution
    
    For EARLY distribution (more surveys at start):
        Module 0: priority = 50% → ~50% get survey
        Module 1: priority = 80% → ~30% more get survey (80% total)
        Module 2: priority = 100% → remaining ~20% get survey
    
    For LATE distribution (more surveys at end):
        Module 0: priority = 20% → ~20% get survey
        Module 1: priority = 50% → ~30% more get survey (50% total)
        Module 2: priority = 100% → remaining ~50% get survey
    
    Formula for conditional probability:
        conditional_prob = (current_priority - previous_priority) / (100 - previous_priority)
    
    Example calculation for Module 1 with 33%, 66%, 100%:
        - After Module 0: 67% of users remain without survey
        - Module 1 conditional: (66 - 33) / (100 - 33) = 33/67 ≈ 49.25%
        - Module 1 receives: 67% * 49.25% ≈ 33% of ALL users
"""

from datetime import timedelta

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
        parser.add_argument(
            "--gradual-join",
            action="store_true",
            help="Simulate users joining the cohort gradually over time (more realistic scenario)",
        )
        parser.add_argument(
            "--join-period-days",
            type=int,
            default=30,
            help="Number of days over which users gradually join (default: 30, only used with --gradual-join)",
        )
        parser.add_argument(
            "--module-completion-days",
            type=int,
            default=7,
            help="Average days to complete a module (default: 7, only used with --gradual-join)",
        )
        parser.add_argument(
            "--new-users-during-study",
            type=int,
            default=0,
            help="Number of new users that join the cohort during the study (simulates realistic scenario where users join after study starts)",
        )
        parser.add_argument(
            "--new-users-join-period-days",
            type=int,
            default=30,
            help="Period (in days) over which new users join during the study (default: 30, only used with --new-users-during-study)",
        )

    def handle(self, *args, **options):
        study_id = options.get("study_id")
        create_study = options.get("create_study")
        cohort_id = options.get("cohort_id")
        num_users = options.get("users")
        module = options.get("module")
        dry_run = options.get("dry_run")
        clear_existing = options.get("clear_existing")
        gradual_join = options.get("gradual_join", False)
        join_period_days = options.get("join_period_days", 30)
        module_completion_days = options.get("module_completion_days", 7)
        new_users_during_study = options.get("new_users_during_study", 0)
        new_users_join_period_days = options.get("new_users_join_period_days", 30)

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

        # Get configs for this study (use distinct to avoid duplicates)
        configs = study.survey_configurations.filter(is_active=True).distinct()
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

        # Display configs (sorted by module for conditional hazard-based sampling)
        def get_module_for_display(config):
            module = (config.syllabus or {}).get("module")
            return module if module is not None else 0
        
        # Convert to list and sort to avoid QuerySet issues
        configs_list = list(configs)
        configs_sorted = sorted(configs_list, key=get_module_for_display)
        
        self.stdout.write("📋 Configurations (Conditional Hazard-Based Sampling):")
        previous_priority = 0.0
        for config in configs_sorted:
            module_info = ""
            if config.syllabus:
                config_module = config.syllabus.get("module")
                if config_module is not None:
                    module_info = f" | Module: {config_module}"
            
            current_priority = config.priority if config.priority is not None else 100.0
            
            # Calculate conditional probability
            if previous_priority >= 100.0:
                conditional_prob = 0.0
            elif previous_priority >= current_priority:
                conditional_prob = 0.0
            else:
                conditional_prob = (current_priority - previous_priority) / (100.0 - previous_priority) * 100.0
            
            self.stdout.write(
                f"  • Config {config.id}: cumulative_target={current_priority}%{module_info} | conditional_prob={conditional_prob:.1f}% | trigger={config.trigger_type}"
            )
            previous_priority = current_priority

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

        self.stdout.write(
            f"\n👥 Cohort '{cohort.name}' (ID: {cohort.id}) has {len(available_users)} students"
        )

        # Calculate total users needed (initial + new during study)
        total_users_needed = num_users + new_users_during_study

        if len(available_users) < total_users_needed:
            self.stdout.write(
                self.style.WARNING(
                    f"\n⚠️  WARNING: Requested {total_users_needed} users ({num_users} initial + {new_users_during_study} new), "
                    f"but only {len(available_users)} students available in cohort.\n"
                    f"   Using all {len(available_users)} available students for simulation.\n"
                    f"   Adjusting: initial={min(num_users, len(available_users))}, "
                    f"new_during_study={min(new_users_during_study, max(0, len(available_users) - num_users))}\n"
                )
            )
            # Adjust numbers
            actual_initial = min(num_users, len(available_users))
            actual_new = min(new_users_during_study, max(0, len(available_users) - actual_initial))
            num_users = actual_initial
            new_users_during_study = actual_new
        else:
            self.stdout.write(
                f"   Will simulate {num_users} initial users + {new_users_during_study} new users during study "
                f"(total: {total_users_needed} users)\n"
            )

        # Select users: initial users + new users during study
        if len(available_users) < total_users_needed:
            # Use all available users
            test_users = available_users
        else:
            # Randomly select from available users
            test_users = random.sample(available_users, total_users_needed)
        
        # Split into initial and new users
        initial_user_ids = test_users[:num_users]
        new_user_ids = test_users[num_users:num_users + new_users_during_study] if new_users_during_study > 0 else []
        
        initial_users = User.objects.filter(id__in=initial_user_ids)
        new_users = User.objects.filter(id__in=new_user_ids) if new_user_ids else User.objects.none()
        
        # Combine all users for simulation
        users = list(initial_users) + list(new_users)

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

        # Simulate user join dates
        user_join_dates = {}
        study_start = study.starts_at if study.starts_at else timezone.now() - timedelta(days=30)
        
        if new_users_during_study > 0:
            # Scenario: Initial users + new users joining during study
            self.stdout.write(
                f"\n📅 Simulating user joins:\n"
                f"   • {len(initial_users)} initial users (joined at study start: {study_start.strftime('%Y-%m-%d')})\n"
                f"   • {len(new_users)} new users joining during study (over {new_users_join_period_days} days)\n"
            )
            
            # Initial users join at study start
            for user in initial_users:
                user_join_dates[user.id] = study_start
            
            # New users join during the study (distributed over new_users_join_period_days)
            if new_users:
                new_users_start = study_start + timedelta(days=1)  # Start joining 1 day after study starts
                for i, user in enumerate(new_users):
                    # Distribute new users evenly across join period
                    join_day = (i / len(new_users)) * new_users_join_period_days
                    join_date = new_users_start + timedelta(days=join_day)
                    user_join_dates[user.id] = join_date
                
                # Show new users join distribution
                new_users_earliest = min(user_join_dates[uid] for uid in new_user_ids)
                new_users_latest = max(user_join_dates[uid] for uid in new_user_ids)
                self.stdout.write(
                    f"   New users join date range: {new_users_earliest.strftime('%Y-%m-%d')} to {new_users_latest.strftime('%Y-%m-%d')}\n"
                )
        elif gradual_join:
            # Scenario: All users join gradually (distributed in the past)
            self.stdout.write(
                f"\n📅 Simulating gradual user joins over {join_period_days} days\n"
            )
            self.stdout.write(
                self.style.WARNING(
                    "   ⚠️  NOTE: This simulates existing users joining at different times in the past.\n"
                    "      It does NOT simulate new users joining during the study.\n"
                    "      Users who joined late may not have completed all modules yet.\n"
                )
            )
            study_start = study.starts_at if study.starts_at else timezone.now() - timedelta(days=join_period_days)
            
            for i, user in enumerate(users):
                # Distribute users evenly across join period
                join_day = (i / len(users)) * join_period_days
                join_date = study_start + timedelta(days=join_day)
                user_join_dates[user.id] = join_date
            
            # Show join distribution
            early_joiners = sum(1 for d in user_join_dates.values() if d <= study_start + timedelta(days=join_period_days / 3))
            mid_joiners = sum(1 for d in user_join_dates.values() if study_start + timedelta(days=join_period_days / 3) < d <= study_start + timedelta(days=2 * join_period_days / 3))
            late_joiners = len(user_join_dates) - early_joiners - mid_joiners
            
            self.stdout.write(
                f"   Early joiners (first {join_period_days // 3} days): {early_joiners} users\n"
                f"   Mid joiners (middle {join_period_days // 3} days): {mid_joiners} users\n"
                f"   Late joiners (last {join_period_days // 3} days): {late_joiners} users\n"
            )
            
            # Show date range
            earliest_join = min(user_join_dates.values())
            latest_join = max(user_join_dates.values())
            self.stdout.write(
                f"   Join date range: {earliest_join.strftime('%Y-%m-%d')} to {latest_join.strftime('%Y-%m-%d')}\n"
                f"   Current date: {timezone.now().strftime('%Y-%m-%d')}\n"
            )
        else:
            # Scenario: All users join at study start
            self.stdout.write(f"\n👥 Simulating {len(users)} users (all joined at study start: {study_start.strftime('%Y-%m-%d')})\n")
            for user in users:
                user_join_dates[user.id] = study_start

        # Simulate completions
        # IMPORTANT: Each user can only receive 1 survey per study
        # Users complete modules sequentially until they receive a survey
        # If gradual_join is enabled, users who joined later complete modules later
        results = {}
        created_count = 0
        skipped_count = 0
        users_not_reached_modules = {}  # Track users who haven't reached modules yet
        user_completion_times = {}  # Track when each user completes modules

        # Determine if we need to calculate completion times based on join dates
        # This is needed for both gradual_join and new_users_during_study scenarios
        needs_time_based_completion = gradual_join or new_users_during_study > 0
        
        # Sort users by join date if we're using time-based completion
        if needs_time_based_completion:
            users_sorted = sorted(users, key=lambda u: user_join_dates.get(u.id, timezone.now()))
        else:
            users_sorted = list(users)

        for user in users_sorted:
            user_received_survey = False
            user_join_date = user_join_dates.get(user.id, timezone.now()) if needs_time_based_completion else timezone.now()
            user_reached_any_module = False
            
            # Process modules in order (ascending)
            for test_module in sorted(modules_to_test):
                if user_received_survey:
                    # User already received survey, skip remaining modules
                    skipped_count += 1
                    continue
                
                # Calculate when user completes this module
                # Users who joined earlier complete modules earlier
                if needs_time_based_completion:
                    # Module completion time = join_date + (module_index * days_per_module) + some variance
                    days_since_join = test_module * module_completion_days
                    # Add some variance (±20% of module_completion_days)
                    variance = random.uniform(-0.2, 0.2) * module_completion_days
                    module_completion_date = user_join_date + timedelta(days=days_since_join + variance)
                    # Don't complete modules in the future
                    if module_completion_date > timezone.now():
                        # User hasn't reached this module yet
                        if test_module not in users_not_reached_modules:
                            users_not_reached_modules[test_module] = []
                        users_not_reached_modules[test_module].append(user.id)
                        continue
                    user_reached_any_module = True
                else:
                    module_completion_date = timezone.now()
                    user_reached_any_module = True
                
                # Create context for module completion
                context = {
                    "academy": cohort.academy,
                    "cohort": cohort,
                    "cohort_id": cohort.id,
                    "cohort_slug": cohort.slug,
                    "syllabus_slug": cohort.syllabus_version.syllabus.slug if cohort.syllabus_version else None,
                    "syllabus_version": cohort.syllabus_version.version if cohort.syllabus_version else None,
                    "module": test_module,
                    "completed_at": module_completion_date.isoformat(),
                }
                
                # Track completion time for statistics
                if user.id not in user_completion_times:
                    user_completion_times[user.id] = {}
                user_completion_times[user.id][test_module] = module_completion_date

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
                        user_received_survey = True
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
                    # Dry run: simulate conditional hazard-based sampling
                    # Get all configs for this study, sorted by module
                    def get_module_for_sim(config):
                        module = (config.syllabus or {}).get("module")
                        return module if module is not None else 0
                    
                    study_configs_sorted = sorted(configs, key=get_module_for_sim)
                    
                    # Filter configs for modules <= current module
                    eligible_for_sim = []
                    for config in study_configs_sorted:
                        config_module = get_module_for_sim(config)
                        if config_module > test_module:
                            continue
                        eligible_for_sim.append(config)
                    
                    # Apply conditional hazard-based sampling
                    # IMPORTANT: This logic must match SurveyManager exactly
                    previous_priority = 0.0
                    
                    for config in eligible_for_sim:
                        if user_received_survey:
                            break
                        
                        config_module = get_module_for_sim(config)
                        current_priority = config.priority if config.priority is not None else 100.0
                        
                        # Calculate conditional probability (must match SurveyManager logic)
                        if previous_priority >= 100.0:
                            conditional_prob = 0.0
                        elif previous_priority >= current_priority:
                            conditional_prob = 0.0
                        else:
                            conditional_prob = (current_priority - previous_priority) / (100.0 - previous_priority)
                        
                        # Hash input must match SurveyManager: f"{user.id}_{study.id}_{config_module}"
                        hash_input = f"{user.id}_{study.id}_{config_module}"
                        hash_value = hash(hash_input)
                        random_value = abs(hash_value) % 100
                        
                        conditional_prob_percent = conditional_prob * 100.0
                        
                        # SurveyManager uses: if random_value >= conditional_probability_percent: continue (skip)
                        # So we create survey if: random_value < conditional_prob_percent
                        # This matches SurveyManager's logic exactly
                        if random_value >= conditional_prob_percent:
                            # Skip (user doesn't receive survey based on conditional probability)
                            # Still update previous_priority (matches SurveyManager line 188)
                            previous_priority = current_priority
                            skipped_count += 1
                            continue
                        
                        # User is selected for this survey config
                        # (In SurveyManager, deduplication check happens here, but we skip it in dry_run)
                        if config.id not in results:
                            results[config.id] = {
                                "count": 0,
                                "users": [],
                                "module": config_module,
                            }
                        results[config.id]["count"] += 1
                        results[config.id]["users"].append(user.id)
                        user_received_survey = True
                        created_count += 1
                        
                        # Track completion time for statistics
                        if user.id not in user_completion_times:
                            user_completion_times[user.id] = {}
                        user_completion_times[user.id][test_module] = module_completion_date
                        
                        # Update previous_priority (matches SurveyManager line 216)
                        previous_priority = current_priority

        # Display results
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("📊 RESULTS"))
        self.stdout.write("=" * 80 + "\n")

        if dry_run:
            self.stdout.write(self.style.WARNING("(DRY RUN - No surveys were actually created)\n"))

        total_created = sum(r["count"] for r in results.values())
        users_with_survey = len(set(user_id for r in results.values() for user_id in r.get("users", [])))
        users_without_survey = len(users) - users_with_survey

        self.stdout.write(f"Total users simulated: {len(users)}")
        if new_users_during_study > 0:
            # Show breakdown by initial vs new users
            initial_user_ids_set = set(initial_user_ids)
            new_user_ids_set = set(new_user_ids)
            
            # Count surveys by user type
            initial_with_survey = len([uid for r in results.values() for uid in r.get("users", []) if uid in initial_user_ids_set])
            new_with_survey = len([uid for r in results.values() for uid in r.get("users", []) if uid in new_user_ids_set])
            
            self.stdout.write(f"   • Initial users: {len(initial_users)} (joined at study start)")
            self.stdout.write(f"   • New users during study: {len(new_users)} (joined during study)")
            self.stdout.write(f"\nSurveys by user type:")
            self.stdout.write(f"   • Initial users with survey: {initial_with_survey}/{len(initial_users)} ({(initial_with_survey/len(initial_users)*100) if len(initial_users) > 0 else 0:.1f}%)")
            self.stdout.write(f"   • New users with survey: {new_with_survey}/{len(new_users)} ({(new_with_survey/len(new_users)*100) if len(new_users) > 0 else 0:.1f}%)")
        
        self.stdout.write(f"\nModules tested: {sorted(modules_to_test)}")
        self.stdout.write(f"Surveys created: {total_created}")
        self.stdout.write(f"Users with survey: {users_with_survey}/{len(users)} ({(users_with_survey/len(users)*100):.1f}%)")
        self.stdout.write(f"Users without survey: {users_without_survey} ({(users_without_survey/len(users)*100):.1f}%)")
        
        # Show users who haven't reached modules yet (gradual join or new users scenario)
        if (gradual_join or new_users_during_study > 0) and users_not_reached_modules:
            total_not_reached = len(set(user_id for module_users in users_not_reached_modules.values() for user_id in module_users))
            self.stdout.write(
                f"\n⚠️  Users who haven't reached modules yet: {total_not_reached} "
                f"(these users joined too late to complete all modules by now)"
            )
            self.stdout.write(
                self.style.WARNING(
                    f"   💡 These {total_not_reached} users are the reason why only {users_with_survey}/{len(users)} "
                    f"({(users_with_survey/len(users)*100):.1f}%) received surveys.\n"
                    f"   They will receive surveys in the future as they complete more modules."
                )
            )
            for mod in sorted(users_not_reached_modules.keys()):
                count = len(users_not_reached_modules[mod])
                self.stdout.write(f"   Module {mod}: {count} users haven't reached this module yet")
        
        # Show gradual join statistics if enabled
        if needs_time_based_completion:
            title = "📅 Time-Based Completion Simulation:"
            if gradual_join and new_users_during_study > 0:
                title = "📅 Gradual Join + New Users Simulation:"
            elif gradual_join:
                title = "📅 Gradual Join Simulation:"
            elif new_users_during_study > 0:
                title = "📅 New Users During Study Simulation:"
            
            self.stdout.write(f"\n{title}")
            if gradual_join:
                self.stdout.write(f"   • Join period: {join_period_days} days")
            if new_users_during_study > 0:
                self.stdout.write(f"   • New users join period: {new_users_join_period_days} days")
            self.stdout.write(f"   • Average module completion time: {module_completion_days} days per module")
            
            # Calculate how many users completed each module at different times
            if user_completion_times:
                module_completion_stats = {}
                for user_id, module_times in user_completion_times.items():
                    for mod, completion_time in module_times.items():
                        if mod not in module_completion_stats:
                            module_completion_stats[mod] = []
                        module_completion_stats[mod].append(completion_time)
                
                if module_completion_stats:
                    self.stdout.write(f"\n   Module Completion Timeline:")
                    for mod in sorted(module_completion_stats.keys()):
                        times = module_completion_stats[mod]
                        if times:
                            earliest = min(times)
                            latest = max(times)
                            span = (latest - earliest).days
                            self.stdout.write(
                                f"     Module {mod}: {len(times)} users completed over {span} days "
                                f"({earliest.strftime('%Y-%m-%d')} to {latest.strftime('%Y-%m-%d')})"
                            )
        
        self.stdout.write(f"\n📌 Conditional Hazard-Based Sampling:")
        self.stdout.write(f"   • Each user receives at most 1 survey per study")
        self.stdout.write(f"   • Priority values are cumulative targets (not direct probabilities)")
        self.stdout.write(f"   • Conditional probabilities: (priority_k - priority_prev) / (1 - priority_prev)\n")

        self.stdout.write("\n📈 Distribution by Configuration:\n")
        previous_priority = 0.0
        for config in configs_sorted:
            config_id = config.id
            current_priority = config.priority if config.priority is not None else 100.0
            module_info = ""
            if config.syllabus:
                config_module = config.syllabus.get("module")
                if config_module is not None:
                    module_info = f" (Module {config_module})"
            
            result = results.get(config_id, {"count": 0, "users": []})
            count = result["count"]
            
            percentage = (count / len(users) * 100) if len(users) > 0 else 0
            # Expected is the cumulative target (priority)
            expected_percentage = current_priority
            
            # Calculate conditional probability for display
            if previous_priority >= 100.0:
                conditional_prob = 0.0
            elif previous_priority >= current_priority:
                conditional_prob = 0.0
            else:
                conditional_prob = (current_priority - previous_priority) / (100.0 - previous_priority) * 100.0
            
            # For conditional sampling, we expect the cumulative distribution to match
            # So if priority=75%, we expect 75% of users to have answered by this module
            status = "✅" if abs(percentage - expected_percentage) < 10 else "⚠️"
            
            self.stdout.write(
                f"  {status} Config {config_id}{module_info}:"
            )
            self.stdout.write(
                f"    Cumulative Target: {current_priority}% | Actual: {count}/{len(users)} ({percentage:.1f}%) | Expected Cumulative: ~{expected_percentage:.1f}%"
            )
            self.stdout.write(
                f"    Conditional Prob: {conditional_prob:.1f}% (calculated from prev={previous_priority}%)"
            )
            
            previous_priority = current_priority

        # Show cumulative target vs actual distribution
        self.stdout.write("\n📊 Cumulative Target vs Actual Distribution:\n")
        previous_priority = 0.0
        for config in configs_sorted:
            config_id = config.id
            current_priority = config.priority if config.priority is not None else 100.0
            result = results.get(config_id, {"count": 0})
            actual = (result["count"] / len(users) * 100) if len(users) > 0 else 0
            
            # For conditional sampling, we compare cumulative actual vs cumulative target
            # We need to sum all previous configs' counts
            cumulative_actual = 0.0
            for prev_config in configs_sorted:
                if prev_config.id == config_id:
                    break
                prev_result = results.get(prev_config.id, {"count": 0})
                cumulative_actual += (prev_result["count"] / len(users) * 100) if len(users) > 0 else 0
            
            # Add current config's contribution
            cumulative_actual += actual
            
            diff = cumulative_actual - current_priority
            
            bar_length = 40
            target_bar = "█" * int(current_priority / 100 * bar_length)
            actual_bar = "█" * int(cumulative_actual / 100 * bar_length)
            
            module_info = ""
            if config.syllabus:
                config_module = config.syllabus.get("module")
                if config_module is not None:
                    module_info = f" (Module {config_module})"
            
            self.stdout.write(f"  Config {config_id}{module_info}:")
            self.stdout.write(f"    Cumulative Target: [{target_bar:<{bar_length}}] {current_priority:.1f}%")
            self.stdout.write(f"    Cumulative Actual: [{actual_bar:<{bar_length}}] {cumulative_actual:.1f}% (diff: {diff:+.1f}%)")
            
            previous_priority = current_priority

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
        # 
        # IMPORTANT: The system checks if user already has survey BEFORE evaluating probabilities.
        # This means users who receive survey in earlier modules won't be evaluated for later modules.
        #
        # For EQUITABLE distribution (~33% per module), we need:
        # - Module 0: 33% of ALL users → priority = 33%
        # - Module 1: 33% of REMAINING users (67% left) → need 33/67 ≈ 49.25% conditional
        #   This means: 33% + (67% * 49.25%) = 33% + 33% = 66% cumulative → priority = 66%
        # - Module 2: 34% of REMAINING users (34% left) → need 100% conditional
        #   This means: 66% + (34% * 100%) = 100% cumulative → priority = 100%
        #
        # However, with these values, when users reach module 2, only ~34% will be left
        # without survey, so module 2 will only get ~34% of users, not 33% of ALL users.
        #
        # For TRUE equitable distribution (33% of ALL users in each module), we need:
        # - Module 0: 33% → priority = 33%
        # - Module 1: 33% of ALL (not just remaining) → need higher conditional prob
        #   To get 33% of ALL from 67% remaining: 33/67 ≈ 49.25% conditional
        #   But this gives us 33% + (67% * 49.25%) = 66% cumulative → priority = 66%
        # - Module 2: 34% of ALL (not just remaining) → need 100% conditional
        #   But only 34% remain, so 100% of them = 34% of ALL → priority = 100%
        #
        # The issue: We CAN'T get exactly 33% in each module because the system
        # prevents users who got survey in module 0 from being evaluated in module 1.
        #
        # BEST APPROXIMATION for equitable distribution:
        # Using 30%, 60%, 100% gives better balance: ~30%, ~30%, ~40%
        # This compensates for the fact that fewer users reach later modules
        configs_data = [
            {"module": 0, "priority": 30.0, "name": "Module 0 - 30% (~30% of all users)"},
            {"module": 1, "priority": 60.0, "name": "Module 1 - 60% (~30% of all users)"},
            {"module": 2, "priority": 100.0, "name": "Module 2 - 100% (~40% of all users)"},
        ]
        
        # Alternative: If you want exactly 33%, 33%, 34% distribution:
        # configs_data = [
        #     {"module": 0, "priority": 33.0, "name": "Module 0 - 33%"},
        #     {"module": 1, "priority": 66.0, "name": "Module 1 - 66%"},
        #     {"module": 2, "priority": 100.0, "name": "Module 2 - 100%"},
        # ]
        # This gives: ~33% in module 0, ~33% in module 1, ~34% in module 2

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

