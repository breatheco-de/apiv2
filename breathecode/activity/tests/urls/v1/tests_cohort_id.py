"""
Test /answer
"""

from breathecode.activity.models import StudentActivity
from django.utils import timezone
from datetime import timedelta
from unittest.mock import MagicMock, call, patch

from django.urls.base import reverse_lazy
from google.cloud.ndb.query import FilterNode
from rest_framework import status

from breathecode.services.google_cloud import Datastore
from breathecode.utils import NDB

from ...mixins import MediaTestCase

DATASTORE_PRIVATE_SEED = [
    {
        "academy_id": 1,
        "cohort": "miami-downtown-pt-xx",
        "created_at": (timezone.now() + timedelta(days=2)).isoformat() + "Z",
        "data": '{"cohort": "miami-downtown-pt-xx", "day": "13"}',
        "day": 13,
        "email": "konan@naruto.io",
        "slug": "classroom_attendance",
        "user_agent": "bc/test",
        "user_id": 1,
    },
]


def init(Model):
    pass


ndb_init_mock = MagicMock(side_effect=init)


def ndb_fetch_mock(result=[]):

    def fetch(query, **kwargs):
        return result

    return MagicMock(side_effect=fetch)


def ndb_count_mock(result=0):

    def count(query):
        return result

    return MagicMock(side_effect=count)


class MediaTestSuite(MediaTestCase):
    """Test /answer"""

    """
    🔽🔽🔽 Auth
    """

    def test_cohort_id__without_auth(self):
        url = reverse_lazy("activity:cohort_id", kwargs={"cohort_id": 1})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cohort_id__wrong_academy(self):
        self.headers(academy=1)
        url = reverse_lazy("activity:cohort_id", kwargs={"cohort_id": 1})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cohort_id__without_capability(self):
        self.headers(academy=1)
        url = reverse_lazy("activity:cohort_id", kwargs={"cohort_id": 1})
        self.generate_models(authenticate=True)
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json,
            {
                "detail": ("You (user: 1) don't have this capability: read_activity for " "academy 1"),
                "status_code": 403,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 Cohort not exists
    """

    @patch.object(NDB, "__init__", new=ndb_init_mock)
    @patch.object(NDB, "fetch", new=ndb_fetch_mock([]))
    def test_cohort_id__without_cohort(self):
        from breathecode.utils import NDB as mock

        ndb_init_mock.call_args_list = []
        mock.fetch.call_args_list = []

        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="read_activity", role="potato", skip_cohort=True
        )

        url = reverse_lazy("activity:cohort_id", kwargs={"cohort_id": 1})
        response = self.client.get(url)

        json = response.json()
        expected = {"detail": "cohort-not-found", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ndb_init_mock.call_args_list, [])
        self.assertEqual(mock.fetch.call_args_list, [])

    """
    🔽🔽🔽 Without data
    """

    @patch.object(NDB, "__init__", new=ndb_init_mock)
    @patch.object(NDB, "fetch", new=ndb_fetch_mock([]))
    def test_cohort_id__without_data(self):
        from breathecode.utils import NDB as mock

        ndb_init_mock.call_args_list = []
        mock.fetch.call_args_list = []

        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="read_activity", role="potato", cohort=True
        )

        url = reverse_lazy("activity:cohort_id", kwargs={"cohort_id": 1})
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(ndb_init_mock.call_args_list, [call(StudentActivity)])
        self.assertEqual(
            mock.fetch.call_args_list,
            [
                call([FilterNode("cohort", "=", model.cohort.slug)], limit=None, offset=None),
            ],
        )

    """
    🔽🔽🔽 With data
    """

    @patch.object(NDB, "__init__", new=ndb_init_mock)
    @patch.object(NDB, "fetch", new=ndb_fetch_mock([DATASTORE_PRIVATE_SEED]))
    def test_cohort_id(self):
        from breathecode.utils import NDB as mock

        ndb_init_mock.call_args_list = []
        mock.fetch.call_args_list = []

        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="read_activity", role="potato", cohort=True
        )

        url = reverse_lazy("activity:cohort_id", kwargs={"cohort_id": 1})
        response = self.client.get(url)

        json = response.json()
        expected = [DATASTORE_PRIVATE_SEED]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(ndb_init_mock.call_args_list, [call(StudentActivity)])
        self.assertEqual(
            mock.fetch.call_args_list,
            [
                call([FilterNode("cohort", "=", model.cohort.slug)], limit=None, offset=None),
            ],
        )

    """
    🔽🔽🔽 With slug
    """

    @patch.object(NDB, "__init__", new=ndb_init_mock)
    @patch.object(NDB, "fetch", new=ndb_fetch_mock([]))
    def test_cohort_id__with_bad_slug_in_querystring(self):
        from breathecode.utils import NDB as mock

        ndb_init_mock.call_args_list = []
        mock.fetch.call_args_list = []

        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="read_activity", role="potato", cohort=True
        )

        url = reverse_lazy("activity:cohort_id", kwargs={"cohort_id": 1}) + "?slug=breathecode_login"
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(ndb_init_mock.call_args_list, [call(StudentActivity)])
        self.assertEqual(
            mock.fetch.call_args_list,
            [
                call(
                    [FilterNode("slug", "=", "breathecode_login"), FilterNode("cohort", "=", model.cohort.slug)],
                    limit=None,
                    offset=None,
                )
            ],
        )

    @patch.object(NDB, "__init__", new=ndb_init_mock)
    @patch.object(NDB, "fetch", new=ndb_fetch_mock([DATASTORE_PRIVATE_SEED]))
    def test_cohort_id__with_slug_in_querystring(self):
        from breathecode.utils import NDB as mock

        ndb_init_mock.call_args_list = []
        mock.fetch.call_args_list = []

        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="read_activity", role="potato", cohort=True
        )

        url = reverse_lazy("activity:cohort_id", kwargs={"cohort_id": 1}) + "?slug=classroom_attendance"
        response = self.client.get(url)

        json = response.json()
        expected = [DATASTORE_PRIVATE_SEED]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(ndb_init_mock.call_args_list, [call(StudentActivity)])
        self.assertEqual(
            mock.fetch.call_args_list,
            [
                call(
                    [FilterNode("slug", "=", "classroom_attendance"), FilterNode("cohort", "=", model.cohort.slug)],
                    limit=None,
                    offset=None,
                )
            ],
        )

    """
    🔽🔽🔽 With pagination
    """

    @patch.object(NDB, "__init__", new=ndb_init_mock)
    @patch.object(NDB, "fetch", new=ndb_fetch_mock([DATASTORE_PRIVATE_SEED]))
    @patch.object(NDB, "count", new=ndb_count_mock(15))
    def test_cohort_id__with_pagination__first_five(self):
        from breathecode.utils import NDB as mock

        ndb_init_mock.call_args_list = []
        mock.fetch.call_args_list = []
        mock.count.call_args_list = []

        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="read_activity", role="potato", cohort=True
        )

        url = reverse_lazy("activity:cohort_id", kwargs={"cohort_id": 1}) + "?limit=5&offset=0"
        response = self.client.get(url)

        json = response.json()
        expected = {
            "count": 15,
            "first": None,
            "next": "http://testserver/v1/activity/cohort/1?limit=5&offset=5",
            "previous": None,
            "last": "http://testserver/v1/activity/cohort/1?limit=5&offset=10",
            "results": [DATASTORE_PRIVATE_SEED],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(ndb_init_mock.call_args_list, [call(StudentActivity)])
        self.assertEqual(
            mock.fetch.call_args_list, [call([FilterNode("cohort", "=", model.cohort.slug)], limit=5, offset=0)]
        )
        self.assertEqual(mock.count.call_args_list, [call([FilterNode("cohort", "=", model.cohort.slug)])])

    @patch.object(NDB, "__init__", new=ndb_init_mock)
    @patch.object(NDB, "fetch", new=ndb_fetch_mock([DATASTORE_PRIVATE_SEED]))
    @patch.object(NDB, "count", new=ndb_count_mock(15))
    def test_cohort_id__with_pagination__second_five(self):
        from breathecode.utils import NDB as mock

        ndb_init_mock.call_args_list = []
        mock.fetch.call_args_list = []
        mock.count.call_args_list = []

        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="read_activity", role="potato", cohort=True
        )

        url = reverse_lazy("activity:cohort_id", kwargs={"cohort_id": 1}) + "?limit=5&offset=5"
        response = self.client.get(url)

        json = response.json()
        expected = {
            "count": 15,
            "first": "http://testserver/v1/activity/cohort/1?limit=5",
            "next": "http://testserver/v1/activity/cohort/1?limit=5&offset=10",
            "previous": "http://testserver/v1/activity/cohort/1?limit=5",
            "last": "http://testserver/v1/activity/cohort/1?limit=5&offset=10",
            "results": [DATASTORE_PRIVATE_SEED],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(ndb_init_mock.call_args_list, [call(StudentActivity)])
        self.assertEqual(
            mock.fetch.call_args_list, [call([FilterNode("cohort", "=", model.cohort.slug)], limit=5, offset=5)]
        )
        self.assertEqual(mock.count.call_args_list, [call([FilterNode("cohort", "=", model.cohort.slug)])])

    @patch.object(NDB, "__init__", new=ndb_init_mock)
    @patch.object(NDB, "fetch", new=ndb_fetch_mock([DATASTORE_PRIVATE_SEED]))
    @patch.object(NDB, "count", new=ndb_count_mock(15))
    def test_cohort_id__with_pagination__last_five(self):
        from breathecode.utils import NDB as mock

        ndb_init_mock.call_args_list = []
        mock.fetch.call_args_list = []
        mock.count.call_args_list = []

        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="read_activity", role="potato", cohort=True
        )

        url = reverse_lazy("activity:cohort_id", kwargs={"cohort_id": 1}) + "?limit=5&offset=10"
        response = self.client.get(url)

        json = response.json()
        expected = {
            "count": 15,
            "first": "http://testserver/v1/activity/cohort/1?limit=5",
            "next": None,
            "previous": "http://testserver/v1/activity/cohort/1?limit=5&offset=5",
            "last": None,
            "results": [DATASTORE_PRIVATE_SEED],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(ndb_init_mock.call_args_list, [call(StudentActivity)])
        self.assertEqual(
            mock.fetch.call_args_list, [call([FilterNode("cohort", "=", model.cohort.slug)], limit=5, offset=10)]
        )
        self.assertEqual(mock.count.call_args_list, [call([FilterNode("cohort", "=", model.cohort.slug)])])
