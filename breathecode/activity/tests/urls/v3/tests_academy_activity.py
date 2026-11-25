"""
Academy activity v3 must stay inside the academy of the request.
"""

import random
from unittest.mock import MagicMock, call, patch
from uuid import uuid4

from django.urls.base import reverse_lazy
from django.utils import timezone
from rest_framework import status

from breathecode.activity.models import ACTIVITY_TABLE_NAME
from breathecode.admissions.models import CohortUser
from breathecode.services.google_cloud.big_query import BigQuery
from breathecode.utils.attr_dict import AttrDict

from ...mixins import MediaTestCase

UTC_NOW = timezone.now()


def bigquery_client_mock(self, n=1, user_id=1):
    rows_to_insert = [
        {
            "id": uuid4().hex,
            "user_id": user_id,
            "kind": self.bc.fake.slug(),
            "related": {
                "type": f"{self.bc.fake.slug()}.{self.bc.fake.slug()}",
                "id": random.randint(1, 100),
                "slug": self.bc.fake.slug(),
            },
            "meta": {
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
            FROM `{project_id}.{dataset}.{ACTIVITY_TABLE_NAME}`
            WHERE meta.academy = @academy_id
                {'AND user_id = @user_id' if user_id else ''}
                {'AND kind IN UNNEST(@kinds)' if False else ''}
                {'AND timestamp >= @date_start' if False else ''}
                {'AND timestamp <= @date_end' if False else ''}
                {'AND meta.cohort = @cohort_id' if False else ''}
            ORDER BY timestamp DESC
            LIMIT @limit
            OFFSET @offset
        """

    expected = [{**row, "academy": None} for row in rows_to_insert]
    return (client_mock, result_mock, query, project_id, dataset, expected)


class MediaTestSuite(MediaTestCase):

    def test_no_auth(self):
        url = reverse_lazy("v3:activity:academy_activity")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_list_filters_by_academy_only(self):
        model = self.bc.database.create(user=1, academy=1, profile_academy=1, capability="read_activity", role=1)

        self.client.force_authenticate(model.user)
        self.bc.request.set_headers(academy=1)

        url = reverse_lazy("v3:activity:academy_activity")

        val = bigquery_client_mock(self, n=1, user_id=None)
        (client_mock, result_mock, query, project_id, dataset, expected) = val

        with patch("breathecode.services.google_cloud.big_query.BigQuery.client") as mock:
            mock.return_value = (client_mock, project_id, dataset)
            response = self.client.get(url)

            self.bc.check.calls(BigQuery.client.call_args_list, [call()])
            assert client_mock.query.call_args[0][0] == query
            assert "meta.academy IS NULL" not in query

        self.assertEqual(response.json(), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_user_id_of_cohort_member(self):
        model = self.bc.database.create(user=2, academy=1, profile_academy=1, capability="read_activity", role=1)
        student = model.user[1]
        CohortUser.objects.create(user=student, cohort=model.cohort, role="STUDENT")

        self.client.force_authenticate(model.user[0])
        self.bc.request.set_headers(academy=1)

        url = reverse_lazy("v3:activity:academy_activity") + f"?user_id={student.id}"

        val = bigquery_client_mock(self, n=1, user_id=student.id)
        (client_mock, result_mock, query, project_id, dataset, expected) = val

        with patch("breathecode.services.google_cloud.big_query.BigQuery.client") as mock:
            mock.return_value = (client_mock, project_id, dataset)
            response = self.client.get(url)

            assert client_mock.query.call_args[0][0] == query
            assert "meta.academy IS NULL" not in query

        self.assertEqual(response.json(), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_id_outside_academy_is_rejected(self):
        model = self.bc.database.create(user=2, academy=1, profile_academy=1, capability="read_activity", role=1)
        outsider = model.user[1]

        self.client.force_authenticate(model.user[0])
        self.bc.request.set_headers(academy=1)

        url = reverse_lazy("v3:activity:academy_activity") + f"?user_id={outsider.id}"

        with patch("breathecode.services.google_cloud.big_query.BigQuery.client") as mock:
            response = self.client.get(url)
            mock.assert_not_called()

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["detail"], "user-not-in-academy")

    def test_detail_filters_by_academy_only(self):
        model = self.bc.database.create(user=1, academy=1, profile_academy=1, capability="read_activity", role=1)

        self.client.force_authenticate(model.user)
        self.bc.request.set_headers(academy=1)

        url = reverse_lazy("v3:activity:academy_activity_id", kwargs={"activity_id": "abc"})

        result_mock = MagicMock()
        result_mock.result.return_value = iter(
            [
                AttrDict(
                    id="abc",
                    user_id=1,
                    kind="login",
                    related={"type": "auth.User", "id": 1, "slug": "user"},
                    meta={},
                    timestamp=timezone.now().isoformat(),
                )
            ]
        )
        client_mock = MagicMock()
        client_mock.query.return_value = result_mock

        with patch("breathecode.services.google_cloud.big_query.BigQuery.client") as mock:
            mock.return_value = (client_mock, "test", "4geeks")
            response = self.client.get(url)
            query = client_mock.query.call_args[0][0]

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assert "AND meta.academy = @academy_id" in query
        assert "meta.academy IS NULL" not in query
        assert "AND user_id = @user_id" not in query
