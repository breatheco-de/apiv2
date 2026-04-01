from datetime import timedelta

from breathecode.payments.models import Consumable
from breathecode.provisioning.models import ProvisioningLLM
from breathecode.provisioning.tasks import deprovision_litellm_user_task
from breathecode.utils.decorators import issue, supervisor

LLM_BUDGET_SERVICE = "free-monthly-llm-budget"


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
