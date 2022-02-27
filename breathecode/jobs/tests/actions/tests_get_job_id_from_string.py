from unittest.mock import patch, call
from breathecode.jobs.services import BaseScrapper
from ..mixins import JobsTestCase


class ActionGetDateFromStringTestCase(JobsTestCase):
    def test_get_job_id_from_string_is_empty(self):
        result = BaseScrapper.get_job_id_from_string('')
        self.assertEquals(result, None)

    def test_get_job_id_from_string_with_id(self):
        result = BaseScrapper.get_job_id_from_string('570286/2/71')
        self.assertEquals(result, ('570286', '2', '71'))
