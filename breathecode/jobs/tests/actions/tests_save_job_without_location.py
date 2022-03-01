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
    'Location': None,
    'Company_name': 'Employer',
    'Post_date': 'November 05, 2021',
    'Extract_date': '2022-01-30',
    'Job_description': 'Vuln exploitation Security reports',
    'Salary': 'Not supplied',
    'Tags': ['back-end', 'cybersecurity', 'english', 'pentesting', 'python'],
    'Apply_to': 'https://www.url.com/1',
    '_type': 'dict'
}]

JOBS1 = [{
    'Searched_job': 'junior web developer',
    'Job_title': 'Pentester Cybersecurity',
    'Location': None,
    'Company_name': 'Employer',
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
    'Location': 'Santiago',
    'Company_name': 'Employer 2',
    'Post_date': 'November 05, 2021',
    'Extract_date': '2022-01-30',
    'Job_description': 'Vuln exploitation Security reports',
    'Salary': 'Not supplied',
    'Tags': ['back-end', 'cybersecurity', 'english', 'pentesting', 'python'],
    'Apply_to': 'https://www.url.com/2',
    '_type': 'dict'
}]

spider = {'name': 'getonboard', 'zyte_spider_number': 3, 'zyte_job_number': 0}
zyte_project = {'zyte_api_key': 1234567, 'zyte_api_deploy': 11223344}
platform = {'name': 'getonboard'}


class ActionSaveJobWithoutLocationTestCase(JobsTestCase):
    @patch('breathecode.jobs.actions.save_data', MagicMock())
    def test_save_one_job_without_location_and_return_remote_true(self):
        model = self.bc.database.create(spider=spider, zyte_project=zyte_project, platform=platform)

        result = save_data(model.spider, JOBS)
        location = self.bc.database.list_of('jobs.Location')
        job = self.bc.database.list_of('jobs.Job')

        self.assertEqual(location, [])
        self.assertEqual(job.pop()['remote'], True)

    @patch('breathecode.jobs.actions.save_data', MagicMock())
    def test_save_two_job_with_location_and_without_location(self):
        model = self.bc.database.create(spider=spider, zyte_project=zyte_project, platform=platform)

        result = save_data(model.spider, JOBS1)
        location = self.bc.database.list_of('jobs.Location')
        job = self.bc.database.list_of('jobs.Job')

        self.assertEqual(location, [{'id': 1, 'name': 'Santiago'}])
        self.assertEqual(len(location), 1)
        self.assertEqual(job, [{
            'id': 1,
            'title': 'Pentester Cybersecurity',
            'published_date_raw': 'November 05, 2021',
            'published_date_processed': None,
            'status': 'OPENED',
            'apply_url': 'https://www.url.com/1',
            'currency': 'USD',
            'min_salary': 0.0,
            'max_salary': 0.0,
            'salary': 'Not supplied',
            'spider_id': 1,
            'job_type': 'Full-time',
            'remote': True,
            'employer_id': 1,
            'position_id': 2
        }, {
            'id': 2,
            'title': 'Pentester Cybersecurity',
            'published_date_raw': 'November 05, 2021',
            'published_date_processed': None,
            'status': 'OPENED',
            'apply_url': 'https://www.url.com/2',
            'currency': 'USD',
            'min_salary': 0.0,
            'max_salary': 0.0,
            'salary': 'Not supplied',
            'spider_id': 1,
            'job_type': 'Full-time',
            'remote': False,
            'employer_id': 2,
            'position_id': 2
        }])
        self.assertEqual(len(job), 2)
