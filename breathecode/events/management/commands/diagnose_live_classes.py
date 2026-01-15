from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from breathecode.admissions.models import Cohort, CohortTimeSlot
from breathecode.events.models import LiveClass
from breathecode.utils.datetime_integer import DatetimeInteger
from dateutil.relativedelta import relativedelta
import pytz


class Command(BaseCommand):
    help = "Diagnose why live classes were not generated for a cohort"

    def add_arguments(self, parser):
        parser.add_argument("cohort", type=str, help="ID, slug or name of the cohort to diagnose")
        parser.add_argument(
            "--timeslot-id",
            type=int,
            default=None,
            help="Specific timeslot ID to diagnose (optional)",
        )

    def handle(self, *args, **options):
        cohort_identifier = options["cohort"]
        timeslot_id = options.get("timeslot_id")

        self.stdout.write(self.style.SUCCESS(f"\n{'='*80}"))
        self.stdout.write(self.style.SUCCESS(f"LIVE CLASSES DIAGNOSIS - Cohort: {cohort_identifier}"))
        self.stdout.write(self.style.SUCCESS(f"{'='*80}\n"))

        # 1. Search for cohort by ID, slug or name
        cohort = None

        # Try to search by ID first
        try:
            cohort_id = int(cohort_identifier)
            cohort = Cohort.objects.filter(id=cohort_id).first()
        except ValueError:
            # Not a number, search by slug or name
            pass

        # If not found by ID, search by slug or name
        if not cohort:
            cohort = (
                Cohort.objects.filter(slug=cohort_identifier).first()
                or Cohort.objects.filter(name=cohort_identifier).first()
            )

        if not cohort:
            self.stdout.write(self.style.ERROR(f"❌ Cohort '{cohort_identifier}' does not exist"))
            self.stdout.write("   Attempted to search by:")
            self.stdout.write(f"      - ID: {cohort_identifier}")
            self.stdout.write(f"      - Slug: {cohort_identifier}")
            self.stdout.write(f"      - Name: {cohort_identifier}")
            raise CommandError(f"Cohort '{cohort_identifier}' not found")

        self.stdout.write(self.style.SUCCESS(f"✅ Cohort found: {cohort.slug}"))
        self.stdout.write(f"   - ID: {cohort.id}")
        self.stdout.write(f"   - Name: {cohort.name}")
        self.stdout.write(f"   - Stage: {cohort.stage}")
        self.stdout.write(f"   - Kickoff: {cohort.kickoff_date}")
        self.stdout.write(f"   - Ending: {cohort.ending_date}")
        self.stdout.write(f"   - Never Ends: {cohort.never_ends}")
        self.stdout.write("")

        # 2. Check receiver conditions
        self.stdout.write(self.style.WARNING("📋 CHECKING RECEIVER CONDITIONS (post_save_cohort_time_slot):"))
        utc_now = timezone.now()

        receiver_conditions_met = False
        issues = []

        if not cohort.ending_date:
            issues.append("❌ cohort.ending_date is None")
        elif cohort.ending_date <= utc_now:
            issues.append(f"❌ cohort.ending_date ({cohort.ending_date}) is <= now ({utc_now})")
        else:
            self.stdout.write(f"   ✅ cohort.ending_date exists and is in the future: {cohort.ending_date}")

        if cohort.never_ends:
            issues.append("❌ cohort.never_ends is True (must be False)")
        else:
            self.stdout.write(f"   ✅ cohort.never_ends is False")

        if cohort.ending_date and cohort.ending_date > utc_now and not cohort.never_ends:
            receiver_conditions_met = True
            self.stdout.write(self.style.SUCCESS("   ✅ Receiver conditions MET"))
        else:
            self.stdout.write(self.style.ERROR("   ❌ Receiver conditions NOT MET"))
            for issue in issues:
                self.stdout.write(f"      {issue}")

        self.stdout.write("")

        # 3. Check timeslots
        self.stdout.write(self.style.WARNING("📋 CHECKING TIMESLOTS:"))
        timeslots = CohortTimeSlot.objects.filter(cohort=cohort)
        if timeslot_id:
            timeslots = timeslots.filter(id=timeslot_id)

        if not timeslots.exists():
            self.stdout.write(self.style.ERROR("   ❌ No timeslots found for this cohort"))
            if timeslot_id:
                self.stdout.write(f"      (Searching for timeslot ID: {timeslot_id})")
            raise CommandError("No timeslots to diagnose")

        self.stdout.write(f"   ✅ Found {timeslots.count()} timeslot(s)")
        self.stdout.write("")

        # 4. Diagnose each timeslot
        for timeslot in timeslots:
            self.stdout.write(self.style.WARNING(f"\n{'─'*80}"))
            self.stdout.write(self.style.WARNING(f"TIMESLOT ID: {timeslot.id}"))
            self.stdout.write(self.style.WARNING(f"{'─'*80}\n"))

            self._diagnose_timeslot(timeslot, cohort, utc_now, receiver_conditions_met)

        self.stdout.write(self.style.SUCCESS(f"\n{'='*80}"))
        self.stdout.write(self.style.SUCCESS("DIAGNOSIS COMPLETED"))
        self.stdout.write(self.style.SUCCESS(f"{'='*80}\n"))

    def _diagnose_timeslot(self, timeslot, cohort, utc_now, receiver_conditions_met):
        # Basic timeslot information
        self.stdout.write(f"📌 Timeslot Information:")
        self.stdout.write(f"   - Timezone: {timeslot.timezone}")
        self.stdout.write(f"   - Starting At (integer): {timeslot.starting_at}")
        self.stdout.write(f"   - Ending At (integer): {timeslot.ending_at}")
        self.stdout.write(f"   - Recurrent: {timeslot.recurrent}")
        self.stdout.write(f"   - Recurrency Type: {timeslot.recurrency_type}")
        self.stdout.write(f"   - Removed At: {timeslot.removed_at}")
        self.stdout.write("")

        # Convert dates
        try:
            starting_at = DatetimeInteger.to_datetime(timeslot.timezone, timeslot.starting_at)
            ending_at = DatetimeInteger.to_datetime(timeslot.timezone, timeslot.ending_at)
            self.stdout.write(f"   ✅ Date conversion successful:")
            self.stdout.write(f"      - Starting At (local): {starting_at}")
            self.stdout.write(f"      - Ending At (local): {ending_at}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Error converting dates: {e}"))
            return

        self.stdout.write("")

        # Check build_live_classes_from_timeslot conditions
        self.stdout.write(self.style.WARNING("📋 CHECKING build_live_classes_from_timeslot CONDITIONS:"))

        until_date = timeslot.removed_at or cohort.ending_date
        start_date = cohort.kickoff_date

        if not until_date:
            self.stdout.write(
                self.style.ERROR("   ❌ until_date is None (timeslot.removed_at and cohort.ending_date are None)")
            )
        else:
            self.stdout.write(f"   ✅ until_date: {until_date}")

        if not start_date:
            self.stdout.write(self.style.ERROR("   ❌ start_date is None (cohort.kickoff_date is None)"))
        else:
            self.stdout.write(f"   ✅ start_date: {cohort.kickoff_date}")

        # Check recurrency_type
        delta = relativedelta(0)
        if timeslot.recurrency_type == "DAILY":
            delta += relativedelta(days=1)
            self.stdout.write(f"   ✅ recurrency_type valid: DAILY")
        elif timeslot.recurrency_type == "WEEKLY":
            delta += relativedelta(weeks=1)
            self.stdout.write(f"   ✅ recurrency_type valid: WEEKLY")
        elif timeslot.recurrency_type == "MONTHLY":
            delta += relativedelta(months=1)
            self.stdout.write(f"   ✅ recurrency_type valid: MONTHLY")
        else:
            self.stdout.write(
                self.style.ERROR(f"   ❌ recurrency_type invalid: {timeslot.recurrency_type}")
            )

        if not delta:
            self.stdout.write(self.style.ERROR("   ❌ Could not calculate delta (invalid recurrency_type)"))

        self.stdout.write("")

        # Check if classes would be created
        if not until_date or not start_date:
            self.stdout.write(
                self.style.ERROR("   ❌ Cannot generate classes (missing until_date or start_date)")
            )
            return

        # Simulate generation loop
        self.stdout.write(self.style.WARNING("📋 SIMULATING CLASS GENERATION:"))

        tz = pytz.timezone(timeslot.timezone)
        current_starting = starting_at
        current_ending = ending_at

        # Adjust if ending_at is less than starting_at
        while current_starting > current_ending:
            current_ending += relativedelta(days=1)

        classes_to_create = []
        iterations = 0
        max_iterations = 100  # Prevent infinite loops

        while iterations < max_iterations:
            if current_ending > until_date:
                break

            if current_starting > start_date:
                classes_to_create.append(
                    {
                        "starting_at": current_starting,
                        "ending_at": current_ending,
                        "local_start": current_starting.strftime("%Y-%m-%d %H:%M:%S %Z"),
                        "local_end": current_ending.strftime("%Y-%m-%d %H:%M:%S %Z"),
                    }
                )

            if not timeslot.recurrent:
                break

            # Increment for next iteration
            naive_starting = current_starting.replace(tzinfo=None) + delta
            naive_ending = current_ending.replace(tzinfo=None) + delta
            current_starting = tz.localize(naive_starting)
            current_ending = tz.localize(naive_ending)

            iterations += 1

        if classes_to_create:
            self.stdout.write(f"   ✅ Would generate {len(classes_to_create)} class(es)")
            self.stdout.write("")
            self.stdout.write("   First 5 classes that would be generated:")
            for i, cls in enumerate(classes_to_create[:5], 1):
                self.stdout.write(f"      {i}. {cls['local_start']} → {cls['local_end']}")
            if len(classes_to_create) > 5:
                self.stdout.write(f"      ... and {len(classes_to_create) - 5} more")
        else:
            self.stdout.write(self.style.ERROR("   ❌ Would not generate classes"))
            self.stdout.write("")
            self.stdout.write("   Possible reasons:")
            if current_starting <= start_date:
                self.stdout.write(
                    f"      - starting_at ({current_starting}) <= start_date ({start_date})"
                )
            if current_ending > until_date:
                self.stdout.write(f"      - ending_at ({current_ending}) > until_date ({until_date})")

        self.stdout.write("")

        # Check existing live classes
        self.stdout.write(self.style.WARNING("📋 EXISTING LIVE CLASSES:"))
        existing_live_classes = LiveClass.objects.filter(cohort_time_slot=timeslot)
        total_existing = existing_live_classes.count()
        future_existing = existing_live_classes.filter(starting_at__gte=utc_now).count()
        past_existing = existing_live_classes.filter(starting_at__lt=utc_now).count()

        self.stdout.write(f"   - Total: {total_existing}")
        self.stdout.write(f"   - Future: {future_existing}")
        self.stdout.write(f"   - Past: {past_existing}")

        if total_existing == 0:
            self.stdout.write(self.style.ERROR("   ❌ No live classes created for this timeslot"))
        else:
            self.stdout.write("")
            self.stdout.write("   Last 3 live classes:")
            for lc in existing_live_classes.order_by("-starting_at")[:3]:
                status = "✅ Occurred" if lc.started_at or lc.ended_at else "⏳ Pending"
                self.stdout.write(
                    f"      - {lc.starting_at} → {lc.ending_at} ({status})"
                )

        self.stdout.write("")

        # Problems summary
        self.stdout.write(self.style.WARNING("📋 PROBLEMS SUMMARY:"))
        problems = []

        if not receiver_conditions_met:
            problems.append("❌ Receiver conditions NOT met (build_live_classes was not triggered)")

        if not until_date:
            problems.append("❌ Missing until_date (removed_at or ending_date)")

        if not start_date:
            problems.append("❌ Missing start_date (kickoff_date)")

        if not delta:
            problems.append("❌ Invalid recurrency_type")

        if not classes_to_create:
            problems.append("❌ Would not generate classes (check dates)")

        if total_existing == 0 and classes_to_create:
            problems.append("⚠️  Should generate classes but they don't exist (possible task error)")

        if problems:
            for problem in problems:
                self.stdout.write(f"   {problem}")
        else:
            self.stdout.write(self.style.SUCCESS("   ✅ No obvious problems found"))

        self.stdout.write("")
