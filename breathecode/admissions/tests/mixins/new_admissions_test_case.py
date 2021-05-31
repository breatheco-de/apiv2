"""
Collections of mixins used to login in authorize microservice
"""
from rest_framework.test import APITestCase
from breathecode.tests.mixins import GenerateModelsMixin, CacheMixin, GenerateQueriesMixin, DatetimeMixin, ICallMixin

class AdmissionsTestCase(APITestCase, GenerateModelsMixin, CacheMixin,
        GenerateQueriesMixin, DatetimeMixin, ICallMixin):
    """AdmissionsTestCase with auth methods"""
    def setUp(self):
        self.generate_queries()

    def tearDown(self):
        self.clear_cache()

    def fill_cohort_timeslot(self, id, cohort_id, certificate_timeslot):
        return {
            'id': id,
            'cohort_id': cohort_id,
            'starting_at': certificate_timeslot.starting_at,
            'ending_at': certificate_timeslot.ending_at,
            'recurrent': certificate_timeslot.recurrent,
            'recurrency_type': certificate_timeslot.recurrency_type,
        }
