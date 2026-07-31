from decimal import Decimal
from unittest.mock import MagicMock, patch

from breathecode.payments import actions
from breathecode.payments.models import Consumable, Service


def _llm_consumable(*, pk=2, academy_id=1, user=None):
    consumable = MagicMock()
    consumable.pk = pk
    consumable.user = user or MagicMock(id=10)
    consumable.subscription_id = 1
    consumable.subscription.academy_id = academy_id
    consumable.plan_financing_id = None
    consumable.subscription_seat_id = None
    consumable.plan_financing_seat_id = None
    consumable.service_item.service.consumer = Service.Consumer.LLM_BUDGET
    return consumable


@patch("breathecode.payments.actions.sync_llm_member_budget_to_llm_provider")
@patch("breathecode.payments.actions.consume_service")
@patch("breathecode.payments.actions.Consumable.list")
@patch("breathecode.provisioning.actions.resolve_llm_provisioning_context")
@patch("breathecode.payments.actions.Consumable.objects")
def test_align_fefo_debits_older_consumables_before_sync(
    mock_objects,
    mock_resolve_ctx,
    mock_consumable_list,
    mock_consume_service,
    mock_sync,
):
    current = _llm_consumable()
    mock_objects.filter.return_value.select_related.return_value.first.return_value = current

    provisioning_llm = MagicMock()
    provisioning_llm.external_user_id = "user-academy"
    provisioning_llm.last_known_spend = Decimal("0")
    provisioning_llm.litellm_team_id = ""

    provisioning_academy = MagicMock()
    provisioning_academy.vendor_settings = {"team_id": "team-1"}

    client = MagicMock()
    client.get_team_info.return_value = {
        "team_memberships": [{"user_id": "user-academy", "spend": 2.5}],
    }
    mock_resolve_ctx.return_value = (provisioning_llm, provisioning_academy, client)

    older = MagicMock()
    older.how_many = 500
    mock_fefo_qs = MagicMock()
    mock_fefo_qs.filter.return_value = mock_fefo_qs
    mock_fefo_qs.exclude.return_value = mock_fefo_qs
    mock_fefo_qs.order_by.return_value = [older]
    mock_consumable_list.return_value = mock_fefo_qs

    actions.align_llm_member_budget_with_consumables(MagicMock(pk=2))

    mock_consume_service.send_robust.assert_called_once_with(
        sender=Consumable,
        instance=older,
        how_many=250,
    )
    mock_sync.assert_called_once_with(
        provisioning_llm,
        provisioning_academy,
        client,
        team_data=client.get_team_info.return_value,
    )
    assert provisioning_llm.last_known_spend == Decimal("2.5")


@patch("breathecode.payments.actions.sync_llm_member_budget_to_llm_provider")
@patch("breathecode.payments.actions.consume_service")
@patch("breathecode.payments.actions.Consumable.list")
@patch("breathecode.provisioning.actions.resolve_llm_provisioning_context")
@patch("breathecode.payments.actions.Consumable.objects")
def test_align_skips_fefo_when_spend_delta_is_zero(
    mock_objects,
    mock_resolve_ctx,
    mock_consumable_list,
    mock_consume_service,
    mock_sync,
):
    current = _llm_consumable()
    mock_objects.filter.return_value.select_related.return_value.first.return_value = current

    provisioning_llm = MagicMock()
    provisioning_llm.external_user_id = "user-academy"
    provisioning_llm.last_known_spend = Decimal("1")
    provisioning_llm.litellm_team_id = ""

    provisioning_academy = MagicMock()
    provisioning_academy.vendor_settings = {"team_id": "team-1"}

    client = MagicMock()
    client.get_team_info.return_value = {
        "team_memberships": [{"user_id": "user-academy", "spend": 1}],
    }
    mock_resolve_ctx.return_value = (provisioning_llm, provisioning_academy, client)

    actions.align_llm_member_budget_with_consumables(MagicMock(pk=2))

    mock_consumable_list.assert_not_called()
    mock_consume_service.send_robust.assert_not_called()
    mock_sync.assert_called_once()


@patch("breathecode.payments.actions.sync_llm_member_budget_to_llm_provider")
@patch("breathecode.provisioning.actions.resolve_llm_provisioning_context")
@patch("breathecode.payments.actions.Consumable.objects")
def test_align_noop_when_no_active_provisioning_llm(mock_objects, mock_resolve_ctx, mock_sync):
    current = _llm_consumable()
    mock_objects.filter.return_value.select_related.return_value.first.return_value = current
    mock_resolve_ctx.return_value = None

    actions.align_llm_member_budget_with_consumables(MagicMock(pk=2))

    mock_sync.assert_not_called()


@patch("breathecode.payments.actions.sync_llm_member_budget_to_llm_provider")
@patch("breathecode.payments.actions.Consumable.objects")
def test_align_noop_for_non_llm_budget_consumer(mock_objects, mock_sync):
    current = _llm_consumable()
    current.service_item.service.consumer = Service.Consumer.VPS_SERVER
    mock_objects.filter.return_value.select_related.return_value.first.return_value = current

    actions.align_llm_member_budget_with_consumables(MagicMock(pk=2))

    mock_sync.assert_not_called()
