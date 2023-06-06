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
from breathecode.provisioning.tasks import link_pending_github_users_to_bills
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
        'currency_code': 'USD',
        'id': 1,
        'paid_at': None,
        'status': 'PENDING',
        'status_details': None,
        'total_amount': 0.0,
        **data,
    }


class RandomFileTestSuite(ProvisioningTestCase):
    # When: with no bills
    # Then: does not happens anything
    @patch('breathecode.provisioning.tasks.calculate_bill_amounts.delay', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('logging.Logger.warning', MagicMock())
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_no_bill(self):
        slug = self.bc.fake.slug()
        link_pending_github_users_to_bills(slug)

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [])
        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningActivity'), [])

        self.bc.check.calls(logging.Logger.info.call_args_list, [
            call(f'Starting link_pending_github_users_to_bills for hash {slug}'),
        ])

        self.bc.check.calls(logging.Logger.error.call_args_list, [])
        self.bc.check.calls(logging.Logger.warning.call_args_list, [
            call(f'Does not exists bills for hash {slug}'),
        ])

    # Given: 1 ProvisioningBill with status DISPUTED, IGNORED or PAID
    # When: no valid bill
    # Then: does not happens anything
    @patch('breathecode.provisioning.tasks.calculate_bill_amounts.delay', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('logging.Logger.warning', MagicMock())
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_bad_bill(self):
        slug = self.bc.fake.slug()

        provisioning_bill = {'hash': slug, 'status': random.choice(['DISPUTED', 'IGNORED', 'PAID'])}
        model = self.bc.database.create(provisioning_bill=provisioning_bill)

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        link_pending_github_users_to_bills(slug)

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [
            self.bc.format.to_dict(model.provisioning_bill),
        ])

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningActivity'), [])

        self.bc.check.calls(logging.Logger.info.call_args_list, [
            call(f'Starting link_pending_github_users_to_bills for hash {slug}'),
        ])

        self.bc.check.calls(logging.Logger.error.call_args_list, [])
        self.bc.check.calls(logging.Logger.warning.call_args_list, [
            call(f'Does not exists bills for hash {slug}'),
        ])

    # Given: 1 ProvisioningBill with status PENDING or DUE
    # When: no pending github users
    # Then: does not happens anything
    @patch('breathecode.provisioning.tasks.calculate_bill_amounts.delay', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('logging.Logger.warning', MagicMock())
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_bill(self):
        slug = self.bc.fake.slug()

        provisioning_bill = {'hash': slug, 'status': random.choice(['PENDING', 'DUE'])}
        model = self.bc.database.create(provisioning_bill=provisioning_bill)

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []
        logging.Logger.warning.call_args_list = []

        link_pending_github_users_to_bills(slug)

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [
            self.bc.format.to_dict(model.provisioning_bill),
        ])

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningActivity'), [])
        self.bc.check.calls(logging.Logger.info.call_args_list, [
            call(f'Starting link_pending_github_users_to_bills for hash {slug}'),
        ])

        self.bc.check.calls(logging.Logger.error.call_args_list, [])

        self.bc.check.calls(logging.Logger.warning.call_args_list, [
            call(f'Does not exists pending github users for hash {slug}'),
        ])

    # Given: 1 ProvisioningBill with status PENDING or DUE, and 1 PendingGithubUser
    # When: ...
    # Then: does not happens anything
    @patch('breathecode.provisioning.tasks.calculate_bill_amounts.delay', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('logging.Logger.warning', MagicMock())
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_bill__with_pending_github_users(self):
        slug = self.bc.fake.slug()

        provisioning_bill = {'hash': slug, 'status': random.choice(['PENDING', 'DUE'])}
        pending_github_user = {'hashes': [slug], 'status': 'PENDING'}
        model = self.bc.database.create(provisioning_bill=provisioning_bill,
                                        pending_github_user=pending_github_user)

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []
        logging.Logger.warning.call_args_list = []

        link_pending_github_users_to_bills(slug)

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [
            self.bc.format.to_dict(model.provisioning_bill),
        ])

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningActivity'), [])
        self.bc.check.calls(logging.Logger.info.call_args_list, [
            call(f'Starting link_pending_github_users_to_bills for hash {slug}'),
        ])

        self.bc.check.calls(logging.Logger.error.call_args_list, [
            call('There are pending github users that cannot be linked to a academy bill'),
        ])

        self.bc.check.calls(logging.Logger.warning.call_args_list, [])
