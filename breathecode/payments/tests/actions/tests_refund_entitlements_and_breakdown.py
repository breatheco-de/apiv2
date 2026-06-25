from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from breathecode.payments import actions


class DummyQuerySet:
    def __init__(self, slugs):
        self._slugs = slugs

    def values_list(self, field, flat=False):
        return self._slugs


def _mock_iou_lookup(mock_subscription, mock_financing, invoice_linked=None, user_linked=None):
    subscription_invoice_qs = MagicMock()
    subscription_invoice_qs.first.return_value = invoice_linked

    subscription_user_qs = MagicMock()
    subscription_user_qs.__iter__ = lambda self: iter(user_linked or [])

    financing_invoice_qs = MagicMock()
    financing_invoice_qs.first.return_value = None

    financing_user_qs = MagicMock()
    financing_user_qs.__iter__ = lambda self: iter([])

    def subscription_filter(**kwargs):
        if "invoices" in kwargs:
            return subscription_invoice_qs
        return subscription_user_qs

    def financing_filter(**kwargs):
        if "invoices" in kwargs:
            return financing_invoice_qs
        return financing_user_qs

    mock_subscription.objects.filter.side_effect = subscription_filter
    mock_financing.objects.filter.side_effect = financing_filter


def test_ensure_invoice_amount_breakdown_skips_when_line_items_exist():
    invoice = SimpleNamespace(id=1, bag_id=10, amount_breakdown={"plans": {"plan-a": {"amount": 50}}})
    with patch.object(actions, "calculate_invoice_breakdown") as mock_calc:
        actions.ensure_invoice_amount_breakdown(invoice, "en")
    mock_calc.assert_not_called()


def test_ensure_invoice_amount_breakdown_recalculates_and_saves():
    invoice = SimpleNamespace(id=2, bag_id=20, bag=SimpleNamespace(), amount_breakdown=None)
    saved = {}

    def _save(update_fields=None):
        saved["fields"] = update_fields

    invoice.save = _save
    breakdown = {"plans": {"plan-a": {"amount": 99.0, "currency": "USD"}}, "service-items": {}}

    with patch.object(actions, "calculate_invoice_breakdown", return_value=breakdown) as mock_calc:
        actions.ensure_invoice_amount_breakdown(invoice, "en")

    mock_calc.assert_called_once_with(invoice.bag, invoice, "en")
    assert invoice.amount_breakdown == breakdown
    assert saved["fields"] == ["amount_breakdown"]


def test_ensure_invoice_amount_breakdown_keeps_null_when_recalculation_fails():
    invoice = SimpleNamespace(id=3, bag_id=30, bag=SimpleNamespace(), amount_breakdown=None)

    with patch.object(actions, "calculate_invoice_breakdown", side_effect=Exception("pricing error")):
        actions.ensure_invoice_amount_breakdown(invoice, "en")

    assert invoice.amount_breakdown is None


@patch.object(actions.Subscription, "objects")
@patch.object(actions.PlanFinancing, "objects")
@patch.object(actions.Plan, "objects")
def test_apply_refund_entitlements_uses_bag_plans_when_no_breakdown(mock_plan, mock_financing, mock_subscription):
    bag = MagicMock()
    bag.plans.values_list.return_value = ["full-stack"]
    bag.plan_addons.values_list.return_value = []
    bag.service_items.select_related.return_value.values_list.return_value = []

    invoice = SimpleNamespace(
        id=99,
        bag=bag,
        user=SimpleNamespace(id=7),
        amount_breakdown=None,
    )

    plan = SimpleNamespace(slug="full-stack")
    subscription = MagicMock()
    mock_plan.objects.filter.return_value = [plan]
    _mock_iou_lookup(mock_subscription, mock_financing, user_linked=[subscription])

    actions._apply_refund_entitlements(invoice, {"full-stack": 25.0})

    subscription.save.assert_called_once()
    assert subscription.status == actions.Subscription.Status.EXPIRED


@patch.object(actions.Subscription, "objects")
@patch.object(actions.PlanFinancing, "objects")
@patch.object(actions.Plan, "objects")
def test_apply_refund_entitlements_expires_subscription_regardless_of_prior_status(
    mock_plan, mock_financing, mock_subscription
):
    bag = MagicMock()
    bag.plans.values_list.return_value = []
    bag.plan_addons.values_list.return_value = []
    bag.service_items.select_related.return_value.values_list.return_value = []

    invoice = SimpleNamespace(
        id=100,
        bag=bag,
        user=SimpleNamespace(id=8),
        amount_breakdown={"plans": {"premium-plan": {"amount": 100}}, "service-items": {}},
    )

    plan = SimpleNamespace(slug="premium-plan")
    subscription = MagicMock(status=actions.Subscription.Status.CANCELLED)
    mock_plan.objects.filter.return_value = [plan]
    _mock_iou_lookup(mock_subscription, mock_financing, invoice_linked=subscription)

    actions._apply_refund_entitlements(invoice, {"premium-plan": 100.0})

    assert subscription.status == actions.Subscription.Status.EXPIRED
    assert "refund of invoice 100" in subscription.status_message


@patch.object(actions.Subscription, "objects")
@patch.object(actions.PlanFinancing, "objects")
@patch.object(actions.Plan, "objects")
def test_apply_refund_entitlements_cancel_at_period_end_sets_cancelled(
    mock_plan, mock_financing, mock_subscription
):
    bag = MagicMock()
    bag.service_items.select_related.return_value.values_list.return_value = []

    invoice = SimpleNamespace(
        id=101,
        bag=bag,
        user=SimpleNamespace(id=9),
        amount_breakdown={"plans": {"premium-plan": {"amount": 100}}, "service-items": {}},
    )

    plan = SimpleNamespace(slug="premium-plan")
    subscription = MagicMock(status=actions.Subscription.Status.ACTIVE)
    mock_plan.objects.filter.return_value = [plan]
    _mock_iou_lookup(mock_subscription, mock_financing, invoice_linked=subscription)

    actions._apply_refund_entitlements(
        invoice,
        {"premium-plan": 50.0},
        plan_entitlement_action=actions.PLAN_ENTITLEMENT_ACTION_CANCEL_AT_PERIOD_END,
    )

    assert subscription.status == actions.Subscription.Status.CANCELLED
    assert "refund of invoice 101" in subscription.status_message


@patch.object(actions.Subscription, "objects")
@patch.object(actions.PlanFinancing, "objects")
@patch.object(actions.Plan, "objects")
def test_apply_refund_entitlements_cancel_at_period_end_for_plan_financing(
    mock_plan, mock_financing, mock_subscription
):
    bag = MagicMock()
    bag.service_items.select_related.return_value.values_list.return_value = []

    invoice = SimpleNamespace(
        id=102,
        bag=bag,
        user=SimpleNamespace(id=10),
        amount_breakdown={"plans": {"financing-plan": {"amount": 100}}, "service-items": {}},
    )

    plan = SimpleNamespace(slug="financing-plan")
    financing = MagicMock(status=actions.PlanFinancing.Status.ACTIVE)

    subscription_invoice_qs = MagicMock()
    subscription_invoice_qs.first.return_value = None
    subscription_user_qs = MagicMock()
    subscription_user_qs.__iter__ = lambda self: iter([])

    financing_invoice_qs = MagicMock()
    financing_invoice_qs.first.return_value = financing
    financing_user_qs = MagicMock()
    financing_user_qs.__iter__ = lambda self: iter([])

    mock_subscription.objects.filter.side_effect = lambda **kwargs: (
        subscription_invoice_qs if "invoices" in kwargs else subscription_user_qs
    )
    mock_financing.objects.filter.side_effect = lambda **kwargs: (
        financing_invoice_qs if "invoices" in kwargs else financing_user_qs
    )
    mock_plan.objects.filter.return_value = [plan]

    actions._apply_refund_entitlements(
        invoice,
        {"financing-plan": 25.0},
        plan_entitlement_action=actions.PLAN_ENTITLEMENT_ACTION_CANCEL_AT_PERIOD_END,
    )

    assert financing.status == actions.PlanFinancing.Status.CANCELLED
    assert "refund of invoice 102" in financing.status_message


@patch.object(actions.Subscription, "objects")
@patch.object(actions.PlanFinancing, "objects")
@patch.object(actions.Plan, "objects")
def test_apply_refund_entitlements_keep_does_not_change_subscription(
    mock_plan, mock_financing, mock_subscription
):
    bag = MagicMock()
    bag.service_items.select_related.return_value.values_list.return_value = []

    invoice = SimpleNamespace(
        id=103,
        bag=bag,
        user=SimpleNamespace(id=11),
        amount_breakdown={"plans": {"premium-plan": {"amount": 100}}, "service-items": {}},
    )

    plan = SimpleNamespace(slug="premium-plan")
    subscription = MagicMock(status=actions.Subscription.Status.ACTIVE)
    mock_plan.objects.filter.return_value = [plan]
    _mock_iou_lookup(mock_subscription, mock_financing, invoice_linked=subscription)

    actions._apply_refund_entitlements(
        invoice,
        {"premium-plan": 50.0},
        plan_entitlement_action=actions.PLAN_ENTITLEMENT_ACTION_KEEP,
    )

    subscription.save.assert_not_called()
    assert subscription.status == actions.Subscription.Status.ACTIVE


@patch.object(actions.Subscription, "objects")
@patch.object(actions.PlanFinancing, "objects")
@patch.object(actions.Plan, "objects")
def test_apply_refund_entitlements_prefers_invoice_linked_iou_over_user_fallback(
    mock_plan, mock_financing, mock_subscription
):
    bag = MagicMock()
    bag.service_items.select_related.return_value.values_list.return_value = []

    invoice = SimpleNamespace(
        id=104,
        bag=bag,
        user=SimpleNamespace(id=12),
        amount_breakdown={"plans": {"premium-plan": {"amount": 100}}, "service-items": {}},
    )

    plan = SimpleNamespace(slug="premium-plan")
    linked_subscription = MagicMock(status=actions.Subscription.Status.ACTIVE)
    other_subscription = MagicMock(status=actions.Subscription.Status.ACTIVE)

    mock_plan.objects.filter.return_value = [plan]
    _mock_iou_lookup(
        mock_subscription,
        mock_financing,
        invoice_linked=linked_subscription,
        user_linked=[other_subscription],
    )

    actions._apply_refund_entitlements(invoice, {"premium-plan": 50.0})

    linked_subscription.save.assert_called_once()
    other_subscription.save.assert_not_called()
    assert linked_subscription.status == actions.Subscription.Status.EXPIRED


def test_invoice_breakdown_has_line_items():
    assert actions._invoice_breakdown_has_line_items(None) is False
    assert actions._invoice_breakdown_has_line_items({}) is False
    assert actions._invoice_breakdown_has_line_items({"plans": {}, "service-items": {}}) is False
    assert actions._invoice_breakdown_has_line_items({"plans": {"x": {}}, "service-items": {}}) is True
