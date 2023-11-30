"""
Test /report
"""
import random
from uuid import uuid4
from django.utils import timezone
from unittest.mock import MagicMock, call, patch

from django.urls.base import reverse_lazy
from rest_framework import status

from breathecode.services.google_cloud.big_query import BigQuery

from breathecode.utils.attr_dict import AttrDict

from ...mixins import MediaTestCase

UTC_NOW = timezone.now()


def bigquery_client_mock(self, n=1, user_id=1, kind=None):
    rows_to_insert = [{
        'id': uuid4().hex,
        'user_id': user_id,
        'kind': kind if kind else self.bc.fake.slug(),
        'related': {
            'type': f'{self.bc.fake.slug()}.{self.bc.fake.slug()}',
            'id': random.randint(1, 100),
            'slug': self.bc.fake.slug(),
        },
        'meta': {
            self.bc.fake.slug().replace('-', '_'): self.bc.fake.slug(),
            self.bc.fake.slug().replace('-', '_'): self.bc.fake.slug(),
            self.bc.fake.slug().replace('-', '_'): self.bc.fake.slug(),
        },
        'timestamp': timezone.now().isoformat(),
    } for _ in range(n)]

    result_mock = MagicMock()
    result_mock.result.return_value = [AttrDict(**kwargs) for kwargs in rows_to_insert]

    client_mock = MagicMock()
    client_mock.query.return_value = result_mock

    project_id = 'test'
    dataset = '4geeks'

    query = f"""
            SELECT *
            FROM `{project_id}.{dataset}.activity`
            WHERE user_id = @user_id
                {'AND kind = @kind' if kind else ''}
            ORDER BY id DESC
            LIMIT @limit
            OFFSET @offset
        """

    return (client_mock, result_mock, query, project_id, dataset, rows_to_insert)


def konoha_mock(self, n=1, name='Row 1', sum__n=1, c1=15, kind=None):
    rows_to_insert = [{
        'sum__n': sum__n,
        'name': name,
        'n': 15,
        'extra': {
            'c1': c1
        },
        'json': None,
    } for _ in range(n)]

    result_mock = MagicMock()
    result_mock.result.return_value = [AttrDict(**kwargs) for kwargs in rows_to_insert]

    client_mock = MagicMock()
    client_mock.query.return_value = result_mock

    project_id = 'test'
    dataset = '4geeks'

    query = f"""
            SELECT *
            FROM `{project_id}.{dataset}.activity`
            WHERE user_id = @user_id
                {'AND kind = @kind' if kind else ''}
            ORDER BY id DESC
            LIMIT @limit
            OFFSET @offset
        """

    return (client_mock, result_mock, query, project_id, dataset, rows_to_insert)


class MediaTestSuite(MediaTestCase):

    def test_no_auth(self):
        url = reverse_lazy('v2:activity:report')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test_get_two(self):
        json_query = '{ "limit": 50 }'
        url = reverse_lazy('v2:activity:report') + f'?query={json_query}'
        model = self.bc.database.create(user=1,
                                        academy=1,
                                        profile_academy=1,
                                        capability='read_activity',
                                        role=1)

        self.bc.request.authenticate(model.user)
        self.bc.request.set_headers(academy=1)

        val = konoha_mock(self)
        (client_mock, result_mock, query, project_id, dataset, expected) = val

        with patch('breathecode.services.google_cloud.big_query.BigQuery.client') as mock:
            mock.return_value = (client_mock, project_id, dataset)
            response = self.client.get(url)
            json = response.json()
            print('json')
            print(json)

            self.bc.check.calls(BigQuery.client.call_args_list, [call()])
            self.bc.check.calls(result_mock.result.call_args_list, [call()])

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
