from unittest.mock import patch, call
from breathecode.jobs.services import BaseScraper
from ..mixins import JobsTestCase


class ActionGetDateFromStringTestCase(JobsTestCase):
    def test_get_job_id_from_string_is_empty(self):
        result = BaseScraper.get_job_id_from_string('')
        self.assertEquals(result, None)

    def test_get_job_id_from_string_with_id(self):
        result = BaseScraper.get_job_id_from_string('223344/6/25')
        self.assertEquals(result, (223344, 6, 25))
