"""
Collections of mixins used to login in authorize microservice
"""


class EventsQueriesMixin:

    def generate_events_queries(self):
        """Generate queries"""
        return {
            "module": "events",
            "models": ["Organization", "Organizer", "Venue", "EventType", "Event", "EventCheckin", "EventbriteWebhook"],
        }
