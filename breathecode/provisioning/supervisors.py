from datetime import timedelta

from breathecode.payments.models import Consumable
from breathecode.provisioning.models import ProvisioningLLM
from breathecode.provisioning.tasks import deprovision_litellm_user_task
from breathecode.provisioning.utils.llm_data_collection import LLMDataCollection, collect_llm_data
from breathecode.utils.decorators import issue, supervisor

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
        slug = getattr(academy["provisioning_academy"].academy, "slug", None)
        if slug:
            slugs.append(str(slug))
    return slugs


def llm_key_missing_team_id(snapshot: LLMDataCollection):
    for key in snapshot["keys"]:
        if key["team_id"]:
            continue

        yield (
            f"LiteLLM key {key['key_alias'] or key['token_id']} has no team_id",
            "llm-key-missing-team-id",
            {"token_id": key["token_id"]},
        )


def llm_key_missing_expires(snapshot: LLMDataCollection):
    for key in snapshot["keys"]:
        if key["expires"]:
            continue

        yield (
            f"LiteLLM key {key['key_alias'] or key['token_id']} has no expires",
            "llm-key-missing-expires",
            {"token_id": key["token_id"]},
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

        yield (
            f"LiteLLM user {user_id} has {key_count} keys (>= 7)",
            "llm-user-too-many-keys",
            {"user_id": user_id, "key_count": key_count},
        )


def llm_key_missing_user_id(snapshot: LLMDataCollection):
    for key in snapshot["keys"]:
        if key["user_id"]:
            continue

        yield (
            f"LiteLLM key {key['key_alias'] or key['token_id']} has no user_id",
            "llm-key-missing-user-id",
            {"token_id": key["token_id"]},
        )


def llm_external_user_without_provisioning(snapshot: LLMDataCollection):
    for user in snapshot["llm_external_users"]:
        if user["user_id"] in LLM_EXCLUDED_USER_IDS:
            continue
        if user["provisioning_llm"] is not None:
            continue

        yield (
            f"LiteLLM user {user['user_id']} has no active ProvisioningLLM record",
            "llm-external-user-without-provisioning",
            {"user_id": user["user_id"], "user_role": user["user_role"]},
        )


def llm_external_user_invalid_convention(snapshot: LLMDataCollection):
    academy_slugs = _known_academy_slugs(snapshot)

    for user in snapshot["llm_external_users"]:
        user_id = user["user_id"]
        if user_id in LLM_EXCLUDED_USER_IDS:
            continue
        if _academy_slug_for_user_id(user_id, academy_slugs):
            continue

        yield (
            f"LiteLLM user {user_id} does not follow the username-academy_slug convention",
            "llm-external-user-invalid-convention",
            {"user_id": user_id, "user_role": user["user_role"]},
        )


def llm_user_missing_team(snapshot: LLMDataCollection):
    academy_by_slug = {}
    for academy in snapshot["academies"]:
        slug = getattr(academy["provisioning_academy"].academy, "slug", None)
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

        provisioning_academy = academy["provisioning_academy"]
        yield (
            f"LiteLLM user {user_id} is not a member of team {team_id}",
            "llm-user-missing-team",
            {
                "user_id": user_id,
                "team_id": team_id,
                "provisioning_academy_id": provisioning_academy.id,
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
    Detect LiteLLM API key anomalies across provisioning academies.

    Performs one paginated ``/key/list`` fetch per ``llm_credentials`` per run, then runs
    compliance checks from the collected snapshot.
    """
    snapshot = collect_llm_data()

    yield from llm_key_missing_team_id(snapshot)
    yield from llm_key_missing_expires(snapshot)
    yield from llm_user_too_many_keys(snapshot)
    yield from llm_key_missing_user_id(snapshot)
    yield from llm_external_user_without_provisioning(snapshot)
    yield from llm_external_user_invalid_convention(snapshot)
    yield from llm_user_missing_team(snapshot)
