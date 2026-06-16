"""Collect and enrich LiteLLM data from vendor APIs and provisioning models."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import TypedDict

from breathecode.provisioning.models import ProvisioningAcademy, ProvisioningLLM
from breathecode.provisioning.utils.llm_client import LLMClientError, get_llm_client

logger = logging.getLogger(__name__)

LLMCredentials = tuple[str, str]

__all__ = [
    "AcademyConfigRow",
    "LLMDataCollection",
    "LLMExternalUserRow",
    "LLMKeyRow",
    "LLMTeamRow",
    "ProvisioningUserRow",
    "collect_llm_data",
]


class AcademyConfigRow(TypedDict):
    provisioning_academy_id: int
    academy_slug: str
    team_id: str
    alert_emails: list[str]


class LLMKeyRow(TypedDict):
    token_id: str | None
    key_alias: str | None
    user_id: str | None
    team_id: str | None
    expires: str | None
    provisioning_llm: ProvisioningLLM | None
    academy_config: AcademyConfigRow | None


class LLMTeamRow(TypedDict):
    team_id: str
    member_user_ids: frozenset[str]
    academy_config: AcademyConfigRow | None
    models: list[str]
    team_spend: float | None
    team_max_budget: float | None
    team_budget_duration: str | None
    team_member_budget_id: str | None
    member_max_budget: float | None
    member_budget_duration: str | None


class ProvisioningUserRow(TypedDict):
    provisioning_academy: ProvisioningAcademy
    provisioning_llm: ProvisioningLLM


class LLMExternalUserRow(TypedDict):
    user_id: str
    user_role: str | None
    teams: list[str]
    key_count: int | None
    provisioning_llm: ProvisioningLLM | None
    academy_config: AcademyConfigRow | None


class LLMDataCollection(TypedDict):
    keys: list[LLMKeyRow]
    teams: list[LLMTeamRow]
    academies: list[AcademyConfigRow]
    provisioning_users: list[ProvisioningUserRow]
    llm_external_users: list[LLMExternalUserRow]


def _extract_soft_budget_alert_emails(raw_team: dict) -> list[str]:
    metadata = raw_team.get("metadata") or {}
    team_info = raw_team.get("team_info") or {}
    team_info_metadata = team_info.get("metadata") or {}
    raw_emails = (
        metadata.get("soft_budget_alerting_emails") or team_info_metadata.get("soft_budget_alerting_emails") or []
    )
    return [str(email).strip() for email in raw_emails if email and str(email).strip()]


def _fetch_member_budgets_by_id(client, raw_teams: list[dict]) -> dict[str, dict]:
    budget_ids: list[str] = []
    for raw_team in raw_teams:
        metadata = raw_team.get("metadata") or {}
        budget_id_raw = metadata.get("team_member_budget_id")
        if budget_id_raw is None or not str(budget_id_raw).strip():
            continue
        budget_ids.append(str(budget_id_raw).strip())

    if not budget_ids or not hasattr(client, "get_budgets_info"):
        return {}

    try:
        budgets = client.get_budgets_info(budgets=list(set(budget_ids)))
    except LLMClientError as exc:
        logger.warning("LiteLLM member budgets fetch failed: %s", exc)
        return {}

    return {str(budget["budget_id"]): budget for budget in budgets if budget.get("budget_id")}


def _academy_config_rows(
    provisioning_academies: list[ProvisioningAcademy], raw_teams: list[dict]
) -> list[AcademyConfigRow]:
    emails_by_team: dict[str, list[str]] = {}
    for raw_team in raw_teams:
        team_id_raw = raw_team.get("team_id")
        if team_id_raw is None or not str(team_id_raw).strip():
            continue
        team_id = str(team_id_raw).strip()
        emails_by_team[team_id] = _extract_soft_budget_alert_emails(raw_team)

    rows: list[AcademyConfigRow] = []
    for provisioning_academy in provisioning_academies:
        vendor_settings = provisioning_academy.vendor_settings or {}
        team_id = str(vendor_settings.get("team_id") or "").strip()
        if not team_id:
            continue

        academy_slug = getattr(provisioning_academy.academy, "slug", None)
        rows.append(
            {
                "provisioning_academy_id": provisioning_academy.id,
                "academy_slug": str(academy_slug) if academy_slug else "",
                "team_id": team_id,
                "alert_emails": emails_by_team.get(team_id, []),
            }
        )
    return rows


def _provisioning_user_rows(provisioning_academies: list[ProvisioningAcademy]) -> list[ProvisioningUserRow]:
    rows: list[ProvisioningUserRow] = []
    for provisioning_academy in provisioning_academies:
        provisioning_llms = (
            ProvisioningLLM.objects.filter(
                academy_id=provisioning_academy.academy_id,
                vendor_id=provisioning_academy.vendor_id,
                status=ProvisioningLLM.STATUS_ACTIVE,
            )
            .exclude(external_user_id__isnull=True)
            .exclude(external_user_id="")
        )
        for provisioning_llm in provisioning_llms:
            rows.append(
                {
                    "provisioning_academy": provisioning_academy,
                    "provisioning_llm": provisioning_llm,
                }
            )
    return rows


def _fetch_litellm_users(client) -> list[dict]:
    if not hasattr(client, "list_users"):
        return []

    all_users: list[dict] = []
    page = 1
    while True:
        page_data = client.list_users(page=page, page_size=100)
        all_users.extend(page_data.get("users") or [])
        total_pages = page_data.get("total_pages") or 1
        if page >= total_pages:
            break
        page += 1

    return all_users


def _fetch_litellm_keys_and_teams(client) -> tuple[list[dict], list[dict]]:
    all_keys: list[dict] = []
    page = 1
    while True:
        page_data = client.list_keys(return_full_object=True, page=page, size=100)
        all_keys.extend(page_data.get("keys") or [])
        total_pages = page_data.get("total_pages") or 1
        if page >= total_pages:
            break
        page += 1

    teams_data = client.list_teams() if hasattr(client, "list_teams") else {}
    return all_keys, teams_data.get("teams") or []


def _llm_key_rows(
    raw_keys: list[dict],
    group_academies: list[AcademyConfigRow],
    group_provisioning_users: list[ProvisioningUserRow],
    default_config: AcademyConfigRow | None,
) -> list[LLMKeyRow]:
    academy_config_by_team = {academy["team_id"]: academy for academy in group_academies}
    provisioning_by_external_user = {
        provisioning_user["provisioning_llm"].external_user_id: provisioning_user
        for provisioning_user in group_provisioning_users
    }
    rows: list[LLMKeyRow] = []

    for raw_key in raw_keys:
        team_id_raw = raw_key.get("team_id")
        team_id = str(team_id_raw).strip() if team_id_raw is not None and str(team_id_raw).strip() else None

        team_config = academy_config_by_team.get(team_id) if team_id else None
        academy_config = team_config or default_config

        user_id_raw = raw_key.get("user_id")
        user_id = str(user_id_raw).strip() if user_id_raw is not None and str(user_id_raw).strip() else None

        match = provisioning_by_external_user.get(user_id) if user_id else None
        provisioning_llm = match["provisioning_llm"] if match else None

        expires_raw = raw_key.get("expires")
        expires = str(expires_raw) if expires_raw else None

        rows.append(
            {
                "token_id": raw_key.get("token_id"),
                "key_alias": raw_key.get("key_alias"),
                "user_id": user_id,
                "team_id": team_id,
                "expires": expires,
                "provisioning_llm": provisioning_llm,
                "academy_config": academy_config,
            }
        )

    return rows


def _llm_team_rows(
    raw_teams: list[dict],
    group_academies: list[AcademyConfigRow],
    member_budgets_by_id: dict[str, dict],
) -> list[LLMTeamRow]:
    academy_config_by_team = {academy["team_id"]: academy for academy in group_academies}
    rows: list[LLMTeamRow] = []

    for raw_team in raw_teams:
        team_id_raw = raw_team.get("team_id")
        if team_id_raw is None or not str(team_id_raw).strip():
            continue

        team_id = str(team_id_raw).strip()
        academy_config = academy_config_by_team.get(team_id)

        members: set[str] = set()
        for member in raw_team.get("members_with_roles") or []:
            user_id = member.get("user_id") if isinstance(member, dict) else None
            if user_id:
                members.add(str(user_id))

        metadata = raw_team.get("metadata") or {}
        team_member_budget_id_raw = metadata.get("team_member_budget_id")
        team_member_budget_id = (
            str(team_member_budget_id_raw).strip()
            if team_member_budget_id_raw is not None and str(team_member_budget_id_raw).strip()
            else None
        )
        member_budget = member_budgets_by_id.get(team_member_budget_id) if team_member_budget_id else None
        member_budget_duration_raw = member_budget.get("budget_duration") if member_budget else None
        member_budget_duration = (
            str(member_budget_duration_raw).strip()
            if member_budget_duration_raw is not None and str(member_budget_duration_raw).strip()
            else None
        )
        team_budget_duration_raw = raw_team.get("budget_duration")
        team_budget_duration = (
            str(team_budget_duration_raw).strip()
            if team_budget_duration_raw is not None and str(team_budget_duration_raw).strip()
            else None
        )

        rows.append(
            {
                "team_id": team_id,
                "member_user_ids": frozenset(members),
                "academy_config": academy_config,
                "models": list(raw_team.get("models") or []),
                "team_spend": raw_team.get("spend"),
                "team_max_budget": raw_team.get("max_budget"),
                "team_budget_duration": team_budget_duration,
                "team_member_budget_id": team_member_budget_id,
                "member_max_budget": member_budget.get("max_budget") if member_budget else None,
                "member_budget_duration": member_budget_duration,
            }
        )

    return rows


def _llm_external_user_rows(
    raw_users: list[dict],
    group_provisioning_users: list[ProvisioningUserRow],
    group_academies: list[AcademyConfigRow],
    default_config: AcademyConfigRow | None,
) -> list[LLMExternalUserRow]:
    provisioning_by_external_user = {
        provisioning_user["provisioning_llm"].external_user_id: provisioning_user
        for provisioning_user in group_provisioning_users
    }
    academy_config_by_team = {academy["team_id"]: academy for academy in group_academies}
    academy_config_by_slug = {
        academy["academy_slug"]: academy for academy in group_academies if academy["academy_slug"]
    }

    rows: list[LLMExternalUserRow] = []

    for raw_user in raw_users:
        user_id_raw = raw_user.get("user_id")
        user_id = str(user_id_raw).strip() if user_id_raw is not None else ""
        if not user_id:
            continue

        match = provisioning_by_external_user.get(user_id)
        key_count_raw = raw_user.get("key_count")
        key_count = int(key_count_raw) if key_count_raw is not None else None
        teams = list(raw_user.get("teams") or [])

        academy_config = None
        for team_id in teams:
            config = academy_config_by_team.get(team_id)
            if config:
                academy_config = config
                break

        if academy_config is None and match:
            for config in group_academies:
                if config["provisioning_academy_id"] == match["provisioning_academy"].id:
                    academy_config = config
                    break

        if academy_config is None:
            for slug in sorted(academy_config_by_slug.keys(), key=len, reverse=True):
                suffix = f"-{slug}"
                if user_id.endswith(suffix) and len(user_id) > len(suffix):
                    academy_config = academy_config_by_slug[slug]
                    break

        if academy_config is None:
            academy_config = default_config

        rows.append(
            {
                "user_id": user_id,
                "user_role": raw_user.get("user_role"),
                "teams": teams,
                "key_count": key_count,
                "provisioning_llm": match["provisioning_llm"] if match else None,
                "academy_config": academy_config,
            }
        )

    return rows


def collect_llm_data() -> LLMDataCollection:
    """
    Collect LiteLLM data as flat, enriched rows.

    Fetches once per ``llm_credentials`` (api_url + api_key), enriches vendor payloads with
    provisioning academy and ProvisioningLLM records, then appends to global lists.
    """
    keys: list[LLMKeyRow] = []
    teams: list[LLMTeamRow] = []
    academies: list[AcademyConfigRow] = []
    provisioning_users: list[ProvisioningUserRow] = []
    llm_external_users: list[LLMExternalUserRow] = []

    # Deduplicate LiteLLM connections (api_url + api_key) to avoid repeated fetches.
    # Each group holds the academies that share that connection.
    llm_credentials_groups: dict[LLMCredentials, list[ProvisioningAcademy]] = defaultdict(list)
    provisioning_academy_queryset = ProvisioningAcademy.objects.select_related("vendor", "academy").filter(
        vendor__isnull=False
    )
    for provisioning_academy in list(provisioning_academy_queryset):
        client = get_llm_client(provisioning_academy)
        if client is None or not hasattr(client, "list_keys"):
            continue

        vendor = provisioning_academy.vendor
        if vendor is None:
            continue

        api_url = getattr(vendor, "api_url", None)
        if not api_url:
            continue

        api_key = provisioning_academy.credentials_token
        if not api_key:
            continue

        llm_credentials = (str(api_url).rstrip("/"), str(api_key))
        llm_credentials_groups[llm_credentials].append(provisioning_academy)

    for provisioning_academies in llm_credentials_groups.values():
        client = get_llm_client(provisioning_academies[0])
        if client is None:
            continue

        try:
            raw_keys, raw_teams = _fetch_litellm_keys_and_teams(client)
            raw_users = _fetch_litellm_users(client)
        except LLMClientError as exc:
            logger.warning(
                "LiteLLM data collection failed for provisioning_academy_id=%s: %s",
                provisioning_academies[0].id,
                exc,
            )
            continue

        group_academies = _academy_config_rows(provisioning_academies, raw_teams)
        group_provisioning_users = _provisioning_user_rows(provisioning_academies)
        member_budgets_by_id = _fetch_member_budgets_by_id(client, raw_teams)
        default_config = next(
            iter(sorted(group_academies, key=lambda row: row["provisioning_academy_id"])),
            None,
        )

        academies.extend(group_academies)
        provisioning_users.extend(group_provisioning_users)
        keys.extend(
            _llm_key_rows(
                raw_keys,
                group_academies,
                group_provisioning_users,
                default_config,
            )
        )
        teams.extend(_llm_team_rows(raw_teams, group_academies, member_budgets_by_id))
        llm_external_users.extend(
            _llm_external_user_rows(raw_users, group_provisioning_users, group_academies, default_config)
        )

    return {
        "keys": keys,
        "teams": teams,
        "academies": academies,
        "provisioning_users": provisioning_users,
        "llm_external_users": llm_external_users,
    }
