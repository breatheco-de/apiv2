"""
Collections of mixins used to login in authorize microservice
"""


class FeedbackQueriesMixin:

    def generate_feedback_queries(self):
        """Generate queries"""
        return {"module": "feedback", "models": ["Survey", "Answer"]}
