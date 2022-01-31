"""
Tasks tests
"""
from unittest.mock import patch, call
from ...actions import get_date_from_string
from ..mixins import JobsTestCase


class ActionGetDateFromStringTestCase(JobsTestCase):
    """Tests action certificate_screenshot"""
    def test_get_date_from_string_is_Empty(self):
        """Test /run_spider without spider"""
        result = get_date_from_string('')
        self.assertEquals(result, None)
