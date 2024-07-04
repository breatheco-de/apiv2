"""
Test mentorships
"""

from unittest.mock import call, patch
from django.http import HttpRequest
from unittest.mock import MagicMock, patch

from breathecode.mentorship.admin import generate_slug_based_on_calendly

from ..mixins import MentorshipTestCase
from django.contrib import messages


class GenerateMentorBillsTestCase(MentorshipTestCase):
    """
    🔽🔽🔽 With zero MentorProfile
    """

    @patch("django.contrib.messages.error", MagicMock())
    def test_with_zero_mentor_profiles(self):
        MentorProfile = self.bc.database.get_model("mentorship.MentorProfile")
        queryset = MentorProfile.objects.filter()
        request = HttpRequest()

        generate_slug_based_on_calendly(None, request, queryset)

        self.assertEqual(self.bc.database.list_of("mentorship.MentorProfile"), [])
        self.assertEqual(messages.error.call_args_list, [])

    """
    🔽🔽🔽 With two MentorProfile without booking_url
    """

    @patch("django.contrib.messages.error", MagicMock())
    def test_with_two_mentor_profiles__without_booking_url(self):
        model = self.bc.database.create(mentor_profile=2)
        MentorProfile = self.bc.database.get_model("mentorship.MentorProfile")
        queryset = MentorProfile.objects.filter()
        request = HttpRequest()

        generate_slug_based_on_calendly(None, request, queryset)

        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorProfile"), self.bc.format.to_dict(model.mentor_profile)
        )

        self.assertEqual(
            messages.error.call_args_list,
            [call(request, f"Mentor {x.id} has no booking url") for x in model.mentor_profile],
        )

    """
    🔽🔽🔽 With two MentorProfile with booking_url
    """

    @patch("django.contrib.messages.error", MagicMock())
    def test_with_two_mentor_profiles__with_booking_url__different_of_calendly(self):
        mentor_profiles = [{"booking_url": self.bc.fake.url()} for _ in range(0, 2)]
        model = self.bc.database.create(mentor_profile=mentor_profiles)

        MentorProfile = self.bc.database.get_model("mentorship.MentorProfile")
        queryset = MentorProfile.objects.filter()
        request = HttpRequest()

        generate_slug_based_on_calendly(None, request, queryset)

        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorProfile"), self.bc.format.to_dict(model.mentor_profile)
        )

        self.assertEqual(
            messages.error.call_args_list,
            [
                call(request, f"Mentor {x.id} booking url is not calendly: {x.booking_url}")
                for x in model.mentor_profile
            ],
        )

    """
    🔽🔽🔽 With two MentorProfile with booking_url of calendly
    """

    @patch("django.contrib.messages.error", MagicMock())
    def test_with_two_mentor_profiles__with_booking_url__of_calendly(self):
        mentor_slug1 = self.bc.fake.slug()
        mentor_slug2 = self.bc.fake.slug()
        service_slug1 = self.bc.fake.slug()
        service_slug2 = self.bc.fake.slug()
        mentor_profiles = [
            {"booking_url": f"https://calendly.com/{mentor_slug}/{service_slug}"}
            for mentor_slug, service_slug in [(mentor_slug1, service_slug1), (mentor_slug2, service_slug2)]
        ]
        model = self.bc.database.create(mentor_profile=mentor_profiles)

        MentorProfile = self.bc.database.get_model("mentorship.MentorProfile")
        queryset = MentorProfile.objects.filter()
        request = HttpRequest()

        generate_slug_based_on_calendly(None, request, queryset)

        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorProfile"),
            [
                {
                    **self.bc.format.to_dict(model.mentor_profile[0]),
                    "slug": mentor_slug1,
                },
                {
                    **self.bc.format.to_dict(model.mentor_profile[1]),
                    "slug": mentor_slug2,
                },
            ],
        )

        self.assertEqual(messages.error.call_args_list, [])
