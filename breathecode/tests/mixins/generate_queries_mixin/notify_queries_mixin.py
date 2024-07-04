"""
Collections of mixins used to login in authorize microservice
"""


class NotifyQueriesMixin:

    def generate_notify_queries(self):
        """Generate queries"""
        return {"module": "notify", "models": ["Device", "SlackTeam", "SlackUser", "SlackUserTeam", "SlackChannel"]}
