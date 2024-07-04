"""
Collections of mixins used to login in authorize microservice
"""


class AssessmentQueriesMixin:

    def generate_assessment_queries(self):
        """Generate queries"""
        return {"module": "assessment", "models": ["Assessment", "Question", "Option", "StudentAssessment", "Answer"]}
