"""
Test mentorships
"""

from datetime import timedelta
import random

from breathecode.mentorship.admin import release_sessions_from_bill

from ..mixins import MentorshipTestCase


class GenerateMentorBillsTestCase(MentorshipTestCase):
    """
    🔽🔽🔽 With zero MentorshipBill
    """

    def test_with_zero_mentorship_bills(self):
        MentorshipBill = self.bc.database.get_model("mentorship.MentorshipBill")
        queryset = MentorshipBill.objects.filter()

        release_sessions_from_bill(None, None, queryset)

        self.assertEqual(self.bc.database.list_of("mentorship.MentorshipBill"), [])
        self.assertEqual(self.bc.database.list_of("mentorship.MentorshipSession"), [])

    """
    🔽🔽🔽 With two MentorshipBill and MentorshipSession
    """

    def test_with_two_mentorship_bills(self):
        mentorship_sessions = [{"bill_id": n} for n in range(1, 3)]
        model = self.bc.database.create(mentorship_bill=2, mentorship_session=mentorship_sessions)

        MentorshipBill = self.bc.database.get_model("mentorship.MentorshipBill")
        queryset = MentorshipBill.objects.filter()

        release_sessions_from_bill(None, None, queryset)

        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipBill"),
            [
                {
                    **x,
                }
                for x in self.bc.format.to_dict(model.mentorship_bill)
            ],
        )

        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                {
                    **x,
                    "bill_id": None,
                }
                for x in self.bc.format.to_dict(model.mentorship_session)
            ],
        )

    """
    🔽🔽🔽 With two MentorshipBill and MentorshipSession, clean all values
    """

    def test_with_two_mentorship_bills__clean_all_values(self):
        mentorship_bills = [
            {
                "total_price": random.randint(0, 10000),
                "total_duration_in_hours": random.randint(0, 10000),
                "total_duration_in_minutes": random.randint(0, 10000),
                "overtime_minutes": random.randint(0, 10000),
            }
            for _ in range(1, 3)
        ]

        mentorship_sessions = [
            {
                "bill_id": n,
                "accounted_duration": timedelta(hours=random.randint(0, 10000)),
            }
            for n in range(1, 3)
        ]
        model = self.bc.database.create(mentorship_bill=mentorship_bills, mentorship_session=mentorship_sessions)

        MentorshipBill = self.bc.database.get_model("mentorship.MentorshipBill")
        queryset = MentorshipBill.objects.filter()

        release_sessions_from_bill(None, None, queryset)

        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipBill"),
            [
                {
                    **x,
                    "total_price": 0.0,
                    "total_duration_in_hours": 0.0,
                    "total_duration_in_minutes": 0.0,
                    "overtime_minutes": 0.0,
                }
                for x in self.bc.format.to_dict(model.mentorship_bill)
            ],
        )

        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                {
                    **x,
                    "bill_id": None,
                    "accounted_duration": None,
                }
                for x in self.bc.format.to_dict(model.mentorship_session)
            ],
        )
