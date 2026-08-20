"""Tests for sync_cohort_user_finantial_status_from_plan_financing."""

from unittest.mock import patch

from dateutil.relativedelta import relativedelta
from django.utils import timezone

from breathecode.admissions.models import CohortUser
from breathecode.payments.actions import sync_cohort_user_finantial_status_from_plan_financing
from breathecode.payments.models import PlanFinancing, Subscription

from ..mixins import PaymentsTestCase


class SyncCohortUserFinantialStatusTestSuite(PaymentsTestCase):
    """Map PlanFinancing.status onto CohortUser.finantial_status."""

    def _setup(self, *, finantial_status="UP_TO_DATE", financing_status="ACTIVE", with_extra_cohort=False):
        utc_now = timezone.now()
        cohort_count = 2 if with_extra_cohort else 1
        model = self.bc.database.create(
            user=1,
            academy=1,
            currency=1,
            cohort=(cohort_count, {"available_as_saas": True}),
            cohort_set=1,
            cohort_set_cohort=1,
            plan={"is_renewable": False, "time_of_life": 1, "time_of_life_unit": "MONTH", "status": "ACTIVE"},
            plan_financing={
                "status": financing_status,
                "monthly_price": 100,
                "how_many_installments": 3,
                "valid_until": utc_now + relativedelta(months=3),
                "next_payment_at": utc_now + relativedelta(months=1),
                "plan_expires_at": utc_now + relativedelta(months=12),
                "selected_cohort_set_id": 1,
            },
            cohort_user={"finantial_status": finantial_status, "role": "STUDENT"},
        )

        plan = model.plan
        plan.cohort_set = model.cohort_set
        plan.save(update_fields=["cohort_set"])

        financing = model.plan_financing
        financing.plans.add(plan)

        if with_extra_cohort:
            # Second cohort is NOT in the cohort set; CU on it must stay untouched.
            extra = model.cohort[1] if isinstance(model.cohort, list) else model.cohort
            covered = model.cohort[0] if isinstance(model.cohort, list) else model.cohort
            # cohort_user was created for first cohort by default; ensure link
            cu = CohortUser.objects.filter(user=model.user).first()
            if cu and cu.cohort_id != covered.id:
                cu.cohort = covered
                cu.save(update_fields=["cohort"])
            CohortUser.objects.create(
                user=model.user,
                cohort=extra,
                role="STUDENT",
                finantial_status=finantial_status,
            )

        return model

    def _covered_cohort_user(self, model):
        cohort = model.cohort[0] if isinstance(model.cohort, list) else model.cohort
        return CohortUser.objects.get(user=model.user, cohort=cohort)

    def test_payment_issue_sets_late(self):
        model = self._setup(financing_status="PAYMENT_ISSUE", finantial_status="UP_TO_DATE")
        updated = sync_cohort_user_finantial_status_from_plan_financing(model.plan_financing)
        self.assertEqual(updated, 1)
        self.assertEqual(self._covered_cohort_user(model).finantial_status, "LATE")

    def test_cancelled_sets_late(self):
        model = self._setup(financing_status="CANCELLED", finantial_status="UP_TO_DATE")
        updated = sync_cohort_user_finantial_status_from_plan_financing(model.plan_financing)
        self.assertEqual(updated, 1)
        self.assertEqual(self._covered_cohort_user(model).finantial_status, "LATE")

    def test_expired_sets_late(self):
        model = self._setup(financing_status="EXPIRED", finantial_status="UP_TO_DATE")
        updated = sync_cohort_user_finantial_status_from_plan_financing(model.plan_financing)
        self.assertEqual(updated, 1)
        self.assertEqual(self._covered_cohort_user(model).finantial_status, "LATE")

    def test_active_sets_up_to_date(self):
        model = self._setup(financing_status="ACTIVE", finantial_status="LATE")
        updated = sync_cohort_user_finantial_status_from_plan_financing(model.plan_financing)
        self.assertEqual(updated, 1)
        self.assertEqual(self._covered_cohort_user(model).finantial_status, "UP_TO_DATE")

    def test_fully_paid_financing_sets_fully_paid(self):
        model = self._setup(financing_status="FULLY_PAID", finantial_status="UP_TO_DATE")
        updated = sync_cohort_user_finantial_status_from_plan_financing(model.plan_financing)
        self.assertEqual(updated, 1)
        self.assertEqual(self._covered_cohort_user(model).finantial_status, "FULLY_PAID")

    def test_payment_issue_overwrites_manual_fully_paid(self):
        model = self._setup(financing_status="PAYMENT_ISSUE", finantial_status="FULLY_PAID")
        updated = sync_cohort_user_finantial_status_from_plan_financing(model.plan_financing)
        self.assertEqual(updated, 1)
        self.assertEqual(self._covered_cohort_user(model).finantial_status, "LATE")

    def test_expired_overwrites_manual_fully_paid(self):
        model = self._setup(financing_status="EXPIRED", finantial_status="FULLY_PAID")
        updated = sync_cohort_user_finantial_status_from_plan_financing(model.plan_financing)
        self.assertEqual(updated, 1)
        self.assertEqual(self._covered_cohort_user(model).finantial_status, "LATE")

    def test_active_overwrites_manual_fully_paid(self):
        model = self._setup(financing_status="ACTIVE", finantial_status="FULLY_PAID")
        updated = sync_cohort_user_finantial_status_from_plan_financing(model.plan_financing)
        self.assertEqual(updated, 1)
        self.assertEqual(self._covered_cohort_user(model).finantial_status, "UP_TO_DATE")

    def test_subscription_active_covering_cohort_skips_late(self):
        model = self._setup(financing_status="PAYMENT_ISSUE", finantial_status="UP_TO_DATE")
        utc_now = timezone.now()
        sub = Subscription.objects.create(
            user=model.user,
            academy=model.academy,
            status=Subscription.Status.ACTIVE,
            paid_at=utc_now,
            next_payment_at=utc_now + relativedelta(months=1),
            selected_cohort_set=model.cohort_set,
        )
        sub.plans.add(model.plan)

        updated = sync_cohort_user_finantial_status_from_plan_financing(model.plan_financing)
        self.assertEqual(updated, 0)
        self.assertEqual(self._covered_cohort_user(model).finantial_status, "UP_TO_DATE")

    def test_other_fully_paid_financing_covering_cohort_skips_late(self):
        model = self._setup(financing_status="PAYMENT_ISSUE", finantial_status="UP_TO_DATE")
        utc_now = timezone.now()
        other = PlanFinancing.objects.create(
            user=model.user,
            academy=model.academy,
            status=PlanFinancing.Status.FULLY_PAID,
            monthly_price=50,
            how_many_installments=1,
            valid_until=utc_now + relativedelta(months=1),
            next_payment_at=utc_now + relativedelta(months=1),
            plan_expires_at=utc_now + relativedelta(months=12),
            currency=model.currency,
            selected_cohort_set=model.cohort_set,
        )
        other.plans.add(model.plan)

        updated = sync_cohort_user_finantial_status_from_plan_financing(model.plan_financing)
        self.assertEqual(updated, 0)
        self.assertEqual(self._covered_cohort_user(model).finantial_status, "UP_TO_DATE")

    def test_fully_paid_cu_with_other_covering_product_skips_late(self):
        model = self._setup(financing_status="PAYMENT_ISSUE", finantial_status="FULLY_PAID")
        utc_now = timezone.now()
        other = PlanFinancing.objects.create(
            user=model.user,
            academy=model.academy,
            status=PlanFinancing.Status.ACTIVE,
            monthly_price=50,
            how_many_installments=2,
            valid_until=utc_now + relativedelta(months=2),
            next_payment_at=utc_now + relativedelta(months=1),
            plan_expires_at=utc_now + relativedelta(months=12),
            currency=model.currency,
            selected_cohort_set=model.cohort_set,
        )
        other.plans.add(model.plan)

        updated = sync_cohort_user_finantial_status_from_plan_financing(model.plan_financing)
        self.assertEqual(updated, 0)
        self.assertEqual(self._covered_cohort_user(model).finantial_status, "FULLY_PAID")

    def test_error_does_not_change_cohort_user(self):
        model = self._setup(financing_status="ERROR", finantial_status="UP_TO_DATE")
        updated = sync_cohort_user_finantial_status_from_plan_financing(model.plan_financing)
        self.assertEqual(updated, 0)
        self.assertEqual(self._covered_cohort_user(model).finantial_status, "UP_TO_DATE")

    def test_deprecated_status_on_instance_does_not_change_cohort_user(self):
        model = self._setup(financing_status="ACTIVE", finantial_status="UP_TO_DATE")
        financing = model.plan_financing
        financing.status = PlanFinancing.Status.DEPRECATED
        updated = sync_cohort_user_finantial_status_from_plan_financing(financing)
        self.assertEqual(updated, 0)
        self.assertEqual(self._covered_cohort_user(model).finantial_status, "UP_TO_DATE")

    def test_only_updates_cohorts_in_cohort_set(self):
        model = self._setup(financing_status="PAYMENT_ISSUE", finantial_status="UP_TO_DATE", with_extra_cohort=True)
        updated = sync_cohort_user_finantial_status_from_plan_financing(model.plan_financing)
        self.assertEqual(updated, 1)

        covered = model.cohort[0]
        extra = model.cohort[1]
        self.assertEqual(CohortUser.objects.get(user=model.user, cohort=covered).finantial_status, "LATE")
        self.assertEqual(CohortUser.objects.get(user=model.user, cohort=extra).finantial_status, "UP_TO_DATE")

    @patch("breathecode.payments.signals.sync_cohort_user_finantial_status.send_robust")
    def test_status_change_via_save_emits_sync(self, mock_send):
        model = self._setup(financing_status="ACTIVE", finantial_status="UP_TO_DATE")
        financing = model.plan_financing
        financing.status = PlanFinancing.Status.PAYMENT_ISSUE
        financing.save()

        mock_send.assert_called()
        self.assertEqual(mock_send.call_args.kwargs["instance"].id, financing.id)
        self.assertEqual(mock_send.call_args.kwargs["sender"], PlanFinancing)
