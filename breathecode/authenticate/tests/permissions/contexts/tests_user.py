import random
from unittest.mock import MagicMock, call, patch
from ....permissions.contexts import user
from ...mixins.new_auth_test_case import AuthTestCase

from breathecode.services import LaunchDarkly


def serializer(user):
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "date_joined": user.date_joined,
        "groups": [x.name for x in user.groups.all()],
    }


value = random.randint(1, 1000)


class AcademyEventTestSuite(AuthTestCase):

    @patch("ldclient.get", MagicMock())
    @patch("breathecode.services.launch_darkly.client.LaunchDarkly.context", MagicMock(return_value=value))
    def test_make_right_calls(self):
        model = self.bc.database.create(user=1)

        ld = LaunchDarkly()
        result = user(ld, model.user)

        self.assertEqual(
            self.bc.database.list_of("auth.User"),
            [
                self.bc.format.to_dict(model.user),
            ],
        )

        contexts = serializer(model.user)

        print(LaunchDarkly.context.call_args_list)

        self.assertEqual(
            LaunchDarkly.context.call_args_list,
            [
                call("1", f"{model.user.first_name} {model.user.last_name} ({model.user.email})", "user", contexts),
            ],
        )

        self.assertEqual(result, value)
