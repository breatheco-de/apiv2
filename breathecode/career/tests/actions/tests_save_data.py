from unittest.mock import patch, call, MagicMock
from ...actions import save_data
from ..mixins import CareerTestCase
from breathecode.tests.mocks import (
    REQUESTS_PATH,
    apply_requests_post_mock,
)

JOBS = [
    {
        "Searched_job": "junior web developer",
        "Job_title": "Desarrollador Full-Stack",
        "Location": "Santiago (temporarily remote)",
        "Company_name": "Centry",
        "Post_date": "January 19, 2022",
        "Extract_date": "2022-01-30",
        "Job_description": "Vuln exploitation Security reports",
        "Salary": "$1800 - 2100 USD/month",
        "Tags": ["api", "back-end", "full-stack", "git", "java", "mvc", "python", "ruby"],
        "Apply_to": "https://www.getonbrd.com/jobs/programming/desarrollador-full-stack-developer-centry-santiago",
        "_type": "dict",
    },
    {
        "Searched_job": "junior web developer",
        "Job_title": "Desarrollador Full-Stack Python/React",
        "Location": "Remote",
        "Company_name": "Alluxi",
        "Post_date": "January 14, 2022",
        "Extract_date": "2022-01-30",
        "Job_description": "Vuln exploitation Security reports",
        "Salary": "$1800 - 2000 USD/month",
        "Tags": [],
        "Apply_to": "https://www.getonbrd.com/jobs/programming/desarrollodor-fullstack-python-react-alluxi-remote",
        "_type": "dict",
    },
    {
        "Searched_job": "junior web developer",
        "Job_title": "Full-Stack Developer",
        "Location": "Santiago",
        "Company_name": "AAXIS Commerce",
        "Post_date": "January 17, 2022",
        "Extract_date": "2022-01-30",
        "Job_description": "Vuln exploitation Security reports",
        "Salary": "Not supplied",
        "Tags": [
            "angularjs",
            "back-end",
            "express",
            "front-end",
            "full-stack",
            "javascript",
            "magento",
            "mobile development",
            "node.js",
            "php",
            "react",
            "redis",
            "responsive",
            "symfony",
            "ui design",
        ],
        "Apply_to": "https://www.getonbrd.com/jobs/programming/full-stack-developer-aaxis-commerce-santiago-3c8e",
        "_type": "dict",
    },
    {
        "Searched_job": "junior web developer",
        "Job_title": "Pentester Cybersecurity",
        "Location": "Remote (Chile)",
        "Company_name": "Rule 1 Ventures",
        "Post_date": "November 05, 2021",
        "Extract_date": "2022-01-30",
        "Job_description": "Vuln exploitation Security reports",
        "Salary": "Not supplied",
        "Tags": ["back-end", "cybersecurity", "english", "pentesting", "python"],
        "Apply_to": "https://www.getonbrd.com/jobs/cybersecurity/security-engineer-rule-1-ventures-remote",
        "_type": "dict",
    },
    {
        "Searched_job": "junior web developer",
        "Job_title": "Pentester Cybersecurity",
        "Location": "Remote (Chile, Venezuela)",
        "Company_name": "Rule 1 Ventures",
        "Post_date": "November 05, 2021",
        "Extract_date": "2022-01-30",
        "Job_description": "Vuln exploitation Security reports",
        "Salary": "$1800 - 2000 a year",
        "Tags": ["back-end", "cybersecurity", "english", "pentesting", "python"],
        "Apply_to": "https://www.getonbrd.com/jobs/cybersecurity/security-engineer-rule-1-ventures-remote",
        "_type": "dict",
    },
    {
        "Searched_job": "junior web developer",
        "Job_title": "Front-end Developer",
        "Location": ".",
        "Company_name": "ID Business Intelligence",
        "Post_date": "January 24, 2022",
        "Extract_date": "2022-01-30",
        "Job_description": "Vuln exploitation Security reports",
        "Salary": "$1800 - k2000 per year",
        "Tags": ["api", "css", "front-end", "git", "javascript", "react"],
        "Apply_to": "https://www.getonbrd.com/jobs/programming/fronted-developer-id-business-intelligence-remote",
        "_type": "dict",
    },
    {
        "Searched_job": "junior web developer",
        "Job_title": "Junior Web Developer",
        "Location": None,
        "Company_name": "Reign",
        "Post_date": "January 29, 2022",
        "Extract_date": "2022-01-30",
        "Job_description": "Vuln exploitation Security reports",
        "Salary": "18000 USD/month",
        "Tags": [
            "angularjs",
            "api",
            "back-end",
            "ci/cd",
            "css",
            "docker",
            "front-end",
            "html5",
            "javascript",
            "json",
            "mongodb",
            "node.js",
            "nosql",
            "postgresql",
            "react",
            "responsive",
            "ui design",
            "virtualization",
        ],
        "Apply_to": "https://www.getonbrd.com/jobs/programming/junior-web-developer-reign-remote",
        "_type": "dict",
    },
]

JOBS1 = [
    {
        "Searched_job": "junior web developer",
        "Job_title": "Pentester Cybersecurity",
        "Location": "Remote (Chile, Venezuela)",
        "Company_name": "Repite Employer",
        "Post_date": "November 05, 2021",
        "Extract_date": "2022-01-30",
        "Job_description": "Vuln exploitation Security reports",
        "Salary": "Not supplied",
        "Tags": ["back-end", "cybersecurity", "english", "pentesting", "python"],
        "Apply_to": "https://www.url.com/1",
        "_type": "dict",
    },
    {
        "Searched_job": "junior web developer",
        "Job_title": "Pentester Cybersecurity",
        "Location": "Remote (Chile)",
        "Company_name": "Repite Employer",
        "Post_date": "November 05, 2021",
        "Extract_date": "2022-01-30",
        "Job_description": "Vuln exploitation Security reports",
        "Salary": "Not supplied",
        "Tags": ["back-end", "cybersecurity", "english", "pentesting", "python"],
        "Apply_to": "https://www.url.com/2",
        "_type": "dict",
    },
    {
        "Searched_job": "junior web developer",
        "Job_title": "Pentester Cybersecurity",
        "Location": "Remote (Peru, Colombia)",
        "Company_name": "Other Employer",
        "Post_date": "November 05, 2021",
        "Extract_date": "2022-01-30",
        "Job_description": "Vuln exploitation Security reports",
        "Salary": "Not supplied",
        "Tags": ["back-end", "cybersecurity", "english", "pentesting", "python"],
        "Apply_to": "https://www.url.com/3",
        "_type": "dict",
    },
]

JOBS2 = [
    {
        "Searched_job": "junior web developer",
        "Job_title": "Pentester Cybersecurity",
        "Location": "Remote (Chile, Venezuela)",
        "Company_name": "Repite Employer",
        "Post_date": "November 05, 2021",
        "Extract_date": "2022-01-30",
        "Job_description": "Vuln exploitation Security reports",
        "Salary": "Not supplied",
        "Tags": ["back-end", "cybersecurity", "english", "pentesting", "python"],
        "Apply_to": "https://www.url.com/1",
        "_type": "dict",
    },
    {
        "Searched_job": "junior web developer",
        "Job_title": "Pentester Cybersecurity",
        "Location": "Remote (Chile)",
        "Company_name": "Repite Employer",
        "Post_date": "November 05, 2021",
        "Extract_date": "2022-01-30",
        "Job_description": "Vuln exploitation Security reports",
        "Salary": "Not supplied",
        "Tags": ["back-end", "cybersecurity", "english", "pentesting", "python"],
        "Apply_to": "https://www.url.com/2",
        "_type": "dict",
    },
]

JOBS3 = [
    {
        "Searched_job": "junior web developer",
        "Job_title": "Pentester Cybersecurity",
        "Location": None,
        "Company_name": "Employer",
        "Post_date": "November 05, 2021",
        "Extract_date": "2022-01-30",
        "Job_description": "Vuln exploitation Security reports",
        "Salary": "$1800 - 2000 USD/month",
        "Tags": ["back-end", "cybersecurity", "english", "pentesting", "python"],
        "Apply_to": "https://www.url.com/1",
        "_type": "dict",
    },
    {
        "Searched_job": "junior web developer",
        "Job_title": "Pentester Cybersecurity",
        "Location": "Chile",
        "Company_name": "Employer",
        "Post_date": "today",
        "Extract_date": "2022-01-30",
        "Job_description": "Vuln exploitation Security reports",
        "Salary": "$1800 - 2000 USD/month",
        "Tags": ["back-end"],
        "Apply_to": "https://www.url.com/2",
        "_type": "dict",
    },
]

JOBS4 = [
    {
        "Searched_job": "junior web developer",
        "Job_title": "Pentester Cybersecurity",
        "Location": "Remote (Chile, Venezuela)",
        "Company_name": "Repite Employer",
        "Post_date": "today",
        "Extract_date": "2022-01-30",
        "Job_description": "Vuln exploitation Security reports",
        "Salary": "Not supplied",
        "Tags": ["back-end", "cybersecurity", "english", "pentesting", "python"],
        "Apply_to": "https://www.url.com/1",
        "_type": "dict",
    },
    {
        "Searched_job": "junior web developer",
        "Job_title": "Python",
        "Location": "Chile",
        "Company_name": "Employer 2",
        "Post_date": "November 05, 2021",
        "Extract_date": "2022-01-30",
        "Job_description": "Vuln exploitation Security reports",
        "Salary": "Not supplied",
        "Tags": ["back-end", "cybersecurity", "english", "pentesting", "python"],
        "Apply_to": "https://www.url.com/2",
        "_type": "dict",
    },
    {
        "Searched_job": "junior web developer",
        "Job_title": "Pentester Cybersecurity",
        "Location": "Venezuela",
        "Company_name": "Repite Employer",
        "Post_date": "November 05, 2021",
        "Extract_date": "2022-01-30",
        "Job_description": "Vuln exploitation Security reports",
        "Salary": "Not supplied",
        "Tags": ["back-end", "cybersecurity", "english", "pentesting", "python"],
        "Apply_to": "https://www.url.com/3",
        "_type": "dict",
    },
]

JOBS5 = [
    {
        "Searched_job": "junior web developer",
        "Job_title": "Pentester Cybersecurity",
        "Location": "Remote (Chile, Venezuela)",
        "Company_name": "Employer",
        "Post_date": "today",
        "Extract_date": "2022-01-30",
        "Job_description": "Vuln exploitation Security reports",
        "currency": "USD",
        "Salary": "Not supplied",
        "Tags": ["back-end", "cybersecurity", "english", "pentesting", "python"],
        "Apply_to": "https://www.url.com/1",
        "_type": "dict",
    },
    {
        "Searched_job": "junior web developer",
        "Job_title": "Pentester Cybersecurity",
        "Location": "Chile",
        "Company_name": "Other Employer",
        "Post_date": "November 05, 2021",
        "Extract_date": "2022-01-30",
        "Job_description": "Vuln exploitation Security reports",
        "currency": "USD",
        "Salary": "Not supplied",
        "Tags": ["back-end", "cybersecurity", "english", "pentesting", "python"],
        "Apply_to": "https://www.url.com/2",
        "_type": "dict",
    },
]

JOBS6 = [
    {
        "Searched_job": "junior web developer",
        "Job_title": "Pentester Cybersecurity",
        "Location": "Remote (Chile, Venezuela)",
        "Company_name": "Employer",
        "Post_date": "today",
        "Extract_date": "2022-01-30",
        "Job_description": "Vuln exploitation Security reports",
        "currency": "USD",
        "Salary": "Not supplied",
        "Tags": ["back-end", "cybersecurity", "english", "pentesting", "python"],
        "Apply_to": "https://www.url.com/1",
        "_type": "dict",
    },
    {
        "Searched_job": "junior web developer",
        "Job_title": "Python",
        "Location": "Chile",
        "Company_name": "Employer",
        "Post_date": "November 05, 2021",
        "Extract_date": "2022-01-30",
        "Job_description": "Vuln exploitation Security reports",
        "currency": "USD",
        "Salary": "Not supplied",
        "Tags": ["back-end", "cybersecurity", "english", "pentesting", "python"],
        "Apply_to": "https://www.url.com/2",
        "_type": "dict",
    },
]

JOBS7 = [
    {
        "Searched_job": "junior web developer",
        "Job_title": "Pentester Cybersecurity",
        "Location": "Remote (Chile)",
        "Company_name": "Employer",
        "Post_date": "November 05, 2021",
        "Extract_date": "2022-01-30",
        "Job_description": "Vuln exploitation Security reports",
        "Salary": "Not supplied",
        "Tags": ["back-end", "cybersecurity", "english", "pentesting", "python"],
        "Apply_to": "https://www.url.com/1",
        "_type": "dict",
    },
    {
        "Searched_job": "junior web developer",
        "Job_title": "Pentester Cybersecurity",
        "Location": "Chile",
        "Company_name": "Employer 1",
        "Post_date": "today",
        "Extract_date": "2022-01-30",
        "Job_description": "Vuln exploitation Security reports",
        "Salary": "Not supplied",
        "Tags": ["back-end", "cybersecurity", "english", "pentesting", "python"],
        "Apply_to": "https://www.url.com/2",
        "_type": "dict",
    },
]

JOBS8 = [
    {
        "Searched_job": "junior web developer",
        "Job_title": "Pentester Cybersecurity",
        "Location": "Remote (Chile, Venezuela)",
        "Company_name": "Employer 2",
        "Post_date": "today",
        "Extract_date": "2022-01-30",
        "Job_description": "Vuln exploitation Security reports",
        "Salary": "Not supplied",
        "Tags": ["back-end", "cybersecurity", "english", "pentesting", "python"],
        "Apply_to": "https://www.url.com/1",
        "_type": "dict",
    },
    {
        "Searched_job": "junior web developer",
        "Job_title": "Pentester Cybersecurity",
        "Location": "Chile",
        "Company_name": "Repite Employer",
        "Post_date": "November 05, 2021",
        "Extract_date": "2022-01-30",
        "Job_description": "Vuln exploitation Security reports",
        "Salary": "Not supplied",
        "Tags": ["back-end", "cybersecurity", "english", "pentesting", "python"],
        "Apply_to": "https://www.url.com/2",
        "_type": "dict",
    },
    {
        "Searched_job": "junior web developer",
        "Job_title": "Pentester Cybersecurity",
        "Location": "Venezuela",
        "Company_name": "Other Employer",
        "Post_date": "November 05, 2021",
        "Extract_date": "2022-01-30",
        "Job_description": "Vuln exploitation Security reports",
        "Salary": "Not supplied",
        "Tags": ["back-end", "cybersecurity", "english", "pentesting", "python"],
        "Apply_to": "https://www.url.com/3",
        "_type": "dict",
    },
]

JOBS9 = [
    {
        "Searched_job": "junior web developer",
        "Job_title": "Pentester Cybersecurity",
        "Location": None,
        "Company_name": "Employer",
        "Post_date": "November 05, 2021",
        "Extract_date": "2022-01-30",
        "Job_description": "Vuln exploitation Security reports",
        "Salary": "Not supplied",
        "Tags": ["back-end", "cybersecurity", "english", "pentesting", "python"],
        "Apply_to": "https://www.url.com/1",
        "_type": "dict",
    }
]

JOBS10 = [
    {
        "Searched_job": "junior web developer",
        "Job_title": "Pentester Cybersecurity",
        "Location": None,
        "Company_name": "Employer",
        "Post_date": "November 05, 2021",
        "Extract_date": "2022-01-30",
        "Job_description": "Vuln exploitation Security reports",
        "Salary": "Not supplied",
        "Tags": ["back-end", "cybersecurity", "english", "pentesting", "python"],
        "Apply_to": "https://www.url.com/1",
        "_type": "dict",
    },
    {
        "Searched_job": "junior web developer",
        "Job_title": "Pentester Cybersecurity",
        "Location": "Santiago",
        "Company_name": "Employer 2",
        "Post_date": "November 05, 2021",
        "Extract_date": "2022-01-30",
        "Job_description": "Vuln exploitation Security reports",
        "Salary": "Not supplied",
        "Tags": ["back-end", "cybersecurity", "english", "pentesting", "python"],
        "Apply_to": "https://www.url.com/2",
        "_type": "dict",
    },
]


class ActionSaveDataTestCase(CareerTestCase):

    def test_save_data__with_spider(self):
        spider = {"name": "getonboard", "zyte_spider_number": 3, "zyte_job_number": 0}
        zyte_project = {"zyte_api_key": 1234567, "zyte_api_deploy": 11223344}
        platform = {"name": "getonboard"}

        model = self.bc.database.create(spider=spider, zyte_project=zyte_project, platform=platform)

        result = save_data(model.spider, JOBS)

        self.assertEqual(
            self.bc.database.list_of("career.Job"),
            [
                {
                    "id": 1,
                    "title": "Desarrollador Full-Stack",
                    "spider_id": 1,
                    "published_date_raw": "January 19, 2022",
                    "published_date_processed": None,
                    "status": "OPENED",
                    "apply_url": "https://www.getonbrd.com/jobs/programming/desarrollador-full-stack-developer-centry-santiago",
                    "currency": "USD",
                    "min_salary": 21600.0,
                    "max_salary": 25200.0,
                    "salary": "$21600.0 - $25200.0 a year.",
                    "job_description": "Vuln exploitation Security reports",
                    "job_type": "Full-time",
                    "remote": True,
                    "employer_id": 1,
                    "position_id": 2,
                },
                {
                    "id": 2,
                    "title": "Desarrollador Full-Stack Python/React",
                    "spider_id": 1,
                    "published_date_raw": "January 14, 2022",
                    "published_date_processed": None,
                    "status": "OPENED",
                    "apply_url": "https://www.getonbrd.com/jobs/programming/desarrollodor-fullstack-python-react-alluxi-remote",
                    "currency": "USD",
                    "min_salary": 21600.0,
                    "max_salary": 24000.0,
                    "salary": "$21600.0 - $24000.0 a year.",
                    "job_description": "Vuln exploitation Security reports",
                    "job_type": "Full-time",
                    "remote": True,
                    "employer_id": 2,
                    "position_id": 2,
                },
                {
                    "id": 3,
                    "title": "Full-Stack Developer",
                    "spider_id": 1,
                    "published_date_raw": "January 17, 2022",
                    "published_date_processed": None,
                    "status": "OPENED",
                    "apply_url": "https://www.getonbrd.com/jobs/programming/full-stack-developer-aaxis-commerce-santiago-3c8e",
                    "currency": "USD",
                    "min_salary": 0.0,
                    "max_salary": 0.0,
                    "salary": "Not supplied",
                    "job_description": "Vuln exploitation Security reports",
                    "job_type": "Full-time",
                    "remote": False,
                    "employer_id": 3,
                    "position_id": 2,
                },
                {
                    "id": 4,
                    "title": "Pentester Cybersecurity",
                    "spider_id": 1,
                    "published_date_raw": "November 05, 2021",
                    "published_date_processed": None,
                    "status": "OPENED",
                    "apply_url": "https://www.getonbrd.com/jobs/cybersecurity/security-engineer-rule-1-ventures-remote",
                    "currency": "USD",
                    "min_salary": 0.0,
                    "max_salary": 0.0,
                    "salary": "Not supplied",
                    "job_description": "Vuln exploitation Security reports",
                    "job_type": "Full-time",
                    "remote": True,
                    "employer_id": 4,
                    "position_id": 2,
                },
                {
                    "id": 5,
                    "title": "Front-end Developer",
                    "spider_id": 1,
                    "published_date_raw": "January 24, 2022",
                    "published_date_processed": None,
                    "status": "OPENED",
                    "apply_url": "https://www.getonbrd.com/jobs/programming/fronted-developer-id-business-intelligence-remote",
                    "currency": "USD",
                    "min_salary": 0.0,
                    "max_salary": 0.0,
                    "salary": "Not supplied",
                    "job_description": "Vuln exploitation Security reports",
                    "job_type": "Full-time",
                    "remote": True,
                    "employer_id": 5,
                    "position_id": 2,
                },
                {
                    "id": 6,
                    "title": "Junior Web Developer",
                    "spider_id": 1,
                    "published_date_raw": "January 29, 2022",
                    "published_date_processed": None,
                    "status": "OPENED",
                    "apply_url": "https://www.getonbrd.com/jobs/programming/junior-web-developer-reign-remote",
                    "currency": "USD",
                    "min_salary": 216000.0,
                    "max_salary": 0.0,
                    "salary": "$216000.0 - $0.0 a year.",
                    "job_description": "Vuln exploitation Security reports",
                    "job_type": "Full-time",
                    "remote": True,
                    "employer_id": 6,
                    "position_id": 2,
                },
            ],
        )
        self.assertEqual(result, 6)

    def test_give_two_employer_repited(self):
        spider = {"name": "getonboard", "zyte_spider_number": 3, "zyte_job_number": 0}
        zyte_project = {"zyte_api_key": 1234567, "zyte_api_deploy": 11223344}
        platform = {"name": "getonboard"}

        model = self.bc.database.create(spider=spider, zyte_project=zyte_project, platform=platform)

        result = save_data(model.spider, JOBS2)
        employer = self.bc.database.list_of("career.Employer")

        self.assertEqual(employer, [{"id": 1, "name": "Repite Employer", "location_id": 1}])
        self.assertEqual(len(employer), 1)

    def test_give_two_employer_repited_and_one_diferent(self):
        spider = {"name": "getonboard", "zyte_spider_number": 3, "zyte_job_number": 0}
        zyte_project = {"zyte_api_key": 1234567, "zyte_api_deploy": 11223344}
        platform = {"name": "getonboard"}

        model = self.bc.database.create(spider=spider, zyte_project=zyte_project, platform=platform)

        result = save_data(model.spider, JOBS1)
        employer = self.bc.database.list_of("career.Employer")
        self.assertEqual(
            employer,
            [
                {"id": 1, "name": "Repite Employer", "location_id": 1},
                {"id": 2, "name": "Other Employer", "location_id": 3},
            ],
        )

        self.assertEqual(len(employer), 2)

    def test_give_two_jobs_repited_save_one(self):
        spider = {"name": "indeed", "zyte_spider_number": 2, "zyte_job_number": 0}
        zyte_project = {"zyte_api_key": 1234567, "zyte_api_deploy": 11223344}
        platform = {"name": "indeed"}

        model = self.bc.database.create(spider=spider, zyte_project=zyte_project, platform=platform)

        result = save_data(model.spider, JOBS3)
        job = self.bc.database.list_of("career.Job")

        self.assertEqual(
            job,
            [
                {
                    "id": 1,
                    "title": "Pentester Cybersecurity",
                    "published_date_raw": "November 05, 2021",
                    "published_date_processed": None,
                    "status": "OPENED",
                    "apply_url": "https://www.url.com/1",
                    "currency": "USD",
                    "min_salary": 1800.0,
                    "max_salary": 2000.0,
                    "salary": "$1800.0 - $2000.0 a year.",
                    "job_description": "Vuln exploitation Security reports",
                    "spider_id": 1,
                    "job_type": "Full-time",
                    "remote": True,
                    "employer_id": 1,
                    "position_id": 2,
                }
            ],
        )
        self.assertEqual(len(job), 1)

    def test_give_two_jobs_repited_and_one_diferen(self):
        spider = {"name": "indeed", "zyte_spider_number": 2, "zyte_job_number": 0}
        zyte_project = {"zyte_api_key": 1234567, "zyte_api_deploy": 11223344}
        platform = {"name": "indeed"}

        model = self.bc.database.create(spider=spider, zyte_project=zyte_project, platform=platform)

        result = save_data(model.spider, JOBS4)
        job = self.bc.database.list_of("career.Job")

        self.assertEqual(
            job,
            [
                {
                    "id": 1,
                    "title": "Pentester Cybersecurity",
                    "published_date_raw": "today",
                    "published_date_processed": None,
                    "status": "OPENED",
                    "apply_url": "https://www.url.com/1",
                    "currency": "USD",
                    "min_salary": 0.0,
                    "max_salary": 0.0,
                    "salary": "Not supplied",
                    "job_description": "Vuln exploitation Security reports",
                    "spider_id": 1,
                    "job_type": "Full-time",
                    "remote": True,
                    "employer_id": 1,
                    "position_id": 2,
                },
                {
                    "id": 2,
                    "title": "Python",
                    "published_date_raw": "November 05, 2021",
                    "published_date_processed": None,
                    "status": "OPENED",
                    "apply_url": "https://www.url.com/2",
                    "currency": "USD",
                    "min_salary": 0.0,
                    "max_salary": 0.0,
                    "salary": "Not supplied",
                    "job_description": "Vuln exploitation Security reports",
                    "spider_id": 1,
                    "job_type": "Full-time",
                    "remote": False,
                    "employer_id": 2,
                    "position_id": 2,
                },
            ],
        )
        self.assertEqual(len(job), 2)

    def test_save_jobs_with_same_title_and_diferent_employer(self):
        spider = {"name": "indeed", "zyte_spider_number": 2, "zyte_job_number": 0}
        zyte_project = {"zyte_api_key": 1234567, "zyte_api_deploy": 11223344}
        platform = {"name": "indeed"}

        model = self.bc.database.create(spider=spider, zyte_project=zyte_project, platform=platform)

        result = save_data(model.spider, JOBS5)
        job = self.bc.database.list_of("career.Job")

        self.assertEqual(
            job,
            [
                {
                    "id": 1,
                    "title": "Pentester Cybersecurity",
                    "published_date_raw": "today",
                    "published_date_processed": None,
                    "status": "OPENED",
                    "apply_url": "https://www.url.com/1",
                    "currency": "USD",
                    "min_salary": 0.0,
                    "max_salary": 0.0,
                    "salary": "Not supplied",
                    "job_description": "Vuln exploitation Security reports",
                    "spider_id": 1,
                    "job_type": "Full-time",
                    "remote": True,
                    "employer_id": 1,
                    "position_id": 2,
                },
                {
                    "id": 2,
                    "title": "Pentester Cybersecurity",
                    "published_date_raw": "November 05, 2021",
                    "published_date_processed": None,
                    "status": "OPENED",
                    "apply_url": "https://www.url.com/2",
                    "currency": "USD",
                    "min_salary": 0.0,
                    "max_salary": 0.0,
                    "salary": "Not supplied",
                    "job_description": "Vuln exploitation Security reports",
                    "spider_id": 1,
                    "job_type": "Full-time",
                    "remote": False,
                    "employer_id": 2,
                    "position_id": 2,
                },
            ],
        )
        self.assertEqual(len(job), 2)

    def test_save_jobs_with_same_employer_and_diferent_title(self):
        spider = {"name": "indeed", "zyte_spider_number": 2, "zyte_job_number": 0}
        zyte_project = {"zyte_api_key": 1234567, "zyte_api_deploy": 11223344}
        platform = {"name": "indeed"}

        model = self.bc.database.create(spider=spider, zyte_project=zyte_project, platform=platform)

        result = save_data(model.spider, JOBS6)
        job = self.bc.database.list_of("career.Job")

        self.assertEqual(
            job,
            [
                {
                    "id": 1,
                    "title": "Pentester Cybersecurity",
                    "published_date_raw": "today",
                    "published_date_processed": None,
                    "status": "OPENED",
                    "apply_url": "https://www.url.com/1",
                    "currency": "USD",
                    "min_salary": 0.0,
                    "max_salary": 0.0,
                    "salary": "Not supplied",
                    "job_description": "Vuln exploitation Security reports",
                    "spider_id": 1,
                    "job_type": "Full-time",
                    "remote": True,
                    "employer_id": 1,
                    "position_id": 2,
                },
                {
                    "id": 2,
                    "title": "Python",
                    "published_date_raw": "November 05, 2021",
                    "published_date_processed": None,
                    "status": "OPENED",
                    "apply_url": "https://www.url.com/2",
                    "currency": "USD",
                    "min_salary": 0.0,
                    "max_salary": 0.0,
                    "salary": "Not supplied",
                    "job_description": "Vuln exploitation Security reports",
                    "spider_id": 1,
                    "job_type": "Full-time",
                    "remote": False,
                    "employer_id": 1,
                    "position_id": 2,
                },
            ],
        )
        self.assertEqual(len(job), 2)

    def test_give_two_location_alias_repited(self):
        spider = {"name": "getonboard", "zyte_spider_number": 3, "zyte_job_number": 0}
        zyte_project = {"zyte_api_key": 1234567, "zyte_api_deploy": 11223344}
        platform = {"name": "getonboard"}

        model = self.bc.database.create(spider=spider, zyte_project=zyte_project, platform=platform)

        result = save_data(model.spider, JOBS7)
        location = self.bc.database.list_of("career.Location")
        location_alias = self.bc.database.list_of("career.LocationAlias")

        self.assertEqual(location, [{"id": 1, "name": "Chile"}])
        self.assertEqual(len(location), 1)
        self.assertEqual(location_alias, [{"id": 1, "name": "Chile", "location_id": 1}])
        self.assertEqual(len(location_alias), 1)

    def test_give_two_location_alias_repited_and_one_diferent(self):
        spider = {"name": "getonboard", "zyte_spider_number": 3, "zyte_job_number": 0}
        zyte_project = {"zyte_api_key": 1234567, "zyte_api_deploy": 11223344}
        platform = {"name": "getonboard"}

        model = self.bc.database.create(spider=spider, zyte_project=zyte_project, platform=platform)

        result = save_data(model.spider, JOBS8)
        location = self.bc.database.list_of("career.Location")
        location_alias = self.bc.database.list_of("career.LocationAlias")

        self.assertEqual(location, [{"id": 1, "name": "Chile"}, {"id": 2, "name": "Venezuela"}])
        self.assertEqual(len(location), 2)
        self.assertEqual(
            location_alias,
            [{"id": 1, "name": "Chile", "location_id": 1}, {"id": 2, "name": "Venezuela", "location_id": 2}],
        )
        self.assertEqual(len(location_alias), 2)

    def test_save_one_job_without_location_and_return_remote_true(self):
        spider = {"name": "getonboard", "zyte_spider_number": 3, "zyte_job_number": 0}
        zyte_project = {"zyte_api_key": 1234567, "zyte_api_deploy": 11223344}
        platform = {"name": "getonboard"}

        model = self.bc.database.create(spider=spider, zyte_project=zyte_project, platform=platform)

        result = save_data(model.spider, JOBS9)
        location = self.bc.database.list_of("career.Location")
        job = self.bc.database.list_of("career.Job")

        self.assertEqual(location, [])
        self.assertEqual(job.pop()["remote"], True)

    def test_save_two_job_with_location_and_without_location(self):
        spider = {"name": "getonboard", "zyte_spider_number": 3, "zyte_job_number": 0}
        zyte_project = {"zyte_api_key": 1234567, "zyte_api_deploy": 11223344}
        platform = {"name": "getonboard"}

        model = self.bc.database.create(spider=spider, zyte_project=zyte_project, platform=platform)

        result = save_data(model.spider, JOBS10)
        location = self.bc.database.list_of("career.Location")
        job = self.bc.database.list_of("career.Job")

        self.assertEqual(location, [{"id": 1, "name": "Santiago"}])
        self.assertEqual(len(location), 1)
        self.assertEqual(
            job,
            [
                {
                    "id": 1,
                    "title": "Pentester Cybersecurity",
                    "published_date_raw": "November 05, 2021",
                    "published_date_processed": None,
                    "status": "OPENED",
                    "apply_url": "https://www.url.com/1",
                    "currency": "USD",
                    "min_salary": 0.0,
                    "max_salary": 0.0,
                    "salary": "Not supplied",
                    "job_description": "Vuln exploitation Security reports",
                    "spider_id": 1,
                    "job_type": "Full-time",
                    "remote": True,
                    "employer_id": 1,
                    "position_id": 2,
                },
                {
                    "id": 2,
                    "title": "Pentester Cybersecurity",
                    "published_date_raw": "November 05, 2021",
                    "published_date_processed": None,
                    "status": "OPENED",
                    "apply_url": "https://www.url.com/2",
                    "currency": "USD",
                    "min_salary": 0.0,
                    "max_salary": 0.0,
                    "salary": "Not supplied",
                    "job_description": "Vuln exploitation Security reports",
                    "spider_id": 1,
                    "job_type": "Full-time",
                    "remote": False,
                    "employer_id": 2,
                    "position_id": 2,
                },
            ],
        )
        self.assertEqual(len(job), 2)
