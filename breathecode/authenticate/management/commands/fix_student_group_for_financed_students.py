from __future__ import annotations

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from breathecode.authenticate.models import ProfileAcademy
from breathecode.payments.models import PlanFinancing, Subscription, SubscriptionSeat


class Command(BaseCommand):
    help = (
        "Add missing 'Student' Django group for users that belong to an academy as students "
        "and have an ACTIVE (not expired) plan financing or subscription in that academy."
    )

    def add_arguments(self, parser):
        parser.add_argument("--academy-id", type=int, default=None, help="Academy id to scope the fix")
        parser.add_argument(
            "--all-academies",
            action="store_true",
            help="Process all academies (ignores --academy-id)",
        )
        parser.add_argument(
            "--commit",
            action="store_true",
            help="Apply changes (otherwise runs in dry-run mode)",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Print each user that gets fixed",
        )

    def handle(self, *args, **options):
        academy_id = options["academy_id"]
        all_academies: bool = options["all_academies"]
        commit: bool = options["commit"]
        verbose: bool = options["verbose"]

        if not all_academies and not academy_id:
            self.stdout.write(self.style.ERROR("You must provide --academy-id or use --all-academies"))
            return

        if not commit:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made (use --commit)\n"))

        try:
            student_group = Group.objects.get(name="Student")
        except Group.DoesNotExist:
            self.stdout.write(self.style.ERROR("Error: Required group not found: Student"))
            self.stdout.write(self.style.WARNING("Run 'python manage.py seed_groups' first"))
            return

        now = timezone.now()
        academy_filter = {} if all_academies else {"academy__id": academy_id}

        # Eligible (academy_id, user_id) pairs from PlanFinancing
        pf_pairs = set(
            PlanFinancing.objects.filter(
                **academy_filter,
                status=PlanFinancing.Status.ACTIVE,
                user__isnull=False,
                valid_until__gte=now,
            ).values_list("academy_id", "user_id")
        )

        # Eligible (academy_id, user_id) pairs from owned Subscriptions
        sub_pairs = set(
            Subscription.objects.filter(
                **academy_filter,
                status=Subscription.Status.ACTIVE,
                user__isnull=False,
            )
            .filter(Q(valid_until__gte=now) | Q(valid_until=None))
            .values_list("academy_id", "user_id")
        )

        # Eligible (academy_id, user_id) pairs from Subscription seats
        seat_pairs = set(
            SubscriptionSeat.objects.filter(
                user__isnull=False,
                is_active=True,
                billing_team__subscription__status=Subscription.Status.ACTIVE,
            )
            .filter(Q(billing_team__subscription__valid_until__gte=now) | Q(billing_team__subscription__valid_until=None))
            .filter(**({} if all_academies else {"billing_team__subscription__academy__id": academy_id}))
            .values_list("billing_team__subscription__academy_id", "user_id")
        )

        eligible_pairs = pf_pairs.union(sub_pairs).union(seat_pairs)

        if not eligible_pairs:
            scope = "all academies" if all_academies else f"academy_id={academy_id}"
            self.stdout.write(self.style.WARNING(f"No eligible ACTIVE plan financings/subscriptions found for {scope}"))
            return

        student_profiles_qs = ProfileAcademy.objects.filter(
            role__slug="student",
            status="ACTIVE",
            user__isnull=False,
        )
        if not all_academies:
            student_profiles_qs = student_profiles_qs.filter(academy__id=academy_id)

        # Keep only profiles whose (academy_id, user_id) has an eligible active plan/subscription.
        candidate_pairs = list(student_profiles_qs.values_list("academy_id", "user_id"))
        candidate_user_ids = [user_id for a_id, user_id in candidate_pairs if (a_id, user_id) in eligible_pairs]

        if not candidate_user_ids:
            self.stdout.write(
                self.style.WARNING(
                    "No active student ProfileAcademy users with active plan/subscription found for the selected scope"
                )
            )
            return

        # Determine which of those users are missing the Student group (fast, set-based).
        existing_user_ids = set(
            student_group.user_set.filter(id__in=candidate_user_ids).values_list("id", flat=True)
        )
        missing_user_ids = [uid for uid in candidate_user_ids if uid not in existing_user_ids]

        fixed = 0
        already_ok = len(candidate_user_ids) - len(missing_user_ids)
        missing_group = len(missing_user_ids)

        if commit and missing_user_ids:
            through_model = student_group.user_set.through
            rows = [through_model(user_id=uid, group_id=student_group.id) for uid in missing_user_ids]
            through_model.objects.bulk_create(rows, ignore_conflicts=True, batch_size=1000)
            fixed = len(missing_user_ids)

        if verbose and missing_user_ids:
            # Print emails for human verification (best-effort).
            for profile in student_profiles_qs.filter(user__id__in=missing_user_ids).select_related("user"):
                user = profile.user
                if user is None:
                    continue
                action = "FIXED" if commit else "WOULD FIX"
                self.stdout.write(
                    self.style.SUCCESS(
                        f"{action}: user_id={user.id} email={user.email} -> add group=Student (academy_id={academy_id})"
                    )
                )

        self.stdout.write(self.style.MIGRATE_HEADING("\n=== Summary ==="))
        self.stdout.write(f"scope={'all_academies' if all_academies else f'academy_id={academy_id}'}")
        self.stdout.write(f"matched_profiles={len(candidate_user_ids)}")
        self.stdout.write(f"already_had_group={already_ok}")
        self.stdout.write(f"missing_group={missing_group}")
        self.stdout.write(f"applied={fixed}" if commit else "applied=0 (dry-run)")


