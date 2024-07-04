from unittest.mock import patch, MagicMock, call
from breathecode.tests.mocks.django_contrib import (
    DJANGO_CONTRIB_PATH,
    DJANGO_CONTRIB_INSTANCES,
    apply_django_contrib_messages_mock,
)
from breathecode.career.models import Spider
from breathecode.career.admin import fetch_sync_all_data_admin
from ..mixins import CareerTestCase
from django.http.request import HttpRequest
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
            "spider": "indeed",
            "spider_args": {"job": "go", "loc": "remote"},
            "close_reason": "finished",
            "elapsed": 646146617,
            "logs": 18,
            "id": "223344/2/71",
            "started_time": "2022-01-02T13:40:20",
            "updated_time": "2022-01-02T13:40:57",
            "items_scraped": 0,
            "errors_count": 0,
            "responses_received": 2,
        },
        {
            "priority": 2,
            "tags": [],
            "version": "2f9f2a5-master",
            "state": "finished",
            "spider_type": "manual",
            "spider": "indeed",
            "spider_args": {"job": "web developer", "loc": "remote"},
            "close_reason": "finished",
            "elapsed": 647281256,
            "logs": 25,
            "id": "223344/2/70",
            "started_time": "2022-01-02T13:15:17",
            "updated_time": "2022-01-02T13:22:03",
            "items_scraped": 0,
            "errors_count": 2,
            "responses_received": 0,
        },
    ],
}

JOBS = [
    {
        "Searched_job": "ruby",
        "Job_title": ".Net Core Developer",
        "Location": "New Orleans, LA",
        "Company_name": "Revelry Labs",
        "Post_date": "8 days ago",
        "Extract_date": "2022-02-17",
        "Job_description": "Net Core Developer who has experience with .net Core, C#, and SQL Server Database experience.",
        "Salary": "",
        "Tags": [],
        "Apply_to": "https://www.indeed.com/company/Revelry/jobs/Net-Core-Developer-a8e4e600cb716fb7?fccid=89b6cc7775dbcb2b&vjs=3",
        "_type": "dict",
    },
    {
        "Searched_job": "ruby",
        "Job_title": "Junior DevOps Engineer",
        "Location": "Remote",
        "Company_name": "Clear Labs",
        "Post_date": "2 days ago",
        "Extract_date": "2022-02-17",
        "Job_description": "We are looking for a qualified engineer for a full time Junior DevOps Role.",
        "Salary": "",
        "Tags": [],
        "Apply_to": "https://www.indeed.com/company/Clear-Labs/jobs/Junior-Devop-Engineer-71a0689ea2bd8cb1?fccid=250710b384a27cb1&vjs=3",
        "_type": "dict",
    },
]

JOBS2 = [
    {
        "Searched_job": "ruby",
        "Job_title": ".Net Core Developer",
        "Location": "New Orleans, LA",
        "Company_name": "Revelry Labs",
        "Post_date": "8 days ago",
        "Extract_date": "2022-02-17",
        "Job_description": "Net Core Developer who has experience with .net Core, C#, and SQL Server Database experience.",
        "Salary": "",
        "Tags": [],
        "Apply_to": "https://www.indeed.com/company/Revelry/jobs/Net-Core-Developer-a8e4e600cb716fb7?fccid=89b6cc7775dbcb2b&vjs=3",
        "_type": "dict",
    },
    {
        "Searched_job": "ruby",
        "Job_title": "Junior DevOps Engineer",
        "Location": "Remote",
        "Company_name": "Clear Labs",
        "Post_date": "2 days ago",
        "Extract_date": "2022-02-17",
        "Job_description": "We are looking for a qualified engineer for a full time Junior DevOps Role.",
        "Salary": "",
        "Tags": [],
        "Apply_to": "https://www.indeed.com/company/Clear-Labs/jobs/Junior-Devop-Engineer-71a0689ea2bd8cb1?fccid=250710b384a27cb1&vjs=3",
        "_type": "dict",
    },
]


class RunSpiderAdminTestSuite(CareerTestCase):

    @patch(DJANGO_CONTRIB_PATH["messages"], apply_django_contrib_messages_mock())
    @patch("django.contrib.messages.add_message", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.career.actions.fetch_sync_all_data", MagicMock(side_effect=Exception("They killed kenny")))
    def test_fetch_sync_all_data_admin__with_zero_spider(self):
        from breathecode.career.actions import fetch_sync_all_data
        from logging import Logger

        model = self.bc.database.create(spider=1)
        request = HttpRequest()
        queryset = Spider.objects.all()

        fetch_sync_all_data_admin(None, request, queryset)

        self.assertEqual(
            Logger.error.call_args_list, [call("There was an error retriving the spider They killed kenny")]
        )
        self.assertEqual(fetch_sync_all_data.call_args_list, [call(model.spider)])

    @patch(DJANGO_CONTRIB_PATH["messages"], apply_django_contrib_messages_mock())
    @patch("breathecode.career.actions.fetch_sync_all_data", MagicMock())
    def test_fetch_sync_all_data_admin__with_one_spider(self):
        from breathecode.career.actions import fetch_sync_all_data
        from django.contrib import messages

        model = self.bc.database.create(spider=True)

        request = HttpRequest()
        queryset = Spider.objects.all()

        fetch_sync_all_data_admin(model.spider, request, queryset)

        self.assertEqual(fetch_sync_all_data.call_args_list, [call(model.spider)])

    @patch(DJANGO_CONTRIB_PATH["messages"], apply_django_contrib_messages_mock())
    @patch("django.contrib.messages.add_message", MagicMock())
    @patch(
        REQUESTS_PATH["get"],
        apply_requests_get_mock(
            [
                (200, "https://app.scrapinghub.com/api/jobs/list.json", DATA),
                (200, "https://storage.scrapinghub.com/items/223344/2/72?apikey=1234567&format=json", JOBS),
                (200, "https://storage.scrapinghub.com/items/223344/2/75?apikey=1234567&format=json", JOBS2),
            ]
        ),
    )
    @patch("breathecode.career.actions.fetch_sync_all_data", MagicMock())
    def test_fetch_sync_all_data_admin__with_two_spiders(self):
        from breathecode.career.actions import fetch_sync_all_data
        from django.contrib import messages

        SPIDER = [
            {"name": "indeed", "zyte_spider_number": 2, "zyte_job_number": 0},
            {"name": "getonboard", "zyte_spider_number": 3, "zyte_job_number": 0},
        ]
        ZYTE_PROJECT = [
            {"zyte_api_key": 1234567, "zyte_api_deploy": 223344},
            {"zyte_api_key": 1234567, "zyte_api_deploy": 223344},
        ]
        PLATFORM = [{"name": "indeed"}, {"name": "getonboard"}]

        request = HttpRequest()

        model = self.bc.database.create(spider=SPIDER, zyte_project=ZYTE_PROJECT, platform=PLATFORM)

        result = fetch_sync_all_data_admin(None, request, Spider.objects.all())

        self.assertEqual(fetch_sync_all_data.call_args_list, [call(model.spider[0]), call(model.spider[1])])
