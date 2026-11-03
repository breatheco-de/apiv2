from datetime import timedelta

from django.utils import timezone

from breathecode.events.actions import exclude_events_denied_for_user, user_has_denied_plan_for_event
from breathecode.events.models import Event
from breathecode.events.tests.mixins.new_events_tests_case import EventTestCase


class UserHasDeniedPlanForEventTestSuite(EventTestCase):

    def test_false_when_event_has_no_denied_plans(self):
        model = self.bc.database.create(user=1, event=1, plan=1)

        self.assertFalse(user_has_denied_plan_for_event(model.user, model.event))

    def test_true_when_user_has_plan_financing_with_denied_plan(self):
        model = self.bc.database.create(
            user=1,
            event=1,
            plan={"slug": "plan-apoyo-profesional-aie"},
            plan_financing={
                "status": "FULLY_PAID",
                "plan_expires_at": timezone.now() + timedelta(days=30),
            },
        )
        model.event.denied_plans.add(model.plan)
        model.plan_financing.plans.add(model.plan)

        self.assertTrue(user_has_denied_plan_for_event(model.user, model.event))

    def test_true_when_user_has_active_subscription_with_denied_plan(self):
        model = self.bc.database.create(
            user=1,
            event=1,
            plan={"slug": "bootcamp-blocked"},
            subscription={"status": "ACTIVE"},
        )
        model.event.denied_plans.add(model.plan)
        model.subscription.plans.add(model.plan)

        self.assertTrue(user_has_denied_plan_for_event(model.user, model.event))

    def test_false_when_user_plan_is_not_denied(self):
        model = self.bc.database.create(
            user=1,
            event=1,
            plan={"slug": "other-plan"},
            subscription={"status": "ACTIVE"},
        )
        denied = self.bc.database.create(plan={"slug": "denied-plan"}).plan
        model.event.denied_plans.add(denied)
        model.subscription.plans.add(model.plan)

        self.assertFalse(user_has_denied_plan_for_event(model.user, model.event))

    def test_exclude_events_denied_for_user_hides_matching_events(self):
        model = self.bc.database.create(
            user=1,
            event=[{"slug": "blocked-event"}, {"slug": "open-event"}],
            plan={"slug": "bootcamp-blocked"},
            subscription={"status": "ACTIVE"},
        )
        blocked, open_event = model.event
        blocked.denied_plans.add(model.plan)
        model.subscription.plans.add(model.plan)

        qs = exclude_events_denied_for_user(Event.objects.all(), model.user)

        self.assertEqual(list(qs.values_list("slug", flat=True)), ["open-event"])

    def test_exclude_events_denied_for_user_keeps_all_for_anonymous(self):
        model = self.bc.database.create(
            user=1,
            event={"slug": "blocked-event"},
            plan={"slug": "bootcamp-blocked"},
            subscription={"status": "ACTIVE"},
        )
        model.event.denied_plans.add(model.plan)
        model.subscription.plans.add(model.plan)

        qs = exclude_events_denied_for_user(Event.objects.all(), None)

        self.assertEqual(qs.count(), 1)
