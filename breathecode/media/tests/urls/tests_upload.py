"""
Test /v1/media/upload
"""

import hashlib
import os
import tempfile
from unittest.mock import MagicMock, PropertyMock, call, patch

from django.urls.base import reverse_lazy
from rest_framework import status

from breathecode.media.views import MIME_ALLOW

from ..mixins import MediaTestCase


class MediaTestSuite(MediaTestCase):
    """Test /answer"""

    def test_upload_without_auth(self):
        from breathecode.services.google_cloud import File, Storage

        self.headers(content_disposition='attachment; filename="filename.jpg"')

        url = reverse_lazy("media:upload")
        data = {}
        response = self.client.put(url, data)
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_upload_wrong_academy(self):
        from breathecode.services.google_cloud import File, Storage

        self.headers(academy=1, content_disposition='attachment; filename="filename.jpg"')

        url = reverse_lazy("media:upload")
        data = {}
        response = self.client.put(url, data)
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_upload_without_capability(self):
        from breathecode.services.google_cloud import File, Storage

        self.headers(academy=1, content_disposition='attachment; filename="filename.jpg"')

        url = reverse_lazy("media:upload")
        self.generate_models(authenticate=True)
        data = {}
        response = self.client.put(url, data)
        json = response.json()

        self.assertEqual(
            json, {"detail": "You (user: 1) don't have this capability: crud_media for academy 1", "status_code": 403}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

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
        url=MagicMock(return_value="https://storage.cloud.google.com/media-breathecode/hardcoded_url"),
        create=True,
    )
    def test_upload_without_data(self):
        from breathecode.services.google_cloud import File, Storage

        self.headers(academy=1)

        model = self.generate_models(authenticate=True, profile_academy=True, capability="crud_media", role="potato")
        url = reverse_lazy("media:upload")
        data = {}
        response = self.client.put(url, data)
        json = response.json()

        self.assertEqual(
            json,
            {
                "detail": "Missing file in request",
                "status_code": 400,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_media_dict(), [])

        self.assertEqual(Storage.__init__.call_args_list, [])
        self.assertEqual(File.__init__.call_args_list, [])
        self.assertEqual(File.upload.call_args_list, [])
        self.assertEqual(File.url.call_args_list, [])

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
        url=MagicMock(return_value="https://storage.cloud.google.com/media-breathecode/hardcoded_url"),
        create=True,
    )
    def test_upload(self):
        from breathecode.services.google_cloud import File, Storage

        self.headers(academy=1)

        model = self.generate_models(authenticate=True, profile_academy=True, capability="crud_media", role="potato")
        url = reverse_lazy("media:upload")

        file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        file.write(os.urandom(1024))
        file.close()

        with open(file.name, "rb") as data:
            hash = hashlib.sha256(data.read()).hexdigest()

        with open(file.name, "rb") as data:
            response = self.client.put(url, {"name": "filename.png", "file": data})
            json = response.json()

            self.assertHash(hash)

            expected = [
                {
                    "academy": 1,
                    "categories": [],
                    "hash": hash,
                    "hits": 0,
                    "id": 1,
                    "mime": "image/png",
                    "name": "filename.png",
                    "slug": "filename-png",
                    "thumbnail": "https://storage.cloud.google.com/media-breathecode/hardcoded_url-thumbnail",
                    "url": "https://storage.cloud.google.com/media-breathecode/hardcoded_url",
                }
            ]

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                self.all_media_dict(),
                [
                    {
                        "academy_id": 1,
                        "hash": hash,
                        "hits": 0,
                        "id": 1,
                        "mime": "image/png",
                        "name": "filename.png",
                        "slug": "filename-png",
                        "thumbnail": "https://storage.cloud.google.com/media-breathecode/hardcoded_url-thumbnail",
                        "url": "https://storage.cloud.google.com/media-breathecode/hardcoded_url",
                    }
                ],
            )

            self.assertEqual(Storage.__init__.call_args_list, [call()])
            self.assertEqual(
                File.__init__.call_args_list,
                [
                    call(Storage().client.bucket("bucket"), hash),
                ],
            )

            args, kwargs = File.upload.call_args_list[0]

            self.assertEqual(len(File.upload.call_args_list), 1)
            self.assertEqual(len(args), 1)
            self.assertEqual(len(args), 1)

            self.assertEqual(args[0].name, os.path.basename(file.name))
            self.assertEqual(args[0].size, 1024)
            self.assertEqual(kwargs, {"content_type": "image/png"})

            self.assertEqual(File.url.call_args_list, [call()])

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
        url=MagicMock(return_value="https://storage.cloud.google.com/media-breathecode/hardcoded_url"),
        create=True,
    )
    def test_upload_with_media(self):
        from breathecode.services.google_cloud import File, Storage

        self.headers(academy=1)

        file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        file.write(os.urandom(1024))
        file.close()

        with open(file.name, "rb") as data:
            hash = hashlib.sha256(data.read()).hexdigest()

        media_kwargs = {"hash": hash}
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_media",
            role="potato",
            media=True,
            media_kwargs=media_kwargs,
        )
        url = reverse_lazy("media:upload")

        with open(file.name, "rb") as data:
            response = self.client.put(url, {"name": ["filename.jpg"], "file": [data]})
            json = response.json()

            self.assertHash(hash)

            expected = [
                {
                    "academy": model["media"].academy.id,
                    "categories": [],
                    "hash": hash,
                    "hits": model["media"].hits,
                    "id": model["media"].id,
                    "mime": "image/png",
                    "name": "filename.jpg",
                    "slug": "filename-jpg",
                    "thumbnail": None,
                    "url": model["media"].url,
                }
            ]

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                self.all_media_dict(),
                [
                    {
                        **self.model_to_dict(model, "media"),
                        "hash": hash,
                        "mime": "image/png",
                        "name": "filename.jpg",
                        "slug": "filename-jpg",
                    }
                ],
            )

            self.assertEqual(Storage.__init__.call_args_list, [])
            self.assertEqual(File.__init__.call_args_list, [])
            self.assertEqual(File.upload.call_args_list, [])
            self.assertEqual(File.url.call_args_list, [])

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
        url=MagicMock(return_value="https://storage.cloud.google.com/media-breathecode/hardcoded_url"),
        create=True,
    )
    def test_upload_with_media_with_same_slug(self):
        from breathecode.services.google_cloud import File, Storage

        self.headers(academy=1)

        file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        file.write(os.urandom(1024))
        file.close()

        with open(file.name, "rb") as data:
            hash = hashlib.sha256(data.read()).hexdigest()

        media_kwargs = {"slug": "filename-jpg"}
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_media",
            role="potato",
            media=True,
            media_kwargs=media_kwargs,
        )
        url = reverse_lazy("media:upload")

        with open(file.name, "rb") as data:
            response = self.client.put(url, {"name": "filename.jpg", "file": data})
            json = response.json()
            expected = [
                {
                    "academy": 1,
                    "categories": [],
                    "hash": hash,
                    "hits": 0,
                    "id": 2,
                    "mime": "image/png",
                    "name": "filename.jpg",
                    "slug": "filename-jpg-ii",
                    "thumbnail": "https://storage.cloud.google.com/media-breathecode/hardcoded_url-thumbnail",
                    "url": "https://storage.cloud.google.com/media-breathecode/hardcoded_url",
                }
            ]

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                self.all_media_dict(),
                [
                    {
                        **self.model_to_dict(model, "media"),
                    },
                    {
                        "academy_id": 1,
                        "hash": hash,
                        "hits": 0,
                        "id": 2,
                        "mime": "image/png",
                        "name": "filename.jpg",
                        "slug": "filename-jpg-ii",
                        "thumbnail": "https://storage.cloud.google.com/media-breathecode/hardcoded_url-thumbnail",
                        "url": "https://storage.cloud.google.com/media-breathecode/hardcoded_url",
                    },
                ],
            )

            self.assertEqual(Storage.__init__.call_args_list, [call()])
            self.assertEqual(
                File.__init__.call_args_list,
                [
                    call(Storage().client.bucket("bucket"), hash),
                ],
            )

            args, kwargs = File.upload.call_args_list[0]

            self.assertEqual(len(File.upload.call_args_list), 1)
            self.assertEqual(len(args), 1)
            self.assertEqual(len(args), 1)

            self.assertEqual(args[0].name, os.path.basename(file.name))
            self.assertEqual(args[0].size, 1024)
            self.assertEqual(kwargs, {"content_type": "image/png"})

            self.assertEqual(File.url.call_args_list, [call()])

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
        url=MagicMock(return_value="https://storage.cloud.google.com/media-breathecode/hardcoded_url"),
        create=True,
    )
    def test_upload_categories(self):
        from breathecode.services.google_cloud import File, Storage

        self.headers(academy=1)

        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="crud_media", role="potato", category=True
        )
        url = reverse_lazy("media:upload")

        file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        file.write(os.urandom(1024))
        file.close()

        with open(file.name, "rb") as file:
            hash = hashlib.sha256(file.read()).hexdigest()

        with open(file.name, "rb") as file:
            data = {"name": "filename.jpg", "file": file, "categories": "1"}
            response = self.client.put(url, data, format="multipart")
            json = response.json()

            self.assertHash(hash)

            expected = [
                {
                    "academy": 1,
                    "categories": [1],
                    "hash": hash,
                    "hits": 0,
                    "id": 1,
                    "mime": "image/png",
                    "name": "filename.jpg",
                    "slug": "filename-jpg",
                    "thumbnail": "https://storage.cloud.google.com/media-breathecode/hardcoded_url-thumbnail",
                    "url": "https://storage.cloud.google.com/media-breathecode/hardcoded_url",
                }
            ]

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                self.all_media_dict(),
                [
                    {
                        "academy_id": 1,
                        "hash": hash,
                        "hits": 0,
                        "id": 1,
                        "mime": "image/png",
                        "name": "filename.jpg",
                        "slug": "filename-jpg",
                        "thumbnail": "https://storage.cloud.google.com/media-breathecode/hardcoded_url-thumbnail",
                        "url": "https://storage.cloud.google.com/media-breathecode/hardcoded_url",
                    }
                ],
            )

            self.assertEqual(Storage.__init__.call_args_list, [call()])
            self.assertEqual(
                File.__init__.call_args_list,
                [
                    call(Storage().client.bucket("bucket"), hash),
                ],
            )

            args, kwargs = File.upload.call_args_list[0]

            self.assertEqual(len(File.upload.call_args_list), 1)
            self.assertEqual(len(args), 1)
            self.assertEqual(len(args), 1)

            self.assertEqual(args[0].name, os.path.basename(file.name))
            self.assertEqual(args[0].size, 1024)
            self.assertEqual(kwargs, {"content_type": "image/png"})

            self.assertEqual(File.url.call_args_list, [call()])

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
        url=MagicMock(return_value="https://storage.cloud.google.com/media-breathecode/hardcoded_url"),
        create=True,
    )
    def test_upload_categories_in_headers(self):
        from breathecode.services.google_cloud import File, Storage

        self.headers(academy=1, categories=1)

        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="crud_media", role="potato", category=True
        )
        url = reverse_lazy("media:upload")

        file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        file.write(os.urandom(1024))
        file.close()

        with open(file.name, "rb") as file:
            file_bytes = file.read()
            hash = hashlib.sha256(file_bytes).hexdigest()

        with open(file.name, "rb") as file:
            data = {"name": "filename.jpg", "file": file}
            response = self.client.put(url, data, format="multipart")
            json = response.json()

            self.assertHash(hash)

            expected = [
                {
                    "academy": 1,
                    "categories": [1],
                    "hash": hash,
                    "hits": 0,
                    "id": 1,
                    "mime": "image/png",
                    "name": "filename.jpg",
                    "slug": "filename-jpg",
                    "thumbnail": "https://storage.cloud.google.com/media-breathecode/hardcoded_url-thumbnail",
                    "url": "https://storage.cloud.google.com/media-breathecode/hardcoded_url",
                }
            ]

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                self.all_media_dict(),
                [
                    {
                        "academy_id": 1,
                        "hash": hash,
                        "hits": 0,
                        "id": 1,
                        "mime": "image/png",
                        "name": "filename.jpg",
                        "slug": "filename-jpg",
                        "thumbnail": "https://storage.cloud.google.com/media-breathecode/hardcoded_url-thumbnail",
                        "url": "https://storage.cloud.google.com/media-breathecode/hardcoded_url",
                    }
                ],
            )

            self.assertEqual(Storage.__init__.call_args_list, [call()])
            self.assertEqual(
                File.__init__.call_args_list,
                [
                    call(Storage().client.bucket("bucket"), hash),
                ],
            )

            args, kwargs = File.upload.call_args_list[0]

            self.assertEqual(len(File.upload.call_args_list), 1)
            self.assertEqual(len(args), 1)
            self.assertEqual(len(args), 1)

            self.assertEqual(args[0].name, os.path.basename(file.name))
            self.assertEqual(args[0].size, 1024)
            self.assertEqual(kwargs, {"content_type": "image/png"})

            self.assertEqual(File.url.call_args_list, [call()])

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
        url=MagicMock(return_value="https://storage.cloud.google.com/media-breathecode/hardcoded_url"),
        create=True,
    )
    def test_upload_categories_in_headers__two_items(self):
        """Test /answer without auth"""
        from breathecode.services.google_cloud import File, Storage

        self.headers(academy=1, categories=1)

        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="crud_media", role="potato", category=True
        )
        url = reverse_lazy("media:upload")

        file1 = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        file1.write(os.urandom(1024))
        file1.close()

        file2 = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        file2.write(os.urandom(1024))
        file2.close()

        with open(file1.name, "rb") as file1:
            file_bytes1 = file1.read()
            hash1 = hashlib.sha256(file_bytes1).hexdigest()

        with open(file2.name, "rb") as file2:
            file_bytes2 = file2.read()
            hash2 = hashlib.sha256(file_bytes2).hexdigest()

        file1 = open(file1.name, "rb")
        file2 = open(file2.name, "rb")

        data = {"name": ["filename1.jpg", "filename2.jpg"], "file": [file1, file2]}
        response = self.client.put(url, data, format="multipart")
        json = response.json()

        expected = [
            {
                "academy": 1,
                "categories": [1],
                "hash": hash1,
                "hits": 0,
                "id": 1,
                "mime": "image/png",
                "name": "filename1.jpg",
                "slug": "filename1-jpg",
                "thumbnail": "https://storage.cloud.google.com/media-breathecode/hardcoded_url-thumbnail",
                "url": "https://storage.cloud.google.com/media-breathecode/hardcoded_url",
            },
            {
                "academy": 1,
                "categories": [1],
                "hash": hash2,
                "hits": 0,
                "id": 2,
                "mime": "image/png",
                "name": "filename2.jpg",
                "slug": "filename2-jpg",
                "thumbnail": "https://storage.cloud.google.com/media-breathecode/hardcoded_url-thumbnail",
                "url": "https://storage.cloud.google.com/media-breathecode/hardcoded_url",
            },
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.all_media_dict(),
            [
                {
                    "academy_id": 1,
                    "hash": hash1,
                    "hits": 0,
                    "id": 1,
                    "mime": "image/png",
                    "name": "filename1.jpg",
                    "slug": "filename1-jpg",
                    "thumbnail": "https://storage.cloud.google.com/media-breathecode/hardcoded_url-thumbnail",
                    "url": "https://storage.cloud.google.com/media-breathecode/hardcoded_url",
                },
                {
                    "academy_id": 1,
                    "hash": hash2,
                    "hits": 0,
                    "id": 2,
                    "mime": "image/png",
                    "name": "filename2.jpg",
                    "slug": "filename2-jpg",
                    "thumbnail": "https://storage.cloud.google.com/media-breathecode/hardcoded_url-thumbnail",
                    "url": "https://storage.cloud.google.com/media-breathecode/hardcoded_url",
                },
            ],
        )

        self.assertEqual(Storage.__init__.call_args_list, [call(), call()])
        self.assertEqual(
            File.__init__.call_args_list,
            [
                call(Storage().client.bucket("bucket"), hash1),
                call(Storage().client.bucket("bucket"), hash2),
            ],
        )

        args1, kwargs1 = File.upload.call_args_list[0]
        args2, kwargs2 = File.upload.call_args_list[1]

        self.assertEqual(len(File.upload.call_args_list), 2)
        self.assertEqual(len(args1), 1)
        self.assertEqual(len(args2), 1)

        self.assertEqual(args1[0].name, os.path.basename(file1.name))
        self.assertEqual(args1[0].size, 1024)
        self.assertEqual(args2[0].name, os.path.basename(file2.name))
        self.assertEqual(args2[0].size, 1024)
        self.assertEqual(kwargs1, {"content_type": "image/png"})
        self.assertEqual(kwargs2, {"content_type": "image/png"})

        self.assertEqual(File.url.call_args_list, [call(), call()])

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
        url=MagicMock(return_value="https://storage.cloud.google.com/media-breathecode/hardcoded_url"),
        create=True,
    )
    def test_upload_valid_format(self):
        from breathecode.services.google_cloud import File, Storage

        self.headers(academy=1)

        model = self.generate_models(authenticate=True, profile_academy=True, capability="crud_media", role="potato")
        url = reverse_lazy("media:upload")
        file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        file.write(os.urandom(1024))
        file.close()
        with open(file.name, "rb") as data:
            hash = hashlib.sha256(data.read()).hexdigest()
        with open(file.name, "rb") as data:
            response = self.client.put(url, {"name": "filename.jpg", "file": data})
            json = response.json()
            self.assertHash(hash)
            expected = [
                {
                    "academy": 1,
                    "categories": [],
                    "hash": hash,
                    "hits": 0,
                    "id": 1,
                    "mime": "image/jpeg",
                    "name": "filename.jpg",
                    "slug": "filename-jpg",
                    "thumbnail": "https://storage.cloud.google.com/media-breathecode/hardcoded_url-thumbnail",
                    "url": "https://storage.cloud.google.com/media-breathecode/hardcoded_url",
                }
            ]
            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                self.all_media_dict(),
                [
                    {
                        "academy_id": 1,
                        "hash": hash,
                        "hits": 0,
                        "id": 1,
                        "mime": "image/jpeg",
                        "name": "filename.jpg",
                        "slug": "filename-jpg",
                        "thumbnail": "https://storage.cloud.google.com/media-breathecode/hardcoded_url-thumbnail",
                        "url": "https://storage.cloud.google.com/media-breathecode/hardcoded_url",
                    }
                ],
            )

            self.assertEqual(Storage.__init__.call_args_list, [call()])
            self.assertEqual(
                File.__init__.call_args_list,
                [
                    call(Storage().client.bucket("bucket"), hash),
                ],
            )

            args, kwargs = File.upload.call_args_list[0]

            self.assertEqual(len(File.upload.call_args_list), 1)
            self.assertEqual(len(args), 1)
            self.assertEqual(len(args), 1)

            self.assertEqual(args[0].name, os.path.basename(file.name))
            self.assertEqual(args[0].size, 1024)
            self.assertEqual(kwargs, {"content_type": "image/jpeg"})

            self.assertEqual(File.url.call_args_list, [call()])

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
        url=MagicMock(return_value="https://storage.cloud.google.com/media-breathecode/hardcoded_url"),
        create=True,
    )
    def test_upload_invalid_format(self):
        from breathecode.services.google_cloud import File, Storage

        self.headers(academy=1)

        model = self.generate_models(authenticate=True, profile_academy=True, capability="crud_media", role="potato")
        url = reverse_lazy("media:upload")

        file = tempfile.NamedTemporaryFile(suffix=".txt", delete=False)
        text = self.bc.fake.text()
        file.write(text.encode("utf-8"))
        file.close()

        with open(file.name, "rb") as data:
            hash = hashlib.sha256(data.read()).hexdigest()

        with open(file.name, "rb") as data:
            response = self.client.put(url, {"name": "filename.lbs", "file": data})

            json = response.json()

            self.assertHash(hash)

            expected = {
                "detail": f'You can upload only files on the following formats: {",".join(MIME_ALLOW)}, got text/plain',
                "status_code": 400,
            }

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
