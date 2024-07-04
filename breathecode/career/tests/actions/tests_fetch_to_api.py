from unittest.mock import patch, call, MagicMock
from ...actions import fetch_to_api
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


class ActionTestfetchToApiTestCase(CareerTestCase):

    @patch("logging.Logger.debug", MagicMock())
    def test_fetch_to_api__without_spider(self):
        from logging import Logger

        try:

            fetch_to_api(None)
            assert False
        except Exception as e:
            self.assertEqual(str(e), ("without-spider"))
            self.assertEqual(Logger.debug.call_args_list, [call("First you must specify a spider (fetch_to_api)")])

    @patch(
        REQUESTS_PATH["get"], apply_requests_get_mock([(200, "https://app.scrapinghub.com/api/jobs/list.json", DATA)])
    )
    def test_status_ok_fetch_to_api__whith_data(self):
        import requests

        model = self.bc.database.create(spider=1)
        result = fetch_to_api(model.spider)

        self.assertEqual(
            result,
            {
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
            },
        )
        self.assertEqual(
            requests.get.call_args_list,
            [
                call(
                    "https://app.scrapinghub.com/api/jobs/list.json",
                    params=(
                        ("project", model.zyte_project.zyte_api_deploy),
                        ("spider", model.zyte_project.platform.name),
                        ("state", "finished"),
                    ),
                    auth=(model.zyte_project.zyte_api_key, ""),
                    timeout=2,
                )
            ],
        )
