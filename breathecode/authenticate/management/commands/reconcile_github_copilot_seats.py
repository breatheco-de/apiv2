import json
import logging
from typing import Any

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from breathecode.authenticate.actions import (
    _user_has_copilot_entitlement_in_sibling_academies,
    provision_github_copilot_for_user,
)
from breathecode.authenticate.models import (
    ACTIVE,
    ADD,
    AcademyAuthSettings,
    CredentialsGithub,
    GithubAcademyUser,
    ProfileAcademy,
    SYNCHED,
)
from breathecode.services.github import Github

logger = logging.getLogger(__name__)


def _copilot_seat_should_be_removed(
    user: User | None,
    *,
    sibling_academy_ids: list[int],
) -> tuple[bool, str]:
    if not user or not user.id:
        return True, "no_internal_user"

    if not GithubAcademyUser.objects.filter(
        user_id=user.id,
        academy_id__in=sibling_academy_ids,
        storage_status=SYNCHED,
        storage_action=ADD,
    ).exists():
        return True, "no_synched_add_github_academy_user"

    if ProfileAcademy.objects.filter(
        user_id=user.id,
        academy_id__in=sibling_academy_ids,
        status=ACTIVE,
    ).exclude(role__slug="student").exists():
        return False, "keep_non_student_profile_academy"

    if _user_has_copilot_entitlement_in_sibling_academies(user, sibling_academy_ids):
        return False, "keep_copilot_entitlement"

    return True, "student_without_copilot_entitlement"


def _format_copilot_list_seats_error(org: str, exc: Exception) -> str:
    msg = str(exc).lower()
    if "404" in str(exc) or "not found" in msg:
        return (
            f"GitHub API 404 listing Copilot seats for org {org!r}. "
            "Common causes: the org has no GitHub Copilot Business (paid org seats), "
            "the org slug in AcademyAuthSettings does not match GitHub, "
            "or the owner token lacks permissions (e.g. org owner / billing admin for Copilot)."
        )
    return str(exc)


def _reconcile_copilot_seats_for_academy_settings(
    settings: AcademyAuthSettings,
    *,
    dry_run: bool = False,
    stdout: Any | None = None,
) -> tuple[int, int, list[dict], list[dict], str | None]:
    empty: list[dict] = []

    if not settings.github_owner_id:
        return 0, 0, empty, empty, None

    owner_creds = CredentialsGithub.objects.filter(user_id=settings.github_owner_id).first()
    if not owner_creds or not owner_creds.token:
        return 0, 0, empty, empty, None

    org = (settings.github_username or "").strip()
    if not org:
        return 0, 0, empty, empty, None

    gb = Github(org=org, token=owner_creds.token)
    if stdout:
        stdout.write(f"    [{org}] list seats...\n")
        stdout.flush()
    try:
        seat_usernames = gb.copilot_list_seat_usernames()
    except Exception as e:
        hint = _format_copilot_list_seats_error(org, e)
        if "404" in str(e) or "not found" in str(e).lower():
            logger.warning("Could not list Copilot seats for org %s: %s", org, hint)
        else:
            logger.exception("Could not list Copilot seats for org %s", org)
        if stdout:
            stdout.write(f"    [{org}] SKIP: {hint}\n")
            stdout.flush()
        return 0, 0, empty, empty, hint

    sibling_academy_ids = list(
        AcademyAuthSettings.objects.filter(github_username__iexact=org).values_list("academy_id", flat=True)
    )
    if not sibling_academy_ids:
        return 0, 0, empty, empty, None

    seat_set = {u.lower() for u in seat_usernames}

    if stdout:
        stdout.write(f"    [{org}] seats={len(seat_usernames)} remove...\n")
        stdout.flush()

    removed = 0
    would_remove: list[dict] = []
    for username in seat_usernames:
        cred = CredentialsGithub.objects.filter(username__iexact=username).select_related("user").first()
        user = cred.user if cred and cred.user_id else None

        should_remove, reason = _copilot_seat_should_be_removed(user, sibling_academy_ids=sibling_academy_ids)
        if not should_remove:
            continue

        entry = {
            "org": org,
            "github_username": username,
            "user_id": getattr(user, "id", None),
            "reason": reason,
        }
        if dry_run:
            would_remove.append(entry)
            continue
        try:
            gb.copilot_remove_selected_users([username])
            removed += 1
            seat_set.discard(username.lower())
        except Exception:
            logger.exception("Failed to remove Copilot seat for %s in org %s (%s)", username, org, reason)

    if dry_run:
        effective_seat_set = seat_set - {w["github_username"].lower() for w in would_remove}
    else:
        effective_seat_set = seat_set

    if stdout:
        stdout.write(f"    [{org}] add...\n")
        stdout.flush()

    added = 0
    would_add: list[dict] = []
    candidate_user_ids = (
        GithubAcademyUser.objects.filter(
            academy_id__in=sibling_academy_ids,
            storage_status=SYNCHED,
            storage_action=ADD,
        )
        .values_list("user_id", flat=True)
        .distinct()
    )
    first_sibling_id = sibling_academy_ids[0]
    for user_id in candidate_user_ids:
        user = User.objects.filter(id=user_id).first()
        if not user:
            continue
        if not _user_has_copilot_entitlement_in_sibling_academies(user, sibling_academy_ids):
            continue
        cred = CredentialsGithub.objects.filter(user_id=user_id).first()
        gh_username = (cred.username or "").strip() if cred else ""
        if not gh_username:
            continue
        if gh_username.lower() in effective_seat_set:
            continue
        entry = {"org": org, "github_username": gh_username, "user_id": user_id}
        if dry_run:
            would_add.append(entry)
            continue
        ok = provision_github_copilot_for_user(
            user_id,
            academy_id=first_sibling_id,
            sibling_academy_ids=sibling_academy_ids,
            source="reconcile_github_copilot_seats",
        )
        if ok:
            added += 1
            effective_seat_set.add(gh_username.lower())

    if dry_run:
        return 0, 0, would_remove, would_add, None
    return removed, added, empty, empty, None


def run_reconcile_github_copilot_seats(
    *,
    dry_run: bool = False,
    stdout: Any | None = None,
) -> dict:
    seen_orgs: set[str] = set()
    seats_removed = 0
    seats_added = 0
    would_remove_all: list[dict] = []
    would_add_all: list[dict] = []
    list_errors: list[dict] = []
    for settings in AcademyAuthSettings.objects.filter(github_owner_id__isnull=False):
        org = (settings.github_username or "").strip().lower()
        if not org or org in seen_orgs:
            continue
        seen_orgs.add(org)
        if stdout:
            stdout.write(f"  org {org}\n")
            stdout.flush()
        removed, added, wr, wa, list_err = _reconcile_copilot_seats_for_academy_settings(
            settings,
            dry_run=dry_run,
            stdout=stdout,
        )
        seats_removed += removed
        seats_added += added
        would_remove_all.extend(wr)
        would_add_all.extend(wa)
        if list_err:
            list_errors.append({"org": org, "error": list_err})
    result: dict = {
        "github_orgs_processed": len(seen_orgs),
        "copilot_seats_removed": seats_removed,
        "copilot_seats_added": seats_added,
    }
    if list_errors:
        result["list_errors"] = list_errors
    if dry_run:
        result["dry_run"] = True
        result["would_remove"] = would_remove_all
        result["would_add"] = would_add_all
    return result


class Command(BaseCommand):
    help = (
        "Align GitHub Copilot seats with GithubAcademyUser + consumables per org: remove ineligible seats, "
        "add missing seats for entitled users. --dry-run: print would_remove / would_add only."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show would_remove and would_add without mutating GitHub.",
        )

    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))
        self.stdout.write("reconcile_github_copilot_seats\n")
        if dry_run:
            self.stdout.write("dry-run (no API mutations)\n")
        self.stdout.flush()
        result = run_reconcile_github_copilot_seats(dry_run=dry_run, stdout=self.stdout)
        if dry_run:
            self.stdout.write(json.dumps(result, indent=2, default=str))
        else:
            self.stdout.write(str(result))
