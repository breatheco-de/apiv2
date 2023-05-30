"""
Test /v1/marketing/upload
"""
import csv
import json
import random
import tempfile
import os
import hashlib
from unittest.mock import MagicMock, Mock, PropertyMock, call, patch
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins import ProvisioningTestCase
from breathecode.marketing.views import MIME_ALLOW
import pandas as pd
from django.utils import timezone, dateparse
from breathecode.provisioning import tasks

UTC_NOW = timezone.now()


class MarketingTestSuite(ProvisioningTestCase):
    """Test /answer"""

    def setUp(self):
        super().setUp()
        self.file_name = ''

    def tearDown(self):
        if self.file_name:
            os.remove(self.file_name)

    # When: no auth
    # Then: should return 401
    def test_upload_without_auth(self):
        from breathecode.services.google_cloud import Storage, File

        self.headers(content_disposition='attachment; filename="filename.csv"')

        url = reverse_lazy('provisioning:academy_upload')
        data = {}
        response = self.client.put(url, data)
        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # When: auth and no academy header
    # Then: should return 401
    def test_upload_wrong_academy(self):
        from breathecode.services.google_cloud import Storage, File

        self.headers(academy=1, content_disposition='attachment; filename="filename.csv"')

        url = reverse_lazy('provisioning:academy_upload')
        data = {}
        response = self.client.put(url, data)
        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # When: auth and no capability
    # Then: should return 403
    def test_upload_without_capability(self):
        from breathecode.services.google_cloud import Storage, File

        self.headers(academy=1, content_disposition='attachment; filename="filename.csv"')

        url = reverse_lazy('provisioning:academy_upload')
        self.generate_models(authenticate=True)
        data = {}
        response = self.client.put(url, data)
        json = response.json()
        expected = {
            'detail': "You (user: 1) don't have this capability: crud_provisioning_activity for academy 1",
            'status_code': 403
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # When: auth and no files
    # Then: should return empty list
    @patch.multiple('breathecode.services.google_cloud.Storage',
                    __init__=MagicMock(return_value=None),
                    client=PropertyMock(),
                    create=True)
    @patch.multiple(
        'breathecode.services.google_cloud.File',
        __init__=MagicMock(return_value=None),
        bucket=PropertyMock(),
        file_name=PropertyMock(),
        upload=MagicMock(),
        url=MagicMock(return_value='https://storage.cloud.google.com/media-breathecode/hardcoded_url'),
        create=True)
    def test_no_files(self):
        from breathecode.services.google_cloud import Storage, File

        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_provisioning_activity',
                                     role='potato')
        url = reverse_lazy('provisioning:academy_upload')

        response = self.client.put(url, {})
        json = response.json()

        self.assertEqual(json, {'success': [], 'failure': []})
        self.assertEqual(response.status_code, status.HTTP_207_MULTI_STATUS)
        self.assertEqual(self.bc.database.list_of('monitoring.CSVUpload'), [])

        self.assertEqual(Storage.__init__.call_args_list, [])
        self.assertEqual(File.__init__.call_args_list, [])
        self.assertEqual(File.upload.call_args_list, [])
        self.assertEqual(File.url.call_args_list, [])

    # When: auth and bad files
    # Then: should return empty list
    @patch('breathecode.marketing.tasks.create_form_entry.delay', MagicMock())
    @patch.multiple('breathecode.services.google_cloud.Storage',
                    __init__=MagicMock(return_value=None),
                    client=PropertyMock(),
                    create=True)
    @patch.multiple(
        'breathecode.services.google_cloud.File',
        __init__=MagicMock(return_value=None),
        bucket=PropertyMock(),
        file_name=PropertyMock(),
        upload=MagicMock(),
        url=MagicMock(return_value='https://storage.cloud.google.com/media-breathecode/hardcoded_url'),
        create=True)
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test_bad_format(self):
        from breathecode.services.google_cloud import Storage, File
        from breathecode.marketing.tasks import create_form_entry

        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_provisioning_activity',
                                     role='potato')

        url = reverse_lazy('provisioning:academy_upload')

        file = tempfile.NamedTemporaryFile(suffix='.csv', delete=False, mode='w+')

        # list of name, degree, score
        first_names = [self.bc.fake.first_name() for _ in range(0, 3)]
        last_names = [self.bc.fake.last_name() for _ in range(0, 3)]
        emails = [self.bc.fake.email() for _ in range(0, 3)]
        locations = [self.bc.fake.country() for _ in range(0, 3)]
        phone_numbers = [self.bc.fake.phone_number() for _ in range(0, 3)]
        languages = [self.bc.fake.language_name() for _ in range(0, 3)]

        # dictionary of lists
        obj = {
            'first_name': first_names,
            'last_name': last_names,
            'email': emails,
            'location': locations,
            'phone': phone_numbers,
            'language': languages,
        }

        df = pd.DataFrame(obj)

        # saving the dataframe

        self.file_name = file.name

        df.to_csv(file.name)

        with open(file.name, 'rb') as data:
            hash = hashlib.sha256(data.read()).hexdigest()

        with open(file.name, 'rb') as data:
            response = self.client.put(url, {'name': file.name, 'file': data})
            json = response.json()

            file_name = file.name.split('/')[-1]
            # expected = [{'file_name': file_name, 'message': 'Despues', 'status': 'PENDING'}]
            expected = {
                'failure': [{
                    'detail': 'csv-from-unknown-source',
                    'resources': [{
                        'display_field': 'index',
                        'display_value': 1,
                    }],
                    'status_code': 400,
                }],
                'success': [],
            }

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_207_MULTI_STATUS)
            self.assertEqual(create_form_entry.delay.call_args_list, [])

            self.assertEqual(self.bc.database.list_of('monitoring.CSVUpload'), [])

            self.assertEqual(Storage.__init__.call_args_list, [])
            self.assertEqual(File.__init__.call_args_list, [])
            self.assertEqual(File.upload.call_args_list, [])
            self.assertEqual(File.url.call_args_list, [])

    # When: auth and bad files
    # Then: should return empty list
    @patch('breathecode.marketing.tasks.create_form_entry.delay', MagicMock())
    @patch.multiple('breathecode.services.google_cloud.Storage',
                    __init__=MagicMock(return_value=None),
                    client=PropertyMock(),
                    create=True)
    @patch.multiple(
        'breathecode.services.google_cloud.File',
        __init__=MagicMock(return_value=None),
        bucket=PropertyMock(),
        file_name=PropertyMock(),
        upload=MagicMock(),
        exists=MagicMock(return_value=False),
        url=MagicMock(return_value='https://storage.cloud.google.com/media-breathecode/hardcoded_url'),
        create=True)
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.provisioning.tasks.upload.delay', MagicMock())
    def test_codespaces(self):
        from breathecode.services.google_cloud import Storage, File

        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_provisioning_activity',
                                     role='potato')

        url = reverse_lazy('provisioning:academy_upload')

        file = tempfile.NamedTemporaryFile(suffix='.csv', delete=False, mode='w+')

        usernames = [self.bc.fake.slug() for _ in range(0, 3)]
        dates = [self.bc.datetime.to_iso_string(self.bc.datetime.now()) for _ in range(0, 3)]
        products = [self.bc.fake.name() for _ in range(0, 3)]
        skus = [self.bc.fake.slug() for _ in range(0, 3)]
        quantities = [random.randint(1, 10) for _ in range(0, 3)]
        unit_types = [self.bc.fake.slug() for _ in range(0, 3)]
        price_per_units = [random.random() * 100 for _ in range(0, 3)]
        multipliers = [random.random() * 100 for _ in range(0, 3)]
        owners = [self.bc.fake.slug() for _ in range(0, 3)]

        # dictionary of lists
        obj = {
            'Username': usernames,
            'Date': dates,
            'Product': products,
            'SKU': skus,
            'Quantity': quantities,
            'Unit Type': unit_types,
            'Price Per Unit ($)': price_per_units,
            'Multiplier': multipliers,
            'Owner': owners,
        }

        df = pd.DataFrame.from_dict(obj)
        self.file_name = file.name

        df.to_csv(file.name)

        with open(file.name, 'rb') as data:
            hash = hashlib.sha256(data.read()).hexdigest()

        with open(file.name, 'rb') as data:
            response = self.client.put(url, {'name': file.name, 'file': data})
            json = response.json()

            expected = {
                'failure': [],
                'success': [
                    {
                        'resources': [
                            {
                                'display_field': 'index',
                                'display_value': 1,
                                'pk': hash,
                            },
                        ],
                        'status_code': 201,
                    },
                ],
            }

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_207_MULTI_STATUS)

            self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [])
            self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningActivity'), [])

            self.assertEqual(Storage.__init__.call_args_list, [call()])
            self.assertEqual(File.__init__.call_args_list, [
                call(Storage().client.bucket('bucket'), hash),
            ])

            args, kwargs = File.upload.call_args_list[0]

            self.assertEqual(len(File.upload.call_args_list), 1)
            self.assertEqual(len(args), 1)

            self.assertEqual(args[0].name, os.path.basename(file.name))
            self.assertEqual(kwargs, {'content_type': 'text/csv'})

            self.assertEqual(File.url.call_args_list, [])

    # When: auth and bad files
    # Then: should return empty list
    @patch('breathecode.marketing.tasks.create_form_entry.delay', MagicMock())
    @patch.multiple('breathecode.services.google_cloud.Storage',
                    __init__=MagicMock(return_value=None),
                    client=PropertyMock(),
                    create=True)
    @patch.multiple(
        'breathecode.services.google_cloud.File',
        __init__=MagicMock(return_value=None),
        bucket=PropertyMock(),
        file_name=PropertyMock(),
        upload=MagicMock(),
        exists=MagicMock(return_value=False),
        url=MagicMock(return_value='https://storage.cloud.google.com/media-breathecode/hardcoded_url'),
        create=True)
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.provisioning.tasks.upload.delay', MagicMock())
    def test_gitpod(self):
        from breathecode.services.google_cloud import Storage, File

        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_provisioning_activity',
                                     role='potato')

        url = reverse_lazy('provisioning:academy_upload')

        file = tempfile.NamedTemporaryFile(suffix='.csv', delete=False, mode='w+')

        ids = [random.randint(1, 10) for _ in range(0, 3)]
        credit_cents = [random.randint(1, 10000) for _ in range(0, 3)]
        effective_times = [self.bc.datetime.to_iso_string(self.bc.datetime.now()) for _ in range(0, 3)]
        kinds = [self.bc.fake.slug() for _ in range(0, 3)]

        def get_metadata():
            username = self.bc.fake.slug()
            repo = self.bc.fake.slug()
            branch = self.bc.fake.slug()
            return {
                'userName': username,
                'contextURL': f'https://github.com/{username}/{repo}/tree/{branch}/',
            }

        metadata = [json.dumps(get_metadata()) for _ in range(0, 3)]

        # dictionary of lists
        obj = {
            'id': ids,
            'creditCents': credit_cents,
            'effectiveTime': effective_times,
            'kind': kinds,
            'metadata': metadata,
        }

        df = pd.DataFrame.from_dict(obj)
        self.file_name = file.name

        df.to_csv(file.name)

        with open(file.name, 'rb') as data:
            hash = hashlib.sha256(data.read()).hexdigest()

        with open(file.name, 'rb') as data:
            response = self.client.put(url, {'name': file.name, 'file': data})
            j = response.json()

            expected = {
                'failure': [],
                'success': [
                    {
                        'resources': [
                            {
                                'display_field': 'index',
                                'display_value': 1,
                                'pk': hash,
                            },
                        ],
                        'status_code': 201,
                    },
                ],
            }

            self.assertEqual(j, expected)
            self.assertEqual(response.status_code, status.HTTP_207_MULTI_STATUS)

            self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [])
            self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningActivity'), [])

            self.assertEqual(Storage.__init__.call_args_list, [call()])
            self.assertEqual(File.__init__.call_args_list, [
                call(Storage().client.bucket('bucket'), hash),
            ])

            args, kwargs = File.upload.call_args_list[0]

            self.assertEqual(len(File.upload.call_args_list), 1)
            self.assertEqual(len(args), 1)

            self.assertEqual(args[0].name, os.path.basename(file.name))
            self.assertEqual(kwargs, {'content_type': 'text/csv'})

            self.assertEqual(File.url.call_args_list, [])

            self.bc.check.calls(tasks.upload.delay.call_args_list, [call(hash)])
