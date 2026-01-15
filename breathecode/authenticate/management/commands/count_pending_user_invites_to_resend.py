import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from breathecode.admissions.models import Academy
from breathecode.authenticate.models import UserInvite

logger = logging.getLogger(__name__)


def _to_int(value, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _get_invites_config(academy: Academy) -> dict:
    academy_features = academy.get_academy_features()
    features = academy_features.get("features") or {}
    invites = features.get("invites") or {}
    return invites if isinstance(invites, dict) else {}


class Command(BaseCommand):
    help = "Read-only: count pending UserInvites that would be resent right now by `resend_pending_user_invites`"

    def add_arguments(self, parser):
        parser.add_argument(
            "--academy",
            type=int,
            default=None,
            help="Optional academy id to scope the count (otherwise checks all academies).",
        )
        parser.add_argument(
            "--details",
            action="store_true",
            help="Print per-academy counts and totals by attempt number.",
        )

    def handle(self, *args, **options):
        now = timezone.now()
        verbosity = options.get("verbosity", 1)
        academy_id = options.get("academy")
        details = options.get("details", False)

        academies = Academy.objects.all()
        if academy_id is not None:
            academies = academies.filter(id=academy_id)

        total = 0
        by_attempt = {1: 0, 2: 0}

        for academy in academies.iterator():
            cfg = _get_invites_config(academy)
            if cfg.get("enabled") is not True:
                continue

            first_days = _to_int(cfg.get("first_timedelta", 3), 3)
            second_days = _to_int(cfg.get("second_timedelta", 10), 10)

            invites = (
                UserInvite.objects.filter(academy=academy, status="PENDING")
                .exclude(email__isnull=True)
                .exclude(email="")
            )

            academy_total = 0
            academy_by_attempt = {1: 0, 2: 0}

            for invite in invites.iterator():
                # Legacy invites created before tracking: treat as 1st attempt already done
                attempts = invite.how_many_attempts or 0
                if attempts == 0:
                    attempts = 1

                # Stop after 3 total attempts (initial + 2 reminders)
                if attempts >= 3:
                    continue

                last_sent_at = invite.sent_at or invite.created_at
                if last_sent_at is None:
                    last_sent_at = now

                if attempts == 1 and last_sent_at + timedelta(days=first_days) <= now:
                    academy_total += 1
                    academy_by_attempt[1] += 1

                elif attempts == 2 and last_sent_at + timedelta(days=second_days) <= now:
                    academy_total += 1
                    academy_by_attempt[2] += 1

            total += academy_total
            by_attempt[1] += academy_by_attempt[1]
            by_attempt[2] += academy_by_attempt[2]

            if details and verbosity >= 1 and academy_total:
                self.stdout.write(
                    f"academy_id={academy.id} academy_slug={academy.slug} total={academy_total} "
                    f"(attempt=1:{academy_by_attempt[1]}, attempt=2:{academy_by_attempt[2]})"
                )

        if verbosity >= 1:
            self.stdout.write(
                f"Total invites to resend right now: {total} (attempt=1:{by_attempt[1]}, attempt=2:{by_attempt[2]})"
            )


