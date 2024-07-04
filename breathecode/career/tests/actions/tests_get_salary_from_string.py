from unittest.mock import patch, call
from breathecode.career.services.getonboard import GetonboardScraper
from breathecode.career.services.indeed import IndeedScraper
from ..mixins import CareerTestCase
from breathecode.tests.mocks import (
    REQUESTS_PATH,
    apply_requests_post_mock,
)


class ActionGetSalaryFromStringTestCase(CareerTestCase):

    def test_get_salary_from_string__with_salary_month(self):
        platform = "getonboard"
        salary = "$2700 - 3700 USD/month"
        result = GetonboardScraper.get_salary_from_string(salary)
        (min_salary, max_salary, salary_str) = result
        self.assertEqual(min_salary, 32400)
        self.assertEqual(max_salary, 44400)
        self.assertEqual(salary_str, "$32400.0 - $44400.0 a year.")

    def test_get_salary_from_string__with_salary_is_null(self):
        platform = "getonboard"
        salary = None
        result = GetonboardScraper.get_salary_from_string(salary)
        (min_salary, max_salary, salary_str) = result
        self.assertEqual(min_salary, 0)
        self.assertEqual(max_salary, 0)
        self.assertEqual(salary_str, "Not supplied")

    def test_get_salary_from_string__with_salary_and_platform_is_other(self):
        platform = "indeed"
        salary = "$32400.0 - $44400.0 a year."
        result = IndeedScraper.get_salary_from_string(salary)
        (min_salary, max_salary, salary_str) = result
        self.assertEqual(min_salary, 32400)
        self.assertEqual(max_salary, 44400)
        self.assertEqual(salary_str, "$32400.0 - $44400.0 a year.")

    def test_get_salary_from_string_is_null_and_platform_is_other(self):
        platform = "indeed"
        salary = None
        result = IndeedScraper.get_salary_from_string(salary)
        (min_salary, max_salary, salary_str) = result
        self.assertEqual(min_salary, 0)
        self.assertEqual(max_salary, 0)
        self.assertEqual(salary_str, "Not supplied")

    def test_get_salary_from_string__with_only_salary(self):
        platform = "getonboard"
        salary = "$2700 USD/month"
        result = GetonboardScraper.get_salary_from_string(salary)
        (min_salary, max_salary, salary_str) = result
        self.assertEqual(min_salary, 32400)
        self.assertEqual(max_salary, 0.0)
        self.assertEqual(salary_str, "$32400.0 - $0.0 a year.")

    def test_get_salary_from_string__with_salary_bad_format(self):
        platform = "getonboard"
        salary = "$2700 - K3700 USD/month"
        result = GetonboardScraper.get_salary_from_string(salary)
        (min_salary, max_salary, salary_str) = result
        self.assertEqual(min_salary, 32400)
        self.assertEqual(max_salary, 44400)
        self.assertEqual(salary_str, "$32400.0 - $44400.0 a year.")
