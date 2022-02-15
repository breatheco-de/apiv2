"""
Tasks tests
"""
from unittest.mock import patch, call
from ...actions import get_job_id_from_string
from ..mixins import JobsTestCase


class ActionGetDateFromStringTestCase(JobsTestCase):
    """Tests action certificate_screenshot"""
    def test_get_job_id_from_string_is_empty(self):
        """Test /run_spider without spider"""
        result = get_job_id_from_string('')
        self.assertEquals(result, None)

    def test_get_job_id_from_string_with_id(self):
        """Test /run_spider without spider"""
        result = get_job_id_from_string('570286/2/71')
        self.assertEquals(result, ['570286', '2', '71'])
