from datetime import timedelta

from breathecode.payments.models import Consumable
from breathecode.provisioning.models import ProvisioningLLM
from breathecode.provisioning.tasks import deprovision_litellm_user_task
from breathecode.utils.decorators import issue, supervisor

LLM_BUDGET_SERVICE = "free_monthly_llm_budget"


@supervisor(delta=timedelta(hours=6))
def supervise_llm_users_without_budget():
    """
    Detect active LLM provisioning rows for users that no longer have LLM budget consumables.
    """
    user_ids = (
        ProvisioningLLM.objects.filter(status=ProvisioningLLM.STATUS_ACTIVE)
        .values_list("user_id", flat=True)
        .distinct()
    )

    for user_id in user_ids.iterator():
        has_budget = Consumable.list(user=user_id, service=LLM_BUDGET_SERVICE).exists()
        if has_budget:
            continue

        yield (
            f"User {user_id} has active LLM provisioning rows but no {LLM_BUDGET_SERVICE} consumable",
            "llm-user-missing-budget",
            {"user_id": user_id},
        )


@issue(supervise_llm_users_without_budget, delta=timedelta(minutes=15), attempts=3)
def llm_user_missing_budget(user_id: int):
    """
    Schedule Litellm deprovision for users that lost entitlement.
    """
    active_llm_exists = ProvisioningLLM.objects.filter(user_id=user_id, status=ProvisioningLLM.STATUS_ACTIVE).exists()
    if not active_llm_exists:
        return True

    has_budget = Consumable.list(user=user_id, service=LLM_BUDGET_SERVICE).exists()
    if has_budget:
        return True

    deprovision_litellm_user_task.delay(user_id=user_id)
    return None
