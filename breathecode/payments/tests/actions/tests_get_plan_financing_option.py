"""Tests for get_plan_financing_option and ambiguous financing option handling."""

from capyc.rest_framework.exceptions import ValidationException

from breathecode.payments.actions import (
    get_plan_financing_option,
    validate_student_invite_plan_access_config,
)
from breathecode.payments.models import FinancingOption

from ..mixins.payments_test_case import PaymentsTestCase


class GetPlanFinancingOptionTestSuite(PaymentsTestCase):
    def test_raises_when_multiple_options_share_installment_count(self):
        model = self.bc.database.create(
            currency=1,
            financing_option=(
                2,
                [
                    {"how_many_months": 5, "monthly_price": 100},
                    {"how_many_months": 5, "monthly_price": 200},
                ],
            ),
            plan={"status": "ACTIVE"},
        )
        fo_a, fo_b = FinancingOption.objects.order_by("id")
        model.plan.financing_options.set([fo_a, fo_b])

        with self.assertRaises(ValidationException) as ctx:
            get_plan_financing_option(model.plan, 5, lang="en")

        self.assertEqual(ctx.exception.slug, "ambiguous-financing-option")

    def test_resolves_by_financing_option_id(self):
        model = self.bc.database.create(
            currency=1,
            financing_option=(
                2,
                [
                    {"how_many_months": 5, "monthly_price": 100},
                    {"how_many_months": 5, "monthly_price": 200},
                ],
            ),
            plan={"status": "ACTIVE"},
        )
        fo_a, fo_b = FinancingOption.objects.order_by("id")
        model.plan.financing_options.set([fo_a, fo_b])

        option = get_plan_financing_option(model.plan, 5, financing_option_id=fo_b.id, lang="en")

        self.assertEqual(option.id, fo_b.id)
        self.assertEqual(option.monthly_price, 200)

    def test_validate_student_invite_persists_financing_option_id(self):
        model = self.bc.database.create(
            currency=1,
            financing_option=(
                2,
                [
                    {"how_many_months": 5, "monthly_price": 100},
                    {"how_many_months": 5, "monthly_price": 200},
                ],
            ),
            plan={"status": "ACTIVE"},
        )
        fo_a, fo_b = FinancingOption.objects.order_by("id")
        model.plan.financing_options.set([fo_a, fo_b])

        payload = validate_student_invite_plan_access_config(
            plans=[model.plan],
            how_many_installments=5,
            initial_payment_amount=None,
            initial_payment_notes=None,
            grace_period_duration=2,
            grace_period_duration_unit="MONTH",
            financing_option_id=fo_b.id,
            lang="en",
        )

        self.assertEqual(payload["financing_option_id"], fo_b.id)
        self.assertEqual(payload["how_many_installments"], 5)
        self.assertEqual(payload["grace_period_duration"], 2)
