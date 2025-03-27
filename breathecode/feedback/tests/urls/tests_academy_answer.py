"""
Test /answer
"""

import re
import urllib
from unittest.mock import MagicMock, call, patch

from django.urls.base import reverse_lazy
from rest_framework import status

from breathecode.feedback.caches import AnswerCache
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_blob_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_client_mock,
)
from breathecode.utils.api_view_extensions.api_view_extension_handlers import APIViewExtensionHandlers

from ..mixins import FeedbackTestCase


def get_serializer(self, answer, cohort=None, academy=None, mentor=None, user=None, event=None, profile=None, data={}):
    if cohort:
        cohort = {
            "id": cohort.id,
            "name": cohort.name,
            "slug": cohort.slug,
        }

    if profile:
        profile = {
            "avatar_url": profile.avatar_url,
        }

    if mentor:
        mentor = {
            "first_name": mentor.first_name,
            "id": mentor.id,
            "last_name": mentor.last_name,
            "profile": profile,
        }

    if academy:
        academy = {
            "id": academy.id,
            "name": academy.name,
            "slug": academy.slug,
        }

    if user:
        user = {
            "first_name": user.first_name,
            "id": user.id,
            "last_name": user.last_name,
            "profile": profile,
        }

    if event:
        event = {
            "description": event.description,
            "excerpt": event.excerpt,
            "id": event.id,
            "lang": event.lang,
            "title": event.title,
        }

    return {
        "created_at": self.datetime_to_iso(answer.created_at),
        "academy": academy,
        "cohort": cohort,
        "asset": None,
        "mentorship_session": None,
        "question_by_slug": None,
        "live_class": None,
        "comment": answer.comment,
        "event": event,
        "highest": answer.highest,
        "id": answer.id,
        "lang": answer.lang,
        "lowest": answer.lowest,
        "mentor": mentor,
        "score": answer.score,
        "status": answer.status,
        "title": answer.title,
        "user": user,
        **data,
    }


class AnswerTestSuite(FeedbackTestCase):
    """Test /answer"""

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_answer_without_auth(self):
        """Test /answer without auth"""
        url = reverse_lazy("feedback:answer")
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_answer_wrong_academy(self):
        """Test /answer without auth"""
        url = reverse_lazy("feedback:answer")
        response = self.client.get(url, **{"HTTP_Academy": 1})
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_answer_without_capability(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy("feedback:answer")
        self.generate_models(authenticate=True)
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json,
            {"detail": "You (user: 1) don't have this capability: read_nps_answers for academy 1", "status_code": 403},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_answer_without_data(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        models = self.generate_models(
            authenticate=True, profile_academy=True, capability="read_nps_answers", role="potato"
        )
        url = reverse_lazy("feedback:answer")
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_answer(), 0)

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_answer_with_data(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, answer=True, profile_academy=True, capability="read_nps_answers", role="potato"
        )
        db = self.model_to_dict(model, "answer")
        url = reverse_lazy("feedback:answer")
        response = self.client.get(url)
        json = response.json()

        json = [{**x, "created_at": None} for x in json if self.assertDatetime(x["created_at"])]

        self.assertEqual(
            json,
            [
                get_serializer(
                    self,
                    model.answer,
                    cohort=model.cohort,
                    academy=model.academy,
                    user=model.user,
                    data={
                        "mentor": {
                            "first_name": model.user.first_name,
                            "id": model.user.id,
                            "last_name": model.user.last_name,
                            "profile": None,
                        },
                        "created_at": None,
                    },
                ),
            ],
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("feedback.Answer"), [db])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_answer__with_data__with_profile(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            answer=True,
            profile_academy=True,
            profile=True,
            capability="read_nps_answers",
            role="potato",
        )
        db = self.model_to_dict(model, "answer")
        url = reverse_lazy("feedback:answer")
        response = self.client.get(url)
        json = response.json()

        json = [{**x, "created_at": None} for x in json if self.assertDatetime(x["created_at"])]

        self.assertEqual(
            json,
            [
                get_serializer(
                    self,
                    model.answer,
                    cohort=model.cohort,
                    academy=model.academy,
                    user=model.user,
                    profile=model.profile,
                    data={
                        "mentor": {
                            "first_name": model.user.first_name,
                            "id": model.user.id,
                            "last_name": model.user.last_name,
                            "profile": {"avatar_url": None},
                        },
                        "created_at": None,
                    },
                ),
            ],
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("feedback.Answer"), [db])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_answer_with_bad_param_user_with_data(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            user=True,
            answer=True,
            profile_academy=True,
            capability="read_nps_answers",
            role="potato",
        )
        db = self.model_to_dict(model, "answer")
        params = {"user": 9999}
        base_url = reverse_lazy("feedback:answer")
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("feedback.Answer"), [db])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_answer_with_param_user_with_data(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            user=True,
            answer=True,
            profile_academy=True,
            capability="read_nps_answers",
            role="potato",
        )
        db = self.model_to_dict(model, "answer")
        params = {
            "user": model["user"].id,
        }
        base_url = reverse_lazy("feedback:answer")
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        response = self.client.get(url)
        json = response.json()

        json = [{**x, "created_at": None} for x in json if self.assertDatetime(x["created_at"])]

        self.assertEqual(
            json,
            [
                get_serializer(
                    self,
                    model.answer,
                    cohort=model.cohort,
                    academy=model.academy,
                    user=model.user,
                    data={
                        "mentor": {
                            "first_name": model.user.first_name,
                            "id": model.user.id,
                            "last_name": model.user.last_name,
                            "profile": None,
                        },
                        "created_at": None,
                    },
                ),
            ],
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("feedback.Answer"), [db])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_answer_with_bad_param_cohort_with_data(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            user=True,
            cohort=True,
            answer=True,
            profile_academy=True,
            capability="read_nps_answers",
            role="potato",
        )
        db = self.model_to_dict(model, "answer")
        params = {
            "cohort": "they-killed-kenny",
        }
        base_url = reverse_lazy("feedback:answer")
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("feedback.Answer"), [db])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_answer_with_param_cohort_with_data(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            user=True,
            cohort=True,
            answer=True,
            profile_academy=True,
            capability="read_nps_answers",
            role="potato",
        )
        db = self.model_to_dict(model, "answer")
        params = {
            "cohort": model["cohort"].slug,
        }
        base_url = reverse_lazy("feedback:answer")
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        response = self.client.get(url)
        json = response.json()

        json = [{**x, "created_at": None} for x in json if self.assertDatetime(x["created_at"])]

        self.assertEqual(
            json,
            [
                get_serializer(
                    self,
                    model.answer,
                    cohort=model.cohort,
                    academy=model.academy,
                    user=model.user,
                    data={
                        "mentor": {
                            "first_name": model.user.first_name,
                            "id": model.user.id,
                            "last_name": model.user.last_name,
                            "profile": None,
                        },
                        "created_at": None,
                    },
                ),
            ],
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("feedback.Answer"), [db])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_answer_with_param_academy_with_data(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            user=True,
            cohort=True,
            academy=True,
            answer=True,
            profile_academy=True,
            capability="read_nps_answers",
            role="potato",
        )
        db = self.model_to_dict(model, "answer")
        params = {
            "academy": model["academy"].id,
        }
        base_url = reverse_lazy("feedback:answer")
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        response = self.client.get(url)
        json = response.json()

        json = [{**x, "created_at": None} for x in json if self.assertDatetime(x["created_at"])]

        self.assertEqual(
            json,
            [
                get_serializer(
                    self,
                    model.answer,
                    cohort=model.cohort,
                    academy=model.academy,
                    user=model.user,
                    data={
                        "mentor": {
                            "first_name": model.user.first_name,
                            "id": model.user.id,
                            "last_name": model.user.last_name,
                            "profile": None,
                        },
                        "created_at": None,
                    },
                ),
            ],
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("feedback.Answer"), [db])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_answer_with_bad_param_mentor_with_data(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            user=True,
            cohort=True,
            academy=True,
            answer=True,
            profile_academy=True,
            capability="read_nps_answers",
            role="potato",
        )
        db = self.model_to_dict(model, "answer")
        params = {
            "mentor": 9999,
        }
        base_url = reverse_lazy("feedback:answer")
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("feedback.Answer"), [db])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_answer_with_param_mentor_with_data(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            user=True,
            cohort=True,
            academy=True,
            answer=True,
            profile_academy=True,
            capability="read_nps_answers",
            role="potato",
        )
        db = self.model_to_dict(model, "answer")
        params = {
            "mentor": model["user"].id,
        }
        base_url = reverse_lazy("feedback:answer")
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        response = self.client.get(url, headers={"Academy": model["academy"].id})
        json = response.json()

        json = [{**x, "created_at": None} for x in json if self.assertDatetime(x["created_at"])]

        self.assertEqual(
            json,
            [
                get_serializer(
                    self,
                    model.answer,
                    cohort=model.cohort,
                    academy=model.academy,
                    user=model.user,
                    data={
                        "mentor": {
                            "first_name": model.user.first_name,
                            "id": model.user.id,
                            "last_name": model.user.last_name,
                            "profile": None,
                        },
                        "created_at": None,
                    },
                ),
            ],
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("feedback.Answer"), [db])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_answer_with_bad_param_event_with_data(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            user=True,
            cohort=True,
            academy=True,
            answer=True,
            event=True,
            profile_academy=True,
            capability="read_nps_answers",
            role="potato",
        )
        db = self.model_to_dict(model, "answer")
        params = {
            "event": 9999,
        }
        base_url = reverse_lazy("feedback:answer")
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("feedback.Answer"), [db])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_answer_with_param_event_with_data(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            user=True,
            cohort=True,
            academy=True,
            answer=True,
            event=True,
            profile_academy=True,
            capability="read_nps_answers",
            role="potato",
        )
        db = self.model_to_dict(model, "answer")
        params = {
            "event": model["event"].id,
        }
        base_url = reverse_lazy("feedback:answer")
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        response = self.client.get(url)
        json = response.json()

        json = [{**x, "created_at": None} for x in json if self.assertDatetime(x["created_at"])]

        self.assertEqual(
            json,
            [
                get_serializer(
                    self,
                    model.answer,
                    cohort=model.cohort,
                    academy=model.academy,
                    user=model.user,
                    event=model.event,
                    data={
                        "mentor": {
                            "first_name": model.user.first_name,
                            "id": model.user.id,
                            "last_name": model.user.last_name,
                            "profile": None,
                        },
                        "created_at": None,
                    },
                ),
            ],
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("feedback.Answer"), [db])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_answer_with_bad_param_score_with_data(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        base = self.generate_models(
            authenticate=True,
            user=True,
            cohort=True,
            academy=True,
            event=True,
            profile_academy=True,
            capability="read_nps_answers",
            role="potato",
        )

        for score in range(1, 10):
            self.remove_all_answer()

            answer_kwargs = {"score": score}
            model = self.generate_models(answer=True, answer_kwargs=answer_kwargs, models=base)
            db = self.model_to_dict(model, "answer")
            params = {
                "score": 1 if score == 10 else score + 1,
            }
            base_url = reverse_lazy("feedback:answer")
            url = f"{base_url}?{urllib.parse.urlencode(params)}"
            response = self.client.get(url)
            json = response.json()

            self.assertEqual(json, [])

            db["score"] = score
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(self.bc.database.list_of("feedback.Answer"), [db])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_answer_with_param_score_with_data(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        base = self.generate_models(
            authenticate=True,
            user=True,
            cohort=True,
            academy=True,
            event=True,
            profile_academy=True,
            capability="read_nps_answers",
            role="potato",
        )

        for score in range(1, 10):
            self.remove_all_answer()

            answer_kwargs = {"score": score}
            model = self.generate_models(answer=True, answer_kwargs=answer_kwargs, models=base)
            db = self.model_to_dict(model, "answer")
            params = {
                "score": score,
            }
            base_url = reverse_lazy("feedback:answer")
            url = f"{base_url}?{urllib.parse.urlencode(params)}"
            response = self.client.get(url, headers={"Academy": model["academy"].id})
            json = response.json()

            json = [{**x, "created_at": None} for x in json if self.assertDatetime(x["created_at"])]

            self.assertEqual(
                json,
                [
                    get_serializer(
                        self,
                        model.answer,
                        cohort=model.cohort,
                        academy=model.academy,
                        user=model.user,
                        event=model.event,
                        data={
                            "mentor": {
                                "first_name": model.user.first_name,
                                "id": model.user.id,
                                "last_name": model.user.last_name,
                                "profile": None,
                            },
                            "created_at": None,
                        },
                    ),
                ],
            )

            db["score"] = score

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(self.bc.database.list_of("feedback.Answer"), [db])

    """
    🔽🔽🔽 With full like querystring
    """

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_answer_with_query_like_full_name(self):
        """Test /answer with like full name"""
        self.headers(academy=1)
        base = self.generate_models(
            authenticate=True, profile_academy=True, capability="read_nps_answers", role="potato"
        )
        del base["user"]
        user_kwargs = {
            "email": "b@b.com",
            "first_name": "Rene",
            "last_name": "Descartes",
        }
        user_kwargs_2 = {
            "email": "a@a.com",
            "first_name": "Reinaldo",
            "last_name": "Descarado",
        }
        models = [
            self.generate_models(user=True, answer=True, user_kwargs=user_kwargs, models=base),
            self.generate_models(user=True, answer=True, user_kwargs=user_kwargs_2, models=base),
        ]

        base_url = reverse_lazy("feedback:answer")
        url = f"{base_url}?like=Rene Descartes"

        response = self.client.get(url)
        json = response.json()

        expected = [
            get_serializer(
                self,
                models[0].answer,
                cohort=models[0].cohort,
                academy=models[0].academy,
                user=models[0].user,
                data={
                    "mentor": {
                        "first_name": models[0].user.first_name,
                        "id": models[0].user.id,
                        "last_name": models[0].user.last_name,
                        "profile": None,
                    },
                },
            ),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_answer_with_query_like_first_name(self):
        """Test /answer with like first name"""
        self.headers(academy=1)
        base = self.generate_models(
            authenticate=True, profile_academy=True, capability="read_nps_answers", role="potato"
        )
        del base["user"]
        user_kwargs = {
            "email": "b@b.com",
            "first_name": "Rene",
            "last_name": "Descartes",
        }
        user_kwargs_2 = {
            "email": "a@a.com",
            "first_name": "Reinaldo",
            "last_name": "Descarado",
        }
        models = [
            self.generate_models(user=True, answer=True, user_kwargs=user_kwargs, models=base),
            self.generate_models(user=True, answer=True, user_kwargs=user_kwargs_2, models=base),
        ]
        base_url = reverse_lazy("feedback:answer")
        url = f"{base_url}?like=Rene"

        response = self.client.get(url)
        json = response.json()

        expected = [
            get_serializer(
                self,
                models[0].answer,
                cohort=models[0].cohort,
                academy=models[0].academy,
                user=models[0].user,
                data={
                    "mentor": {
                        "first_name": models[0].user.first_name,
                        "id": models[0].user.id,
                        "last_name": models[0].user.last_name,
                        "profile": None,
                    },
                },
            ),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_answer_with_query_like_last_name(self):
        """Test /answer with like last name"""
        self.headers(academy=1)
        base = self.generate_models(
            authenticate=True, profile_academy=True, capability="read_nps_answers", role="potato"
        )
        del base["user"]
        user_kwargs = {
            "email": "b@b.com",
            "first_name": "Rene",
            "last_name": "Descartes",
        }
        user_kwargs_2 = {
            "email": "a@a.com",
            "first_name": "Reinaldo",
            "last_name": "Descarado",
        }
        models = [
            self.generate_models(user=True, answer=True, user_kwargs=user_kwargs, models=base),
            self.generate_models(user=True, answer=True, user_kwargs=user_kwargs_2, models=base),
        ]
        base_url = reverse_lazy("feedback:answer")
        url = f"{base_url}?like=Descartes"

        response = self.client.get(url)
        json = response.json()

        expected = [
            get_serializer(
                self,
                models[0].answer,
                cohort=models[0].cohort,
                academy=models[0].academy,
                user=models[0].user,
                data={
                    "mentor": {
                        "first_name": models[0].user.first_name,
                        "id": models[0].user.id,
                        "last_name": models[0].user.last_name,
                        "profile": None,
                    },
                },
            ),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_answer_with_query_like_email(self):
        """Test /answer with like email"""
        self.headers(academy=1)
        base = self.generate_models(
            authenticate=True, profile_academy=True, capability="read_nps_answers", role="potato"
        )
        del base["user"]
        user_kwargs = {
            "email": "b@b.com",
            "first_name": "Rene",
            "last_name": "Descartes",
        }
        user_kwargs_2 = {
            "email": "a@a.com",
            "first_name": "Reinaldo",
            "last_name": "Descarado",
        }
        models = [
            self.generate_models(user=True, answer=True, user_kwargs=user_kwargs, models=base),
            self.generate_models(user=True, answer=True, user_kwargs=user_kwargs_2, models=base),
        ]
        base_url = reverse_lazy("feedback:answer")
        url = f"{base_url}?like=b@b.com"

        response = self.client.get(url)
        json = response.json()

        expected = [
            get_serializer(
                self,
                models[0].answer,
                cohort=models[0].cohort,
                academy=models[0].academy,
                user=models[0].user,
                data={
                    "mentor": {
                        "first_name": models[0].user.first_name,
                        "id": models[0].user.id,
                        "last_name": models[0].user.last_name,
                        "profile": None,
                    },
                },
            ),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    """
    🔽🔽🔽 Spy extensions
    """

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch.object(APIViewExtensionHandlers, "_spy_extensions", MagicMock())
    def test_answer__spy_extensions(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        models = self.generate_models(
            authenticate=True, profile_academy=True, capability="read_nps_answers", role="potato"
        )

        url = reverse_lazy("feedback:answer")
        self.client.get(url)

        self.bc.check.calls(
            APIViewExtensionHandlers._spy_extensions.call_args_list,
            [
                call(
                    ["CacheExtension", "LanguageExtension", "LookupExtension", "PaginationExtension", "SortExtension"]
                ),
            ],
        )

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch.object(APIViewExtensionHandlers, "_spy_extension_arguments", MagicMock())
    def test_answer__spy_extension_arguments(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        models = self.generate_models(
            authenticate=True, profile_academy=True, capability="read_nps_answers", role="potato"
        )

        url = reverse_lazy("feedback:answer")
        self.client.get(url)

        self.assertEqual(
            APIViewExtensionHandlers._spy_extension_arguments.call_args_list,
            [
                call(cache=AnswerCache, sort="-created_at", paginate=True),
            ],
        )
