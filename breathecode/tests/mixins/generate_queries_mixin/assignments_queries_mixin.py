"""
Collections of mixins used to login in authorize microservice
"""

class AssignmentsQueriesMixin():
    def generate_assignments_queries(self, **kwargs):
        """Generate queries"""
        return {
            'module': 'assignments',
            'models': ['Task']
        }
