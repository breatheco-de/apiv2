"""
Tasks tests
"""
from unittest.mock import patch, call
from ...actions import fetch_sync_all_data, fetch_to_api
from ..mixins import JobsTestCase
from breathecode.tests.mocks import (
    REQUESTS_PATH,
    apply_requests_get_mock,
    apply_requests_post_mock,
)

DATA = {
    'status':
    'ok',
    'count':
    3,
    'total':
    3,
    'jobs': [{
        'priority': 2,
        'tags': [],
        'version': '2f9f2a5-master',
        'state': 'finished',
        'spider_type': 'manual',
        'spider': 'indeed',
        'spider_args': {
            'job': 'front end',
            'loc': 'remote'
        },
        'close_reason': 'finished',
        'elapsed': 609370879,
        'logs': 74,
        'id': '570286/2/72',
        'started_time': '2022-01-02T22:56:02',
        'updated_time': '2022-01-02T23:53:52',
        'items_scraped': 227,
        'errors_count': 0,
        'responses_received': 555
    }, {
        'priority': 2,
        'tags': [],
        'version': '2f9f2a5-master',
        'state': 'finished',
        'spider_type': 'manual',
        'spider': 'indeed',
        'spider_args': {
            'job': 'go',
            'loc': 'remote'
        },
        'close_reason': 'finished',
        'elapsed': 646146617,
        'logs': 18,
        'id': '570286/2/71',
        'started_time': '2022-01-02T13:40:20',
        'updated_time': '2022-01-02T13:40:57',
        'items_scraped': 0,
        'errors_count': 0,
        'responses_received': 2
    }, {
        'priority': 2,
        'tags': [],
        'version': '2f9f2a5-master',
        'state': 'finished',
        'spider_type': 'manual',
        'spider': 'indeed',
        'spider_args': {
            'job': 'web developer',
            'loc': 'remote'
        },
        'close_reason': 'finished',
        'elapsed': 647281256,
        'logs': 25,
        'id': '570286/2/70',
        'started_time': '2022-01-02T13:15:17',
        'updated_time': '2022-01-02T13:22:03',
        'items_scraped': 0,
        'errors_count': 2,
        'responses_received': 0
    }]
}


class ActionTestFetchSyncAllDataAdminTestCase(JobsTestCase):
    """Tests action fetch_sync_all_data"""
    """
    🔽🔽🔽 With zero Spider
    """
    def test_fetch_funtion___with_zero_spider(self):
        """Test /answer.With zero Spider"""
        try:
            fetch_sync_all_data(None)
        except Exception as e:
            self.assertEquals(str(e), ('First you must specify a spider'))

    """
    🔽🔽🔽 With one Spider
    """

    @patch(REQUESTS_PATH['get'],
           apply_requests_get_mock([(200, 'https://app.scrapinghub.com/api/jobs/list.json', DATA)]))
    def test_fetch_funtion__with_one_spider(self):
        """Test /answer With one Spider"""
        import requests

        model = self.generate_models(spider=True)
        result = fetch_sync_all_data(model.spider)
        self.assertEqual(result, DATA)
        self.assertEqual(requests.get.call_args_list, [
            call('https://app.scrapinghub.com/api/jobs/list.json',
                 params=(
                     ('project', model.zyte_project.zyte_api_deploy),
                     ('spider', model.zyte_project.platform.name),
                     ('state', 'finished'),
                 ),
                 auth=(model.zyte_project.zyte_api_key, ''))
        ])

    """
    🔽🔽🔽 With two Spiders
    """

    @patch(REQUESTS_PATH['get'],
           apply_requests_get_mock([(200, 'https://app.scrapinghub.com/api/jobs/list.json', DATA)]))
    def test_fetch_funtion__with_two_spiders(self):
        """Test /answer With two Spiders"""
        import requests

        model_1 = self.generate_models(spider=True)
        model_2 = self.generate_models(spider=True)
        result_1 = fetch_sync_all_data(model_1.spider)
        result_2 = fetch_sync_all_data(model_2.spider)

        self.assertEqual(result_1, DATA)
        self.assertEqual(result_2, DATA)
        self.assertEqual(requests.get.call_args_list, [
            call('https://app.scrapinghub.com/api/jobs/list.json',
                 params=(
                     ('project', model_1.zyte_project.zyte_api_deploy),
                     ('spider', model_1.zyte_project.platform.name),
                     ('state', 'finished'),
                 ),
                 auth=(model_1.zyte_project.zyte_api_key, '')),
            call('https://app.scrapinghub.com/api/jobs/list.json',
                 params=(
                     ('project', model_2.zyte_project.zyte_api_deploy),
                     ('spider', model_2.zyte_project.platform.name),
                     ('state', 'finished'),
                 ),
                 auth=(model_2.zyte_project.zyte_api_key, ''))
        ])

    """
    🔽🔽🔽 Verify fetch function was calletd with one Spider
    """

    @patch(REQUESTS_PATH['get'],
           apply_requests_get_mock([(200, 'https://app.scrapinghub.com/api/jobs/list.json', DATA)]))
    def test_verify_fetch_funtions_was_calletd(self):
        """Test /Verify fetch function was calletd with one Spider"""
        import requests

        model = self.generate_models(spider=True)
        result = fetch_sync_all_data(model.spider)
        requests.get.assert_called()
        self.assertEqual(result, DATA)
