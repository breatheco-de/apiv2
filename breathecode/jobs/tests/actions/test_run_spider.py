"""
Tasks tests
"""
from unittest.mock import patch, call
from ...actions import run_spider
from ..mixins import JobsTestCase
from breathecode.tests.mocks import (
    REQUESTS_PATH,
    apply_requests_post_mock,
)


class ActionRunSpiderTestCase(JobsTestCase):
    """Tests action certificate_screenshot"""
    def test_run_spider__without_spider(self):
        """Test /run_spider without spider"""
        try:
            run_spider(None)
        except Exception as e:
            self.assertEquals(str(e), ('First you must specify a spider'))

    @patch(REQUESTS_PATH['post'],
           apply_requests_post_mock([(200, 'https://app.scrapinghub.com/api/run.json', {
               'status': 'ok',
               'data': []
           })]))
    def test_run_spider__with_one_spider(self):
        """Test /answer without auth"""
        import requests

        model = self.generate_models(spider=True)

        result = run_spider(model.spider)
        self.assertEqual(result, (True, {'status': 'ok', 'data': []}))
        self.assertEqual(requests.post.call_args_list, [
            call('https://app.scrapinghub.com/api/run.json',
                 data={
                     'project': model.zyte_project.zyte_api_deploy,
                     'spider': model.zyte_project.platform.name,
                     'job': model.spider.job,
                     'loc': model.spider.loc
                 },
                 auth=(model.zyte_project.zyte_api_key, ''))
        ])

    @patch(REQUESTS_PATH['post'],
           apply_requests_post_mock([(200, 'https://app.scrapinghub.com/api/run.json', {
               'status': 'ok',
               'data': []
           })]))
    def test_run_spider__with_two_spiders(self):
        """Test /answer without auth"""
        from breathecode.jobs.actions import run_spider
        import requests

        model_1 = self.generate_models(spider=True, spider_kwargs={'job': 'python'})
        model_2 = self.generate_models(spider=True, spider_kwargs={'job': 'go'})

        result_1 = run_spider(model_1.spider)
        result_2 = run_spider(model_2.spider)

        self.assertEqual(result_1, (True, {'status': 'ok', 'data': []}))
        self.assertEqual(result_2, (True, {'status': 'ok', 'data': []}))

        self.assertEqual(requests.post.call_args_list, [
            call('https://app.scrapinghub.com/api/run.json',
                 data={
                     'project': model_1.zyte_project.zyte_api_deploy,
                     'spider': model_1.zyte_project.platform.name,
                     'job': model_1.spider.job,
                     'loc': model_1.spider.loc
                 },
                 auth=(model_1.zyte_project.zyte_api_key, '')),
            call('https://app.scrapinghub.com/api/run.json',
                 data={
                     'project': model_2.zyte_project.zyte_api_deploy,
                     'spider': model_2.zyte_project.platform.name,
                     'job': model_2.spider.job,
                     'loc': model_2.spider.loc
                 },
                 auth=(model_2.zyte_project.zyte_api_key, ''))
        ])
