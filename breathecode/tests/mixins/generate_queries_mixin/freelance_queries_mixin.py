"""
Collections of mixins used to login in authorize microservice
"""


class FreelanceQueriesMixin:

    def generate_freelance_queries(self):
        """Generate queries"""
        return {"module": "freelance", "models": ["Freelancer", "Bill", "Issue"]}
