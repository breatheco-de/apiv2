import random
from unittest.mock import MagicMock, call, patch
from .....permissions.flags import api
from ....mixins.new_events_tests_case import EventTestCase
from breathecode.authenticate.permissions import contexts as authenticate_contexts
from breathecode.services import LaunchDarkly

value = bool(random.randbytes(1))

context_value = random.randint(1, 100)


class AcademyEventTestSuite(EventTestCase):

    @patch("ldclient.get", MagicMock())
    @patch("breathecode.services.launch_darkly.client.LaunchDarkly.get", MagicMock(return_value=value))
    @patch("breathecode.authenticate.permissions.contexts.user", MagicMock(return_value=context_value))
    def test_make_right_calls(self):
        model = self.bc.database.create(user=1)

        result = api.release.enable_consume_live_classes(model.user)

        self.assertEqual(
            self.bc.database.list_of("auth.User"),
            [
                self.bc.format.to_dict(model.user),
            ],
        )

        self.assertEqual(len(authenticate_contexts.user.call_args_list), 1)
        args, kwargs = authenticate_contexts.user.call_args_list[0]

        self.assertEqual(len(args), 2)
        self.assertEqual(len(kwargs), 0)

        self.assertTrue(isinstance(args[0], LaunchDarkly))
        self.assertEqual(args[1], model.user)

        self.assertEqual(result, value)

        self.assertEqual(
            LaunchDarkly.get.call_args_list,
            [
                call("api.release.enable_consume_live_classes", context_value, False),
            ],
        )
