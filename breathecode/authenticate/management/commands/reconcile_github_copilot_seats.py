import json
import logging
from typing import Any

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from breathecode.authenticate.actions import (
    _copilot_provisioning_academies,
    _user_has_copilot_entitlement_in_sibling_academies,
    is_copilot_auto_provision_enabled,
    copilot_org_sibling_academy_ids,
    get_copilot_settings,
    github_academy_user_allows_copilot_in_sibling_academies,
    provision_github_copilot_for_user,
    save_provisioning_copilot_status,
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
from breathecode.provisioning.models import ProvisioningCopilot
from breathecode.services.github import Github

logger = logging.getLogger(__name__)


def _candidate_user_ids_with_copilot_consumable(sibling_academy_ids: list[int]) -> set[int]:
    """
    Candidate users are sourced from github-copilot consumables first,
    then later filtered by GithubAcademyUser SYNCHED + ADD.
    """
    from breathecode.payments.models import Consumable, PlanFinancingTeam, Service, SubscriptionBillingTeam

    if not sibling_academy_ids:
        return set()

    base_qs = Consumable.objects.filter(
        service_item__service__consumer=Service.Consumer.GITHUB_COPILOT,
    ).filter(
        subscription__academy_id__in=sibling_academy_ids,
    ) | Consumable.objects.filter(
        service_item__service__consumer=Service.Consumer.GITHUB_COPILOT,
        plan_financing__academy_id__in=sibling_academy_ids,
    ) | Consumable.objects.filter(
        service_item__service__consumer=Service.Consumer.GITHUB_COPILOT,
        standalone_invoice__academy_id__in=sibling_academy_ids,
    )

    user_ids: set[int] = set(base_qs.exclude(user_id__isnull=True).values_list("user_id", flat=True))
    user_ids.update(
        base_qs.filter(subscription_seat__is_active=True)
        .exclude(subscription_seat__user_id__isnull=True)
        .values_list("subscription_seat__user_id", flat=True)
    )
    user_ids.update(
        base_qs.filter(plan_financing_seat__is_active=True)
        .exclude(plan_financing_seat__user_id__isnull=True)
        .values_list("plan_financing_seat__user_id", flat=True)
    )
    user_ids.update(
        base_qs.filter(
            user_id__isnull=True,
            subscription_billing_team__consumption_strategy=SubscriptionBillingTeam.ConsumptionStrategy.PER_TEAM,
            subscription_billing_team__seats__is_active=True,
        )
        .exclude(subscription_billing_team__seats__user_id__isnull=True)
        .values_list("subscription_billing_team__seats__user_id", flat=True)
    )
    user_ids.update(
        base_qs.filter(
            user_id__isnull=True,
            plan_financing_team__consumption_strategy=PlanFinancingTeam.ConsumptionStrategy.PER_TEAM,
            plan_financing_team__seats__is_active=True,
        )
        .exclude(plan_financing_team__seats__user_id__isnull=True)
        .values_list("plan_financing_team__seats__user_id", flat=True)
    )

    return user_ids


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
            "the org slug in AcademyAuthSettings / ProvisioningAcademy does not match GitHub, "
            "or the owner token lacks permissions (e.g. org owner / billing admin for Copilot)."
        )
    return str(exc)


def _reconcile_copilot_seats_for_org(
    org: str,
    academy_id: int,
    *,
    dry_run: bool = False,
    stdout: Any | None = None,
) -> tuple[int, int, list[dict], list[dict], list[dict], str | None]:
    empty: list[dict] = []

    _, resolved_org, token = get_copilot_settings(academy_id)
    org = (resolved_org or org or "").strip()
    if not org:
        return 0, 0, empty, empty, empty, None

    if not token:
        hint = f"Missing GitHub admin token for Copilot org {org!r} (academy_id={academy_id})."
        logger.warning("Could not reconcile Copilot seats: %s", hint)
        if stdout:
            stdout.write(f"    [{org}] SKIP: {hint}\n")
            stdout.flush()
        return 0, 0, empty, empty, empty, hint

    started_at = timezone.now()
    gb = Github(org=org, token=token)
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
        return 0, 0, empty, empty, empty, hint

    sibling_academy_ids = copilot_org_sibling_academy_ids(org)
    if not sibling_academy_ids:
        return 0, 0, empty, empty, empty, None

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
            if not dry_run:
                save_provisioning_copilot_status(user, academy_id, "ACTIVE")
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
            if user:
                save_provisioning_copilot_status(user, academy_id, "DEPROVISIONED")
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
    would_skip_add: list[dict] = []
    candidate_user_ids = sorted(_candidate_user_ids_with_copilot_consumable(sibling_academy_ids))
    for user_id in candidate_user_ids:
        user = User.objects.filter(id=user_id).first()
        if not user:
            if dry_run:
                would_skip_add.append({"org": org, "user_id": user_id, "reason": "user_not_found"})
            continue
        if not github_academy_user_allows_copilot_in_sibling_academies(user, sibling_academy_ids):
            if dry_run:
                would_skip_add.append({"org": org, "user_id": user_id, "reason": "no_synched_add_github_academy_user"})
            continue
        if not _user_has_copilot_entitlement_in_sibling_academies(user, sibling_academy_ids):
            if dry_run:
                would_skip_add.append({"org": org, "user_id": user_id, "reason": "no_copilot_entitlement"})
            continue
        cred = CredentialsGithub.objects.filter(user_id=user_id).first()
        gh_username = (cred.username or "").strip() if cred else ""
        if not gh_username:
            if dry_run:
                would_skip_add.append({"org": org, "user_id": user_id, "reason": "missing_github_username"})
            continue
        if gh_username.lower() in effective_seat_set:
            if dry_run:
                would_skip_add.append(
                    {"org": org, "user_id": user_id, "github_username": gh_username, "reason": "already_has_seat"}
                )
            continue
        if not is_copilot_auto_provision_enabled(user, academy_id):
            if dry_run:
                would_skip_add.append({"org": org, "user_id": user_id, "reason": "manual_mode"})
            continue
        entry = {"org": org, "github_username": gh_username, "user_id": user_id}
        if dry_run:
            would_add.append(entry)
            continue
        ok = provision_github_copilot_for_user(
            user_id,
            academy_id=academy_id,
            sibling_academy_ids=sibling_academy_ids,
            source="reconcile_github_copilot_seats",
        )
        if ok:
            added += 1
            effective_seat_set.add(gh_username.lower())

    if dry_run:
        return 0, 0, would_remove, would_add, would_skip_add, None

    # Seats removed directly in GitHub. Rows provisioned during this run aren't in the list downloaded at the start.
    # The table is only a record: failing to read it must not stop the next orgs.
    try:
        active_rows = ProvisioningCopilot.objects.filter(
            org__iexact=org, status=ProvisioningCopilot.STATUS_ACTIVE
        ).exclude(provisioned_at__gte=started_at)
        for row in active_rows.select_related("user"):
            if row.github_username.lower() not in effective_seat_set:
                save_provisioning_copilot_status(row.user, academy_id, "DEPROVISIONED")
    except Exception:
        logger.exception("Could not align ProvisioningCopilot rows for org %s", org)

    return removed, added, empty, empty, empty, None


def _copilot_orgs_to_reconcile() -> dict[str, int]:
    """
    Map each resolved Copilot org (lowercased) to the academy whose credentials are used to reconcile it.

    Candidates: legacy AcademyAuthSettings with an org and an owner, then academies with a Copilot
    ProvisioningAcademy. Academies with a token go first, so one without it doesn't block the whole org.
    """
    pa_academy_ids = list(_copilot_provisioning_academies().order_by("id").values_list("academy_id", flat=True))
    legacy_academy_ids = list(
        AcademyAuthSettings.objects.filter(github_owner_id__isnull=False)
        .exclude(github_username="")
        .exclude(academy_id__in=pa_academy_ids)
        .order_by("id")
        .values_list("academy_id", flat=True)
    )

    with_token: dict[str, int] = {}
    without_token: dict[str, int] = {}
    for academy_id in legacy_academy_ids + pa_academy_ids:
        _, org, token = get_copilot_settings(academy_id)
        org = (org or "").strip().lower()
        if org:
            (with_token if token else without_token).setdefault(org, academy_id)
    return {**without_token, **with_token}


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
    would_skip_add_all: list[dict] = []
    list_errors: list[dict] = []
    for org, academy_id in _copilot_orgs_to_reconcile().items():
        seen_orgs.add(org)
        if stdout:
            stdout.write(f"  org {org}\n")
            stdout.flush()
        removed, added, wr, wa, ws, list_err = _reconcile_copilot_seats_for_org(
            org,
            academy_id,
            dry_run=dry_run,
            stdout=stdout,
        )
        seats_removed += removed
        seats_added += added
        would_remove_all.extend(wr)
        would_add_all.extend(wa)
        would_skip_add_all.extend(ws)
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
        result["would_skip_add"] = would_skip_add_all
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
