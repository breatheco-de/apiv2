"""
Collections of mixins used to login in authorize microservice
"""


class CarreerQueriesMixin():
    def generate_carreer_queries(self):
        """Generate queries"""
        return {
            'module':
            'carreer',
            'models': [
                'Platform', 'Position', 'ZyteProject', 'Spider', 'PositionAlias', 'CarreerTag', 'Location',
                'LocationAlias', 'Employer', 'Job'
            ]
        }
