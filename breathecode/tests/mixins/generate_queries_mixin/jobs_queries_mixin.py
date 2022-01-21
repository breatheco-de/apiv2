"""
Collections of mixins used to login in authorize microservice
"""


class JobsQueriesMixin():
    def generate_jobs_queries(self):
        """Generate queries"""
        return {
            'module':
            'jobs',
            'models': [
                'Platform', 'Position', 'ZyteProject', 'Spider', 'PositionAlias', 'Tag', 'Location',
                'LocationAlias', 'Employer', 'Job'
            ]
        }
