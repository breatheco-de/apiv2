"""
Action tests
"""
from unittest.mock import patch, call, MagicMock
from ...actions import save_data
from ..mixins import JobsTestCase
from breathecode.tests.mocks import (
    REQUESTS_PATH,
    apply_requests_post_mock,
)

JOBS = [{
    'Searched_job': 'junior web developer',
    'Job_title': 'Pentester Cybersecurity',
    'Location': 'Remote (Chile, Venezuela)',
    'Company_name': 'Repite Employer',
    'Post_date': 'November 05, 2021',
    'Extract_date': '2022-01-30',
    'Job_description': 'Vuln exploitation Security reports',
    'Salary': 'Not supplied',
    'Tags': ['back-end', 'cybersecurity', 'english', 'pentesting', 'python'],
    'Apply_to': 'https://www.url.com/1',
    '_type': 'dict'
}, {
    'Searched_job': 'junior web developer',
    'Job_title': 'Pentester Cybersecurity',
    'Location': 'Remote (Chile)',
    'Company_name': 'Repite Employer',
    'Post_date': 'November 05, 2021',
    'Extract_date': '2022-01-30',
    'Job_description': 'Vuln exploitation Security reports',
    'Salary': 'Not supplied',
    'Tags': ['back-end', 'cybersecurity', 'english', 'pentesting', 'python'],
    'Apply_to': 'https://www.url.com/2',
    '_type': 'dict'
}]

JOBS1 = [{
    'Searched_job': 'junior web developer',
    'Job_title': 'Pentester Cybersecurity',
    'Location': 'Remote (Chile, Venezuela)',
    'Company_name': 'Repite Employer',
    'Post_date': 'November 05, 2021',
    'Extract_date': '2022-01-30',
    'Job_description': 'Vuln exploitation Security reports',
    'Salary': 'Not supplied',
    'Tags': ['back-end', 'cybersecurity', 'english', 'pentesting', 'python'],
    'Apply_to': 'https://www.url.com/1',
    '_type': 'dict'
}, {
    'Searched_job': 'junior web developer',
    'Job_title': 'Pentester Cybersecurity',
    'Location': 'Remote (Chile)',
    'Company_name': 'Repite Employer',
    'Post_date': 'November 05, 2021',
    'Extract_date': '2022-01-30',
    'Job_description': 'Vuln exploitation Security reports',
    'Salary': 'Not supplied',
    'Tags': ['back-end', 'cybersecurity', 'english', 'pentesting', 'python'],
    'Apply_to': 'https://www.url.com/2',
    '_type': 'dict'
}, {
    'Searched_job': 'junior web developer',
    'Job_title': 'Pentester Cybersecurity',
    'Location': 'Remote (Peru)',
    'Company_name': 'Other Employer',
    'Post_date': 'November 05, 2021',
    'Extract_date': '2022-01-30',
    'Job_description': 'Vuln exploitation Security reports',
    'Salary': 'Not supplied',
    'Tags': ['back-end', 'cybersecurity', 'english', 'pentesting', 'python'],
    'Apply_to': 'https://www.url.com/3',
    '_type': 'dict'
}]

spider = {'name': 'getonboard', 'zyte_spider_number': 3, 'zyte_job_number': 0}
zyte_project = {'zyte_api_key': 1234567, 'zyte_api_deploy': 11223344}
platform = {'name': 'getonboard'}


class ActionNotSaveEmployerRepitedTestCase(JobsTestCase):
    @patch('breathecode.jobs.actions.save_data', MagicMock())
    def test_give_two_employer_repited(self):
        model = self.generate_models(spider=spider, zyte_project=zyte_project, platform=platform)

        result = save_data(model.spider, JOBS)
        employer = self.bc.database.list_of('jobs.Employer')

        self.assertEqual(employer, [{'id': 1, 'name': 'Repite Employer', 'location_id': 1}])
        self.assertEqual(len(employer), 1)

    @patch('breathecode.jobs.actions.save_data', MagicMock())
    def test_give_two_employer_repited_and_one_diferent(self):
        model = self.generate_models(spider=spider, zyte_project=zyte_project, platform=platform)

        result = save_data(model.spider, JOBS1)
        employer = self.bc.database.list_of('jobs.Employer')

        self.assertEqual(employer, [{
            'id': 1,
            'name': 'Repite Employer',
            'location_id': 1
        }, {
            'id': 2,
            'name': 'Other Employer',
            'location_id': 3
        }])

        self.assertEqual(len(employer), 2)
