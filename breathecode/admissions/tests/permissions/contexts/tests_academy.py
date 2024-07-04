import random
from unittest.mock import MagicMock, call, patch
from ....permissions.contexts import academy
from ...mixins import AdmissionsTestCase

from breathecode.services import LaunchDarkly


def serializer(academy):
    return {
        "id": academy.id,
        "slug": academy.slug,
        "city": academy.city.name,
        "country": academy.country.name,
        "zip_code": academy.zip_code,
        "timezone": academy.timezone,
    }


value = random.randint(1, 1000)


class AcademyEventTestSuite(AdmissionsTestCase):

    @patch("ldclient.get", MagicMock())
    @patch("breathecode.services.launch_darkly.client.LaunchDarkly.context", MagicMock(return_value=value))
    def test_make_right_calls(self):
        model = self.bc.database.create(academy=1)

        ld = LaunchDarkly()
        result = academy(ld, model.academy)

        self.assertEqual(
            self.bc.database.list_of("admissions.Academy"),
            [
                self.bc.format.to_dict(model.academy),
            ],
        )

        contexts = serializer(model.academy)

        self.assertEqual(
            LaunchDarkly.context.call_args_list,
            [
                call("1", f"{model.academy.name} ({model.academy.slug})", "academy", contexts),
            ],
        )

        self.assertEqual(result, value)
