from datetime import timedelta
from unittest.mock import MagicMock, patch

import capyc.pytest as capy
import pytest
from django.utils import timezone
from task_manager.core.exceptions import AbortTask

from breathecode.payments.tasks import notify_plan_financing_renewal


def _run_notify(plan_financing_id: int):
    fn = notify_plan_financing_renewal
    while hasattr(fn, "__wrapped__"):
        fn = fn.__wrapped__
    return fn(MagicMock(), plan_financing_id)


@pytest.mark.usefixtures("db")
@patch("breathecode.payments.tasks.notify_actions.send_email_message")
def test_skips_when_created_by_admin(mock_send, database: capy.Database):
    now = timezone.now()
    model = database.create(
        academy=1,
        user=1,
        plan={"is_renewable": False, "time_of_life": 12, "time_of_life_unit": "MONTH"},
        plan_financing={
            "status": "ACTIVE",
            "created_by_admin": True,
            "next_payment_at": now + timedelta(days=1),
            "valid_until": now + timedelta(days=180),
            "plan_expires_at": now + timedelta(days=365),
            "how_many_installments": 12,
            "installments_paid": 1,
            "monthly_price": 200,
        },
    )
    model.plan_financing.plans.add(model.plan)

    with pytest.raises(AbortTask, match="admin-managed"):
        _run_notify(model.plan_financing.id)

    mock_send.assert_not_called()
