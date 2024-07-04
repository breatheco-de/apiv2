"""
Collections of mixins used to login in authorize microservice
"""


class CareerQueriesMixin:

    def generate_career_queries(self):
        """Generate queries"""
        return {
            "module": "career",
            "models": [
                "Platform",
                "Position",
                "ZyteProject",
                "Spider",
                "PositionAlias",
                "CareerTag",
                "Location",
                "LocationAlias",
                "Employer",
                "Job",
            ],
        }
