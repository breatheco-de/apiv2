from unittest.mock import patch, call, MagicMock
from ...actions import fetch_sync_all_data, fetch_to_api, get_scraped_data_of_platform
from ..mixins import CareerTestCase
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
            "spider_args": {"job": "front end", "loc": "remote"},
            "close_reason": "finished",
            "elapsed": 609370879,
            "logs": 75,
            "id": "223344/2/75",
            "started_time": "2022-01-02T22:56:02",
            "updated_time": "2022-01-02T23:53:52",
            "items_scraped": 227,
            "errors_count": 0,
            "responses_received": 555,
        },
    ],
}

DATA1 = {
    "status": "ok",
    "count": 1,
    "total": 1,
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
        }
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

spider = {"name": "indeed", "zyte_spider_number": 2, "zyte_job_number": 0}
zyte_project = {"zyte_api_key": 1234567, "zyte_api_deploy": 223344}
platform = {"name": "indeed"}


class ActionTestFetchSyncAllDataAdminTestCase(CareerTestCase):

    @patch("logging.Logger.debug", MagicMock())
    def test_fetch_funtion___with_zero_spider(self):
        from logging import Logger

        try:
            fetch_sync_all_data(None)
            assert False

        except Exception as e:
            self.assertEqual(
                Logger.debug.call_args_list, [call("First you must specify a spider (fetch_sync_all_data)")]
            )
            self.assertEqual(str(e), "without-spider")

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
    def test_fetch_funtion__with_one_spider_two_requests(self):
        import requests

        model = self.bc.database.create(spider=spider, zyte_project=zyte_project, platform=platform)

        result = fetch_sync_all_data(model.spider)

        self.assertEqual(result, DATA)
        self.assertEqual(
            requests.get.call_args_list,
            [
                call(
                    "https://app.scrapinghub.com/api/jobs/list.json",
                    params=(("project", "223344"), ("spider", "indeed"), ("state", "finished")),
                    auth=("1234567", ""),
                    timeout=2,
                ),
                call("https://storage.scrapinghub.com/items/223344/2/72?apikey=1234567&format=json", timeout=2),
                call("https://storage.scrapinghub.com/items/223344/2/75?apikey=1234567&format=json", timeout=2),
            ],
        )

    @patch(
        REQUESTS_PATH["get"],
        apply_requests_get_mock(
            [
                (200, "https://app.scrapinghub.com/api/jobs/list.json", DATA1),
                (200, "https://storage.scrapinghub.com/items/223344/2/72?apikey=1234567&format=json", JOBS),
            ]
        ),
    )
    def test_verify_fetch_funtions_was_called(self):
        import requests

        model = self.bc.database.create(spider=spider, zyte_project=zyte_project, platform=platform)

        result = fetch_sync_all_data(model.spider)

        requests.get.assert_called()
        self.assertEqual(result, DATA1)
        self.assertEqual(
            requests.get.call_args_list,
            [
                call(
                    "https://app.scrapinghub.com/api/jobs/list.json",
                    params=(("project", "223344"), ("spider", "indeed"), ("state", "finished")),
                    auth=("1234567", ""),
                    timeout=2,
                ),
                call("https://storage.scrapinghub.com/items/223344/2/72?apikey=1234567&format=json", timeout=2),
            ],
        )
