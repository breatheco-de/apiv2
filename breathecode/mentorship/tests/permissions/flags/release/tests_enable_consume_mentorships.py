import random
from unittest.mock import MagicMock, call, patch
from .....permissions.flags import api
from breathecode.authenticate.permissions import contexts as authenticate_contexts
from breathecode.admissions.permissions import contexts as admissions_contexts
from breathecode.mentorship.permissions import contexts
from breathecode.services import LaunchDarkly
from ....mixins import MentorshipTestCase

value = bool(random.randbytes(1))
join_contexts_value = random.randint(1, 100)

context1 = random.randint(1, 100)
context2 = random.randint(1, 100)
context3 = random.randint(1, 100)


def assert_context_was_call(self, fn, model):
    self.assertEqual(len(fn.call_args_list), 1)
    args, kwargs = fn.call_args_list[0]

    self.assertEqual(len(args), 2)
    self.assertEqual(len(kwargs), 0)

    self.assertTrue(isinstance(args[0], LaunchDarkly))
    self.assertEqual(args[1], model)


class AcademyEventTestSuite(MentorshipTestCase):

    @patch("ldclient.get", MagicMock())
    @patch("breathecode.services.launch_darkly.client.LaunchDarkly.get", MagicMock(return_value=value))
    @patch(
        "breathecode.services.launch_darkly.client.LaunchDarkly.join_contexts",
        MagicMock(return_value=join_contexts_value),
    )
    @patch("breathecode.authenticate.permissions.contexts.user", MagicMock(return_value=context1))
    @patch("breathecode.mentorship.permissions.contexts.mentorship_service", MagicMock(return_value=context2))
    @patch("breathecode.admissions.permissions.contexts.academy", MagicMock(return_value=context3))
    def test_make_right_calls(self):
        model = self.bc.database.create(user=1, mentorship_service=1)

        result = api.release.enable_consume_mentorships(model.user, model.mentorship_service)

        self.assertEqual(
            self.bc.database.list_of("auth.User"),
            [
                self.bc.format.to_dict(model.user),
            ],
        )

        assert_context_was_call(self, authenticate_contexts.user, model.user)
        assert_context_was_call(self, admissions_contexts.academy, model.academy)
        assert_context_was_call(self, contexts.mentorship_service, model.mentorship_service)

        self.assertEqual(result, value)

        self.assertEqual(
            LaunchDarkly.join_contexts.call_args_list,
            [
                call(context1, context2, context3),
            ],
        )

        self.assertEqual(
            LaunchDarkly.get.call_args_list,
            [
                call("api.release.enable_consume_mentorships", join_contexts_value, False),
            ],
        )
