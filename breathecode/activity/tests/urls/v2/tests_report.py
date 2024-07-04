"""
Test /report
"""

import functools
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

    return (client_mock, result_mock, project_id, dataset, rows_to_insert)


def bigquery_client_mock_group(self, n=1, user_id=1, kind=None, fields=[], by=""):
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

    query_rows = []
    grouped_data = []
    for row in rows_to_insert:
        new_row = {key: row[key] for key in fields}
        query_rows.append(new_row)

    for row in query_rows:
        if next(filter(lambda x: x[by] == row[by], grouped_data), None) is None:
            grouped_data.append(row)

    result_mock = MagicMock()
    result_mock.result.return_value = [AttrDict(**kwargs) for kwargs in grouped_data]

    client_mock = MagicMock()
    client_mock.query.return_value = result_mock

    project_id = "test"
    dataset = "4geeks"

    return (client_mock, result_mock, project_id, dataset, grouped_data)


def bigquery_client_mock_filters(self, n=1, user_id=1, kind=None, filters={}):
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

    for key in filters:
        literal = filters[key]
        if key.endswith("__lte"):
            rows_to_insert = list(filter(lambda x: x[key[:-5]] <= literal, rows_to_insert))
        elif key.endswith("__lt"):
            rows_to_insert = list(filter(lambda x: x[key[:-4]] < literal, rows_to_insert))
        elif key.endswith("__gte"):
            rows_to_insert = list(filter(lambda x: x[key[:-5]] >= literal, rows_to_insert))
        elif key.endswith("__gt"):
            rows_to_insert = list(filter(lambda x: x[key[:-4]] > literal, rows_to_insert))
        else:
            rows_to_insert = list(filter(lambda x: x[key] == literal, rows_to_insert))

    result_mock = MagicMock()
    result_mock.result.return_value = [AttrDict(**kwargs) for kwargs in rows_to_insert]

    client_mock = MagicMock()
    client_mock.query.return_value = result_mock

    project_id = "test"
    dataset = "4geeks"

    return (client_mock, result_mock, project_id, dataset, rows_to_insert)


def bigquery_client_mock_aggregation(self, n=1, user_id=1, kind=None, aggregation={}):
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

    query_rows = []
    grouped_data = []
    for row in rows_to_insert:
        new_row = {key: row[key] for key in aggregation.values()}
        query_rows.append(new_row)

    res_dict = {}
    if "sum" in aggregation:
        val = aggregation["sum"]
        new_key = f"sum__{val}"
        res_dict[new_key] = functools.reduce(lambda x, y: x[val] + y[val], query_rows)

    if "count" in aggregation:
        val = aggregation["count"]
        new_key = f"count__{val}"
        res_dict[new_key] = len(query_rows)

    if "avg" in aggregation:
        val = aggregation["avg"]
        new_key = f"avg__{val}"
        res_dict[new_key] = functools.reduce(lambda x, y: x[val] + y[val], query_rows) / len(query_rows)

    grouped_data.append(res_dict)

    result_mock = MagicMock()
    result_mock.result.return_value = [AttrDict(**kwargs) for kwargs in grouped_data]

    client_mock = MagicMock()
    client_mock.query.return_value = result_mock

    project_id = "test"
    dataset = "4geeks"

    return (client_mock, result_mock, project_id, dataset, grouped_data)


class MediaTestSuite(MediaTestCase):

    def test_no_auth(self):
        url = reverse_lazy("v2:activity:report")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_get_all_fields(self):
        expected_query = "SELECT * FROM `test.4geeks.activity` "
        url = reverse_lazy("v2:activity:report")
        model = self.bc.database.create(user=1, academy=1, profile_academy=1, capability="read_activity", role=1)

        self.client.force_authenticate(model.user)
        self.bc.request.set_headers(academy=1)

        val = bigquery_client_mock(self)
        (client_mock, result_mock, project_id, dataset, expected) = val

        with patch("breathecode.services.google_cloud.big_query.BigQuery.client") as mock:
            mock.return_value = (client_mock, project_id, dataset)
            response = self.client.get(url)
            json = response.json()

            self.bc.check.calls(BigQuery.client.call_args_list, [call()])
            assert client_mock.query.call_args[0][0] == expected_query
            self.bc.check.calls(result_mock.result.call_args_list, [call()])

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_get_all_fields_limit(self):
        expected_query = "SELECT * FROM `test.4geeks.activity`  LIMIT 5"
        url = reverse_lazy("v2:activity:report") + f"?limit=5"
        model = self.bc.database.create(user=1, academy=1, profile_academy=1, capability="read_activity", role=1)

        self.client.force_authenticate(model.user)
        self.bc.request.set_headers(academy=1)

        val = bigquery_client_mock(self)
        (client_mock, result_mock, project_id, dataset, expected) = val
        expected = expected[0:5]

        with patch("breathecode.services.google_cloud.big_query.BigQuery.client") as mock:
            mock.return_value = (client_mock, project_id, dataset)
            response = self.client.get(url)
            json = response.json()

            self.bc.check.calls(BigQuery.client.call_args_list, [call()])
            assert client_mock.query.call_args[0][0] == expected_query
            self.bc.check.calls(result_mock.result.call_args_list, [call()])

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_get_group(self):
        expected_query = "SELECT kind FROM `test.4geeks.activity`  GROUP BY kind"
        url = reverse_lazy("v2:activity:report") + f"?by=kind&fields=kind"
        model = self.bc.database.create(user=1, academy=1, profile_academy=1, capability="read_activity", role=1)

        self.client.force_authenticate(model.user)
        self.bc.request.set_headers(academy=1)

        val = bigquery_client_mock_group(self, by="kind", fields=["kind"])
        (client_mock, result_mock, project_id, dataset, expected) = val

        with patch("breathecode.services.google_cloud.big_query.BigQuery.client") as mock:
            mock.return_value = (client_mock, project_id, dataset)
            response = self.client.get(url)
            json = response.json()

            self.bc.check.calls(BigQuery.client.call_args_list, [call()])
            assert client_mock.query.call_args[0][0] == expected_query
            self.bc.check.calls(result_mock.result.call_args_list, [call()])

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_get_filters_lte(self):
        json_query = '{ "filter": { "user_id__lte": 5 } }'
        expected_query = "SELECT * FROM `test.4geeks.activity` WHERE user_id <= @x__user_id"
        url = reverse_lazy("v2:activity:report") + f"?query={json_query}"
        model = self.bc.database.create(user=1, academy=1, profile_academy=1, capability="read_activity", role=1)

        self.client.force_authenticate(model.user)
        self.bc.request.set_headers(academy=1)

        val = bigquery_client_mock_filters(self, filters={"user_id__lte": 5})
        (client_mock, result_mock, project_id, dataset, expected) = val

        with patch("breathecode.services.google_cloud.big_query.BigQuery.client") as mock:
            mock.return_value = (client_mock, project_id, dataset)
            response = self.client.get(url)
            json = response.json()

            self.bc.check.calls(BigQuery.client.call_args_list, [call()])
            assert client_mock.query.call_args[0][0] == expected_query
            self.bc.check.calls(result_mock.result.call_args_list, [call()])

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_get_filters_lt(self):
        json_query = '{ "filter": { "user_id__lt": 5 } }'
        expected_query = "SELECT * FROM `test.4geeks.activity` WHERE user_id < @x__user_id"
        url = reverse_lazy("v2:activity:report") + f"?query={json_query}"
        model = self.bc.database.create(user=1, academy=1, profile_academy=1, capability="read_activity", role=1)

        self.client.force_authenticate(model.user)
        self.bc.request.set_headers(academy=1)

        val = bigquery_client_mock_filters(self, filters={"user_id__lt": 5})
        (client_mock, result_mock, project_id, dataset, expected) = val

        with patch("breathecode.services.google_cloud.big_query.BigQuery.client") as mock:
            mock.return_value = (client_mock, project_id, dataset)
            response = self.client.get(url)
            json = response.json()

            self.bc.check.calls(BigQuery.client.call_args_list, [call()])
            assert client_mock.query.call_args[0][0] == expected_query
            self.bc.check.calls(result_mock.result.call_args_list, [call()])

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_get_filters_gte(self):
        json_query = '{ "filter": { "user_id__gte": 5 } }'
        expected_query = "SELECT * FROM `test.4geeks.activity` WHERE user_id >= @x__user_id"
        url = reverse_lazy("v2:activity:report") + f"?query={json_query}"
        model = self.bc.database.create(user=1, academy=1, profile_academy=1, capability="read_activity", role=1)

        self.client.force_authenticate(model.user)
        self.bc.request.set_headers(academy=1)

        val = bigquery_client_mock_filters(self, filters={"user_id__gte": 5})
        (client_mock, result_mock, project_id, dataset, expected) = val

        with patch("breathecode.services.google_cloud.big_query.BigQuery.client") as mock:
            mock.return_value = (client_mock, project_id, dataset)
            response = self.client.get(url)
            json = response.json()

            self.bc.check.calls(BigQuery.client.call_args_list, [call()])
            assert client_mock.query.call_args[0][0] == expected_query
            self.bc.check.calls(result_mock.result.call_args_list, [call()])

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_get_filters_gt(self):
        json_query = '{ "filter": { "user_id__gt": 5 } }'
        expected_query = "SELECT * FROM `test.4geeks.activity` WHERE user_id > @x__user_id"
        url = reverse_lazy("v2:activity:report") + f"?query={json_query}"
        model = self.bc.database.create(user=1, academy=1, profile_academy=1, capability="read_activity", role=1)

        self.client.force_authenticate(model.user)
        self.bc.request.set_headers(academy=1)

        val = bigquery_client_mock_filters(self, filters={"user_id__gt": 5})
        (client_mock, result_mock, project_id, dataset, expected) = val

        with patch("breathecode.services.google_cloud.big_query.BigQuery.client") as mock:
            mock.return_value = (client_mock, project_id, dataset)
            response = self.client.get(url)
            json = response.json()

            self.bc.check.calls(BigQuery.client.call_args_list, [call()])
            assert client_mock.query.call_args[0][0] == expected_query
            self.bc.check.calls(result_mock.result.call_args_list, [call()])

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_get_aggregation_sum(self):
        json_query = '{ "grouping_function": { "sum": ["id"] } }'
        expected_query = "SELECT SUM(id) AS sum__id FROM `test.4geeks.activity` "
        url = reverse_lazy("v2:activity:report") + f"?query={json_query}"
        model = self.bc.database.create(user=1, academy=1, profile_academy=1, capability="read_activity", role=1)

        self.client.force_authenticate(model.user)
        self.bc.request.set_headers(academy=1)

        val = bigquery_client_mock_aggregation(self, aggregation={"sum": "id"})
        (client_mock, result_mock, project_id, dataset, expected) = val

        with patch("breathecode.services.google_cloud.big_query.BigQuery.client") as mock:
            mock.return_value = (client_mock, project_id, dataset)
            response = self.client.get(url)
            json = response.json()

            self.bc.check.calls(BigQuery.client.call_args_list, [call()])
            assert client_mock.query.call_args[0][0] == expected_query
            self.bc.check.calls(result_mock.result.call_args_list, [call()])

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_get_aggregation_count(self):
        json_query = '{ "grouping_function": { "count": ["kind"] } }'
        expected_query = "SELECT COUNT(kind) AS count__kind FROM `test.4geeks.activity` "
        url = reverse_lazy("v2:activity:report") + f"?query={json_query}"
        model = self.bc.database.create(user=1, academy=1, profile_academy=1, capability="read_activity", role=1)

        self.client.force_authenticate(model.user)
        self.bc.request.set_headers(academy=1)

        val = bigquery_client_mock_aggregation(self, n=2, aggregation={"count": "kind"})
        (client_mock, result_mock, project_id, dataset, expected) = val

        with patch("breathecode.services.google_cloud.big_query.BigQuery.client") as mock:
            mock.return_value = (client_mock, project_id, dataset)
            response = self.client.get(url)
            json = response.json()

            self.bc.check.calls(BigQuery.client.call_args_list, [call()])
            assert client_mock.query.call_args[0][0] == expected_query
            self.bc.check.calls(result_mock.result.call_args_list, [call()])

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_get_aggregation_avg(self):
        json_query = '{ "grouping_function": { "avg": ["user_id"] } }'
        expected_query = "SELECT AVG(user_id) AS avg__user_id FROM `test.4geeks.activity` "
        url = reverse_lazy("v2:activity:report") + f"?query={json_query}"
        model = self.bc.database.create(user=1, academy=1, profile_academy=1, capability="read_activity", role=1)

        self.client.force_authenticate(model.user)
        self.bc.request.set_headers(academy=1)

        val = bigquery_client_mock_aggregation(self, n=2, aggregation={"avg": "user_id"})
        (client_mock, result_mock, project_id, dataset, expected) = val

        with patch("breathecode.services.google_cloud.big_query.BigQuery.client") as mock:
            mock.return_value = (client_mock, project_id, dataset)
            response = self.client.get(url)
            json = response.json()

            self.bc.check.calls(BigQuery.client.call_args_list, [call()])
            assert client_mock.query.call_args[0][0] == expected_query
            self.bc.check.calls(result_mock.result.call_args_list, [call()])

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
