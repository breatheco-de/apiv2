import logging
from collections import defaultdict
from datetime import timedelta

from breathecode.notify.actions import send_email_message
from breathecode.payments.models import Consumable
from breathecode.provisioning.models import ProvisioningAcademy, ProvisioningLLM
from breathecode.provisioning.tasks import deprovision_litellm_user_task
from breathecode.provisioning.utils.llm_client import LLMClientError, get_llm_client
from breathecode.provisioning.utils.llm_data_collection import (
    LLMDataCollection,
    collect_llm_daily_spend,
    collect_llm_data,
)
from breathecode.utils.decorators import issue, supervisor

logger = logging.getLogger(__name__)

LLM_BUDGET_SERVICE = "free-monthly-llm-budget"
LLM_EXCLUDED_USER_IDS = frozenset({"default_user_id"})
LLM_DAILY_SPEND_NEAR_LIMIT_RATIO = 0.9
LLM_DAILY_SPEND_FALLBACK_MAX_BUDGET = 10.0


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


def _compliance_entity_display_label(entity_kind: str, entity_id: str, messages: list[str]) -> str:
    prefix = f"LiteLLM {entity_kind} "
    for message in messages:
        if not message.startswith(prefix):
            continue
        rest = message[len(prefix) :]
        for sep in (" has ", " ("):
            if sep in rest:
                return rest.split(sep, 1)[0]
        if rest:
            return rest
    return entity_id


def _build_grouped_compliance_alert_body(entity_kind: str, entity_id: str, messages: list[str]) -> str:
    if len(messages) == 1:
        return messages[0]

    label = _compliance_entity_display_label(entity_kind, entity_id, messages)
    header = f'LiteLLM compliance alert — {entity_kind} "{label}" ({len(messages)} issues)'
    return header + ":\n\n" + "\n".join(f"- {line}" for line in messages)


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
            f"LiteLLM team {slug} has models without {slug}/ prefix: {', '.join(sorted(invalid_models))}"
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
            f"LiteLLM team {slug} has budget fields not defined (should be configured): "
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
            f"LiteLLM team {slug} spend is {percent}% of max_budget "
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


def llm_team_daily_spend_near_limit(snapshot: LLMDataCollection):
    for team in snapshot["teams"]:
        academy_config = team.get("academy_config")
        if not academy_config:
            continue

        team_max_budget = team.get("team_max_budget")
        team_daily_spend = team.get("team_daily_spend")
        if team_max_budget is None or team_daily_spend is None:
            continue

        try:
            max_budget = float(team_max_budget)
            spend = float(team_daily_spend)
        except (TypeError, ValueError):
            continue

        if max_budget <= 0 or spend <= 0:
            continue

        spend_ratio = spend / max_budget
        if spend_ratio < LLM_DAILY_SPEND_NEAR_LIMIT_RATIO:
            continue

        team_id = team["team_id"]
        slug = academy_config.get("academy_slug") or ""
        percent = int(spend_ratio * 100)
        message = (
            f"LiteLLM team {slug} has high single-day spend: {percent}% of max_budget "
            f"({spend}/{max_budget} USD for today only, threshold >= 90%)"
        )
        yield (
            message,
            "alert-llm-spend-anomaly",
            {
                "message": message,
                "team_id": team_id,
                "academy_config": academy_config,
            },
        )


def llm_user_daily_spend_near_limit(snapshot: LLMDataCollection):
    for user in snapshot["llm_external_users"]:
        user_id = user["user_id"]
        if user_id in LLM_EXCLUDED_USER_IDS:
            continue

        daily_spend = user.get("daily_spend")
        if daily_spend is None:
            continue

        member_max_budget = None
        academy_config = user.get("academy_config")
        team_ids = [str(team_id) for team_id in (user.get("teams") or []) if team_id]
        for team in snapshot["teams"]:
            if str(team["team_id"]) in team_ids:
                member_max_budget = team.get("member_max_budget")
                academy_config = team.get("academy_config") or academy_config
                break

        if academy_config is None:
            continue

        spend = daily_spend
        if spend <= 0:
            continue

        if member_max_budget and member_max_budget > 0:
            max_budget = member_max_budget
            used_fallback = False
        else:
            max_budget = LLM_DAILY_SPEND_FALLBACK_MAX_BUDGET
            used_fallback = True

        spend_ratio = spend / max_budget
        if spend_ratio < LLM_DAILY_SPEND_NEAR_LIMIT_RATIO:
            continue

        slug = academy_config.get("academy_slug") or ""
        percent = int(spend_ratio * 100)
        budget_label = f"fallback max_budget ({max_budget} USD)" if used_fallback else "member max_budget"
        message = (
            f"LiteLLM user {user_id} ({slug}) has high single-day spend: {percent}% of {budget_label} "
            f"({spend}/{max_budget} USD for today only, threshold >= 90%)"
        )
        yield (
            message,
            "alert-llm-spend-anomaly",
            {
                "message": message,
                "user_id": user_id,
                "academy_config": academy_config,
            },
        )


def llm_key_without_user_daily_spend(snapshot: LLMDataCollection):
    for key in snapshot["keys"]:
        if key.get("user_id"):
            continue

        daily_spend = key.get("daily_spend")
        if daily_spend is None:
            continue

        spend = daily_spend
        if spend <= 0:
            continue

        member_max_budget = None
        team_academy_config = None
        team_id = key.get("team_id")
        if team_id:
            for team in snapshot["teams"]:
                if str(team["team_id"]) == str(team_id):
                    member_max_budget = team.get("member_max_budget")
                    team_academy_config = team.get("academy_config")
                    break

        academy_config = team_academy_config or key.get("academy_config")
        if not academy_config:
            continue

        if member_max_budget and member_max_budget > 0:
            max_budget = member_max_budget
            used_fallback = False
        else:
            max_budget = LLM_DAILY_SPEND_FALLBACK_MAX_BUDGET
            used_fallback = True

        spend_ratio = spend / max_budget
        if spend_ratio < LLM_DAILY_SPEND_NEAR_LIMIT_RATIO:
            continue

        budget_label = f"fallback max_budget ({max_budget} USD)" if used_fallback else "member max_budget"
        percent = int(spend_ratio * 100)
        message = (
            f"LiteLLM key {key['key_alias'] or key['token_id']} (no user_id) has high single-day spend: "
            f"{percent}% of {budget_label} ({spend}/{max_budget} USD for today only, threshold >= 90%)"
        )
        params = {
            "message": message,
            "token_id": key["token_id"],
            "academy_config": academy_config,
        }

        yield (message, "alert-llm-spend-anomaly", params)


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
            f"LiteLLM user {user_id} is not a member of team {slug}",
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


@supervisor(delta=timedelta(hours=8))
def supervise_llm_key_compliance():
    """
    Detect LiteLLM compliance issues across provisioning academies.

    Performs one ``collect_llm_data()`` fetch per run, then runs key/user checks (S1)
    and team config checks (S2) from the collected snapshot.
    """
    snapshot = collect_llm_data()

    # Auto-fixes: one issue per problem, handled by fix_* (no email).
    yield from llm_key_missing_expires(snapshot)
    yield from llm_user_missing_team(snapshot)

    # Email alerts: run supervisors into one list first.
    compliance_alerts: list[tuple[str, str, dict]] = []
    for detector in (
        llm_key_missing_team_id,
        llm_user_too_many_keys,
        llm_key_missing_user_id,
        llm_external_user_without_provisioning,
        llm_external_user_invalid_convention,
        llm_team_models_missing_academy_prefix,
        llm_team_budget_misconfigured,
        llm_team_spend_near_limit,
    ):
        compliance_alerts.extend(detector(snapshot))

    # Group by entity so one key/user/team with N problems -> one email.
    # Order matters: token_id wins over user_id over team_id.
    group_specs = (
        ("token_id", "key"),
        ("user_id", "user"),
        ("team_id", "team"),
    )
    grouped_alerts = {entity_param: defaultdict(list) for entity_param, _ in group_specs}

    for message, code, params in compliance_alerts:
        if code != "alert-llm-compliance":
            continue

        params = params or {}
        for entity_param in grouped_alerts:
            if entity_id := params.get(entity_param):
                grouped_alerts[entity_param][str(entity_id)].append((message, params))
                break
        else:
            logger.warning("LiteLLM compliance alert skipped (no group key): %s", message)

    for entity_param, entity_kind in group_specs:
        for entity_id, items in grouped_alerts[entity_param].items():
            messages = sorted(message for message, _ in items)
            # Used by alert_llm_compliance to pick soft_budget_alerting_emails recipients.
            academy_config = next(
                (item_params["academy_config"] for _, item_params in items if item_params.get("academy_config")),
                None,
            )

            body = _build_grouped_compliance_alert_body(entity_kind, entity_id, messages)
            issue_params = {
                "message": body,
                entity_param: entity_id,
                "grouped": True,
                "issue_count": len(messages),
                "items": [item_params for _, item_params in items],
            }
            if academy_config:
                issue_params["academy_config"] = academy_config
            yield (body, "alert-llm-compliance", issue_params)


@supervisor(delta=timedelta(hours=6))
def supervise_llm_spend_anomalies():
    """
    Detect LiteLLM daily spend anomalies across provisioning academies.

    Uses ``collect_llm_daily_spend()`` which enriches the compliance snapshot with
    per-key, per-user, and per-team daily spend from daily activity aggregated API.
    """
    snapshot = collect_llm_daily_spend()

    yield from llm_user_daily_spend_near_limit(snapshot)
    yield from llm_team_daily_spend_near_limit(snapshot)
    yield from llm_key_without_user_daily_spend(snapshot)


@issue(supervise_llm_spend_anomalies, delta=timedelta(minutes=30), attempts=1)
def alert_llm_spend_anomaly(message: str, academy_config: dict | None = None, **_):
    return _deliver_llm_compliance_alert(message, academy_config, subject="LiteLLM spend alert")


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
    return _deliver_llm_compliance_alert(message, academy_config)


def _deliver_llm_compliance_alert(
    message: str,
    academy_config: dict | None = None,
    *,
    subject: str = "LiteLLM compliance alert",
):
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
            "subject": subject,
            "details": message,
        },
        academy=provisioning_academy.academy,
    )
    return True
