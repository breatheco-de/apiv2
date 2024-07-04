import re
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins.new_auth_test_case import AuthTestCase
from breathecode.services import datetime_to_iso_format


class AuthenticateTestSuite(AuthTestCase):
    """Authentication test suite"""

    def test_academy_token_without_auth(self):
        """Test /academy/:id/member/:id without auth"""
        url = reverse_lazy("authenticate:academy_token")
        response = self.client.post(url)
        json = response.json()

        self.assertEqual(
            json,
            {
                "detail": "Authentication credentials were not provided.",
                "status_code": status.HTTP_401_UNAUTHORIZED,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_academy_token_get_without_capability(self):
        """Test /academy/:id/member/:id without auth"""
        self.headers(academy=1)
        self.generate_models(authenticate=True)
        url = reverse_lazy("authenticate:academy_token")
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json,
            {
                "detail": "You (user: 1) don't have this capability: get_academy_token " "for academy 1",
                "status_code": 403,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_academy_token_get_without_user(self):
        """Test /academy/:id/member/:id without auth"""
        role = "konan"
        self.headers(academy=1)
        self.generate_models(authenticate=True, role=role, capability="get_academy_token", profile_academy=True)
        url = reverse_lazy("authenticate:academy_token")
        response = self.client.get(url)
        json = response.json()
        expected = {"detail": "academy-token-not-found", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_academy_token_get_without_token(self):
        """Test /academy/:id/member/:id without auth"""
        role = "konan"
        self.headers(academy=1)
        user_kwargs = {"username": "kenny"}
        academy_kwargs = {"slug": "kenny"}
        self.generate_models(
            authenticate=True,
            role=role,
            user=True,
            capability="get_academy_token",
            profile_academy=True,
            user_kwargs=user_kwargs,
            academy_kwargs=academy_kwargs,
        )
        url = reverse_lazy("authenticate:academy_token")
        response = self.client.get(url)
        json = response.json()
        expected = {"detail": "academy-token-not-found", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_academy_token_post_without_capability(self):
        """Test /academy/:id/member/:id without auth"""
        self.headers(academy=1)
        self.generate_models(authenticate=True)
        url = reverse_lazy("authenticate:academy_token")
        response = self.client.post(url)
        json = response.json()

        self.assertEqual(
            json,
            {
                "detail": "You (user: 1) don't have this capability: generate_academy_token " "for academy 1",
                "status_code": 403,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_academy_token_post(self):
        """Test /academy/:id/member/:id without auth"""
        role = "academy_token"
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, role=role, capability="generate_academy_token", profile_academy=True
        )
        url = reverse_lazy("authenticate:academy_token")
        response = self.client.post(url)
        json = response.json()
        token_pattern = re.compile(r"[0-9a-zA-Z]{,40}$")
        expected = {"token_type": "permanent", "expires_at": None}

        token = self.get_token(1)
        user = self.get_user(2)

        self.assertEqual(
            self.all_token_dict(),
            [
                {
                    "created": token.created,
                    "expires_at": json["expires_at"],
                    "id": 1,
                    "key": json["token"],
                    "token_type": json["token_type"],
                    "user_id": 2,
                }
            ],
        )
        self.assertEqual(bool(token_pattern.match(json["token"])), True)
        del json["token"]
        self.assertEqual(json, expected)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.all_user_dict(),
            [
                {
                    **self.model_to_dict(model, "user"),
                },
                {
                    "date_joined": user.date_joined,
                    "username": model["academy"].slug,
                    "email": f"{model['academy'].slug}@token.com",
                    "first_name": "",
                    "id": 2,
                    "is_staff": False,
                    "is_superuser": False,
                    "last_login": None,
                    "last_name": "",
                    "password": "",
                    "is_active": True,
                },
            ],
        )
        self.assertEqual(
            self.all_profile_academy_dict(),
            [
                {
                    **self.model_to_dict(model, "profile_academy"),
                },
                {
                    "academy_id": model["academy"].id,
                    "address": None,
                    "email": None,
                    "first_name": None,
                    "last_name": None,
                    "id": 2,
                    "phone": "",
                    "role_id": role,
                    "status": "ACTIVE",
                    "user_id": 2,
                },
            ],
        )
        self.assertEqual(
            self.all_role_dict(),
            [
                {
                    **self.model_to_dict(model, "role"),
                }
            ],
        )

    def test_academy_token_post_refresh_token(self):
        """Test /academy/:id/member/:id without auth"""
        role = "academy_token"
        self.headers(academy=1)
        academy_kwargs = {"slug": "academy-a"}
        user_kwargs = {"username": "academy-a"}
        model = self.generate_models(
            authenticate=True,
            role=role,
            user=True,
            academy_kwargs=academy_kwargs,
            capability="generate_academy_token",
            profile_academy=True,
            token=True,
            user_kwargs=user_kwargs,
        )
        url = reverse_lazy("authenticate:academy_token")
        response = self.client.post(url)
        expected = {"token_type": "permanent", "expires_at": None}
        json = response.json()
        token_pattern = re.compile(r"[0-9a-zA-Z]{,40}$")

        token = self.get_token(2)

        self.assertEqual(
            self.all_token_dict(),
            [
                {
                    "created": token.created,
                    "expires_at": json["expires_at"],
                    "id": 2,
                    "key": json["token"],
                    "token_type": json["token_type"],
                    "user_id": model["user"].id,
                }
            ],
        )
        self.assertEqual(bool(token_pattern.match(json["token"])), True)
        del json["token"]
        self.assertEqual(json, expected)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.all_user_dict(),
            [
                {
                    **self.model_to_dict(model, "user"),
                }
            ],
        )
        self.assertEqual(
            self.all_profile_academy_dict(),
            [
                {
                    **self.model_to_dict(model, "profile_academy"),
                }
            ],
        )

    def test_academy_token_with_other_endpoints(self):
        """Test /academy/:id/member/:id without auth"""
        role = "academy_token"
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            role=role,
            academy=True,
            capability="generate_academy_token",
            profile_academy=True,
            form_entry=True,
        )
        url = reverse_lazy("authenticate:academy_token")
        response = self.client.post(url)
        json = response.json()
        token_pattern = re.compile(r"[0-9a-zA-Z]{,40}$")

        self.assertEqual(bool(token_pattern.match(json["token"])), True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.client.logout()
        self.client.credentials(HTTP_AUTHORIZATION="Token " + json["token"])

        url = reverse_lazy("marketing:lead_all")
        response = self.client.get(url)
        json = response.json()

        self.assertDatetime(json[0]["created_at"])
        del json[0]["created_at"]

        expected = [
            {
                "academy": {
                    "id": model.form_entry.academy.id,
                    "name": model.form_entry.academy.name,
                    "slug": model.form_entry.academy.slug,
                },
                "country": model.form_entry.country,
                "course": model.form_entry.course,
                "email": model.form_entry.email,
                "client_comments": model.form_entry.client_comments,
                "first_name": model.form_entry.first_name,
                "gclid": model.form_entry.gclid,
                "id": model.form_entry.id,
                "language": model.form_entry.language,
                "last_name": model.form_entry.last_name,
                "lead_type": model.form_entry.lead_type,
                "location": model.form_entry.location,
                "storage_status": model.form_entry.storage_status,
                "tags": model.form_entry.tags,
                "utm_campaign": model.form_entry.utm_campaign,
                "utm_medium": model.form_entry.utm_medium,
                "utm_source": model.form_entry.utm_source,
                "utm_url": model.form_entry.utm_url,
                "sex": model.form_entry.sex,
                "custom_fields": model.form_entry.custom_fields,
                "utm_placement": model.form_entry.utm_placement,
                "utm_plan": model.form_entry.utm_plan,
                "utm_term": model.form_entry.utm_term,
            }
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{**self.model_to_dict(model, "form_entry")}])

    def test_academy_no_token_with_other_endpoints(self):
        """Test /academy/:id/member/:id without auth"""
        role = "academy_token"
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            role=role,
            academy=True,
            capability="generate_academy_token",
            profile_academy=True,
            form_entry=True,
        )
        url = reverse_lazy("authenticate:academy_token")
        response = self.client.post(url)
        json = response.json()
        token_pattern = re.compile(r"[0-9a-zA-Z]{,40}$")

        self.assertEqual(bool(token_pattern.match(json["token"])), True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.client.logout()

        url = reverse_lazy("marketing:lead_all")
        response = self.client.get(url)
        json = response.json()

        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.all_form_entry_dict(), [{**self.model_to_dict(model, "form_entry")}])

    def test_academy_token_showing_on_other_endpoints(self):
        """Test /academy/:id/member/:id without auth"""
        role = "academy_token"
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, role=role, capability="generate_academy_token", profile_academy=True
        )
        url = reverse_lazy("authenticate:academy_token")
        response = self.client.post(url)
        json = response.json()
        token_pattern = re.compile(r"[0-9a-zA-Z]{,40}$")

        self.assertEqual(bool(token_pattern.match(json["token"])), True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        url = reverse_lazy("authenticate:user")
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json,
            [
                {
                    "id": model["user"].id,
                    "email": model["user"].email,
                    "first_name": model["user"].first_name,
                    "last_name": model["user"].last_name,
                    "github": None,
                    "profile": None,
                }
            ],
        )
