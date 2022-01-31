"""
Tasks tests
"""
from unittest.mock import patch, call
from ...actions import get_salary_format
from ..mixins import JobsTestCase
from breathecode.tests.mocks import (
    REQUESTS_PATH,
    apply_requests_post_mock,
)


class ActionGetSalaryFormatTestCase(JobsTestCase):
    def test_get_salary_format__with_salary_month(self):
        platform = 'getonboard'
        salary = '$2700 - 3700 USD/month'
        tags = ['PHP', 'GO', 'javascript']
        result = get_salary_format(platform, salary, tags)
        (min_salary, max_salary, salary_str, tags) = result
        self.assertEqual(min_salary, 32400)
        self.assertEqual(max_salary, 44400)
        self.assertEqual(salary_str, '$32400.0 - $44400.0 a year.')

    def test_get_salary_format__with_salary_is_null(self):
        platform = 'getonboard'
        salary = None
        tags = ['PHP', 'GO', 'javascript']
        result = get_salary_format(platform, salary, tags)
        (min_salary, max_salary, salary_str, tags) = result
        self.assertEqual(min_salary, 0)
        self.assertEqual(max_salary, 0)
        self.assertEqual(salary_str, 'Not supplied')

    def test_get_salary_format__with_salary_and_platform_is_other(self):
        platform = 'indeed'
        salary = '$32400.0 - $44400.0 a year.'
        tags = []
        result = get_salary_format(platform, salary, tags)
        (min_salary, max_salary, salary_str, tags) = result
        self.assertEqual(min_salary, 32400)
        self.assertEqual(max_salary, 44400)
        self.assertEqual(salary_str, '$32400.0 - $44400.0 a year.')

    def test_salary_with_salary_is_null_and_platform_is_other(self):
        platform = 'indeed'
        salary = None
        tags = []
        result = get_salary_format(platform, salary, tags)
        (min_salary, max_salary, salary_str, tags) = result
        self.assertEqual(min_salary, 0)
        self.assertEqual(max_salary, 0)
        self.assertEqual(salary_str, 'Not supplied')

    def test_get_salary_format__with_only_salary(self):
        platform = 'getonboard'
        salary = '$2700 USD/month'
        tags = ['PHP', 'GO', 'javascript']
        result = get_salary_format(platform, salary, tags)
        (min_salary, max_salary, salary_str, tags) = result
        self.assertEqual(min_salary, 32400)
        self.assertEqual(max_salary, 0.0)
        self.assertEqual(salary_str, '$32400.0 - $0.0 a year.')

    def test_get_salary_format__with_salary_bad_format(self):
        platform = 'getonboard'
        salary = '$2700 - K3700 USD/month'
        tags = ['PHP', 'GO', 'javascript']
        result = get_salary_format(platform, salary, tags)
        (min_salary, max_salary, salary_str, tags) = result
        self.assertEqual(min_salary, 32400)
        self.assertEqual(max_salary, 44400)
        self.assertEqual(salary_str, '$32400.0 - $44400.0 a year.')
