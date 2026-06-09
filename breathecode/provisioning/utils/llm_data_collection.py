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


class LLMKeyRow(TypedDict):
    token_id: str | None
    key_alias: str | None
    user_id: str | None
    team_id: str | None
    expires: str | None
    provisioning_academy: ProvisioningAcademy | None
    provisioning_llm: ProvisioningLLM | None


class LLMTeamRow(TypedDict):
    team_id: str
    member_user_ids: frozenset[str]
    provisioning_academy: ProvisioningAcademy | None


class AcademyConfigRow(TypedDict):
    provisioning_academy: ProvisioningAcademy
    team_id: str


class ProvisioningUserRow(TypedDict):
    provisioning_academy: ProvisioningAcademy
    provisioning_llm: ProvisioningLLM


class LLMExternalUserRow(TypedDict):
    user_id: str
    user_role: str | None
    teams: list[str]
    key_count: int | None
    provisioning_academy: ProvisioningAcademy | None
    provisioning_llm: ProvisioningLLM | None


class LLMDataCollection(TypedDict):
    keys: list[LLMKeyRow]
    teams: list[LLMTeamRow]
    academies: list[AcademyConfigRow]
    provisioning_users: list[ProvisioningUserRow]
    llm_external_users: list[LLMExternalUserRow]


def _academy_config_rows(provisioning_academies: list[ProvisioningAcademy]) -> list[AcademyConfigRow]:
    rows: list[AcademyConfigRow] = []
    for provisioning_academy in provisioning_academies:
        vendor_settings = provisioning_academy.vendor_settings or {}
        team_id = str(vendor_settings.get("team_id") or "").strip()
        if not team_id:
            continue

        rows.append(
            {
                "provisioning_academy": provisioning_academy,
                "team_id": team_id,
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
) -> list[LLMKeyRow]:
    academy_by_team = {academy["team_id"]: academy["provisioning_academy"] for academy in group_academies}
    provisioning_by_external_user = {
        provisioning_user["provisioning_llm"].external_user_id: provisioning_user
        for provisioning_user in group_provisioning_users
    }
    rows: list[LLMKeyRow] = []

    for raw_key in raw_keys:
        team_id_raw = raw_key.get("team_id")
        team_id = str(team_id_raw).strip() if team_id_raw is not None and str(team_id_raw).strip() else None

        provisioning_academy = academy_by_team.get(team_id) if team_id else None

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
                "provisioning_academy": provisioning_academy,
                "provisioning_llm": provisioning_llm,
            }
        )

    return rows


def _llm_team_rows(raw_teams: list[dict], group_academies: list[AcademyConfigRow]) -> list[LLMTeamRow]:
    academy_by_team = {academy["team_id"]: academy["provisioning_academy"] for academy in group_academies}
    rows: list[LLMTeamRow] = []

    for raw_team in raw_teams:
        team_id_raw = raw_team.get("team_id")
        if team_id_raw is None or not str(team_id_raw).strip():
            continue

        team_id = str(team_id_raw).strip()
        provisioning_academy = academy_by_team.get(team_id)

        members: set[str] = set()
        for member in raw_team.get("members_with_roles") or []:
            user_id = member.get("user_id") if isinstance(member, dict) else None
            if user_id:
                members.add(str(user_id))

        rows.append(
            {
                "team_id": team_id,
                "member_user_ids": frozenset(members),
                "provisioning_academy": provisioning_academy,
            }
        )

    return rows


def _llm_external_user_rows(
    raw_users: list[dict],
    group_provisioning_users: list[ProvisioningUserRow],
) -> list[LLMExternalUserRow]:
    provisioning_by_external_user = {
        provisioning_user["provisioning_llm"].external_user_id: provisioning_user
        for provisioning_user in group_provisioning_users
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

        rows.append(
            {
                "user_id": user_id,
                "user_role": raw_user.get("user_role"),
                "teams": list(raw_user.get("teams") or []),
                "key_count": key_count,
                "provisioning_academy": match["provisioning_academy"] if match else None,
                "provisioning_llm": match["provisioning_llm"] if match else None,
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

        group_academies = _academy_config_rows(provisioning_academies)
        group_provisioning_users = _provisioning_user_rows(provisioning_academies)

        academies.extend(group_academies)
        provisioning_users.extend(group_provisioning_users)
        keys.extend(_llm_key_rows(raw_keys, group_academies, group_provisioning_users))
        teams.extend(_llm_team_rows(raw_teams, group_academies))
        llm_external_users.extend(_llm_external_user_rows(raw_users, group_provisioning_users))

    return {
        "keys": keys,
        "teams": teams,
        "academies": academies,
        "provisioning_users": provisioning_users,
        "llm_external_users": llm_external_users,
    }
