"""
Test /academy/cohort
"""
import urllib, pytz
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins import MarketingTestCase

class AcademyCohortTestSuite(MarketingTestCase):
