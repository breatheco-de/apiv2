"""
Test /answer
"""

import random
from unittest.mock import MagicMock, call, patch
from uuid import uuid4

from django.urls.base import reverse_lazy
from django.utils import timezone
from rest_framework import status

from breathecode.services.google_cloud.big_query import BigQuery
from breathecode.utils.attr_dict import AttrDict

from ...mixins import MediaTestCase

UTC_NOW = timezone.now()


def bigquery_client_mock(self, n=1, user_id=1, kind=None):
    rows_to_insert = [
        {
            "id": uuid4().hex,
            "user_id": user_id,
            "kind": kind if kind else self.bc.fake.slug(),
            "related": {
                "type": f"{self.bc.fake.slug()}.{self.bc.fake.slug()}",
                "id": random.randint(1, 100),
                "slug": self.bc.fake.slug(),
            },
            "meta": {
                self.bc.fake.slug().replace("-", "_"): self.bc.fake.slug(),
                self.bc.fake.slug().replace("-", "_"): self.bc.fake.slug(),
                self.bc.fake.slug().replace("-", "_"): self.bc.fake.slug(),
            },
            "timestamp": timezone.now().isoformat(),
        }
        for _ in range(n)
    ]

    result_mock = MagicMock()
    result_mock.result.return_value = [AttrDict(**kwargs) for kwargs in rows_to_insert]

    client_mock = MagicMock()
    client_mock.query.return_value = result_mock

    project_id = "test"
    dataset = "4geeks"

    query = f"""
            SELECT *
            FROM `{project_id}.{dataset}.activity`
            WHERE user_id = @user_id
                {'AND kind = @kind' if kind else ''}
            ORDER BY timestamp DESC
            LIMIT @limit
            OFFSET @offset
        """

    return (client_mock, result_mock, query, project_id, dataset, rows_to_insert)


class MediaTestSuite(MediaTestCase):

    def test_no_auth(self):
        url = reverse_lazy("v2:activity:me_activity")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_get_two(self):
        url = reverse_lazy("v2:activity:me_activity")
        self.generate_models(authenticate=True)

        val = bigquery_client_mock(self, n=2, user_id=1)
        (client_mock, result_mock, query, project_id, dataset, expected) = val

        with patch("breathecode.services.google_cloud.big_query.BigQuery.client") as mock:
            mock.return_value = (client_mock, project_id, dataset)
            response = self.client.get(url)
            json = response.json()

            self.bc.check.calls(BigQuery.client.call_args_list, [call()])
            assert client_mock.query.call_args[0][0] == query
            self.bc.check.calls(result_mock.result.call_args_list, [call()])

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_filter_by_kind(self):
        model = self.bc.database.create(user=1, academy=1)

        self.client.force_authenticate(model.user)
        kind = self.bc.fake.slug()

        url = reverse_lazy("v2:activity:me_activity") + f"?kind={kind}"

        val = bigquery_client_mock(self, n=2, user_id=1, kind=kind)
        (client_mock, result_mock, query, project_id, dataset, expected) = val

        with patch("breathecode.services.google_cloud.big_query.BigQuery.client") as mock:
            mock.return_value = (client_mock, project_id, dataset)
            response = self.client.get(url)
            json = response.json()

            self.bc.check.calls(BigQuery.client.call_args_list, [call()])
            assert client_mock.query.call_args[0][0] == query
            assert "AND kind = @kind" in query
            self.bc.check.calls(result_mock.result.call_args_list, [call()])

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
