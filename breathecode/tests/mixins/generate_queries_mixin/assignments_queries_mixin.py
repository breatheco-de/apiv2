"""
Collections of mixins used to login in authorize microservice
"""


class AssignmentsQueriesMixin:

    def generate_assignments_queries(self):
        """Generate queries"""
        return {"module": "assignments", "models": ["Task"]}
