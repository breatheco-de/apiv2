from unittest.mock import MagicMock, call, patch

from breathecode.tests.mocks import REQUESTS_PATH, apply_requests_post_mock

from ...actions import run_spider
from ..mixins import CareerTestCase

RESULT = {
    "spider": ['Invalid pk "indeed5" - object does not exist.'],
    "status": "error",
    "message": 'spider: Invalid pk "indeed5" - object does not exist.',
}

spider = {"name": "getonboard", "zyte_spider_number": 3, "zyte_job_number": 0}
zyte_project = {"zyte_api_key": 1234567, "zyte_api_deploy": 223344}
platform = {"name": "getonboard"}

spider1 = {"name": "indeed", "zyte_spider_number": 2, "zyte_job_number": 0}
zyte_project1 = {"zyte_api_key": 1234567, "zyte_api_deploy": 223344}
platform1 = {"name": "indeed"}


class ActionRunSpiderTestCase(CareerTestCase):

    def test_run_spider__without_spider(self):
        try:
            run_spider(None)
            assert False
        except Exception as e:
            self.assertEqual(str(e), "missing-spider")

    @patch(REQUESTS_PATH["post"], apply_requests_post_mock([(400, "https://app.scrapinghub.com/api/run.json", RESULT)]))
    @patch("logging.Logger.error", MagicMock())
    def test_run_spider__with_status_code_error(self):
        from logging import Logger

        import requests

        from breathecode.career.actions import run_spider

        model = self.bc.database.create(spider=spider, zyte_project=zyte_project, platform=platform)
        try:
            result = run_spider(model.spider)
            self.assertEqual(
                result,
                (
                    False,
                    {
                        "spider": ['Invalid pk "indeed5" - object does not exist.'],
                        "status": "error",
                        "message": 'spider: Invalid pk "indeed5" - object does not exist.',
                    },
                ),
            )
            self.assertEqual(
                requests.post.call_args_list,
                [
                    call(
                        "https://app.scrapinghub.com/api/run.json",
                        data={
                            "project": model.zyte_project.zyte_api_deploy,
                            "spider": model.zyte_project.platform.name,
                            "job": model.spider.job_search,
                            "loc": model.spider.loc_search,
                        },
                        auth=(model.zyte_project.zyte_api_key, ""),
                        timeout=2,
                    )
                ],
            )
        except Exception as e:
            self.assertEqual(str(e), ("bad-request"))
            self.assertEqual(
                Logger.error.call_args_list,
                [
                    call(
                        "The spider ended error. Type error ['Invalid pk \"indeed5\" - object does not exist.'] to getonboard"
                    ),
                    call("Status 400 - bad-request"),
                ],
            )

    @patch(
        REQUESTS_PATH["post"],
        apply_requests_post_mock([(200, "https://app.scrapinghub.com/api/run.json", {"status": "ok", "data": []})]),
    )
    def test_run_spider__with_one_spider(self):
        import requests

        from breathecode.career.actions import run_spider

        model = self.bc.database.create(spider=spider, zyte_project=zyte_project, platform=platform)

        result = run_spider(model.spider)
        self.assertEqual(result, (True, {"status": "ok", "data": []}))
        self.assertEqual(
            requests.post.call_args_list,
            [
                call(
                    "https://app.scrapinghub.com/api/run.json",
                    data={
                        "project": model.zyte_project.zyte_api_deploy,
                        "spider": model.zyte_project.platform.name,
                        "job": model.spider.job_search,
                        "loc": model.spider.loc_search,
                    },
                    auth=(model.zyte_project.zyte_api_key, ""),
                    timeout=2,
                )
            ],
        )

    @patch(
        REQUESTS_PATH["post"],
        apply_requests_post_mock([(200, "https://app.scrapinghub.com/api/run.json", {"status": "ok", "data": []})]),
    )
    def test_run_spider__with_two_spiders(self):
        import requests

        from breathecode.career.actions import run_spider

        model_1 = self.bc.database.create(spider=spider, zyte_project=zyte_project, platform=platform)
        model_2 = self.bc.database.create(spider=spider1, zyte_project=zyte_project1, platform=platform1)

        result_1 = run_spider(model_1.spider)
        result_2 = run_spider(model_2.spider)

        self.assertEqual(result_1, (True, {"status": "ok", "data": []}))
        self.assertEqual(result_2, (True, {"status": "ok", "data": []}))

        self.assertEqual(
            requests.post.call_args_list,
            [
                call(
                    "https://app.scrapinghub.com/api/run.json",
                    data={
                        "project": model_1.zyte_project.zyte_api_deploy,
                        "spider": model_1.zyte_project.platform.name,
                        "job": model_1.spider.job_search,
                        "loc": model_1.spider.loc_search,
                    },
                    auth=(model_1.zyte_project.zyte_api_key, ""),
                    timeout=2,
                ),
                call(
                    "https://app.scrapinghub.com/api/run.json",
                    data={
                        "project": model_2.zyte_project.zyte_api_deploy,
                        "spider": model_2.zyte_project.platform.name,
                        "job": model_2.spider.job_search,
                        "loc": model_2.spider.loc_search,
                    },
                    auth=(model_2.zyte_project.zyte_api_key, ""),
                    timeout=2,
                ),
            ],
        )
