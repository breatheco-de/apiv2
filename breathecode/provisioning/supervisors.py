import logging
from datetime import timedelta

from breathecode.notify.actions import send_email_message
from breathecode.payments.models import Consumable
from breathecode.provisioning.models import ProvisioningAcademy, ProvisioningLLM
from breathecode.provisioning.tasks import deprovision_litellm_user_task
from breathecode.provisioning.utils.llm_client import LLMClientError, get_llm_client
from breathecode.provisioning.utils.llm_data_collection import (
    LLMDataCollection,
    collect_llm_data,
)
from breathecode.utils.decorators import issue, supervisor

logger = logging.getLogger(__name__)

LLM_BUDGET_SERVICE = "free-monthly-llm-budget"
LLM_EXCLUDED_USER_IDS = frozenset({"default_user_id"})


def _academy_slug_for_user_id(user_id: str, academy_slugs: list[str]) -> str | None:
    for slug in sorted(academy_slugs, key=len, reverse=True):
        suffix = f"-{slug}"
        if user_id.endswith(suffix) and len(user_id) > len(suffix):
            return slug
    return None


def _known_academy_slugs(snapshot: LLMDataCollection) -> list[str]:
    slugs: list[str] = []
    for academy in snapshot["academies"]:
        slug = academy.get("academy_slug")
        if slug:
            slugs.append(str(slug))
    return slugs


def llm_team_models_missing_academy_prefix(snapshot: LLMDataCollection):
    for team in snapshot["teams"]:
        academy_config = team.get("academy_config")
        if not academy_config:
            continue

        academy_slug = academy_config.get("academy_slug")
        if not academy_slug:
            continue

        slug = str(academy_slug)
        expected_prefix = f"{slug}/"
        invalid_models = [
            str(model).strip()
            for model in (team.get("models") or [])
            if model and not str(model).strip().startswith(expected_prefix)
        ]
        if not invalid_models:
            continue

        team_id = team["team_id"]
        message = (
            f"LiteLLM team {team_id} ({slug}) has models without {slug}/ prefix: {', '.join(sorted(invalid_models))}"
        )
        yield (
            message,
            "alert-llm-compliance",
            {
                "message": message,
                "team_id": team_id,
                "academy_config": academy_config,
            },
        )


def llm_team_budget_misconfigured(snapshot: LLMDataCollection):
    for team in snapshot["teams"]:
        academy_config = team.get("academy_config")
        if not academy_config:
            continue

        team_id = team["team_id"]
        slug = academy_config.get("academy_slug") or ""
        problems: list[str] = []

        team_max_budget = team.get("team_max_budget")
        team_max_budget_missing = True
        if team_max_budget is not None:
            try:
                team_max_budget_missing = float(team_max_budget) <= 0
            except (TypeError, ValueError):
                team_max_budget_missing = True
        if team_max_budget_missing:
            problems.append("team max_budget")

        team_duration = team.get("team_budget_duration")
        if team_duration is None or not str(team_duration).strip():
            problems.append("team budget_duration")

        team_member_budget_id = team.get("team_member_budget_id")
        if not team_member_budget_id:
            problems.append("team_member_budget_id")
        else:
            if team.get("member_max_budget") is None:
                problems.append("member max_budget")

            member_duration = team.get("member_budget_duration")
            if member_duration is None or not str(member_duration).strip():
                problems.append("member budget_duration")

        if not problems:
            continue

        message = (
            f"LiteLLM team {team_id} ({slug}) has budget fields not defined (should be configured): "
            f"{', '.join(problems)}"
        )
        yield (
            message,
            "alert-llm-compliance",
            {
                "message": message,
                "team_id": team_id,
                "academy_config": academy_config,
            },
        )


def llm_team_spend_near_limit(snapshot: LLMDataCollection):
    for team in snapshot["teams"]:
        academy_config = team.get("academy_config")
        if not academy_config:
            continue

        team_max_budget = team.get("team_max_budget")
        team_spend = team.get("team_spend")
        if team_max_budget is None or team_spend is None:
            continue

        try:
            max_budget = float(team_max_budget)
            spend = float(team_spend)
        except (TypeError, ValueError):
            continue

        if max_budget <= 0:
            continue

        spend_ratio = spend / max_budget
        if spend_ratio < 0.9:
            continue

        team_id = team["team_id"]
        slug = academy_config.get("academy_slug") or ""
        percent = int(spend_ratio * 100)
        message = (
            f"LiteLLM team {team_id} ({slug}) spend is {percent}% of max_budget "
            f"({spend}/{max_budget} USD, threshold >= 90%)"
        )
        yield (
            message,
            "alert-llm-compliance",
            {
                "message": message,
                "team_id": team_id,
                "academy_config": academy_config,
            },
        )


def llm_key_missing_team_id(snapshot: LLMDataCollection):
    for key in snapshot["keys"]:
        if key["team_id"]:
            continue

        message = f"LiteLLM key {key['key_alias'] or key['token_id']} has no team_id"
        params = {
            "message": message,
            "token_id": key["token_id"],
        }
        if academy_config := key.get("academy_config"):
            params["academy_config"] = academy_config

        yield (message, "alert-llm-compliance", params)


def llm_key_missing_expires(snapshot: LLMDataCollection):
    for key in snapshot["keys"]:
        if key["expires"]:
            continue

        params = {"token_id": key["token_id"]}
        if key.get("team_id"):
            params["team_id"] = key["team_id"]
        academy_config = key.get("academy_config")
        if academy_config:
            params["provisioning_academy_id"] = academy_config["provisioning_academy_id"]

        yield (
            f"LiteLLM key {key['key_alias'] or key['token_id']} has no expires",
            "fix-llm-key-missing-expires",
            params,
        )


def llm_user_too_many_keys(snapshot: LLMDataCollection):
    counts: dict[str, int] = {}
    for key in snapshot["keys"]:
        user_id = key["user_id"]
        if not user_id:
            continue
        counts[user_id] = counts.get(user_id, 0) + 1

    for user_id, key_count in counts.items():
        if key_count < 7:
            continue

        message = f"LiteLLM user {user_id} has {key_count} keys (>= 7)"
        academy_config = None
        for key in snapshot["keys"]:
            if key["user_id"] == user_id and key.get("academy_config"):
                academy_config = key["academy_config"]
                break

        params = {
            "message": message,
            "user_id": user_id,
            "key_count": key_count,
        }
        if academy_config:
            params["academy_config"] = academy_config

        yield (message, "alert-llm-compliance", params)


def llm_key_missing_user_id(snapshot: LLMDataCollection):
    for key in snapshot["keys"]:
        if key["user_id"]:
            continue

        message = f"LiteLLM key {key['key_alias'] or key['token_id']} has no user_id"

        params = {
            "message": message,
            "token_id": key["token_id"],
        }
        if academy_config := key.get("academy_config"):
            params["academy_config"] = academy_config

        yield (message, "alert-llm-compliance", params)


def llm_external_user_without_provisioning(snapshot: LLMDataCollection):
    for user in snapshot["llm_external_users"]:
        if user["user_id"] in LLM_EXCLUDED_USER_IDS:
            continue
        if user["provisioning_llm"] is not None:
            continue

        message = f"LiteLLM user {user['user_id']} has no active ProvisioningLLM record"

        params = {
            "message": message,
            "user_id": user["user_id"],
            "user_role": user["user_role"],
        }
        if academy_config := user.get("academy_config"):
            params["academy_config"] = academy_config

        yield (message, "alert-llm-compliance", params)


def llm_external_user_invalid_convention(snapshot: LLMDataCollection):
    academy_slugs = _known_academy_slugs(snapshot)

    for user in snapshot["llm_external_users"]:
        user_id = user["user_id"]
        if user_id in LLM_EXCLUDED_USER_IDS:
            continue
        if _academy_slug_for_user_id(user_id, academy_slugs):
            continue

        message = f"LiteLLM user {user_id} does not follow the username-academy_slug convention"
        params = {
            "message": message,
            "user_id": user_id,
            "user_role": user["user_role"],
        }
        if academy_config := user.get("academy_config"):
            params["academy_config"] = academy_config

        yield (message, "alert-llm-compliance", params)


def llm_user_missing_team(snapshot: LLMDataCollection):
    academy_by_slug = {}
    for academy in snapshot["academies"]:
        slug = academy.get("academy_slug")
        if slug:
            academy_by_slug[str(slug)] = academy

    for user in snapshot["llm_external_users"]:
        user_id = user["user_id"]
        if user_id in LLM_EXCLUDED_USER_IDS:
            continue

        slug = _academy_slug_for_user_id(user_id, list(academy_by_slug.keys()))
        if slug is None:
            continue

        academy = academy_by_slug[slug]
        team_id = academy["team_id"]
        if team_id in user["teams"]:
            continue

        yield (
            f"LiteLLM user {user_id} is not a member of team {team_id}",
            "fix-llm-user-missing-team",
            {
                "user_id": user_id,
                "team_id": team_id,
                "provisioning_academy_id": academy["provisioning_academy_id"],
            },
        )


@supervisor(delta=timedelta(hours=6))
def supervise_llm_users_without_budget():
    """
    Detect active LLM provisioning rows for users that no longer have LLM budget consumables.
    """
    pairs = (
        ProvisioningLLM.objects.filter(status=ProvisioningLLM.STATUS_ACTIVE)
        .values_list("user_id", "academy_id")
        .distinct()
    )

    for user_id, academy_id in pairs.iterator():
        has_budget = (
            Consumable.list(
                user=user_id,
                service=LLM_BUDGET_SERVICE,
                extra={"subscription__academy_id": academy_id},
            ).exists()
            or Consumable.list(
                user=user_id,
                service=LLM_BUDGET_SERVICE,
                extra={"plan_financing__academy_id": academy_id},
            ).exists()
        )
        if has_budget:
            continue

        yield (
            f"User {user_id} has active LLM provisioning rows in academy {academy_id} but no {LLM_BUDGET_SERVICE} consumable",
            "llm-user-missing-budget",
            {"user_id": user_id, "academy_id": academy_id},
        )


@issue(supervise_llm_users_without_budget, delta=timedelta(minutes=15), attempts=3)
def llm_user_missing_budget(user_id: int, academy_id: int):
    """
    Schedule Litellm deprovision for users that lost entitlement.
    """
    active_llm_exists = ProvisioningLLM.objects.filter(
        user_id=user_id, academy_id=academy_id, status=ProvisioningLLM.STATUS_ACTIVE
    ).exists()
    if not active_llm_exists:
        return True

    has_budget = (
        Consumable.list(
            user=user_id,
            service=LLM_BUDGET_SERVICE,
            extra={"subscription__academy_id": academy_id},
        ).exists()
        or Consumable.list(
            user=user_id,
            service=LLM_BUDGET_SERVICE,
            extra={"plan_financing__academy_id": academy_id},
        ).exists()
    )
    if has_budget:
        return True

    deprovision_litellm_user_task.delay(user_id=user_id, academy_id=academy_id)
    return None


@supervisor(delta=timedelta(hours=4))
def supervise_llm_key_compliance():
    """
    Detect LiteLLM compliance issues across provisioning academies.

    Performs one ``collect_llm_data()`` fetch per run, then runs key/user checks (S1)
    and team config checks (S2) from the collected snapshot.
    """
    snapshot = collect_llm_data()

    yield from llm_key_missing_team_id(snapshot)
    yield from llm_key_missing_expires(snapshot)
    yield from llm_user_too_many_keys(snapshot)
    yield from llm_key_missing_user_id(snapshot)
    yield from llm_external_user_without_provisioning(snapshot)
    yield from llm_external_user_invalid_convention(snapshot)
    yield from llm_user_missing_team(snapshot)

    yield from llm_team_models_missing_academy_prefix(snapshot)
    yield from llm_team_budget_misconfigured(snapshot)
    yield from llm_team_spend_near_limit(snapshot)


@issue(supervise_llm_key_compliance, delta=timedelta(minutes=30), attempts=3)
def fix_llm_key_missing_expires(token_id: str, team_id: str | None = None, provisioning_academy_id: int | None = None):
    if not token_id:
        return False

    if provisioning_academy_id is None:
        logger.warning("fix_llm_key_missing_expires skipped: missing provisioning_academy_id for token_id=%s", token_id)
        return False

    provisioning_academy = ProvisioningAcademy.objects.filter(id=provisioning_academy_id).first()
    if provisioning_academy is None:
        return False

    client = get_llm_client(provisioning_academy)
    if client is None or not hasattr(client, "update_key"):
        return None

    try:
        client.update_key(key=token_id, duration="30d")
    except LLMClientError as exc:
        logger.warning(
            "fix_llm_key_missing_expires failed for token_id=%s team_id=%s: %s",
            token_id,
            team_id,
            exc,
        )
        return None

    return True


@issue(supervise_llm_key_compliance, delta=timedelta(minutes=30), attempts=3)
def fix_llm_user_missing_team(user_id: str, team_id: str, provisioning_academy_id: int):
    provisioning_academy = ProvisioningAcademy.objects.filter(id=provisioning_academy_id).first()
    if provisioning_academy is None:
        return False

    client = get_llm_client(provisioning_academy)
    if client is None or not hasattr(client, "add_user_to_team"):
        return None

    try:
        client.add_user_to_team(team_id=team_id, user_ids=[user_id])
    except LLMClientError as exc:
        exc_msg = str(exc).lower()
        if "409" in exc_msg or "already" in exc_msg or "exists" in exc_msg:
            return True
        logger.warning(
            "fix_llm_user_missing_team failed for user_id=%s team_id=%s: %s",
            user_id,
            team_id,
            exc,
        )
        return None

    return True


@issue(supervise_llm_key_compliance, delta=timedelta(minutes=30), attempts=1)
def alert_llm_compliance(message: str, academy_config: dict | None = None, **_):
    config = academy_config or {}
    provisioning_academy_id = config.get("provisioning_academy_id")
    alert_emails = config.get("alert_emails") or []

    if not provisioning_academy_id or not alert_emails:
        logger.warning("LiteLLM compliance alert skipped: missing provisioning_academy_id or alert_emails")
        return True

    provisioning_academy = (
        ProvisioningAcademy.objects.filter(id=provisioning_academy_id).select_related("academy").first()
    )
    if provisioning_academy is None:
        logger.warning(
            "LiteLLM compliance alert skipped: provisioning_academy_id=%s not found",
            provisioning_academy_id,
        )
        return True

    send_email_message(
        "diagnostic",
        alert_emails,
        {
            "subject": f"LiteLLM compliance alert: {message}",
            "details": message,
        },
        academy=provisioning_academy.academy,
    )
    return True
