"""
Test cases for /academy/:id/member/:id
"""

import os
import random
from unittest.mock import MagicMock, PropertyMock, call, patch

import numpy as np
from django.urls.base import reverse_lazy
from rest_framework import status

from breathecode.services.google_cloud.storage import File, Storage
from breathecode.tests.mocks.requests import apply_requests_request_mock

from ..mixins.new_auth_test_case import AuthTestCase

SHAPE_OF_URL = "https://us-central1-labor-day-story.cloudfunctions.net/shape-of-image"


def apply_get_env(configuration={}):

    def get_env(key, value=None):
        return configuration.get(key, value)

    return get_env


def put_serializer_creating(user, data={}):
    return {
        "avatar_url": "",
        "bio": None,
        "blog": None,
        "github_username": None,
        "linkedin_url": None,
        "phone": "",
        "portfolio_url": None,
        "show_tutorial": True,
        "twitter_username": None,
        "user": {
            "email": user.email,
            "first_name": user.first_name,
            "id": user.id,
            "last_name": user.last_name,
            "username": user.username,
        },
        **data,
    }


def put_serializer_updating(profile, user, data={}):
    return {
        "avatar_url": profile.avatar_url,
        "bio": profile.bio,
        "blog": profile.blog,
        "github_username": profile.github_username,
        "linkedin_url": profile.linkedin_url,
        "phone": profile.phone,
        "portfolio_url": profile.portfolio_url,
        "show_tutorial": profile.show_tutorial,
        "twitter_username": profile.twitter_username,
        "user": {
            "email": user.email,
            "first_name": user.first_name,
            "id": user.id,
            "last_name": user.last_name,
            "username": user.username,
        },
        **data,
    }


def profile_row(data={}):
    return {
        "avatar_url": None,
        "bio": None,
        "blog": None,
        "github_username": None,
        "id": 0,
        "linkedin_url": None,
        "phone": "",
        "portfolio_url": None,
        "show_tutorial": True,
        "twitter_username": None,
        "user_id": 0,
        **data,
    }


class AuthenticateTestSuite(AuthTestCase):
    """
    🔽🔽🔽 Auth
    """

    filename = ""

    def tearDown(self):
        self.bc.garbage_collector.collect()
        super().tearDown()

    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env({"PROFILE_BUCKET": "https://dot.dot", "GCLOUD_SHAPE_OF_IMAGE": SHAPE_OF_URL})
        ),
    )
    def test__without_auth(self):
        url = reverse_lazy("authenticate:profile_me_picture")
        response = self.client.put(url)
        json = response.json()

        self.assertEqual(
            json,
            {
                "detail": "Authentication credentials were not provided.",
                "status_code": status.HTTP_401_UNAUTHORIZED,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.bc.database.list_of("authenticate.Profile"), [])

    """
    🔽🔽🔽 Put without permission
    """

    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env({"PROFILE_BUCKET": "https://dot.dot", "GCLOUD_SHAPE_OF_IMAGE": SHAPE_OF_URL})
        ),
    )
    def test__without_permission(self):
        model = self.bc.database.create(user=1)

        self.client.force_authenticate(model.user)
        url = reverse_lazy("authenticate:profile_me_picture")
        response = self.client.put(url)

        json = response.json()
        expected = {"detail": "without-permission", "status_code": 403}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.bc.database.list_of("authenticate.Profile"), [])

    """
    🔽🔽🔽 Put without passing file
    """

    @patch.multiple(
        "breathecode.services.google_cloud.Storage",
        __init__=MagicMock(return_value=None),
        client=PropertyMock(),
        create=True,
    )
    @patch.multiple(
        "breathecode.services.google_cloud.File",
        __init__=MagicMock(return_value=None),
        bucket=PropertyMock(),
        file_name=PropertyMock(),
        upload=MagicMock(),
        exists=MagicMock(return_value=True),
        url=MagicMock(return_value="https://storage.cloud.google.com/media-breathecode/hardcoded_url-100x100"),
        create=True,
    )
    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env({"PROFILE_BUCKET": "https://dot.dot", "GCLOUD_SHAPE_OF_IMAGE": SHAPE_OF_URL})
        ),
    )
    def test__without_passing_file(self):
        permission = {"codename": "update_my_profile"}
        model = self.bc.database.create(user=1, permission=permission)

        self.client.force_authenticate(model.user)
        url = reverse_lazy("authenticate:profile_me_picture")
        data = {}
        response = self.client.put(url, data)

        json = response.json()
        expected = {"detail": "missing-file", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            self.bc.database.list_of("authenticate.Profile"),
            [
                profile_row(
                    {
                        "user_id": 1,
                        "id": 1,
                    }
                ),
            ],
        )

        self.assertEqual(Storage.__init__.call_args_list, [])
        self.assertEqual(File.upload.call_args_list, [])
        self.assertEqual(File.exists.call_args_list, [])
        self.assertEqual(File.url.call_args_list, [])

    """
    🔽🔽🔽 Put passing file and exists in google cloud
    """

    @patch.multiple(
        "breathecode.services.google_cloud.Storage",
        __init__=MagicMock(return_value=None),
        client=PropertyMock(),
        create=True,
    )
    @patch.multiple(
        "breathecode.services.google_cloud.File",
        __init__=MagicMock(return_value=None),
        bucket=PropertyMock(),
        file_name=PropertyMock(),
        upload=MagicMock(),
        exists=MagicMock(return_value=True),
        url=MagicMock(return_value="https://storage.cloud.google.com/media-breathecode/hardcoded_url-100x100"),
        create=True,
    )
    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env({"PROFILE_BUCKET": "https://dot.dot", "GCLOUD_SHAPE_OF_IMAGE": SHAPE_OF_URL})
        ),
    )
    def test__passing_file__file_exists(self):
        # random_image
        file, self.filename = self.bc.random.file()

        permission = {"codename": "update_my_profile"}
        model = self.bc.database.create(user=1, permission=permission)

        self.client.force_authenticate(model.user)
        url = reverse_lazy("authenticate:profile_me_picture")
        response = self.client.put(url, {"name": self.filename, "file": file})

        json = response.json()
        expected = {"detail": "bad-file-format", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            self.bc.database.list_of("authenticate.Profile"),
            [
                profile_row(
                    {
                        "user_id": 1,
                        "id": 1,
                    }
                ),
            ],
        )

        self.assertEqual(Storage.__init__.call_args_list, [])
        self.assertEqual(File.upload.call_args_list, [])
        self.assertEqual(File.exists.call_args_list, [])
        self.assertEqual(File.url.call_args_list, [])

    """
    🔽🔽🔽 Put with Profile, passing file and exists in google cloud
    """

    @patch.multiple(
        "breathecode.services.google_cloud.Storage",
        __init__=MagicMock(return_value=None),
        client=PropertyMock(),
        create=True,
    )
    @patch.multiple(
        "breathecode.services.google_cloud.File",
        __init__=MagicMock(return_value=None),
        bucket=PropertyMock(),
        file_name=PropertyMock(),
        upload=MagicMock(),
        exists=MagicMock(return_value=True),
        url=MagicMock(return_value="https://storage.cloud.google.com/media-breathecode/hardcoded_url-100x100"),
        create=True,
    )
    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env({"PROFILE_BUCKET": "https://dot.dot", "GCLOUD_SHAPE_OF_IMAGE": SHAPE_OF_URL})
        ),
    )
    def test__passing_file__with_profile__file_exists(self):
        exts = ["png", "jpg", "jpeg"]
        permission = {"codename": "update_my_profile"}
        base = self.bc.database.create(permission=permission)

        for ext in exts:
            file, self.filename = self.bc.random.image(2, 2, ext)

            model = self.bc.database.create(user=1, permission=base.permission, profile=1)

            self.client.force_authenticate(model.user)
            url = reverse_lazy("authenticate:profile_me_picture")
            response = self.client.put(url, {"name": "filename.lbs", "file": file})

            json = response.json()
            expected = put_serializer_updating(
                model.profile,
                model.user,
                data={
                    "avatar_url": "https://storage.cloud.google.com/media-breathecode/hardcoded_url-100x100",
                },
            )

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                self.bc.database.list_of("authenticate.Profile"),
                [
                    profile_row(
                        {
                            "user_id": model.user.id,
                            "id": model.profile.id,
                            "avatar_url": "https://storage.cloud.google.com/media-breathecode/hardcoded_url-100x100",
                        }
                    ),
                ],
            )

            self.assertEqual(Storage.__init__.call_args_list, [call()])
            self.assertEqual(File.upload.call_args_list, [])
            self.assertEqual(File.exists.call_args_list, [call()])
            self.assertEqual(File.url.call_args_list, [call()])

            # teardown
            self.bc.database.delete("authenticate.Profile")
            Storage.__init__.call_args_list = []
            File.upload.call_args_list = []
            File.exists.call_args_list = []
            File.url.call_args_list = []

    """
    🔽🔽🔽 Put with Profile, passing file and does'nt exists in google cloud, shape is square
    """

    @patch.multiple(
        "breathecode.services.google_cloud.Storage",
        __init__=MagicMock(return_value=None),
        client=PropertyMock(),
        create=True,
    )
    @patch.multiple(
        "breathecode.services.google_cloud.File",
        __init__=MagicMock(return_value=None),
        bucket=PropertyMock(),
        file_name=PropertyMock(),
        delete=MagicMock(),
        upload=MagicMock(),
        exists=MagicMock(return_value=False),
        url=MagicMock(return_value="https://storage.cloud.google.com/media-breathecode/hardcoded_url-100x100"),
        create=True,
    )
    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env({"PROFILE_BUCKET": "https://dot.dot", "GCLOUD_SHAPE_OF_IMAGE": SHAPE_OF_URL})
        ),
    )
    @patch("google.oauth2.id_token.fetch_id_token", MagicMock(return_value="blablabla"))
    @patch("requests.request", apply_requests_request_mock([(200, SHAPE_OF_URL, {"shape": "Square"})]))
    @patch("breathecode.services.google_cloud.credentials.resolve_credentials", MagicMock())
    def test__passing_file__with_profile__file_does_not_exists__shape_is_square(self):
        file, self.filename = self.bc.random.image(2, 2)

        permission = {"codename": "update_my_profile"}
        profile = {"avatar_url": f"https://blabla.bla/{self.bc.random.string(size=64, lower=True)}-100x100"}
        model = self.bc.database.create(user=1, permission=permission, profile=profile)

        self.client.force_authenticate(model.user)
        url = reverse_lazy("authenticate:profile_me_picture")
        response = self.client.put(url, {"name": "filename.lbs", "file": file})

        json = response.json()
        expected = put_serializer_updating(
            model.profile,
            model.user,
            data={
                "avatar_url": "https://storage.cloud.google.com/media-breathecode/hardcoded_url-100x100",
            },
        )

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("authenticate.Profile"),
            [
                profile_row(
                    {
                        "user_id": 1,
                        "id": 1,
                        "avatar_url": "https://storage.cloud.google.com/media-breathecode/hardcoded_url-100x100",
                    }
                ),
            ],
        )

        self.assertEqual(Storage.__init__.call_args_list, [call()])
        self.assertEqual(len(File.upload.call_args_list), 1)
        self.assertEqual(File.exists.call_args_list, [call()])
        self.assertEqual(File.url.call_args_list, [call()])
        self.assertEqual(File.delete.call_args_list, [call(), call()])

    """
    🔽🔽🔽 Put with Profile, passing file and does'nt exists in google cloud, shape is not square
    """

    @patch.multiple(
        "breathecode.services.google_cloud.Storage",
        __init__=MagicMock(return_value=None),
        client=PropertyMock(),
        create=True,
    )
    @patch.multiple(
        "breathecode.services.google_cloud.File",
        __init__=MagicMock(return_value=None),
        bucket=PropertyMock(),
        file_name=PropertyMock(),
        delete=MagicMock(),
        upload=MagicMock(),
        exists=MagicMock(return_value=False),
        url=MagicMock(return_value="https://storage.cloud.google.com/media-breathecode/hardcoded_url-100x100"),
        create=True,
    )
    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env({"PROFILE_BUCKET": "https://dot.dot", "GCLOUD_SHAPE_OF_IMAGE": SHAPE_OF_URL})
        ),
    )
    @patch("google.oauth2.id_token.fetch_id_token", MagicMock(return_value="blablabla"))
    @patch("requests.request", apply_requests_request_mock([(200, SHAPE_OF_URL, {"shape": "Rectangle"})]))
    @patch("breathecode.services.google_cloud.credentials.resolve_credentials", MagicMock())
    def test__passing_file__with_profile__file_does_not_exists__shape_is_not_square(self):
        options = [2, 1]

        width = random.choice(options)
        options.remove(width)
        height = options[0]

        file, self.filename = self.bc.random.image(width, height)

        permission = {"codename": "update_my_profile"}
        profile = {"avatar_url": f"https://blabla.bla/{self.bc.random.string(size=64, lower=True)}-100x100"}
        model = self.bc.database.create(user=1, permission=permission, profile=profile)

        self.client.force_authenticate(model.user)
        url = reverse_lazy("authenticate:profile_me_picture")
        response = self.client.put(url, {"name": "filename.lbs", "file": file})

        json = response.json()
        expected = {"detail": "not-square-image", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            self.bc.database.list_of("authenticate.Profile"),
            [
                self.bc.format.to_dict(model.profile),
            ],
        )

        self.assertEqual(Storage.__init__.call_args_list, [call()])
        self.assertEqual(len(File.upload.call_args_list), 1)
        self.assertEqual(File.exists.call_args_list, [call()])
        self.assertEqual(File.url.call_args_list, [])
        self.assertEqual(File.delete.call_args_list, [call()])
