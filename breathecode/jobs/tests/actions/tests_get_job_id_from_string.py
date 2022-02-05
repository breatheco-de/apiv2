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
