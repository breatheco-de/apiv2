"""
Test /v1/marketing/upload
"""

import hashlib
import os
import random
import re
import tempfile
from unittest.mock import MagicMock, PropertyMock, call, patch

import pandas as pd
from django.urls.base import reverse_lazy
from django.utils import timezone
from faker import Faker
from pytz import UTC
from rest_framework import status

from breathecode.provisioning import tasks

from ..mixins import ProvisioningTestCase

UTC_NOW = timezone.now()

fake = Faker()


def datetime_to_iso(date) -> str:
    return re.sub(r"\+00:00$", "Z", date.replace(tzinfo=UTC).isoformat())


def rigobot_csv(lines=1, data={}):
    organizations = ["4Geeks" for _ in range(lines)]
    consumption_period_ids = [random.randint(1, 10) for _ in range(lines)]
    times = [datetime_to_iso(timezone.now()) for _ in range(lines)]
    billing_statuses = ["OPEN" for _ in range(lines)]
    total_spent_periods = [(random.random() * 30) + 0.01 for _ in range(lines)]
    consumption_item_ids = [random.randint(1, 10) for _ in range(lines)]
    user_ids = [10 for _ in range(lines)]
    emails = [fake.email() for _ in range(lines)]
    consumption_types = ["MESSAGE" for _ in range(lines)]
    pricing_types = [random.choice(["INPUT", "OUTPUT"]) for _ in range(lines)]
    total_tokens = [random.randint(1, 100) for _ in range(lines)]
    total_spents = []
    res = []
    for i in range(lines):
        total_token = total_tokens[i]
        pricing_type = pricing_types[i]
        price = 0.04 if pricing_type == "OUTPUT" else 0.02
        total_spent = price * total_token
        while total_spent in res:
            total_tokens[i] = random.randint(1, 100)
            total_token = total_tokens[i]
            total_spent = price * total_token

        total_spents.append(total_spent)
        res.append(total_spent)

    models = [
        random.choice(["gpt-4-turbo", "gpt-4", "gpt-4-turbo", "gpt-4o", "gpt-3.5-turbo", "gpt-3.5"])
        for _ in range(lines)
    ]
    purpose_ids = [random.randint(1, 10) for _ in range(lines)]
    purpose_slugs = [fake.slug() for _ in range(lines)]
    purposes = [" ".join(fake.words()) for _ in range(lines)]
    github_usernames = [fake.user_name() for _ in range(lines)]

    created_ats = [datetime_to_iso(timezone.now()) for _ in range(lines)]

    # dictionary of lists
    return {
        "organization": organizations,
        "consumption_period_id": consumption_period_ids,
        "consumption_period_start": times,
        "consumption_period_end": times,
        "billing_status": billing_statuses,
        "total_spent_period": total_spent_periods,
        "consumption_item_id": consumption_item_ids,
        "user_id": user_ids,
        "email": emails,
        "consumption_type": consumption_types,
        "pricing_type": pricing_types,
        "total_spent": total_spents,
        "total_tokens": total_tokens,
        "model": models,
        "purpose_id": purpose_ids,
        "purpose_slug": purpose_slugs,
        "purpose": purposes,
        "created_at": created_ats,
        "github_username": github_usernames,
        **data,
    }


class MarketingTestSuite(ProvisioningTestCase):
    """Test /answer"""

    def setUp(self):
        super().setUp()
        self.file_name = ""

    def tearDown(self):
        if self.file_name:
            os.remove(self.file_name)

    # When: no auth
    # Then: should return 401
    def test_upload_without_auth(self):
        from breathecode.services.google_cloud import File, Storage

        self.headers(content_disposition='attachment; filename="filename.csv"')

        url = reverse_lazy("provisioning:admin_upload")
        data = {}
        response = self.client.put(url, data)
        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # When: auth and no capability
    # Then: should return 403
    def test_upload_without_capability(self):
        from breathecode.services.google_cloud import File, Storage

        self.headers(academy=1, content_disposition='attachment; filename="filename.csv"')

        url = reverse_lazy("provisioning:admin_upload")
        self.generate_models(authenticate=True)
        data = {}
        response = self.client.put(url, data)
        json = response.json()
        expected = {"detail": "without-permission", "status_code": 403}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # When: auth and no files
    # Then: should return empty list
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
    def test_no_files(self):
        from breathecode.services.google_cloud import File, Storage

        self.headers(academy=1)

        model = self.generate_models(
            authenticate=True, group=1, permission={"codename": "upload_provisioning_activity"}
        )
        url = reverse_lazy("provisioning:admin_upload")

        response = self.client.put(url, {})
        json = response.json()

        self.assertEqual(json, {"success": [], "failure": []})
        self.assertEqual(response.status_code, status.HTTP_207_MULTI_STATUS)

        self.assertEqual(Storage.__init__.call_args_list, [])
        self.assertEqual(File.__init__.call_args_list, [])
        self.assertEqual(File.upload.call_args_list, [])
        self.assertEqual(File.url.call_args_list, [])

    # When: auth and bad file type
    # Then: should return empty list
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
    def test_bad_file_type(self):
        from breathecode.marketing.tasks import create_form_entry
        from breathecode.services.google_cloud import File, Storage

        self.headers(academy=1)

        model = self.generate_models(
            authenticate=True, group=1, permission={"codename": "upload_provisioning_activity"}
        )

        url = reverse_lazy("provisioning:admin_upload")

        file = tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w+")

        self.file_name = file.name
        file.write("Hello world")

        with open(file.name, "rb") as data:
            hash = hashlib.sha256(data.read()).hexdigest()

        with open(file.name, "rb") as data:
            response = self.client.put(url, {"name": file.name, "file": data})
            json = response.json()

            expected = {
                "failure": [
                    {
                        "detail": "bad-format",
                        "resources": [
                            {
                                "display_field": "index",
                                "display_value": 1,
                            }
                        ],
                        "status_code": 400,
                    }
                ],
                "success": [],
            }

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_207_MULTI_STATUS)
            self.assertEqual(create_form_entry.delay.call_args_list, [])

            self.assertEqual(Storage.__init__.call_args_list, [])
            self.assertEqual(File.__init__.call_args_list, [])
            self.assertEqual(File.upload.call_args_list, [])
            self.assertEqual(File.url.call_args_list, [])

    # When: auth and bad files
    # Then: should return empty list
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
    def test_bad_format(self):
        from breathecode.marketing.tasks import create_form_entry
        from breathecode.services.google_cloud import File, Storage

        self.headers(academy=1)

        model = self.generate_models(
            authenticate=True, group=1, permission={"codename": "upload_provisioning_activity"}
        )

        url = reverse_lazy("provisioning:admin_upload")

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

            expected = {
                "failure": [
                    {
                        "detail": "csv-from-unknown-source",
                        "resources": [
                            {
                                "display_field": "index",
                                "display_value": 1,
                            }
                        ],
                        "status_code": 400,
                    }
                ],
                "success": [],
            }

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_207_MULTI_STATUS)
            self.assertEqual(create_form_entry.delay.call_args_list, [])

            self.assertEqual(Storage.__init__.call_args_list, [])
            self.assertEqual(File.__init__.call_args_list, [])
            self.assertEqual(File.upload.call_args_list, [])
            self.assertEqual(File.url.call_args_list, [])

    # When: auth and file with codespaces format
    # Then: should return a 201
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
        exists=MagicMock(return_value=False),
        url=MagicMock(return_value="https://storage.cloud.google.com/media-breathecode/hardcoded_url"),
        create=True,
    )
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.provisioning.tasks.upload.delay", MagicMock())
    def test_codespaces(self):
        from breathecode.services.google_cloud import File, Storage

        self.headers(academy=1)

        model = self.generate_models(
            authenticate=True, group=1, permission={"codename": "upload_provisioning_activity"}
        )

        url = reverse_lazy("provisioning:admin_upload")

        file = tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w+")

        usernames = [self.bc.fake.slug() for _ in range(0, 3)]
        dates = [self.bc.datetime.to_iso_string(self.bc.datetime.now()).split("T")[0] for _ in range(0, 3)]
        products = [self.bc.fake.name() for _ in range(0, 3)]
        skus = [self.bc.fake.slug() for _ in range(0, 3)]
        quantities = [random.randint(1, 10) for _ in range(0, 3)]
        unit_types = [self.bc.fake.slug() for _ in range(0, 3)]
        price_per_units = [random.random() * 100 for _ in range(0, 3)]
        multipliers = [random.random() * 100 for _ in range(0, 3)]
        owners = [self.bc.fake.slug() for _ in range(0, 3)]

        # dictionary of lists
        obj = {
            "Username": usernames,
            "Date": dates,
            "Product": products,
            "SKU": skus,
            "Quantity": quantities,
            "Unit Type": unit_types,
            "Price Per Unit ($)": price_per_units,
            "Multiplier": multipliers,
            "Owner": owners,
        }

        df = pd.DataFrame.from_dict(obj)
        self.file_name = file.name

        df.to_csv(file.name)

        with open(file.name, "rb") as data:
            hash = hashlib.sha256(data.read()).hexdigest()

        with open(file.name, "rb") as data:
            response = self.client.put(url, {"name": file.name, "file": data})
            json = response.json()

            expected = {
                "failure": [],
                "success": [
                    {
                        "resources": [
                            {
                                "display_field": "index",
                                "display_value": 1,
                                "pk": hash,
                            },
                        ],
                        "status_code": 201,
                    },
                ],
            }

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_207_MULTI_STATUS)

            self.assertEqual(self.bc.database.list_of("provisioning.ProvisioningBill"), [])
            self.assertEqual(self.bc.database.list_of("provisioning.ProvisioningUserConsumption"), [])

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

            self.assertEqual(File.url.call_args_list, [])
            self.bc.check.calls(tasks.upload.delay.call_args_list, [call(hash, total_pages=1)])

    # When: auth and file with codespaces format, file exists
    # Then: should return a 200
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
        exists=MagicMock(return_value=True),
        url=MagicMock(return_value="https://storage.cloud.google.com/media-breathecode/hardcoded_url"),
        create=True,
    )
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.provisioning.tasks.upload.delay", MagicMock())
    def test_codespaces__update(self):
        from breathecode.services.google_cloud import File, Storage

        self.headers(academy=1)

        model = self.generate_models(
            authenticate=True, group=1, permission={"codename": "upload_provisioning_activity"}
        )

        url = reverse_lazy("provisioning:admin_upload")

        file = tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w+")

        usernames = [self.bc.fake.slug() for _ in range(0, 3)]
        dates = [self.bc.datetime.to_iso_string(self.bc.datetime.now()).split("T")[0] for _ in range(0, 3)]
        products = [self.bc.fake.name() for _ in range(0, 3)]
        skus = [self.bc.fake.slug() for _ in range(0, 3)]
        quantities = [random.randint(1, 10) for _ in range(0, 3)]
        unit_types = [self.bc.fake.slug() for _ in range(0, 3)]
        price_per_units = [random.random() * 100 for _ in range(0, 3)]
        multipliers = [random.random() * 100 for _ in range(0, 3)]
        owners = [self.bc.fake.slug() for _ in range(0, 3)]

        # dictionary of lists
        obj = {
            "Username": usernames,
            "Date": dates,
            "Product": products,
            "SKU": skus,
            "Quantity": quantities,
            "Unit Type": unit_types,
            "Price Per Unit ($)": price_per_units,
            "Multiplier": multipliers,
            "Owner": owners,
        }

        df = pd.DataFrame.from_dict(obj)
        self.file_name = file.name

        df.to_csv(file.name)

        with open(file.name, "rb") as data:
            hash = hashlib.sha256(data.read()).hexdigest()

        with open(file.name, "rb") as data:
            response = self.client.put(url, {"name": file.name, "file": data})
            json = response.json()

            expected = {
                "failure": [],
                "success": [
                    {
                        "resources": [
                            {
                                "display_field": "index",
                                "display_value": 1,
                                "pk": hash,
                            },
                        ],
                        "status_code": 200,
                    },
                ],
            }

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_207_MULTI_STATUS)

            self.assertEqual(self.bc.database.list_of("provisioning.ProvisioningBill"), [])
            self.assertEqual(self.bc.database.list_of("provisioning.ProvisioningUserConsumption"), [])

            self.assertEqual(Storage.__init__.call_args_list, [call()])
            self.assertEqual(
                File.__init__.call_args_list,
                [
                    call(Storage().client.bucket("bucket"), hash),
                ],
            )

            self.assertEqual(File.upload.call_args_list, [])
            self.assertEqual(File.url.call_args_list, [])
            self.bc.check.calls(tasks.upload.delay.call_args_list, [call(hash, total_pages=1)])

    # When: auth and file with gitpod format
    # Then: should return a 201
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
        exists=MagicMock(return_value=False),
        url=MagicMock(return_value="https://storage.cloud.google.com/media-breathecode/hardcoded_url"),
        create=True,
    )
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.provisioning.tasks.upload.delay", MagicMock())
    def test_gitpod(self):
        from breathecode.services.google_cloud import File, Storage

        self.headers(academy=1)

        model = self.generate_models(
            authenticate=True, group=1, permission={"codename": "upload_provisioning_activity"}
        )

        url = reverse_lazy("provisioning:admin_upload")

        file = tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w+")

        ids = [random.randint(1, 10) for _ in range(0, 3)]
        credit_cents = [random.randint(1, 10000) for _ in range(0, 3)]
        effective_times = [self.bc.datetime.to_iso_string(self.bc.datetime.now()) for _ in range(0, 3)]
        kinds = [self.bc.fake.slug() for _ in range(0, 3)]
        usernames = [self.bc.fake.slug() for _ in range(0, 3)]
        contextURLs = [
            f"https://github.com/{username}/{self.bc.fake.slug()}/tree/{self.bc.fake.slug()}/" for username in usernames
        ]

        # dictionary of lists
        obj = {
            "id": ids,
            "credits": credit_cents,
            "startTime": effective_times,
            "endTime": effective_times,
            "kind": kinds,
            "userName": usernames,
            "contextURL": contextURLs,
        }

        df = pd.DataFrame.from_dict(obj)
        self.file_name = file.name

        df.to_csv(file.name)

        with open(file.name, "rb") as data:
            hash = hashlib.sha256(data.read()).hexdigest()

        with open(file.name, "rb") as data:
            response = self.client.put(url, {"name": file.name, "file": data})
            j = response.json()

            expected = {
                "failure": [],
                "success": [
                    {
                        "resources": [
                            {
                                "display_field": "index",
                                "display_value": 1,
                                "pk": hash,
                            },
                        ],
                        "status_code": 201,
                    },
                ],
            }

            self.assertEqual(j, expected)
            self.assertEqual(response.status_code, status.HTTP_207_MULTI_STATUS)

            self.assertEqual(self.bc.database.list_of("provisioning.ProvisioningBill"), [])
            self.assertEqual(self.bc.database.list_of("provisioning.ProvisioningUserConsumption"), [])

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

            self.assertEqual(File.url.call_args_list, [])

            self.bc.check.calls(tasks.upload.delay.call_args_list, [call(hash, total_pages=1)])

    # When: auth and file with gitpod format, file exists
    # Then: should return a 200
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
        exists=MagicMock(return_value=True),
        url=MagicMock(return_value="https://storage.cloud.google.com/media-breathecode/hardcoded_url"),
        create=True,
    )
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.provisioning.tasks.upload.delay", MagicMock())
    def test_gitpod__update(self):
        from breathecode.services.google_cloud import File, Storage

        self.headers(academy=1)

        model = self.generate_models(
            authenticate=True, group=1, permission={"codename": "upload_provisioning_activity"}
        )

        url = reverse_lazy("provisioning:admin_upload")

        file = tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w+")

        ids = [random.randint(1, 10) for _ in range(0, 3)]
        credit_cents = [random.randint(1, 10000) for _ in range(0, 3)]
        effective_times = [self.bc.datetime.to_iso_string(self.bc.datetime.now()) for _ in range(0, 3)]
        kinds = [self.bc.fake.slug() for _ in range(0, 3)]
        usernames = [self.bc.fake.slug() for _ in range(0, 3)]
        contextURLs = [
            f"https://github.com/{username}/{self.bc.fake.slug()}/tree/{self.bc.fake.slug()}/" for username in usernames
        ]

        # dictionary of lists
        obj = {
            "id": ids,
            "credits": credit_cents,
            "startTime": effective_times,
            "endTime": effective_times,
            "kind": kinds,
            "userName": usernames,
            "contextURL": contextURLs,
        }

        df = pd.DataFrame.from_dict(obj)
        self.file_name = file.name

        df.to_csv(file.name)

        with open(file.name, "rb") as data:
            hash = hashlib.sha256(data.read()).hexdigest()

        with open(file.name, "rb") as data:
            response = self.client.put(url, {"name": file.name, "file": data})
            j = response.json()

            expected = {
                "failure": [],
                "success": [
                    {
                        "resources": [
                            {
                                "display_field": "index",
                                "display_value": 1,
                                "pk": hash,
                            },
                        ],
                        "status_code": 200,
                    },
                ],
            }

            self.assertEqual(j, expected)
            self.assertEqual(response.status_code, status.HTTP_207_MULTI_STATUS)

            self.assertEqual(self.bc.database.list_of("provisioning.ProvisioningBill"), [])
            self.assertEqual(self.bc.database.list_of("provisioning.ProvisioningUserConsumption"), [])

            self.assertEqual(Storage.__init__.call_args_list, [call()])
            self.assertEqual(
                File.__init__.call_args_list,
                [
                    call(Storage().client.bucket("bucket"), hash),
                ],
            )

            self.assertEqual(File.upload.call_args_list, [])
            self.assertEqual(File.url.call_args_list, [])
            self.bc.check.calls(tasks.upload.delay.call_args_list, [call(hash, total_pages=1)])

    # When: auth and file with gitpod format
    # Then: should return a 201
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
        exists=MagicMock(return_value=False),
        url=MagicMock(return_value="https://storage.cloud.google.com/media-breathecode/hardcoded_url"),
        create=True,
    )
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.provisioning.tasks.upload.delay", MagicMock())
    def test_rigobot(self):
        from breathecode.services.google_cloud import File, Storage

        self.headers(academy=1)

        model = self.generate_models(
            authenticate=True, group=1, permission={"codename": "upload_provisioning_activity"}
        )

        url = reverse_lazy("provisioning:admin_upload")

        file = tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w+")

        # dictionary of lists
        obj = rigobot_csv(lines=3, data={})

        df = pd.DataFrame.from_dict(obj)
        self.file_name = file.name

        df.to_csv(file.name)

        with open(file.name, "rb") as data:
            hash = hashlib.sha256(data.read()).hexdigest()

        with open(file.name, "rb") as data:
            response = self.client.put(url, {"name": file.name, "file": data})
            j = response.json()

            expected = {
                "failure": [],
                "success": [
                    {
                        "resources": [
                            {
                                "display_field": "index",
                                "display_value": 1,
                                "pk": hash,
                            },
                        ],
                        "status_code": 201,
                    },
                ],
            }

            self.assertEqual(j, expected)
            self.assertEqual(response.status_code, status.HTTP_207_MULTI_STATUS)

            self.assertEqual(self.bc.database.list_of("provisioning.ProvisioningBill"), [])
            self.assertEqual(self.bc.database.list_of("provisioning.ProvisioningUserConsumption"), [])

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

            self.assertEqual(File.url.call_args_list, [])

            self.bc.check.calls(tasks.upload.delay.call_args_list, [call(hash, total_pages=1)])

    # When: auth and file with gitpod format, file exists
    # Then: should return a 200
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
        exists=MagicMock(return_value=True),
        url=MagicMock(return_value="https://storage.cloud.google.com/media-breathecode/hardcoded_url"),
        create=True,
    )
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.provisioning.tasks.upload.delay", MagicMock())
    def test_rigobot__update(self):
        from breathecode.services.google_cloud import File, Storage

        self.headers(academy=1)

        model = self.generate_models(
            authenticate=True, group=1, permission={"codename": "upload_provisioning_activity"}
        )

        url = reverse_lazy("provisioning:admin_upload")

        file = tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w+")

        # dictionary of lists
        obj = rigobot_csv(lines=3, data={})

        df = pd.DataFrame.from_dict(obj)
        self.file_name = file.name

        df.to_csv(file.name)

        with open(file.name, "rb") as data:
            hash = hashlib.sha256(data.read()).hexdigest()

        with open(file.name, "rb") as data:
            response = self.client.put(url, {"name": file.name, "file": data})
            j = response.json()

            expected = {
                "failure": [],
                "success": [
                    {
                        "resources": [
                            {
                                "display_field": "index",
                                "display_value": 1,
                                "pk": hash,
                            },
                        ],
                        "status_code": 200,
                    },
                ],
            }

            self.assertEqual(j, expected)
            self.assertEqual(response.status_code, status.HTTP_207_MULTI_STATUS)

            self.assertEqual(self.bc.database.list_of("provisioning.ProvisioningBill"), [])
            self.assertEqual(self.bc.database.list_of("provisioning.ProvisioningUserConsumption"), [])

            self.assertEqual(Storage.__init__.call_args_list, [call()])
            self.assertEqual(
                File.__init__.call_args_list,
                [
                    call(Storage().client.bucket("bucket"), hash),
                ],
            )

            self.assertEqual(File.upload.call_args_list, [])
            self.assertEqual(File.url.call_args_list, [])
            self.bc.check.calls(tasks.upload.delay.call_args_list, [call(hash, total_pages=1)])
