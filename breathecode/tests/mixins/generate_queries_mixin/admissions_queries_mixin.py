"""
Collections of mixins used to login in authorize microservice
"""


class AdmissionsQueriesMixin:

    def generate_admissions_queries(self):
        """Generate queries"""
        return {
            "module": "admissions",
            "models": [
                "Country",
                "City",
                "Academy",
                "Syllabus",
                "SyllabusVersion",
                "SyllabusSchedule",
                "Cohort",
                "CohortUser",
                "SyllabusScheduleTimeSlot",
                "CohortTimeSlot",
            ],
        }
