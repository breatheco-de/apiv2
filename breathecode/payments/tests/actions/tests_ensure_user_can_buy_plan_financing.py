"""Tests for ensure_user_can_buy_plan_financing."""

from capyc.rest_framework.exceptions import ValidationException
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from task_manager.core.exceptions import AbortTask

from breathecode.payments.actions import ensure_user_can_buy_plan_financing
from breathecode.payments.models import PlanFinancing

from ..mixins import PaymentsTestCase


class EnsureUserCanBuyPlanFinancingTestSuite(PaymentsTestCase):

    def _setup(self, *, financing_status="ACTIVE"):
        utc_now = timezone.now()
        model = self.bc.database.create(
            user=1,
            academy=1,
            currency=1,
            plan={"is_renewable": False, "time_of_life": 1, "time_of_life_unit": "MONTH", "status": "ACTIVE"},
            plan_financing={
                "status": financing_status,
                "monthly_price": 100,
                "how_many_installments": 3,
                "valid_until": utc_now + relativedelta(months=3),
                "next_payment_at": utc_now + relativedelta(months=1),
                "plan_expires_at": utc_now + relativedelta(months=12),
            },
        )
        model.plan_financing.plans.add(model.plan)
        if model.plan_financing.status != financing_status:
            PlanFinancing.objects.filter(pk=model.plan_financing.pk).update(status=financing_status)
            model.plan_financing.refresh_from_db()
        return model

    def test_active_blocks(self):
        model = self._setup(financing_status="ACTIVE")
        with self.assertRaises(ValidationException) as cm:
            ensure_user_can_buy_plan_financing(model.user, model.plan, lang="en")
        self.assertEqual(getattr(cm.exception, "slug", None), "plan-already-financed")

    def test_fully_paid_blocks(self):
        model = self._setup(financing_status="FULLY_PAID")
        with self.assertRaises(ValidationException):
            ensure_user_can_buy_plan_financing(model.user, model.plan, lang="en")

    def test_cancelled_allows(self):
        model = self._setup(financing_status="CANCELLED")
        ensure_user_can_buy_plan_financing(model.user, model.plan, lang="en")

    def test_expired_allows(self):
        model = self._setup(financing_status="EXPIRED")
        ensure_user_can_buy_plan_financing(model.user, model.plan, lang="en")

    def test_payment_issue_allows(self):
        model = self._setup(financing_status="PAYMENT_ISSUE")
        ensure_user_can_buy_plan_financing(model.user, model.plan, lang="en")

    def test_error_allows(self):
        model = self._setup(financing_status="ERROR")
        ensure_user_can_buy_plan_financing(model.user, model.plan, lang="en")

    def test_task_mode_raises_abort(self):
        model = self._setup(financing_status="ACTIVE")
        with self.assertRaises(AbortTask):
            ensure_user_can_buy_plan_financing(model.user, model.plan, lang=None)

    def test_no_existing_financing_allows(self):
        model = self.bc.database.create(
            user=1,
            academy=1,
            currency=1,
            plan={"is_renewable": False, "time_of_life": 1, "time_of_life_unit": "MONTH", "status": "ACTIVE"},
        )
        ensure_user_can_buy_plan_financing(model.user, model.plan, lang="en")
