"""
Test mentorships
"""

from breathecode.mentorship.admin import allow_billing_this_session
from ..mixins import MentorshipTestCase


class GenerateMentorBillsTestCase(MentorshipTestCase):
    """
    🔽🔽🔽 With zero MentorshipSession
    """

    def test_with_zero_mentorship_sessions(self):
        MentorshipSession = self.bc.database.get_model("mentorship.MentorshipSession")
        queryset = MentorshipSession.objects.filter()

        allow_billing_this_session(None, None, queryset)

        self.assertEqual(self.bc.database.list_of("mentorship.MentorshipSession"), [])

    """
    🔽🔽🔽 With two MentorshipSession, allow_billing equal to False
    """

    def test_with_two_mentorship_sessions__allow_billing_equal_to_false(self):
        mentorship_sessions = [{"allow_billing": False} for _ in range(0, 2)]
        model = self.bc.database.create(mentorship_session=mentorship_sessions)

        MentorshipSession = self.bc.database.get_model("mentorship.MentorshipSession")
        queryset = MentorshipSession.objects.filter()

        allow_billing_this_session(None, None, queryset)

        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                {
                    **x,
                    "allow_billing": True,
                }
                for x in self.bc.format.to_dict(model.mentorship_session)
            ],
        )

    """
    🔽🔽🔽 With two MentorshipSession, allow_billing equal to True
    """

    def test_with_two_mentorship_sessions__allow_billing_equal_to_true(self):
        mentor_profiles = [{"allow_billing": True} for _ in range(0, 2)]
        model = self.bc.database.create(mentorship_session=mentor_profiles)

        MentorshipSession = self.bc.database.get_model("mentorship.MentorshipSession")
        queryset = MentorshipSession.objects.filter()

        allow_billing_this_session(None, None, queryset)

        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"), self.bc.format.to_dict(model.mentorship_session)
        )
