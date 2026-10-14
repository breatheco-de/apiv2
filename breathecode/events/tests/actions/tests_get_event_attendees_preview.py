from breathecode.events.actions import get_event_attendees_preview

from ..mixins.new_events_tests_case import EventTestCase


class GetEventAttendeesPreviewTestSuite(EventTestCase):

    def test_without_checkins(self):
        model = self.bc.database.create(event=1)

        result = get_event_attendees_preview(model.event)

        self.assertEqual(result, {"total": 0, "attendees": []})

    def test_counts_all_checkins_but_only_lists_users(self):
        event_checkins = [{"attendee_id": 1}, {"attendee_id": 2}, {"attendee_id": None}]
        model = self.bc.database.create(
            event=1,
            user=2,
            profile={"user_id": 1, "avatar_url": "https://example.com/avatar.png"},
            event_checkin=event_checkins,
        )

        result = get_event_attendees_preview(model.event)

        self.assertEqual(result["total"], 3)
        self.assertEqual(
            sorted(result["attendees"], key=lambda x: x["first_name"] or ""),
            sorted(
                [
                    {
                        "first_name": model.user[0].first_name,
                        "last_name": model.user[0].last_name,
                        "avatar_url": "https://example.com/avatar.png",
                    },
                    {
                        "first_name": model.user[1].first_name,
                        "last_name": model.user[1].last_name,
                        "avatar_url": None,
                    },
                ],
                key=lambda x: x["first_name"] or "",
            ),
        )

    def test_respects_limit(self):
        model = self.bc.database.create(
            event=1,
            user=3,
            event_checkin=[{"attendee_id": n} for n in range(1, 4)],
        )

        result = get_event_attendees_preview(model.event, limit=2)

        self.assertEqual(result["total"], 3)
        self.assertEqual(len(result["attendees"]), 2)
