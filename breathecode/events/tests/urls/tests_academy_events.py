import re
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.tests.mixins import HeadersMixin

class AcademyEventsTestSuite(HeadersMixin):
    def test_all_academy_events_no_auth(self):
        self.headers(academy=4)
        url = reverse_lazy('events:academy_all_events')
        
        response = self.client.get(url)
        json = response.json()
        expected = {}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 401)
