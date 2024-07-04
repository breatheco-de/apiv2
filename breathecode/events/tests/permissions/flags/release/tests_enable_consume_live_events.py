import random
from unittest.mock import MagicMock, call, patch
from .....permissions.flags import api
from ....mixins.new_events_tests_case import EventTestCase
from breathecode.authenticate.permissions import contexts as authenticate_contexts
from breathecode.admissions.permissions import contexts as admissions_contexts
from breathecode.events.permissions import contexts
from breathecode.services import LaunchDarkly

value = bool(random.randbytes(1))
join_contexts_value = random.randint(1, 100)

context1 = random.randint(1, 100)
context2 = random.randint(1, 100)
context3 = random.randint(1, 100)
context4 = random.randint(1, 100)


def assert_context_was_call(self, fn, model):
    self.assertEqual(len(fn.call_args_list), 1)
    args, kwargs = fn.call_args_list[0]

    self.assertEqual(len(args), 2)
    self.assertEqual(len(kwargs), 0)

    self.assertTrue(isinstance(args[0], LaunchDarkly))
    self.assertEqual(args[1], model)


class AcademyEventTestSuite(EventTestCase):

    @patch("ldclient.get", MagicMock())
    @patch("breathecode.services.launch_darkly.client.LaunchDarkly.get", MagicMock(return_value=value))
    @patch(
        "breathecode.services.launch_darkly.client.LaunchDarkly.join_contexts",
        MagicMock(return_value=join_contexts_value),
    )
    @patch("breathecode.authenticate.permissions.contexts.user", MagicMock(return_value=context1))
    @patch("breathecode.events.permissions.contexts.event", MagicMock(return_value=context2))
    @patch("breathecode.events.permissions.contexts.event_type", MagicMock(return_value=context3))
    @patch("breathecode.admissions.permissions.contexts.academy", MagicMock(return_value=context4))
    def test_make_right_calls__without_all_contexts(self):
        model = self.bc.database.create(user=1, event=1)

        result = api.release.enable_consume_live_events(model.user, model.event)

        self.assertEqual(
            self.bc.database.list_of("auth.User"),
            [
                self.bc.format.to_dict(model.user),
            ],
        )

        assert_context_was_call(self, authenticate_contexts.user, model.user)
        # assert_context_call(self, admissions_contexts.academy, model.academy)
        assert_context_was_call(self, contexts.event, model.event)
        # assert_context_call(self, contexts.event_type, model.event_type)

        self.assertEqual(admissions_contexts.academy.call_args_list, [])
        self.assertEqual(contexts.event_type.call_args_list, [])

        self.assertEqual(result, value)

        self.assertEqual(
            LaunchDarkly.join_contexts.call_args_list,
            [
                call(context1, context2),
            ],
        )

        self.assertEqual(
            LaunchDarkly.get.call_args_list,
            [
                call("api.release.enable_consume_live_events", join_contexts_value, False),
            ],
        )

    @patch("ldclient.get", MagicMock())
    @patch("breathecode.services.launch_darkly.client.LaunchDarkly.get", MagicMock(return_value=value))
    @patch(
        "breathecode.services.launch_darkly.client.LaunchDarkly.join_contexts",
        MagicMock(return_value=join_contexts_value),
    )
    @patch("breathecode.authenticate.permissions.contexts.user", MagicMock(return_value=context1))
    @patch("breathecode.events.permissions.contexts.event", MagicMock(return_value=context2))
    @patch("breathecode.events.permissions.contexts.event_type", MagicMock(return_value=context3))
    @patch("breathecode.admissions.permissions.contexts.academy", MagicMock(return_value=context4))
    def test_make_right_calls__with_all_contexts(self):
        event_type = {"icon_url": self.bc.fake.url()}
        model = self.bc.database.create(user=1, event=1, academy=1, event_type=event_type)

        result = api.release.enable_consume_live_events(model.user, model.event)

        self.assertEqual(
            self.bc.database.list_of("auth.User"),
            [
                self.bc.format.to_dict(model.user),
            ],
        )

        assert_context_was_call(self, authenticate_contexts.user, model.user)
        assert_context_was_call(self, admissions_contexts.academy, model.academy)
        assert_context_was_call(self, contexts.event, model.event)
        assert_context_was_call(self, contexts.event_type, model.event_type)

        self.assertEqual(result, value)

        self.assertEqual(
            LaunchDarkly.join_contexts.call_args_list,
            [
                call(context1, context2, context3, context4),
            ],
        )

        self.assertEqual(
            LaunchDarkly.get.call_args_list,
            [
                call("api.release.enable_consume_live_events", join_contexts_value, False),
            ],
        )
