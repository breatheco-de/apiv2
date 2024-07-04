"""
Test mentorships
"""

from unittest.mock import call, patch
from unittest.mock import MagicMock, patch

from breathecode.mentorship.admin import generate_bill
import breathecode.mentorship.actions as actions

from ..mixins import MentorshipTestCase


class GenerateMentorBillsTestCase(MentorshipTestCase):
    """
    🔽🔽🔽 With zero MentorProfile
    """

    @patch("breathecode.mentorship.actions.generate_mentor_bills", MagicMock())
    def test_with_zero_mentor_profiles(self):
        MentorProfile = self.bc.database.get_model("mentorship.MentorProfile")
        queryset = MentorProfile.objects.filter()

        generate_bill(None, None, queryset)

        self.assertEqual(self.bc.database.list_of("mentorship.MentorProfile"), [])
        self.assertEqual(actions.generate_mentor_bills.call_args_list, [])

    """
    🔽🔽🔽 With two MentorProfile
    """

    @patch("breathecode.mentorship.actions.generate_mentor_bills", MagicMock())
    def test_with_two_mentor_profiles(self):
        model = self.bc.database.create(mentor_profile=2)
        MentorProfile = self.bc.database.get_model("mentorship.MentorProfile")
        queryset = MentorProfile.objects.filter()

        generate_bill(None, None, queryset)

        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorProfile"), self.bc.format.to_dict(model.mentor_profile)
        )
        self.assertEqual(
            actions.generate_mentor_bills.call_args_list,
            [call(x, reset=True) for x in model.mentor_profile],
        )
