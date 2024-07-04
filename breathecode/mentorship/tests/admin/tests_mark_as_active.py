"""
Test mentorships
"""

from unittest.mock import call, patch
from django.http import HttpRequest
from unittest.mock import MagicMock, patch

from breathecode.mentorship.admin import mark_as_active
import breathecode.mentorship.actions as actions

from ..mixins import MentorshipTestCase
from django.contrib import messages
from requests import exceptions


class GenerateMentorBillsTestCase(MentorshipTestCase):
    """
    🔽🔽🔽 With zero MentorProfile
    """

    @patch("django.contrib.messages.success", MagicMock())
    @patch("django.contrib.messages.error", MagicMock())
    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
    def test_with_zero_mentor_profiles(self):
        MentorProfile = self.bc.database.get_model("mentorship.MentorProfile")
        queryset = MentorProfile.objects.filter()
        request = HttpRequest()

        mark_as_active(None, request, queryset)

        self.assertEqual(self.bc.database.list_of("mentorship.MentorProfile"), [])

        self.assertEqual(actions.mentor_is_ready.call_args_list, [])
        self.assertEqual(messages.success.call_args_list, [])
        self.assertEqual(messages.error.call_args_list, [])

    """
    🔽🔽🔽 With two MentorProfile
    """

    @patch("django.contrib.messages.success", MagicMock())
    @patch("django.contrib.messages.error", MagicMock())
    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
    def test_with_two_mentor_profiles(self):
        model = self.bc.database.create(mentor_profile=2)
        MentorProfile = self.bc.database.get_model("mentorship.MentorProfile")
        queryset = MentorProfile.objects.filter()
        request = HttpRequest()

        mark_as_active(None, request, queryset)

        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorProfile"), self.bc.format.to_dict(model.mentor_profile)
        )

        self.assertEqual(actions.mentor_is_ready.call_args_list, [call(x) for x in model.mentor_profile])
        self.assertEqual(
            messages.success.call_args_list,
            [
                call(request, "Mentor updated successfully"),
            ],
        )
        self.assertEqual(messages.error.call_args_list, [])

    """
    🔽🔽🔽 With two MentorProfile, with ConnectionError
    """

    @patch("django.contrib.messages.success", MagicMock())
    @patch("django.contrib.messages.error", MagicMock())
    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock(side_effect=exceptions.ConnectionError()))
    def test_with_two_mentor_profiles__with_connection_error(self):
        model = self.bc.database.create(mentor_profile=2)
        MentorProfile = self.bc.database.get_model("mentorship.MentorProfile")
        queryset = MentorProfile.objects.filter()
        request = HttpRequest()

        mark_as_active(None, request, queryset)

        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorProfile"), self.bc.format.to_dict(model.mentor_profile)
        )

        self.assertEqual(actions.mentor_is_ready.call_args_list, [call(x) for x in model.mentor_profile])
        self.assertEqual(messages.success.call_args_list, [])
        self.assertEqual(
            messages.error.call_args_list,
            [
                call(
                    request,
                    "Error: Booking or meeting URL for mentor is failing "
                    f'({", ".join([x.slug for x in model.mentor_profile])}).',
                ),
            ],
        )

    """
    🔽🔽🔽 With two MentorProfile, with Exception
    """

    @patch("django.contrib.messages.success", MagicMock())
    @patch("django.contrib.messages.error", MagicMock())
    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock(side_effect=Exception("xyz")))
    def test_with_two_mentor_profiles__with_exception(self):
        model = self.bc.database.create(mentor_profile=2)
        MentorProfile = self.bc.database.get_model("mentorship.MentorProfile")
        queryset = MentorProfile.objects.filter()
        request = HttpRequest()

        mark_as_active(None, request, queryset)

        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorProfile"), self.bc.format.to_dict(model.mentor_profile)
        )

        self.assertEqual(actions.mentor_is_ready.call_args_list, [call(x) for x in model.mentor_profile])
        self.assertEqual(messages.success.call_args_list, [])
        self.assertEqual(
            messages.error.call_args_list,
            [
                call(request, f'Error: xyz ({", ".join([x.slug for x in model.mentor_profile])}).'),
            ],
        )

    """
    🔽🔽🔽 With two MentorProfile, with ConnectionError and Exception
    """

    @patch("django.contrib.messages.success", MagicMock())
    @patch("django.contrib.messages.error", MagicMock())
    @patch(
        "breathecode.mentorship.actions.mentor_is_ready",
        MagicMock(side_effect=[exceptions.ConnectionError(), Exception("xyz")]),
    )
    def test_with_three_mentor_profiles__with_connection_error__with_exception(self):
        model = self.bc.database.create(mentor_profile=2)
        MentorProfile = self.bc.database.get_model("mentorship.MentorProfile")
        queryset = MentorProfile.objects.filter()
        request = HttpRequest()

        mark_as_active(None, request, queryset)

        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorProfile"), self.bc.format.to_dict(model.mentor_profile)
        )

        self.assertEqual(actions.mentor_is_ready.call_args_list, [call(x) for x in model.mentor_profile])
        self.assertEqual(messages.success.call_args_list, [])
        self.assertEqual(
            messages.error.call_args_list,
            [
                call(
                    request,
                    "Error: Booking or meeting URL for mentor is failing "
                    f"({model.mentor_profile[0].slug}). xyz ({model.mentor_profile[1].slug}).",
                ),
            ],
        )
