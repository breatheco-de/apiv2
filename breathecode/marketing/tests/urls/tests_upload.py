"""
Test /v1/marketing/upload
"""

import csv
import tempfile
import os
import hashlib
from unittest.mock import MagicMock, Mock, PropertyMock, call, patch
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins import MarketingTestCase
from breathecode.marketing.views import MIME_ALLOW
import pandas as pd
from django.utils import timezone, dateparse

UTC_NOW = timezone.now()


class MarketingTestSuite(MarketingTestCase):
    """Test /answer"""

    def setUp(self):
        super().setUp()
        self.file_name = ""

    def tearDown(self):
        if self.file_name:
            os.remove(self.file_name)

    def test_upload_without_auth(self):
        from breathecode.services.google_cloud import Storage, File

        self.headers(content_disposition='attachment; filename="filename.csv"')

        url = reverse_lazy("marketing:upload")
        data = {}
        response = self.client.put(url, data)
        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_upload_wrong_academy(self):
        from breathecode.services.google_cloud import Storage, File

        self.headers(academy=1, content_disposition='attachment; filename="filename.csv"')

        url = reverse_lazy("marketing:upload")
        data = {}
        response = self.client.put(url, data)
        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_upload_without_capability(self):
        from breathecode.services.google_cloud import Storage, File

        self.headers(academy=1, content_disposition='attachment; filename="filename.csv"')

        url = reverse_lazy("marketing:upload")
        self.generate_models(authenticate=True)
        data = {}
        response = self.client.put(url, data)
        json = response.json()
        expected = {"detail": "You (user: 1) don't have this capability: crud_media for academy 1", "status_code": 403}

        self.assertEqual(json, expected)
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
    def test_upload_with_csv_file(self):
        from breathecode.services.google_cloud import Storage, File

        self.headers(academy=1)

        model = self.generate_models(authenticate=True, profile_academy=True, capability="crud_media", role="potato")
        url = reverse_lazy("marketing:upload")

        response = self.client.put(url, {})
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("monitoring.CSVUpload"), [])

        self.assertEqual(Storage.__init__.call_args_list, [])
        self.assertEqual(File.__init__.call_args_list, [])
        self.assertEqual(File.upload.call_args_list, [])
        self.assertEqual(File.url.call_args_list, [])

    @patch("breathecode.marketing.tasks.create_form_entry.delay", MagicMock())
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
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_upload_random(self):
        from breathecode.services.google_cloud import Storage, File
        from breathecode.marketing.tasks import create_form_entry

        self.headers(academy=1)

        model = self.generate_models(authenticate=True, profile_academy=True, capability="crud_media", role="potato")

        url = reverse_lazy("marketing:upload")

        file = tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w+")

        # list of name, degree, score
        first_names = [self.bc.fake.first_name() for _ in range(0, 3)]
        last_names = [self.bc.fake.last_name() for _ in range(0, 3)]
        emails = [self.bc.fake.email() for _ in range(0, 3)]
        locations = [self.bc.fake.country() for _ in range(0, 3)]
        phone_numbers = [self.bc.fake.phone_number() for _ in range(0, 3)]
        languages = [self.bc.fake.language_name() for _ in range(0, 3)]

        # dictionary of lists
        obj = {
            "first_name": first_names,
            "last_name": last_names,
            "email": emails,
            "location": locations,
            "phone": phone_numbers,
            "language": languages,
        }

        df = pd.DataFrame(obj)

        # saving the dataframe

        self.file_name = file.name

        df.to_csv(file.name)

        with open(file.name, "rb") as data:
            hash = hashlib.sha256(data.read()).hexdigest()

        with open(file.name, "rb") as data:
            response = self.client.put(url, {"name": file.name, "file": data})
            json = response.json()

            file_name = file.name.split("/")[-1]
            expected = [{"file_name": file_name, "message": "Despues", "status": "PENDING"}]

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                create_form_entry.delay.call_args_list,
                [
                    call(
                        1,
                        **{
                            "first_name": df.iloc[0]["first_name"],
                            "last_name": df.iloc[0]["last_name"],
                            "email": df.iloc[0]["email"],
                            "location": df.iloc[0]["location"],
                            "phone": df.iloc[0]["phone"],
                            "language": df.iloc[0]["language"],
                        }
                    ),
                    call(
                        1,
                        **{
                            "first_name": df.iloc[1]["first_name"],
                            "last_name": df.iloc[1]["last_name"],
                            "email": df.iloc[1]["email"],
                            "location": df.iloc[1]["location"],
                            "phone": df.iloc[1]["phone"],
                            "language": df.iloc[1]["language"],
                        }
                    ),
                    call(
                        1,
                        **{
                            "first_name": df.iloc[2]["first_name"],
                            "last_name": df.iloc[2]["last_name"],
                            "email": df.iloc[2]["email"],
                            "location": df.iloc[2]["location"],
                            "phone": df.iloc[2]["phone"],
                            "language": df.iloc[2]["language"],
                        }
                    ),
                ],
            )

            self.assertEqual(
                self.bc.database.list_of("monitoring.CSVUpload"),
                [
                    {
                        "academy_id": 1,
                        "hash": hash,
                        "finished_at": UTC_NOW,
                        "id": 1,
                        "name": file_name,
                        "status": "PENDING",
                        "log": "",
                        "status_message": None,
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

            self.assertEqual(args[0].name, os.path.basename(file.name))
            self.assertEqual(kwargs, {"content_type": "text/csv"})

            self.assertEqual(File.url.call_args_list, [call()])
