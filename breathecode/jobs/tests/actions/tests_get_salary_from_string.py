"""
Tasks tests
"""
from unittest.mock import patch, call
from ...actions import get_salary_from_string
from ..mixins import JobsTestCase


class ActionGetSalaryFromStringTestCase(JobsTestCase):
    """Tests action certificate_screenshot"""
    def test_get_salary_from_string_is_Empty(self):
        """Test /run_spider without spider"""
        result = get_salary_from_string('')
        self.assertEquals(result, None)
