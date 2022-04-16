from unittest.mock import patch, call
from breathecode.career.services import BaseScraper
from ..mixins import CareerTestCase


class ActionGetDateFromStringTestCase(CareerTestCase):
    def test_get_job_id_from_string_is_empty(self):
        result = BaseScraper.get_job_id_from_string('')
        self.assertEquals(result, None)

    def test_get_job_id_from_string_with_id(self):
        result = BaseScraper.get_job_id_from_string('223344/6/25')
        self.assertEquals(result, (223344, 6, 25))
