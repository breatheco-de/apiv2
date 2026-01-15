import logging
import os
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from breathecode.admissions.models import Academy
from breathecode.authenticate.actions import bump_user_invite_attempts, get_app_url, get_invite_url
from breathecode.authenticate.models import UserInvite
from breathecode.notify import actions as notify_actions

logger = logging.getLogger(__name__)


def _get_invites_config(academy: Academy) -> dict:
    academy_features = academy.get_academy_features()
    features = academy_features.get("features") or {}
    invites = features.get("invites") or {}
    return invites if isinstance(invites, dict) else {}


def _to_int(value, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


class Command(BaseCommand):
    help = "Resend pending UserInvite emails based on Academy.academy_features.features.invites"

    def handle(self, *args, **options):
        now = timezone.now()
        verbosity = options.get("verbosity", 1)

        total_sent = 0
        for academy in Academy.objects.all().iterator():
            cfg = _get_invites_config(academy)
            if cfg.get("enabled") is not True:
                continue

            first_days = _to_int(cfg.get("first_timedelta", 3), 3)
            second_days = _to_int(cfg.get("second_timedelta", 10), 10)

            template_slug = cfg.get("template_slug") or "welcome_academy"
            second_template_slug = cfg.get("second_template_slug") or template_slug

            invites = UserInvite.objects.filter(academy=academy, status="PENDING").exclude(email__isnull=True).exclude(email="")

            for invite in invites.iterator():
                # Legacy invites created before tracking: treat as 1st attempt already done
                attempts = invite.how_many_attempts or 0
                if attempts == 0:
                    attempts = 1

                last_sent_at = invite.sent_at or invite.created_at
                if last_sent_at is None:
                    last_sent_at = now

                should_send = False
                chosen_template = template_slug

                if attempts == 1 and last_sent_at + timedelta(days=first_days) <= now:
                    should_send = True
                    chosen_template = template_slug

                elif attempts == 2 and last_sent_at + timedelta(days=second_days) <= now:
                    should_send = True
                    chosen_template = second_template_slug

                # Stop after 3 total attempts (initial + 2 reminders)
                elif attempts >= 3:
                    continue

                if not should_send:
                    continue

                callback_url = get_app_url(academy=academy)
                url = get_invite_url(invite.token, academy=academy, callback_url=callback_url)

                email_data = {
                    "email": invite.email,
                    "subject": f"{academy.name} is inviting you to {academy.slug}.4Geeks.com",
                    "LINK": url,
                    "FIRST_NAME": invite.first_name,
                    "TRACKER_URL": f"{os.getenv('API_URL', '')}/v1/auth/invite/track/open/{invite.id}",
                }

                if invite.welcome_video:
                    welcome_video = (
                        invite.welcome_video.copy()
                        if isinstance(invite.welcome_video, dict)
                        else invite.welcome_video
                    )
                    email_data["WELCOME_VIDEO"] = welcome_video

                try:
                    notify_actions.send_email_message(chosen_template, invite.email, email_data, academy=academy)
                    bump_user_invite_attempts(invite, save=True)
                    total_sent += 1

                    if verbosity >= 2:
                        self.stdout.write(
                            f"Resent invite id={invite.id} academy={academy.slug} attempts={invite.how_many_attempts} template={chosen_template}"
                        )

                except Exception as e:
                    logger.error(
                        f"Error resending invite id={invite.id} academy={academy.slug}: {str(e)}",
                        exc_info=True,
                    )

        if verbosity >= 1:
            self.stdout.write(f"Done. Total resent invites: {total_sent}")


