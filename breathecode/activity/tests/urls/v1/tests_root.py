"""
Test /answer
"""

from django.utils import timezone
from datetime import timedelta
from unittest.mock import MagicMock, call, patch

from django.urls.base import reverse_lazy
from rest_framework import status

from breathecode.services.google_cloud import Datastore

from ...mixins import MediaTestCase

DATASTORE_SHARED_SEED = [
    {
        "academy_id": 0,
        "cohort": None,
        "created_at": (timezone.now() + timedelta(days=1)).isoformat() + "Z",
        "data": None,
        "day": 13,
        "email": "konan@naruto.io",
        "slug": "breathecode_login",
        "user_agent": "bc/test",
        "user_id": 1,
    },
]
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


def datastore_fetch_mock(first_fetch=[], second_fetch=[]):

    class Vars:
        fetch_call_counter = 0
        fetch_call_one = first_fetch
        fetch_call_two = second_fetch

    Vars.fetch_call_counter = 0

    def fetch(**kwargs):
        Vars.fetch_call_counter += 1

        if Vars.fetch_call_counter % 2 == 1:
            return Vars.fetch_call_one

        if Vars.fetch_call_counter % 2 == 0:
            return Vars.fetch_call_two

        return []

    return MagicMock(side_effect=fetch)


def datastore_update_mock():

    def update(key: str, data: dict):
        pass

    return MagicMock(side_effect=update)


class MediaTestSuite(MediaTestCase):
    """Test /answer"""

    """
    🔽🔽🔽 Auth
    """

    def test_type__without_auth(self):
        url = reverse_lazy("activity:root")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_type__wrong_academy(self):
        self.headers(academy=1)
        url = reverse_lazy("activity:root")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_type__without_capability(self):
        self.headers(academy=1)
        url = reverse_lazy("activity:root")
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
    🔽🔽🔽 Without data
    """

    @patch.object(Datastore, "__init__", new=lambda x: None)
    @patch.object(Datastore, "fetch", new=datastore_fetch_mock(first_fetch=[], second_fetch=[]))
    def test_type__without_data(self):
        from breathecode.services.google_cloud import Datastore as mock

        mock.fetch.call_args_list = []

        self.headers(academy=1)
        self.generate_models(authenticate=True, profile_academy=True, capability="read_activity", role="potato")

        url = reverse_lazy("activity:root")
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            mock.fetch.call_args_list,
            [
                call(kind="student_activity", academy_id=1),
                call(kind="student_activity", academy_id=0),
            ],
        )

    """
    🔽🔽🔽 With data
    """

    @patch.object(Datastore, "__init__", new=lambda x: None)
    @patch.object(Datastore, "fetch", new=datastore_fetch_mock(first_fetch=[], second_fetch=DATASTORE_SHARED_SEED))
    def test_type__just_have_public_activities(self):
        from breathecode.services.google_cloud import Datastore as mock

        mock.fetch.call_args_list = []

        self.headers(academy=1)
        self.generate_models(authenticate=True, profile_academy=True, capability="read_activity", role="potato")

        url = reverse_lazy("activity:root")
        response = self.client.get(url)

        json = response.json()
        expected = [
            {
                "academy_id": 0,
                "cohort": None,
                "created_at": DATASTORE_SHARED_SEED[0]["created_at"],
                "data": None,
                "day": 13,
                "email": "konan@naruto.io",
                "slug": "breathecode_login",
                "user_agent": "bc/test",
                "user_id": 1,
            },
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            mock.fetch.call_args_list,
            [
                call(kind="student_activity", academy_id=1),
                call(kind="student_activity", academy_id=0),
            ],
        )

    @patch.object(Datastore, "__init__", new=lambda x: None)
    @patch.object(Datastore, "fetch", new=datastore_fetch_mock(first_fetch=DATASTORE_PRIVATE_SEED, second_fetch=[]))
    def test_type__just_have_activities_from_current_academy(self):
        from breathecode.services.google_cloud import Datastore as mock

        mock.fetch.call_args_list = []

        self.headers(academy=1)
        self.generate_models(authenticate=True, profile_academy=True, capability="read_activity", role="potato")

        url = reverse_lazy("activity:root")
        response = self.client.get(url)

        json = response.json()
        expected = [
            {
                "academy_id": 1,
                "cohort": "miami-downtown-pt-xx",
                "created_at": DATASTORE_PRIVATE_SEED[0]["created_at"],
                "data": '{"cohort": "miami-downtown-pt-xx", "day": "13"}',
                "day": 13,
                "email": "konan@naruto.io",
                "slug": "classroom_attendance",
                "user_agent": "bc/test",
                "user_id": 1,
            },
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            mock.fetch.call_args_list,
            [
                call(kind="student_activity", academy_id=1),
                call(kind="student_activity", academy_id=0),
            ],
        )

    @patch.object(Datastore, "__init__", new=lambda x: None)
    @patch.object(
        Datastore,
        "fetch",
        new=datastore_fetch_mock(first_fetch=DATASTORE_PRIVATE_SEED, second_fetch=DATASTORE_SHARED_SEED),
    )
    def test_type__have_activities_public_and_from_current_academy(self):
        from breathecode.services.google_cloud import Datastore as mock

        mock.fetch.call_args_list = []

        self.headers(academy=1)
        self.generate_models(authenticate=True, profile_academy=True, capability="read_activity", role="potato")

        url = reverse_lazy("activity:root")
        response = self.client.get(url)

        json = response.json()
        expected = [
            {
                "academy_id": 1,
                "cohort": "miami-downtown-pt-xx",
                "created_at": DATASTORE_PRIVATE_SEED[0]["created_at"],
                "data": '{"cohort": "miami-downtown-pt-xx", "day": "13"}',
                "day": 13,
                "email": "konan@naruto.io",
                "slug": "classroom_attendance",
                "user_agent": "bc/test",
                "user_id": 1,
            },
            {
                "academy_id": 0,
                "cohort": None,
                "created_at": DATASTORE_SHARED_SEED[0]["created_at"],
                "data": None,
                "day": 13,
                "email": "konan@naruto.io",
                "slug": "breathecode_login",
                "user_agent": "bc/test",
                "user_id": 1,
            },
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            mock.fetch.call_args_list,
            [
                call(kind="student_activity", academy_id=1),
                call(kind="student_activity", academy_id=0),
            ],
        )

    """
    🔽🔽🔽 Slug in querystring
    """

    @patch.object(Datastore, "__init__", new=lambda x: None)
    @patch.object(Datastore, "fetch", new=datastore_fetch_mock(first_fetch=[], second_fetch=[]))
    def test_type__with_data__bad_slug_by_querystring(self):
        from breathecode.services.google_cloud import Datastore as mock

        mock.fetch.call_args_list = []

        self.headers(academy=1)
        self.generate_models(authenticate=True, profile_academy=True, capability="read_activity", role="potato")

        url = reverse_lazy("activity:root") + "?slug=asdasd"
        response = self.client.get(url)

        json = response.json()
        expected = {
            "detail": "activity-not-found",
            "status_code": 400,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(mock.fetch.call_args_list, [])

    @patch.object(Datastore, "__init__", new=lambda x: None)
    @patch.object(Datastore, "fetch", new=datastore_fetch_mock(first_fetch=[], second_fetch=[]))
    def test_type__with_data__slug_by_querystring__its_not_exist(self):
        from breathecode.services.google_cloud import Datastore as mock

        mock.fetch.call_args_list = []

        self.headers(academy=1)
        self.generate_models(authenticate=True, profile_academy=True, capability="read_activity", role="potato")

        url = reverse_lazy("activity:root") + "?slug=lesson_opened"
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            mock.fetch.call_args_list,
            [
                call(kind="student_activity", slug="lesson_opened", academy_id=1),
                call(kind="student_activity", slug="lesson_opened", academy_id=0),
            ],
        )

    @patch.object(Datastore, "__init__", new=lambda x: None)
    @patch.object(Datastore, "fetch", new=datastore_fetch_mock(first_fetch=[], second_fetch=DATASTORE_SHARED_SEED))
    def test_type__with_data__slug_by_querystring__its_exist(self):
        from breathecode.services.google_cloud import Datastore as mock

        mock.fetch.call_args_list = []

        self.headers(academy=1)
        self.generate_models(authenticate=True, profile_academy=True, capability="read_activity", role="potato")

        url = reverse_lazy("activity:root") + "?slug=breathecode_login"
        response = self.client.get(url)

        json = response.json()
        expected = [
            {
                "academy_id": 0,
                "cohort": None,
                "created_at": DATASTORE_SHARED_SEED[0]["created_at"],
                "data": None,
                "day": 13,
                "email": "konan@naruto.io",
                "slug": "breathecode_login",
                "user_agent": "bc/test",
                "user_id": 1,
            },
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            mock.fetch.call_args_list,
            [
                call(kind="student_activity", slug="breathecode_login", academy_id=1),
                call(kind="student_activity", slug="breathecode_login", academy_id=0),
            ],
        )

    """
    🔽🔽🔽 Cohort in querystring
    """

    @patch.object(Datastore, "__init__", new=lambda x: None)
    @patch.object(Datastore, "fetch", new=datastore_fetch_mock(first_fetch=[], second_fetch=[]))
    def test_type__with_data__bad_cohort_by_querystring(self):
        from breathecode.services.google_cloud import Datastore as mock

        mock.fetch.call_args_list = []

        self.headers(academy=1)
        self.generate_models(authenticate=True, profile_academy=True, capability="read_activity", role="potato")

        url = reverse_lazy("activity:root") + "?cohort=asdasd"
        response = self.client.get(url)

        json = response.json()
        expected = {
            "detail": "cohort-not-found",
            "status_code": 400,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(mock.fetch.call_args_list, [])

    @patch.object(Datastore, "__init__", new=lambda x: None)
    @patch.object(Datastore, "fetch", new=datastore_fetch_mock(first_fetch=[], second_fetch=[]))
    def test_type__with_data__cohort_by_querystring__its_not_exist(self):
        from breathecode.services.google_cloud import Datastore as mock

        mock.fetch.call_args_list = []

        self.headers(academy=1)
        cohort_kwargs = {"slug": "miami-downtown-pt-xx"}
        self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="read_activity",
            role="potato",
            cohort=True,
            cohort_kwargs=cohort_kwargs,
        )

        url = reverse_lazy("activity:root") + "?cohort=miami-downtown-pt-xx"
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            mock.fetch.call_args_list,
            [
                call(kind="student_activity", cohort="miami-downtown-pt-xx", academy_id=1),
                call(kind="student_activity", cohort="miami-downtown-pt-xx", academy_id=0),
            ],
        )

    @patch.object(Datastore, "__init__", new=lambda x: None)
    @patch.object(Datastore, "fetch", new=datastore_fetch_mock(first_fetch=DATASTORE_PRIVATE_SEED, second_fetch=[]))
    def test_type__with_data__cohort_by_querystring__its_exist(self):
        from breathecode.services.google_cloud import Datastore as mock

        mock.fetch.call_args_list = []

        self.headers(academy=1)
        cohort_kwargs = {"slug": "miami-downtown-pt-xx"}
        self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="read_activity",
            role="potato",
            cohort=True,
            cohort_kwargs=cohort_kwargs,
        )

        url = reverse_lazy("activity:root") + "?cohort=miami-downtown-pt-xx"
        response = self.client.get(url)

        json = response.json()
        expected = [
            {
                "academy_id": 1,
                "cohort": "miami-downtown-pt-xx",
                "created_at": DATASTORE_PRIVATE_SEED[0]["created_at"],
                "data": '{"cohort": "miami-downtown-pt-xx", "day": "13"}',
                "day": 13,
                "email": "konan@naruto.io",
                "slug": "classroom_attendance",
                "user_agent": "bc/test",
                "user_id": 1,
            },
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            mock.fetch.call_args_list,
            [
                call(kind="student_activity", cohort="miami-downtown-pt-xx", academy_id=1),
                call(kind="student_activity", cohort="miami-downtown-pt-xx", academy_id=0),
            ],
        )

    """
    🔽🔽🔽 User id in querystring
    """

    @patch.object(Datastore, "__init__", new=lambda x: None)
    @patch.object(Datastore, "fetch", new=datastore_fetch_mock(first_fetch=[], second_fetch=[]))
    def test_type__with_data__bad_user_id_by_querystring(self):
        from breathecode.services.google_cloud import Datastore as mock

        mock.fetch.call_args_list = []

        self.headers(academy=1)
        self.generate_models(authenticate=True, profile_academy=True, capability="read_activity", role="potato")

        url = reverse_lazy("activity:root") + "?user_id=0"
        response = self.client.get(url)

        json = response.json()
        expected = {
            "detail": "user-not-exists",
            "status_code": 400,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(mock.fetch.call_args_list, [])

    @patch.object(Datastore, "__init__", new=lambda x: None)
    @patch.object(Datastore, "fetch", new=datastore_fetch_mock(first_fetch=[], second_fetch=[]))
    def test_type__with_data__user_id_is_string_by_querystring(self):
        from breathecode.services.google_cloud import Datastore as mock

        mock.fetch.call_args_list = []

        self.headers(academy=1)
        self.generate_models(authenticate=True, profile_academy=True, capability="read_activity", role="potato")

        url = reverse_lazy("activity:root") + "?user_id=they-killed-kenny"
        response = self.client.get(url)

        json = response.json()
        expected = {
            "detail": "bad-user-id",
            "status_code": 400,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(mock.fetch.call_args_list, [])

    @patch.object(Datastore, "__init__", new=lambda x: None)
    @patch.object(Datastore, "fetch", new=datastore_fetch_mock(first_fetch=[], second_fetch=[]))
    def test_type__with_data__user_id_by_querystring__its_not_exist(self):
        from breathecode.services.google_cloud import Datastore as mock

        mock.fetch.call_args_list = []

        self.headers(academy=1)
        cohort_kwargs = {"slug": "miami-downtown-pt-xx"}
        self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="read_activity",
            role="potato",
            cohort=True,
            cohort_kwargs=cohort_kwargs,
        )

        url = reverse_lazy("activity:root") + "?user_id=1"
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            mock.fetch.call_args_list,
            [
                call(kind="student_activity", user_id=1, academy_id=1),
                call(kind="student_activity", user_id=1, academy_id=0),
            ],
        )

    @patch.object(Datastore, "__init__", new=lambda x: None)
    @patch.object(Datastore, "fetch", new=datastore_fetch_mock(first_fetch=DATASTORE_PRIVATE_SEED, second_fetch=[]))
    def test_type__with_data__user_id_by_querystring__its_exist(self):
        from breathecode.services.google_cloud import Datastore as mock

        mock.fetch.call_args_list = []

        self.headers(academy=1)
        cohort_kwargs = {"slug": "miami-downtown-pt-xx"}
        self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="read_activity",
            role="potato",
            cohort=True,
            cohort_kwargs=cohort_kwargs,
        )

        url = reverse_lazy("activity:root") + "?user_id=1"
        response = self.client.get(url)

        json = response.json()
        expected = [
            {
                "academy_id": 1,
                "cohort": "miami-downtown-pt-xx",
                "created_at": DATASTORE_PRIVATE_SEED[0]["created_at"],
                "data": '{"cohort": "miami-downtown-pt-xx", "day": "13"}',
                "day": 13,
                "email": "konan@naruto.io",
                "slug": "classroom_attendance",
                "user_agent": "bc/test",
                "user_id": 1,
            },
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            mock.fetch.call_args_list,
            [
                call(kind="student_activity", user_id=1, academy_id=1),
                call(kind="student_activity", user_id=1, academy_id=0),
            ],
        )

    """
    🔽🔽🔽 Email in querystring
    """

    @patch.object(Datastore, "__init__", new=lambda x: None)
    @patch.object(Datastore, "fetch", new=datastore_fetch_mock(first_fetch=[], second_fetch=[]))
    def test_type__with_data__bad_email_by_querystring(self):
        from breathecode.services.google_cloud import Datastore as mock

        mock.fetch.call_args_list = []

        self.headers(academy=1)
        self.generate_models(authenticate=True, profile_academy=True, capability="read_activity", role="potato")

        url = reverse_lazy("activity:root") + "?email=xyz"
        response = self.client.get(url)

        json = response.json()
        expected = {
            "detail": "user-not-exists",
            "status_code": 400,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(mock.fetch.call_args_list, [])

    @patch.object(Datastore, "__init__", new=lambda x: None)
    @patch.object(Datastore, "fetch", new=datastore_fetch_mock(first_fetch=[], second_fetch=[]))
    def test_type__with_data__email_by_querystring__its_not_exist(self):
        from breathecode.services.google_cloud import Datastore as mock

        mock.fetch.call_args_list = []

        self.headers(academy=1)
        cohort_kwargs = {"slug": "miami-downtown-pt-xx"}
        user_kwargs = {"email": "konan@naruto.io"}
        self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="read_activity",
            role="potato",
            cohort=True,
            cohort_kwargs=cohort_kwargs,
            user_kwargs=user_kwargs,
        )

        url = reverse_lazy("activity:root") + "?email=konan@naruto.io"
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            mock.fetch.call_args_list,
            [
                call(kind="student_activity", email="konan@naruto.io", academy_id=1),
                call(kind="student_activity", email="konan@naruto.io", academy_id=0),
            ],
        )

    @patch.object(Datastore, "__init__", new=lambda x: None)
    @patch.object(Datastore, "fetch", new=datastore_fetch_mock(first_fetch=DATASTORE_PRIVATE_SEED, second_fetch=[]))
    def test_type__with_data__email_by_querystring__its_exist(self):
        from breathecode.services.google_cloud import Datastore as mock

        mock.fetch.call_args_list = []

        self.headers(academy=1)
        cohort_kwargs = {"slug": "miami-downtown-pt-xx"}
        user_kwargs = {"email": "konan@naruto.io"}
        self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="read_activity",
            role="potato",
            cohort=True,
            cohort_kwargs=cohort_kwargs,
            user_kwargs=user_kwargs,
        )

        url = reverse_lazy("activity:root") + "?email=konan@naruto.io"
        response = self.client.get(url)

        json = response.json()
        expected = [
            {
                "academy_id": 1,
                "cohort": "miami-downtown-pt-xx",
                "created_at": DATASTORE_PRIVATE_SEED[0]["created_at"],
                "data": '{"cohort": "miami-downtown-pt-xx", "day": "13"}',
                "day": 13,
                "email": "konan@naruto.io",
                "slug": "classroom_attendance",
                "user_agent": "bc/test",
                "user_id": 1,
            },
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            mock.fetch.call_args_list,
            [
                call(kind="student_activity", email="konan@naruto.io", academy_id=1),
                call(kind="student_activity", email="konan@naruto.io", academy_id=0),
            ],
        )

    """
    🔽🔽🔽 Post missing fields
    """

    @patch.object(Datastore, "__init__", new=lambda x: None)
    @patch.object(Datastore, "update", new=datastore_update_mock())
    def test_user_id__post__missing_slug(self):
        from breathecode.services.google_cloud import Datastore as mock

        mock.update.call_args_list = []

        self.headers(academy=1)
        self.generate_models(authenticate=True, profile_academy=True, capability="crud_activity", role="potato")

        url = reverse_lazy("activity:root")
        data = {}
        response = self.client.post(url, data)

        json = response.json()
        expected = {"detail": "missing-slug", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(mock.update.call_args_list, [])

    @patch.object(Datastore, "__init__", new=lambda x: None)
    @patch.object(Datastore, "update", new=datastore_update_mock())
    def test_user_id__post__missing_user_agent(self):
        from breathecode.services.google_cloud import Datastore as mock

        mock.update.call_args_list = []

        self.headers(academy=1)
        self.generate_models(authenticate=True, profile_academy=True, capability="crud_activity", role="potato")

        url = reverse_lazy("activity:root")
        data = {"slug": "they-killed-kenny"}
        response = self.client.post(url, data)

        json = response.json()
        expected = {"detail": "missing-user-agent", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(mock.update.call_args_list, [])

    """
    🔽🔽🔽 Post bad slug
    """

    @patch.object(Datastore, "__init__", new=lambda x: None)
    @patch.object(Datastore, "update", new=datastore_update_mock())
    def test_user_id__post__with_bad_slug(self):
        from breathecode.services.google_cloud import Datastore as mock

        mock.update.call_args_list = []

        self.headers(academy=1)
        self.generate_models(authenticate=True, profile_academy=True, capability="crud_activity", role="potato")

        url = reverse_lazy("activity:root")
        data = {
            "slug": "they-killed-kenny",
            "user_agent": "bc/test",
        }
        response = self.client.post(url, data, format="json")
        json = response.json()
        expected = {"detail": "activity-not-found", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(mock.update.call_args_list, [])

    """
    🔽🔽🔽 Post with public slug
    """

    @patch.object(Datastore, "__init__", new=lambda x: None)
    @patch.object(Datastore, "update", new=datastore_update_mock())
    def test_user_id__post__with_public_slug(self):
        from breathecode.services.google_cloud import Datastore as mock

        mock.update.call_args_list = []

        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True, capability="crud_activity", role="potato")

        url = reverse_lazy("activity:root")
        data = {
            "slug": "breathecode_login",
            "user_agent": "bc/test",
        }
        response = self.client.post(url, data, format="json")

        json = response.json()

        self.assertDatetime(json["created_at"])
        created_at = json["created_at"]
        del json["created_at"]

        expected = {
            "academy_id": 0,
            "email": model.user.email,
            "slug": "breathecode_login",
            "user_agent": "bc/test",
            "user_id": 1,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            mock.update.call_args_list,
            [
                call(
                    "student_activity",
                    {
                        "slug": "breathecode_login",
                        "user_agent": "bc/test",
                        "created_at": self.iso_to_datetime(created_at),
                        "user_id": 1,
                        "email": model.user.email,
                        "academy_id": 0,
                    },
                ),
            ],
        )

    """
    🔽🔽🔽 Post with private slug missing cohort
    """

    @patch.object(Datastore, "__init__", new=lambda x: None)
    @patch.object(Datastore, "update", new=datastore_update_mock())
    def test_user_id__post__missing_cohort(self):
        from breathecode.services.google_cloud import Datastore as mock

        mock.update.call_args_list = []

        self.headers(academy=1)
        self.generate_models(authenticate=True, profile_academy=True, capability="crud_activity", role="potato")

        url = reverse_lazy("activity:root")
        data = {
            "slug": "nps_survey_answered",
            "user_agent": "bc/test",
        }
        response = self.client.post(url, data, format="json")
        json = response.json()
        expected = {"detail": "missing-cohort", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(mock.update.call_args_list, [])

    """
    🔽🔽🔽 Post with private slug without cohort
    """

    @patch.object(Datastore, "__init__", new=lambda x: None)
    @patch.object(Datastore, "update", new=datastore_update_mock())
    def test_user_id__post__with_private_slug__slug_require_a_cohort(self):
        from breathecode.services.google_cloud import Datastore as mock

        mock.update.call_args_list = []

        self.headers(academy=1)
        self.generate_models(authenticate=True, profile_academy=True, capability="crud_activity", role="potato")

        url = reverse_lazy("activity:root")
        data = {
            "cohort": "they-killed-kenny",
            "slug": "nps_survey_answered",
            "user_agent": "bc/test",
        }
        response = self.client.post(url, data, format="json")
        json = response.json()
        expected = {"detail": "missing-data", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(mock.update.call_args_list, [])

    """
    🔽🔽🔽 Post with private slug without data
    """

    @patch.object(Datastore, "__init__", new=lambda x: None)
    @patch.object(Datastore, "update", new=datastore_update_mock())
    def test_user_id__post__with_private_slug__slug_require_a_data(self):
        from breathecode.services.google_cloud import Datastore as mock

        mock.update.call_args_list = []

        self.headers(academy=1)
        self.generate_models(authenticate=True, profile_academy=True, capability="crud_activity", role="potato")

        url = reverse_lazy("activity:root")
        data = {
            "data": "",
            "cohort": "they-killed-kenny",
            "slug": "nps_survey_answered",
            "user_agent": "bc/test",
        }
        response = self.client.post(url, data, format="json")
        json = response.json()
        expected = {"detail": "data-is-not-a-json", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(mock.update.call_args_list, [])

    """
    🔽🔽🔽 Post with private slug bad cohort
    """

    @patch.object(Datastore, "__init__", new=lambda x: None)
    @patch.object(Datastore, "update", new=datastore_update_mock())
    def test_user_id__post__with_private_slug__cohort_not_exist(self):
        from breathecode.services.google_cloud import Datastore as mock

        mock.update.call_args_list = []

        self.headers(academy=1)
        self.generate_models(authenticate=True, profile_academy=True, capability="crud_activity", role="potato")

        url = reverse_lazy("activity:root")
        data = {
            "data": '{"name": "Freyja"}',
            "cohort": "they-killed-kenny",
            "slug": "nps_survey_answered",
            "user_agent": "bc/test",
        }
        response = self.client.post(url, data, format="json")
        json = response.json()
        expected = {"detail": "cohort-not-exists", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(mock.update.call_args_list, [])

    """
    🔽🔽🔽 Post with private slug field not allowed
    """

    @patch.object(Datastore, "__init__", new=lambda x: None)
    @patch.object(Datastore, "update", new=datastore_update_mock())
    def test_user_id__post__with_private_slug__field_not_allowed(self):
        from breathecode.services.google_cloud import Datastore as mock

        mock.update.call_args_list = []

        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="crud_activity", role="potato", cohort=True
        )

        url = reverse_lazy("activity:root")
        data = {
            "data": '{"name": "Freyja"}',
            "cohort": model.cohort.slug,
            "slug": "nps_survey_answered",
            "user_agent": "bc/test",
            "id": 1,
        }
        response = self.client.post(url, data, format="json")
        json = response.json()
        expected = {"detail": "id-not-allowed", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(mock.update.call_args_list, [])

    """
    🔽🔽🔽 Post with private slug
    """

    @patch.object(Datastore, "__init__", new=lambda x: None)
    @patch.object(Datastore, "update", new=datastore_update_mock())
    def test_user_id__post__with_private_slug__cohort_not_exist___(self):
        from breathecode.services.google_cloud import Datastore as mock

        mock.update.call_args_list = []

        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="crud_activity", role="potato", cohort=True
        )

        url = reverse_lazy("activity:root")
        data = {
            "data": '{"name": "Freyja"}',
            "cohort": model.cohort.slug,
            "slug": "nps_survey_answered",
            "user_agent": "bc/test",
        }
        response = self.client.post(url, data, format="json")
        json = response.json()
        expected = {
            "academy_id": 1,
            "cohort": model.cohort.slug,
            "data": '{"name": "Freyja"}',
            "email": model.user.email,
            "slug": "nps_survey_answered",
            "user_agent": "bc/test",
            "user_id": 1,
        }

        self.assertDatetime(json["created_at"])
        created_at = json["created_at"]
        del json["created_at"]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            mock.update.call_args_list,
            [
                call(
                    "student_activity",
                    {
                        "cohort": model.cohort.slug,
                        "data": '{"name": "Freyja"}',
                        "user_agent": "bc/test",
                        "created_at": self.iso_to_datetime(created_at),
                        "slug": "nps_survey_answered",
                        "user_id": 1,
                        "email": model.user.email,
                        "academy_id": 1,
                    },
                ),
            ],
        )
