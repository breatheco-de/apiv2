"""
Test /answer/:id
"""
from datetime import datetime
import io
import json
import random
import pytz
from django.utils import timezone
import pandas as pd
from pytz import UTC
from breathecode.provisioning.tasks import upload
from breathecode.provisioning import tasks
import re, string, os
import logging
from unittest.mock import PropertyMock, patch, MagicMock, call
from breathecode.services.datetime_to_iso_format import datetime_to_iso_format
from random import choices

from breathecode.tests.mocks.requests import apply_requests_get_mock

from ..mixins import ProvisioningTestCase
from faker import Faker

GOOGLE_CLOUD_KEY = os.getenv('GOOGLE_CLOUD_KEY', None)

fake = Faker()
fake_url = fake.url()

UTC_NOW = timezone.now()

USERNAMES = [fake.slug() for _ in range(10)]


def parse(s):
    return json.loads(s)


def repo_name(url):
    pattern = r'^https://github\.com/[^/]+/([^/]+)/'
    result = re.findall(pattern, url)
    return result[0]


def random_string():
    return ''.join(choices(string.ascii_letters, k=10))


def datetime_to_iso(date) -> str:
    return re.sub(r'\+00:00$', 'Z', date.replace(tzinfo=UTC).isoformat())


def datetime_to_show_date(date) -> str:
    return date.strftime('%Y-%m-%d')


def response_mock(status_code=200, content=[]):

    class Response():

        def __init__(self, status_code, content):
            self.status_code = status_code
            self.content = content

        def json(self):
            return self.content

    return MagicMock(side_effect=[Response(status_code, x) for x in content])


def random_csv(lines=1):
    obj = {}

    for i in range(random.randint(1, 7)):
        obj[fake.slug()] = [fake.slug() for _ in range(lines)]

    return obj


def codespaces_csv(lines=1, data={}):
    usernames = [fake.slug() for _ in range(lines)]
    dates = [datetime_to_show_date(datetime.utcnow()) for _ in range(lines)]
    products = [fake.name() for _ in range(lines)]
    skus = [fake.slug() for _ in range(lines)]
    quantities = [random.randint(1, 10) for _ in range(lines)]
    unit_types = [fake.slug() for _ in range(lines)]
    price_per_units = [round(random.random() * 100, 6) for _ in range(lines)]
    multipliers = [round(random.random() * 100, 6) for _ in range(lines)]
    repository_slugs = [fake.slug() for _ in range(lines)]
    owners = [fake.slug() for _ in range(lines)]

    # dictionary of lists
    return {
        'Repository Slug': repository_slugs,
        'Username': usernames,
        'Date': dates,
        'Product': products,
        'SKU': skus,
        'Quantity': quantities,
        'Unit Type': unit_types,
        'Price Per Unit ($)': price_per_units,
        'Multiplier': multipliers,
        'Owner': owners,
        **data,
    }


def get_gitpod_metadata():
    username = fake.slug()
    repo = fake.slug()
    branch = fake.slug()
    return {
        'userName': username,
        'contextURL': f'https://github.com/{username}/{repo}/tree/{branch}/',
    }


def gitpod_csv(lines=1, data={}):
    ids = [random.randint(1, 10) for _ in range(lines)]
    credit_cents = [random.randint(1, 10000) for _ in range(lines)]
    effective_times = [datetime_to_iso(datetime.utcnow()) for _ in range(lines)]
    kinds = [fake.slug() for _ in range(lines)]

    metadata = [json.dumps(get_gitpod_metadata()) for _ in range(lines)]

    # dictionary of lists
    return {
        'id': ids,
        'creditCents': credit_cents,
        'effectiveTime': effective_times,
        'kind': kinds,
        'metadata': metadata,
        **data,
    }


def csv_file_mock(obj):
    df = pd.DataFrame.from_dict(obj)

    s_buf = io.StringIO()
    df.to_csv(s_buf)

    s_buf.seek(0)

    return s_buf.read().encode('utf-8')


def provisioning_activity_data(data={}):
    return {
        'bill_id': 1,
        'currency_code': 'USD',
        'id': 1,
        'multiplier': None,
        'notes': None,
        'price_per_unit': 38.810343970751504,
        'processed_at': ...,
        'product_name': 'Lori Cook',
        'quantity': 8.0,
        'registered_at': ...,
        'repository_url': 'https://github.com/answer-same-which/heart-bill-computer',
        'sku': 'point-yes-another',
        'status': 'PERSISTED',
        'status_text': '',
        'task_associated_slug': 'heart-bill-computer',
        'unit_type': 'eat-hold-member',
        'username': 'soldier-job-woman',
        **data,
    }


def provisioning_bill_data(data={}):
    return {
        'academy_id': 1,
        'currency_code': 'usd',
        'id': 1,
        'paid_at': None,
        'status': 'PENDING',
        'status_details': None,
        'total_amount': 0.0,
        **data,
    }


class RandomFileTestSuite(ProvisioningTestCase):
    # When: random csv is uploaded
    # Then: the task should not create any bill or activity
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
        exists=MagicMock(return_value=True),
        url=MagicMock(return_value='https://storage.cloud.google.com/media-breathecode/hardcoded_url'),
        create=True)
    @patch('breathecode.provisioning.tasks.upload.delay', MagicMock(wraps=upload.delay))
    @patch('breathecode.provisioning.tasks.make_bills.delay', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_random_csv(self):
        csv = random_csv(10)

        slug = self.bc.fake.slug()
        with patch('requests.get', response_mock(content=[{'id': 1} for _ in range(10)])):
            with patch('breathecode.services.google_cloud.File.download',
                       MagicMock(return_value=csv_file_mock(csv))):

                upload(slug)

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [])
        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningActivity'), [])

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f'Starting upload for hash {slug}')])
        self.bc.check.calls(logging.Logger.error.call_args_list, [
            call(f'File {slug} has an unsupported origin or the provider had changed the file format'),
        ])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])


class CodespacesTestSuite(ProvisioningTestCase):

    # Given: a csv with codespaces data
    # When: users does not exist
    # Then: the task should not create any bill or activity
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
        exists=MagicMock(return_value=True),
        url=MagicMock(return_value='https://storage.cloud.google.com/media-breathecode/hardcoded_url'),
        create=True)
    @patch('breathecode.provisioning.tasks.upload.delay', MagicMock(wraps=upload.delay))
    @patch('breathecode.provisioning.tasks.make_bills.delay', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_users_not_found(self):
        csv = codespaces_csv(10)

        slug = self.bc.fake.slug()
        with patch('requests.get', response_mock(content=[{'id': 1} for _ in range(10)])):
            with patch('breathecode.services.google_cloud.File.download',
                       MagicMock(return_value=csv_file_mock(csv))):

                upload(slug)

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [])
        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningActivity'), [])

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f'Starting upload for hash {slug}')])
        self.bc.check.calls(logging.Logger.error.call_args_list,
                            [call(f'User {slug} not found') for slug in csv['Username']])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])

    # Given: a csv with codespaces data and 10 User
    # When: get emails from github and the email is registered
    # Then: the task should not create any bill or activity
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
        exists=MagicMock(return_value=True),
        url=MagicMock(return_value='https://storage.cloud.google.com/media-breathecode/hardcoded_url'),
        create=True)
    @patch('breathecode.provisioning.tasks.upload.delay', MagicMock(wraps=upload.delay))
    @patch('breathecode.provisioning.tasks.make_bills.delay', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_from_github__users_not_found_in_any_cohort(self):
        csv = codespaces_csv(10)

        model = self.bc.database.create(user=10)

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        slug = self.bc.fake.slug()
        with patch('requests.get', response_mock(content=[{'email': x.email} for x in model.user])):
            with patch('breathecode.services.google_cloud.File.download',
                       MagicMock(return_value=csv_file_mock(csv))):

                upload(slug)

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [])
        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningActivity'), [])

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f'Starting upload for hash {slug}')])
        self.bc.check.calls(logging.Logger.error.call_args_list,
                            [call(f'User {slug} not found in any cohort') for slug in csv['Username']])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])

    # Given: a csv with codespaces data and 10 User, 10 CredentialsGithub
    # When: user with github credentials saved
    # Then: the task should not create any bill or activity
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
        exists=MagicMock(return_value=True),
        url=MagicMock(return_value='https://storage.cloud.google.com/media-breathecode/hardcoded_url'),
        create=True)
    @patch('breathecode.provisioning.tasks.upload.delay', MagicMock(wraps=upload.delay))
    @patch('breathecode.provisioning.tasks.make_bills.delay', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_from_github_credentials__users_not_found_in_any_cohort(self):
        csv = codespaces_csv(10)

        credentials_github = [{
            'username': csv['Username'][n],
            'user_id': n + 1,
        } for n in range(10)]
        model = self.bc.database.create(user=10, credentials_github=credentials_github)

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        slug = self.bc.fake.slug()
        with patch('breathecode.services.google_cloud.File.download',
                   MagicMock(return_value=csv_file_mock(csv))):

            upload(slug)

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [])
        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningActivity'), [])

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f'Starting upload for hash {slug}')])
        self.bc.check.calls(logging.Logger.error.call_args_list,
                            [call(f'User {slug} not found in any cohort') for slug in csv['Username']])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])

    # Given: a csv with codespaces data and 10 User, 10 CohortUser, 10 Cohort, 10 CredentialsGithub and
    #        1 SyllabusVersion
    # When: vendor not found
    # Then: the task should not create any bill or activity
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
        exists=MagicMock(return_value=True),
        url=MagicMock(return_value='https://storage.cloud.google.com/media-breathecode/hardcoded_url'),
        create=True)
    @patch('breathecode.provisioning.tasks.upload.delay', MagicMock(wraps=upload.delay))
    @patch('breathecode.provisioning.tasks.make_bills.delay', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_from_github_credentials__vendor_not_found(self):
        csv = codespaces_csv(10)

        credentials_github = [{
            'username': csv['Username'][n],
            'user_id': n + 1,
        } for n in range(10)]
        cohort_users = [{'user_id': n + 1} for n in range(10)]
        syllabus_version = {'json': {'tasks': [csv['Repository Slug'][n] for n in range(10)]}}
        model = self.bc.database.create(user=10,
                                        credentials_github=credentials_github,
                                        cohort_user=cohort_users,
                                        syllabus_version=syllabus_version)

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        slug = self.bc.fake.slug()
        with patch('breathecode.services.google_cloud.File.download',
                   MagicMock(return_value=csv_file_mock(csv))):

            upload(slug)

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [
            provisioning_bill_data({'hash': slug}),
        ])
        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningActivity'), [])

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f'Starting upload for hash {slug}')])
        self.bc.check.calls(
            logging.Logger.error.call_args_list,
            [call(f'File {slug} cannot be processed due to: Provisioning vendor Codespaces not found')])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])

    # Given: a csv with codespaces data and 10 User, 10 CohortUser, 10 Cohort, 10 CredentialsGithub,
    #        1 SyllabusVersion and 1 ProvisioningVendor of type codespaces
    # When: all the data is correct
    # Then: the task should create 1 bills and 10 activities
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
        exists=MagicMock(return_value=True),
        url=MagicMock(return_value='https://storage.cloud.google.com/media-breathecode/hardcoded_url'),
        create=True)
    @patch('breathecode.provisioning.tasks.upload.delay', MagicMock(wraps=upload.delay))
    @patch('breathecode.provisioning.tasks.make_bills.delay', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_from_github_credentials__generate_anything(self):
        csv = codespaces_csv(10)

        credentials_github = [{
            'username': csv['Username'][n],
            'user_id': n + 1,
        } for n in range(10)]
        cohort_users = [{'user_id': n + 1} for n in range(10)]
        syllabus_version = {'json': {'tasks': [csv['Repository Slug'][n] for n in range(10)]}}
        provisioning_vendor = {'name': 'Codespaces'}
        model = self.bc.database.create(user=10,
                                        credentials_github=credentials_github,
                                        cohort_user=cohort_users,
                                        provisioning_vendor=provisioning_vendor,
                                        syllabus_version=syllabus_version)

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        slug = self.bc.fake.slug()
        with patch('breathecode.services.google_cloud.File.download',
                   MagicMock(return_value=csv_file_mock(csv))):

            upload(slug)

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [
            provisioning_bill_data({'hash': slug}),
        ])

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningActivity'), [
            provisioning_activity_data(
                {
                    'id': n + 1,
                    'bill_id': 1,
                    'username': csv['Username'][n],
                    'registered_at': datetime.strptime(csv['Date'][n], '%Y-%m-%d').replace(tzinfo=pytz.UTC),
                    'product_name': csv['Product'][n],
                    'sku': csv['SKU'][n],
                    'quantity': float(csv['Quantity'][n]),
                    'unit_type': csv['Unit Type'][n],
                    'price_per_unit': csv['Price Per Unit ($)'][n],
                    'currency_code': 'USD',
                    'multiplier': csv['Multiplier'][n],
                    'repository_url': f"https://github.com/{csv['Owner'][n]}/{csv['Repository Slug'][n]}",
                    'task_associated_slug': csv['Repository Slug'][n],
                    'processed_at': UTC_NOW,
                    'status': 'PERSISTED',
                }) for n in range(10)
        ])

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f'Starting upload for hash {slug}')])
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])


class GitpodTestSuite(ProvisioningTestCase):

    # Given: a csv with codespaces data
    # When: users does not exist
    # Then: the task should not create any bill or activity
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
        exists=MagicMock(return_value=True),
        url=MagicMock(return_value='https://storage.cloud.google.com/media-breathecode/hardcoded_url'),
        create=True)
    @patch('breathecode.provisioning.tasks.upload.delay', MagicMock(wraps=upload.delay))
    @patch('breathecode.provisioning.tasks.make_bills.delay', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_users_not_found(self):
        csv = gitpod_csv(10)

        slug = self.bc.fake.slug()
        with patch('requests.get', response_mock(content=[{'id': 1} for _ in range(10)])):
            with patch('breathecode.services.google_cloud.File.download',
                       MagicMock(return_value=csv_file_mock(csv))):

                upload(slug)

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [])
        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningActivity'), [])

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f'Starting upload for hash {slug}')])
        self.bc.check.calls(logging.Logger.error.call_args_list,
                            [call(f'User {parse(x)["userName"]} not found') for x in csv['metadata']])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])

    # Given: a csv with codespaces data and 10 User
    # When: get emails from github and the email is registered
    # Then: the task should not create any bill or activity
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
        exists=MagicMock(return_value=True),
        url=MagicMock(return_value='https://storage.cloud.google.com/media-breathecode/hardcoded_url'),
        create=True)
    @patch('breathecode.provisioning.tasks.upload.delay', MagicMock(wraps=upload.delay))
    @patch('breathecode.provisioning.tasks.make_bills.delay', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_from_github__users_not_found_in_any_cohort(self):
        csv = gitpod_csv(10)

        model = self.bc.database.create(user=10)

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        slug = self.bc.fake.slug()
        with patch('requests.get', response_mock(content=[{'email': x.email} for x in model.user])):
            with patch('breathecode.services.google_cloud.File.download',
                       MagicMock(return_value=csv_file_mock(csv))):

                upload(slug)

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [])
        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningActivity'), [])

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f'Starting upload for hash {slug}')])
        self.bc.check.calls(
            logging.Logger.error.call_args_list,
            [call(f'User {parse(x)["userName"]} not found in any cohort') for x in csv['metadata']])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])

    # Given: a csv with codespaces data and 10 User, 10 CredentialsGithub
    # When: user with github credentials saved
    # Then: the task should not create any bill or activity
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
        exists=MagicMock(return_value=True),
        url=MagicMock(return_value='https://storage.cloud.google.com/media-breathecode/hardcoded_url'),
        create=True)
    @patch('breathecode.provisioning.tasks.upload.delay', MagicMock(wraps=upload.delay))
    @patch('breathecode.provisioning.tasks.make_bills.delay', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_from_github_credentials__users_not_found_in_any_cohort(self):
        csv = gitpod_csv(10)

        credentials_github = [{
            'username': parse(csv['metadata'][n])['userName'],
            'user_id': n + 1,
        } for n in range(10)]
        model = self.bc.database.create(user=10, credentials_github=credentials_github)

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        slug = self.bc.fake.slug()
        with patch('breathecode.services.google_cloud.File.download',
                   MagicMock(return_value=csv_file_mock(csv))):

            upload(slug)

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [])
        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningActivity'), [])

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f'Starting upload for hash {slug}')])
        self.bc.check.calls(
            logging.Logger.error.call_args_list,
            [call(f'User {parse(x)["userName"]} not found in any cohort') for x in csv['metadata']])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])

    # Given: a csv with codespaces data and 10 User, 10 CohortUser, 10 Cohort, 10 CredentialsGithub and
    #        1 SyllabusVersion
    # When: vendor not found
    # Then: the task should not create any bill or activity
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
        exists=MagicMock(return_value=True),
        url=MagicMock(return_value='https://storage.cloud.google.com/media-breathecode/hardcoded_url'),
        create=True)
    @patch('breathecode.provisioning.tasks.upload.delay', MagicMock(wraps=upload.delay))
    @patch('breathecode.provisioning.tasks.make_bills.delay', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_from_github_credentials__vendor_not_found(self):
        csv = gitpod_csv(10)

        credentials_github = [{
            'username': parse(csv['metadata'][n])['userName'],
            'user_id': n + 1,
        } for n in range(10)]
        cohort_users = [{'user_id': n + 1} for n in range(10)]
        syllabus_version = {
            'json': {
                'tasks': [repo_name(parse(csv['metadata'][n])['contextURL']) for n in range(10)]
            }
        }
        model = self.bc.database.create(user=10,
                                        credentials_github=credentials_github,
                                        cohort_user=cohort_users,
                                        syllabus_version=syllabus_version)

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        slug = self.bc.fake.slug()
        with patch('breathecode.services.google_cloud.File.download',
                   MagicMock(return_value=csv_file_mock(csv))):

            upload(slug)

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [
            provisioning_bill_data({'hash': slug}),
        ])
        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningActivity'), [])

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f'Starting upload for hash {slug}')])
        self.bc.check.calls(
            logging.Logger.error.call_args_list,
            [call(f'File {slug} cannot be processed due to: Provisioning vendor Codespaces not found')])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])

    # Given: a csv with codespaces data and 10 User, 10 CohortUser, 10 Cohort, 10 CredentialsGithub,
    #        1 SyllabusVersion and 1 ProvisioningVendor of type codespaces
    # When: all the data is correct
    # Then: the task should create 1 bills and 10 activities
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
        exists=MagicMock(return_value=True),
        url=MagicMock(return_value='https://storage.cloud.google.com/media-breathecode/hardcoded_url'),
        create=True)
    @patch('breathecode.provisioning.tasks.upload.delay', MagicMock(wraps=upload.delay))
    @patch('breathecode.provisioning.tasks.make_bills.delay', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_from_github_credentials__generate_anything(self):
        csv = gitpod_csv(10)

        credentials_github = [{
            'username': parse(csv['metadata'][n])['userName'],
            'user_id': n + 1,
        } for n in range(10)]
        cohort_users = [{'user_id': n + 1} for n in range(10)]
        syllabus_version = {
            'json': {
                'tasks': [repo_name(parse(csv['metadata'][n])['contextURL']) for n in range(10)]
            }
        }
        provisioning_vendor = {'name': 'Codespaces'}
        model = self.bc.database.create(user=10,
                                        credentials_github=credentials_github,
                                        cohort_user=cohort_users,
                                        provisioning_vendor=provisioning_vendor,
                                        syllabus_version=syllabus_version)

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        slug = self.bc.fake.slug()
        with patch('breathecode.services.google_cloud.File.download',
                   MagicMock(return_value=csv_file_mock(csv))):

            upload(slug)

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [
            provisioning_bill_data({'hash': slug}),
        ])

        self.assertEqual(
            self.bc.database.list_of('provisioning.ProvisioningActivity'),
            [
                provisioning_activity_data(
                    {
                        'id': n + 1,
                        'bill_id': 1,
                        'username': parse(csv['metadata'][n])['userName'],
                        'registered_at': self.bc.datetime.from_iso_string(csv['effectiveTime'][n]),
                        'product_name': csv['kind'][n],
                        'sku': str(csv['id'][n]),
                        'quantity': float(csv['creditCents'][n]),
                        'unit_type': 'Credit cents',
                        'price_per_unit': 0.00036,
                        'currency_code': 'USD',
                        # 'multiplier': csv['Multiplier'][n],
                        'repository_url': parse(csv['metadata'][n])['contextURL'],
                        'task_associated_slug': repo_name(parse(csv['metadata'][n])['contextURL']),
                        'processed_at': UTC_NOW,
                        'status': 'PERSISTED',
                    }) for n in range(10)
            ])

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f'Starting upload for hash {slug}')])
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])
