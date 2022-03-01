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
    'Salary': '$1800 - 2000 USD/month',
    'Tags': ['back-end', 'cybersecurity', 'english', 'pentesting', 'python'],
    'Apply_to': 'https://www.url.com/1',
    '_type': 'dict'
}, {
    'Searched_job': 'junior web developer',
    'Job_title': 'Pentester Cybersecurity',
    'Location': 'Chile',
    'Company_name': 'Employer',
    'Post_date': 'today',
    'Extract_date': '2022-01-30',
    'Job_description': 'Other job',
    'Salary': '$1800 - 2000 USD/month',
    'Tags': ['back-end'],
    'Apply_to': 'https://www.url.com/2',
    '_type': 'dict'
}]

JOBS1 = [{
    'Searched_job': 'junior web developer',
    'Job_title': 'Pentester Cybersecurity',
    'Location': 'Remote (Chile, Venezuela)',
    'Company_name': 'Repite Employer',
    'Post_date': 'today',
    'Extract_date': '2022-01-30',
    'Job_description': 'Vuln exploitation Security reports',
    'Salary': 'Not supplied',
    'Tags': ['back-end', 'cybersecurity', 'english', 'pentesting', 'python'],
    'Apply_to': 'https://www.url.com/1',
    '_type': 'dict'
}, {
    'Searched_job': 'junior web developer',
    'Job_title': 'Python',
    'Location': 'Chile',
    'Company_name': 'Employer 2',
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
    'Location': 'Venezuela',
    'Company_name': 'Repite Employer',
    'Post_date': 'November 05, 2021',
    'Extract_date': '2022-01-30',
    'Job_description': 'Vuln exploitation Security reports',
    'Salary': 'Not supplied',
    'Tags': ['back-end', 'cybersecurity', 'english', 'pentesting', 'python'],
    'Apply_to': 'https://www.url.com/3',
    '_type': 'dict'
}]

JOBS2 = [{
    'Searched_job': 'junior web developer',
    'Job_title': 'Pentester Cybersecurity',
    'Location': 'Remote (Chile, Venezuela)',
    'Company_name': 'Employer',
    'Post_date': 'today',
    'Extract_date': '2022-01-30',
    'Job_description': 'Vuln exploitation Security reports',
    'currency': 'USD',
    'Salary': 'Not supplied',
    'Tags': ['back-end', 'cybersecurity', 'english', 'pentesting', 'python'],
    'Apply_to': 'https://www.url.com/1',
    '_type': 'dict'
}, {
    'Searched_job': 'junior web developer',
    'Job_title': 'Pentester Cybersecurity',
    'Location': 'Chile',
    'Company_name': 'Other Employer',
    'Post_date': 'November 05, 2021',
    'Extract_date': '2022-01-30',
    'Job_description': 'Vuln exploitation Security reports',
    'currency': 'USD',
    'Salary': 'Not supplied',
    'Tags': ['back-end', 'cybersecurity', 'english', 'pentesting', 'python'],
    'Apply_to': 'https://www.url.com/2',
    '_type': 'dict'
}]

JOBS3 = [{
    'Searched_job': 'junior web developer',
    'Job_title': 'Pentester Cybersecurity',
    'Location': 'Remote (Chile, Venezuela)',
    'Company_name': 'Employer',
    'Post_date': 'today',
    'Extract_date': '2022-01-30',
    'Job_description': 'Vuln exploitation Security reports',
    'currency': 'USD',
    'Salary': 'Not supplied',
    'Tags': ['back-end', 'cybersecurity', 'english', 'pentesting', 'python'],
    'Apply_to': 'https://www.url.com/1',
    '_type': 'dict'
}, {
    'Searched_job': 'junior web developer',
    'Job_title': 'Python',
    'Location': 'Chile',
    'Company_name': 'Employer',
    'Post_date': 'November 05, 2021',
    'Extract_date': '2022-01-30',
    'Job_description': 'Vuln exploitation Security reports',
    'currency': 'USD',
    'Salary': 'Not supplied',
    'Tags': ['back-end', 'cybersecurity', 'english', 'pentesting', 'python'],
    'Apply_to': 'https://www.url.com/2',
    '_type': 'dict'
}]

spider = {'name': 'indeed', 'zyte_spider_number': 2, 'zyte_job_number': 0}
zyte_project = {'zyte_api_key': 1234567, 'zyte_api_deploy': 11223344}
platform = {'name': 'indeed'}


class ActionNotSaveJobRepitedTestCase(JobsTestCase):
    @patch('breathecode.jobs.actions.save_data', MagicMock())
    def test_give_two_jobs_repited_save_one(self):
        model = self.bc.database.create(spider=spider, zyte_project=zyte_project, platform=platform)

        result = save_data(model.spider, JOBS)
        job = self.bc.database.list_of('jobs.Job')

        self.assertEqual(job, [{
            'id': 1,
            'title': 'Pentester Cybersecurity',
            'published_date_raw': 'November 05, 2021',
            'published_date_processed': None,
            'status': 'OPENED',
            'apply_url': 'https://www.url.com/1',
            'currency': 'USD',
            'min_salary': 1800.0,
            'max_salary': 2000.0,
            'salary': '$1800.0 - $2000.0 a year.',
            'spider_id': 1,
            'job_type': 'Full-time',
            'remote': True,
            'employer_id': 1,
            'position_id': 2
        }])
        self.assertEqual(len(job), 1)

    @patch('breathecode.jobs.actions.save_data', MagicMock())
    def test_give_two_jobs_repited_and_one_diferen(self):
        model = self.bc.database.create(spider=spider, zyte_project=zyte_project, platform=platform)

        result = save_data(model.spider, JOBS1)
        job = self.bc.database.list_of('jobs.Job')

        self.assertEqual(job, [{
            'id': 1,
            'title': 'Pentester Cybersecurity',
            'published_date_raw': 'today',
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
            'title': 'Python',
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

    @patch('breathecode.jobs.actions.save_data', MagicMock())
    def test_save_jobs_with_same_title_and_diferent_employer(self):
        model = self.bc.database.create(spider=spider, zyte_project=zyte_project, platform=platform)

        result = save_data(model.spider, JOBS2)
        job = self.bc.database.list_of('jobs.Job')

        self.assertEqual(job, [{
            'id': 1,
            'title': 'Pentester Cybersecurity',
            'published_date_raw': 'today',
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

    @patch('breathecode.jobs.actions.save_data', MagicMock())
    def test_save_jobs_with_same_employer_and_diferent_title(self):
        model = self.bc.database.create(spider=spider, zyte_project=zyte_project, platform=platform)

        result = save_data(model.spider, JOBS3)
        job = self.bc.database.list_of('jobs.Job')

        self.assertEqual(job, [{
            'id': 1,
            'title': 'Pentester Cybersecurity',
            'published_date_raw': 'today',
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
            'title': 'Python',
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
            'employer_id': 1,
            'position_id': 2
        }])
        self.assertEqual(len(job), 2)
