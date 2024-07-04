from unittest.mock import patch, call, MagicMock
from ...actions import get_scraped_data_of_platform
from ..mixins import CareerTestCase
from breathecode.tests.mocks.django_contrib import DJANGO_CONTRIB_PATH, apply_django_contrib_messages_mock
from breathecode.tests.mocks import (
    REQUESTS_PATH,
    apply_requests_get_mock,
    apply_requests_post_mock,
)

DATA = {
    "status": "ok",
    "count": 3,
    "total": 3,
    "jobs": [
        {
            "priority": 2,
            "tags": [],
            "version": "2f9f2a5-master",
            "state": "finished",
            "spider_type": "manual",
            "spider": "indeed",
            "spider_args": {"job": "front end", "loc": "remote"},
            "close_reason": "finished",
            "elapsed": 609370879,
            "logs": 74,
            "id": "223344/2/72",
            "started_time": "2022-01-02T22:56:02",
            "updated_time": "2022-01-02T23:53:52",
            "items_scraped": 227,
            "errors_count": 0,
            "responses_received": 555,
        },
        {
            "priority": 2,
            "tags": [],
            "version": "2f9f2a5-master",
            "state": "finished",
            "spider_type": "manual",
            "spider": "getonboard",
            "spider_args": {"job": "go", "loc": "remote"},
            "close_reason": "finished",
            "elapsed": 646146617,
            "logs": 18,
            "id": "223344/3/35",
            "started_time": "2022-01-02T13:40:20",
            "updated_time": "2022-01-02T13:40:57",
            "items_scraped": 6,
            "errors_count": 0,
            "responses_received": 2,
        },
        {
            "priority": 2,
            "tags": [],
            "version": "2f9f2a5-master",
            "state": "finished",
            "spider_type": "manual",
            "spider": "getonboard",
            "spider_args": {"job": "web developer", "loc": "remote"},
            "close_reason": "finished",
            "elapsed": 647281256,
            "logs": 25,
            "id": "223344/3/34",
            "started_time": "2022-01-02T13:15:17",
            "updated_time": "2022-01-02T13:22:03",
            "items_scraped": 3,
            "errors_count": 2,
            "responses_received": 0,
        },
    ],
}

JOBS = [
    {
        "Searched_job": "junior web developer",
        "Job_title": "Desarrollador Full-Stack",
        "Location": "Santiago (temporarily remote)",
        "Company_name": "Centry",
        "Post_date": "January 19, 2022",
        "Extract_date": "2022-01-30",
        "Job_description": "",
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
        "Job_description": "Al menos 1 año de experiencia trabajando con Python y Django Al menos 1 año de experiencia trabajando con React.js Experiencia desarrollando APIs REST Ingles Conversacional Buscamos un desarrollador responsable, autodidacta, proactivo, eficiente y organizado.",
        "Salary": "$1800 - 2000 USD/month",
        "Tags": ["api", "back-end", "django", "english", "front-end", "full-stack", "javascript", "python", "react"],
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
        "Job_description": "Four-year degree in any computer science-related field or equivalent experience. At least 3-year solid front-end developer as well as back-end full stack developer. Relevant experience working with PHP/Symfony (if it is in Magento or Oro Commerce, even better). Familiar with responsive/adaptive design and mobile development best practices. Web and mobile development, familiar with front+back end developing and data interaction.  Experience with Express, Redis. and Node.js, mainframe (React, Angular, Knockout) preferred for React.",
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
        "Salary": "Not supplied",
        "Tags": ["back-end", "cybersecurity", "english", "pentesting", "python"],
        "Apply_to": "https://www.getonbrd.com/jobs/cybersecurity/security-engineer-rule-1-ventures-remote",
        "_type": "dict",
    },
    {
        "Searched_job": "junior web developer",
        "Job_title": "Front-end Developer",
        "Location": "Lima",
        "Company_name": "ID Business Intelligence",
        "Post_date": "January 24, 2022",
        "Extract_date": "2022-01-30",
        "Job_description": "Manejo de Git Flow. (~°-°)~ Dominar a profundidad CSS y JS (mínimo 1 año) Experiencia con React Experiencia consumiendo Web Service (Rest) Preocuparse por entregar productos de calidad.",
        "Salary": "Not supplied",
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
        "Job_description": "",
        "Salary": "Not supplied",
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

spider = {"name": "getonboard", "zyte_spider_number": 3, "zyte_job_number": 0}
zyte_project = {"zyte_api_key": 1234567, "zyte_api_deploy": 223344}
platform = {"name": "getonboard"}


class ActionGetScrapedDataOfPlatformTestCase(CareerTestCase):

    @patch(DJANGO_CONTRIB_PATH["messages"], apply_django_contrib_messages_mock())
    @patch("django.contrib.messages.add_message", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    def test_get_scraped_data_of_platform__without_spider(self):
        from breathecode.career.actions import get_scraped_data_of_platform
        from logging import Logger

        try:
            get_scraped_data_of_platform(None, DATA)
        except Exception as e:
            self.assertEqual(str(e), ("without-spider"))
            self.assertEqual(
                Logger.error.call_args_list,
                [
                    call("First you must specify a spider (get_scraped_data_of_platform)"),
                ],
            )

    @patch(DJANGO_CONTRIB_PATH["messages"], apply_django_contrib_messages_mock())
    @patch("django.contrib.messages.add_message", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    def test_get_scraped_data_of_platform__without_data(self):
        from breathecode.career.actions import get_scraped_data_of_platform
        from logging import Logger

        model = self.bc.database.create(spider=1)
        try:
            get_scraped_data_of_platform(model.spider, None)
        except Exception as e:
            self.assertEqual(str(e), ("no-return-json-data"))
            self.assertEqual(
                Logger.error.call_args_list,
                [
                    call("I did not receive results from the API (get_scraped_data_of_platform)"),
                ],
            )

    @patch(
        REQUESTS_PATH["get"],
        apply_requests_get_mock(
            [
                (200, "https://storage.scrapinghub.com/items/223344/3/35?apikey=1234567&format=json", JOBS),
                (200, "https://storage.scrapinghub.com/items/223344/3/34?apikey=1234567&format=json", JOBS),
            ]
        ),
    )
    def test_fetch_data__with_two_num_jobs(self):
        import requests

        model = self.bc.database.create(spider=spider, zyte_project=zyte_project, platform=platform)

        result = get_scraped_data_of_platform(model.spider, DATA)

        self.assertEqual(
            result,
            [
                {"status": "ok", "platform_name": model.platform.name, "num_spider": 3, "num_job": 35, "jobs_saved": 6},
                {"status": "ok", "platform_name": model.platform.name, "num_spider": 3, "num_job": 34, "jobs_saved": 0},
            ],
        )
        self.assertEqual(
            requests.get.call_args_list,
            [
                call("https://storage.scrapinghub.com/items/223344/3/35?apikey=1234567&format=json", timeout=2),
                call("https://storage.scrapinghub.com/items/223344/3/34?apikey=1234567&format=json", timeout=2),
            ],
        )

    @patch(
        REQUESTS_PATH["get"],
        apply_requests_get_mock(
            [
                (
                    400,
                    "https://storage.scrapinghub.com/items/223344/3/35?apikey=1234567&format=json",
                    [{"status_code": 400, "data": []}],
                )
            ]
        ),
    )
    @patch(DJANGO_CONTRIB_PATH["messages"], apply_django_contrib_messages_mock())
    @patch("django.contrib.messages.add_message", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    def test_fetch_data__with_bad_request(self):
        import requests
        from logging import Logger

        model = self.bc.database.create(spider=spider, zyte_project=zyte_project, platform=platform)
        try:
            result = get_scraped_data_of_platform(model.spider, DATA)

            self.assertEqual(result, [{"status_code": 400, "data": []}])
            self.assertEqual(
                requests.get.call_args_list,
                [call("https://storage.scrapinghub.com/items/223344/3/35?apikey=1234567&format=json")],
            )

        except Exception as e:
            self.assertEqual(str(e), ("bad-response-fetch"))
            self.assertEqual(
                Logger.error.call_args_list,
                [
                    call("There was a 400 error fetching spider 3 job 3 (get_scraped_data_of_platform)"),
                ],
            )
