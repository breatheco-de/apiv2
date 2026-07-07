from datetime import timedelta

from django.db.models import Q

from breathecode.payments.models import Consumable
from breathecode.provisioning.models import ProvisioningLLM
from breathecode.provisioning.tasks import deprovision_litellm_user_task
from breathecode.utils.decorators import issue, supervisor


@supervisor(delta=timedelta(hours=6))
def supervise_llm_users_without_budget():
    """
    Detect active LLM provisioning rows for users that no longer have a vigente llm-budget
    consumable in the academy (including ``how_many=0`` within a valid cycle).
    """
    pairs = (
        ProvisioningLLM.objects.filter(status=ProvisioningLLM.STATUS_ACTIVE)
        .values_list("user_id", "academy_id")
        .distinct()
    )

    for user_id, academy_id in pairs.iterator():
        if (
            Consumable.list(user=user_id, service="llm-budget", include_zero_balance=True)
            .filter(
                Q(subscription__academy_id=academy_id)
                | Q(plan_financing__academy_id=academy_id)
                | Q(standalone_invoice__bag__academy_id=academy_id)
                | Q(subscription_seat__billing_team__subscription__academy_id=academy_id)
                | Q(plan_financing_seat__team__financing__academy_id=academy_id)
            )
            .exists()
        ):
            continue

        yield (
            f"User {user_id} has active LLM provisioning rows in academy {academy_id} "
            "but no vigente llm-budget consumable",
            "llm-user-missing-budget",
            {"user_id": user_id, "academy_id": academy_id},
        )


@issue(supervise_llm_users_without_budget, delta=timedelta(minutes=15), attempts=3)
def llm_user_missing_budget(user_id: int, academy_id: int):
    """
    Schedule Litellm deprovision for users that lost vigente llm-budget entitlement.
    """
    active_llm_exists = ProvisioningLLM.objects.filter(
        user_id=user_id, academy_id=academy_id, status=ProvisioningLLM.STATUS_ACTIVE
    ).exists()
    if not active_llm_exists:
        return True

    if (
        Consumable.list(user=user_id, service="llm-budget", include_zero_balance=True)
        .filter(
            Q(subscription__academy_id=academy_id)
            | Q(plan_financing__academy_id=academy_id)
            | Q(standalone_invoice__bag__academy_id=academy_id)
            | Q(subscription_seat__billing_team__subscription__academy_id=academy_id)
            | Q(plan_financing_seat__team__financing__academy_id=academy_id)
        )
        .exists()
    ):
        return True

    deprovision_litellm_user_task.delay(user_id=user_id, academy_id=academy_id)
    return None
