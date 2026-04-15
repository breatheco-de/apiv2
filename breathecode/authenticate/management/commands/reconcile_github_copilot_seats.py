import logging

from django.core.management.base import BaseCommand

from breathecode.authenticate.models import ADD, AcademyAuthSettings, CredentialsGithub, GithubAcademyUser, SYNCHED
from breathecode.services.github import Github

logger = logging.getLogger(__name__)


def _reconcile_copilot_seats_for_academy_settings(settings: AcademyAuthSettings) -> int:
    """
    Remove Copilot seats for org members who are billed for Copilot but have no GithubAcademyUser
    SYNCHED+ADD in any academy that shares this GitHub organization.
    """
    if not settings.github_owner_id:
        return 0

    owner_creds = CredentialsGithub.objects.filter(user_id=settings.github_owner_id).first()
    if not owner_creds or not owner_creds.token:
        return 0

    org = (settings.github_username or "").strip()
    if not org:
        return 0

    gb = Github(org=org, token=owner_creds.token)
    try:
        seat_usernames = gb.copilot_list_seat_usernames()
    except Exception:
        logger.exception("Could not list Copilot seats for org %s", org)
        return 0

    sibling_academy_ids = list(
        AcademyAuthSettings.objects.filter(github_username__iexact=org).values_list("academy_id", flat=True)
    )
    if not sibling_academy_ids:
        return 0

    removed = 0
    for username in seat_usernames:
        cred = CredentialsGithub.objects.filter(username__iexact=username).select_related("user").first()
        if not cred or not cred.user_id:
            continue
        allowed = GithubAcademyUser.objects.filter(
            user_id=cred.user_id,
            academy_id__in=sibling_academy_ids,
            storage_status=SYNCHED,
            storage_action=ADD,
        ).exists()
        if allowed:
            continue
        try:
            gb.copilot_remove_selected_users([username])
            removed += 1
        except Exception:
            logger.exception("Failed to remove Copilot seat for %s in org %s", username, org)

    return removed


def run_reconcile_github_copilot_seats() -> dict[str, int]:
    """Run seat reconciliation once per distinct GitHub org (shared github_username)."""
    seen_orgs: set[str] = set()
    seats_removed = 0
    for settings in AcademyAuthSettings.objects.filter(github_owner_id__isnull=False).select_related(
        "academy", "github_owner"
    ):
        org = (settings.github_username or "").strip().lower()
        if not org or org in seen_orgs:
            continue
        seen_orgs.add(org)
        seats_removed += _reconcile_copilot_seats_for_academy_settings(settings)
    return {"github_orgs_processed": len(seen_orgs), "copilot_seats_removed": seats_removed}


class Command(BaseCommand):
    help = (
        "Remove GitHub Copilot seats for org members who are not tracked as SYNCHED+ADD in GithubAcademyUser "
        "for any academy sharing that GitHub org. Schedule nightly (e.g. Heroku Scheduler) after backups."
    )

    def handle(self, *args, **options):
        result = run_reconcile_github_copilot_seats()
        self.stdout.write(str(result))
