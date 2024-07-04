import random
from unittest.mock import MagicMock, call, patch
from ....permissions.contexts import mentorship_service
from ...mixins import MentorshipTestCase

from breathecode.services import LaunchDarkly


def serializer(mentorship_service):
    return {
        "id": mentorship_service.id,
        "slug": mentorship_service.slug,
        "max_duration": mentorship_service.max_duration,
        "language": mentorship_service.language,
        "academy": mentorship_service.academy.slug,
    }


value = random.randint(1, 1000)


class AcademyEventTestSuite(MentorshipTestCase):

    @patch("ldclient.get", MagicMock())
    @patch("breathecode.services.launch_darkly.client.LaunchDarkly.context", MagicMock(return_value=value))
    def test_make_right_calls(self):
        model = self.bc.database.create(mentorship_service=1)

        ld = LaunchDarkly()
        result = mentorship_service(ld, model.mentorship_service)

        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipService"),
            [
                self.bc.format.to_dict(model.mentorship_service),
            ],
        )

        contexts = serializer(model.mentorship_service)

        self.assertEqual(
            LaunchDarkly.context.call_args_list,
            [
                call(
                    "1",
                    f"{model.mentorship_service.name} ({model.mentorship_service.slug})",
                    "mentoring-service",
                    contexts,
                ),
            ],
        )

        self.assertEqual(result, value)
