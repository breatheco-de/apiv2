"""
Test /answer/:id
"""

import json
import logging
import os
import random
import re
import string
from datetime import datetime, timedelta
from decimal import Decimal, localcontext
from random import choices
from unittest.mock import MagicMock, PropertyMock, call, patch

import pandas as pd
import pytest
import pytz
from django.utils import timezone
from faker import Faker
from pytz import UTC

from breathecode.provisioning import tasks
from breathecode.provisioning.tasks import upload

from ..mixins import ProvisioningTestCase

GOOGLE_CLOUD_KEY = os.getenv("GOOGLE_CLOUD_KEY", None)

fake = Faker()
fake_url = fake.url()

UTC_NOW = timezone.now()

USERNAMES = [fake.slug() for _ in range(10)]
RANDOM_ACADEMIES = [random.randint(0, 2) for _ in range(10)]

while len(set(RANDOM_ACADEMIES[:3])) != 3:
    RANDOM_ACADEMIES = [random.randint(0, 2) for _ in range(10)]


@pytest.fixture(autouse=True)
def setup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("linked_services.django.tasks.check_credentials.delay", MagicMock())


def parse(s):
    return json.loads(s)


def repo_name(url):
    pattern = r"^https://github\.com/[^/]+/([^/]+)/"
    result = re.findall(pattern, url)
    return result[0]


def random_string():
    return "".join(choices(string.ascii_letters, k=10))


def datetime_to_iso(date) -> str:
    return re.sub(r"\+00:00$", "Z", date.replace(tzinfo=UTC).isoformat())


def datetime_to_show_date(date) -> str:
    return date.strftime("%Y-%m-%d")


def response_mock(status_code=200, content=[]):

    class Response:

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
    dates = [datetime_to_show_date(timezone.now()) for _ in range(lines)]
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
        "Repository Slug": repository_slugs,
        "Username": usernames,
        "Date": dates,
        "Product": products,
        "SKU": skus,
        "Quantity": quantities,
        "Unit Type": unit_types,
        "Price Per Unit ($)": price_per_units,
        "Multiplier": multipliers,
        "Owner": owners,
        **data,
    }


def gitpod_csv(lines=1, data={}):
    ids = [random.randint(1, 10) for _ in range(lines)]
    credit_cents = [random.randint(1, 10000) for _ in range(lines)]
    effective_times = [datetime_to_iso(timezone.now()) for _ in range(lines)]
    kinds = [fake.slug() for _ in range(lines)]
    usernames = [fake.slug() for _ in range(lines)]
    contextURLs = [f"https://github.com/{username}/{fake.slug()}/tree/{fake.slug()}/" for username in usernames]

    # dictionary of lists
    return {
        "id": ids,
        "credits": credit_cents,
        "startTime": effective_times,
        "endTime": effective_times,
        "kind": kinds,
        "userName": usernames,
        "contextURL": contextURLs,
        **data,
    }


def datetime_to_date_str(date: datetime) -> str:
    return date.strftime("%Y-%m-%d")


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


def csv_file_mock(obj):
    df = pd.DataFrame.from_dict(obj)

    def csv_file_mock_inner(file):
        df.to_csv(file)
        file.seek(0)

    return csv_file_mock_inner


def currency_data(data={}):
    return {
        "code": "USD",
        "decimals": 2,
        "id": 1,
        "name": "US Dollar",
        **data,
    }


def provisioning_activity_kind_data(data={}):
    return {
        "id": 1,
        "product_name": "Lori Cook",
        "sku": "point-yes-another",
        **data,
    }


def provisioning_activity_price_data(data={}):
    return {
        "id": 1,
        "currency_id": 1,
        "multiplier": 1.0,
        "price_per_unit": 0.0,
        "unit_type": "",
        **data,
    }


def provisioning_activity_item_data(data={}):
    return {
        "external_pk": None,
        "id": 1,
        "price_id": 1,
        "quantity": 0.0,
        "registered_at": ...,
        "repository_url": None,
        "task_associated_slug": None,
        "vendor_id": None,
        "csv_row": 0,
        **data,
    }


def provisioning_activity_data(data={}):
    return {
        "id": 1,
        "processed_at": ...,
        "status": "PERSISTED",
        "status_text": "",
        "username": "soldier-job-woman",
        "amount": 0.0,
        "quantity": 0.0,
        **data,
    }


def provisioning_bill_data(data={}):
    return {
        "academy_id": 1,
        "currency_code": "USD",
        "id": 1,
        "paid_at": None,
        "status": "PENDING",
        "status_details": None,
        "total_amount": 0.0,
        "fee": 0.0,
        "stripe_id": None,
        "stripe_url": None,
        "vendor_id": None,
        "started_at": None,
        "ended_at": None,
        "title": None,
        "archived_at": None,
        **data,
    }


def github_academy_user_data(data={}):
    return {
        "academy_id": 0,
        "id": 0,
        "storage_action": "ADD",
        "storage_log": None,
        "storage_status": "PENDING",
        "storage_synch_at": None,
        "user_id": None,
        "username": None,
        **data,
    }


def get_last_task_manager_id(bc):
    task_manager_cls = bc.database.get_model("task_manager.TaskManager")
    task_manager = task_manager_cls.objects.order_by("-id").first()

    if task_manager is None:
        return 0

    return task_manager.id


class RandomFileTestSuite(ProvisioningTestCase):
    # When: random csv is uploaded and the file does not exists
    # Then: the task should not create any bill or activity
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
    @patch("breathecode.provisioning.tasks.upload.delay", MagicMock(wraps=upload.delay))
    @patch("breathecode.provisioning.tasks.calculate_bill_amounts.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    def test_random_csv__file_does_not_exists(self):
        csv = random_csv(10)

        slug = self.bc.fake.slug()
        with patch("requests.get", response_mock(content=[{"id": 1} for _ in range(10)])):
            with patch("breathecode.services.google_cloud.File.download", MagicMock(side_effect=csv_file_mock(csv))):

                upload(slug)

        self.assertEqual(self.bc.database.list_of("provisioning.ProvisioningBill"), [])
        self.assertEqual(self.bc.database.list_of("provisioning.ProvisioningUserConsumption"), [])
        self.assertEqual(self.bc.database.list_of("authenticate.GithubAcademyUser"), [])

        self.bc.check.calls(
            logging.Logger.info.call_args_list,
            [
                call(f"Starting upload for hash {slug}"),
                # retrying
                call(f"Starting upload for hash {slug}"),
            ],
        )
        self.bc.check.calls(
            logging.Logger.error.call_args_list,
            [
                call(f"File {slug} not found", exc_info=True),
            ],
        )

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])
        self.bc.check.calls(tasks.calculate_bill_amounts.delay.call_args_list, [])

    # When: random csv is uploaded and the file exists
    # Then: the task should not create any bill or activity
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
    @patch("breathecode.provisioning.tasks.upload.delay", MagicMock(wraps=upload.delay))
    @patch("breathecode.provisioning.tasks.calculate_bill_amounts.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    def test_random_csv__file_exists(self):
        csv = random_csv(10)

        slug = self.bc.fake.slug()
        with patch("requests.get", response_mock(content=[{"id": 1} for _ in range(10)])):
            with patch("breathecode.services.google_cloud.File.download", MagicMock(side_effect=csv_file_mock(csv))):

                upload(slug)

        self.assertEqual(self.bc.database.list_of("provisioning.ProvisioningBill"), [])
        self.assertEqual(self.bc.database.list_of("provisioning.ProvisioningUserConsumption"), [])
        self.assertEqual(self.bc.database.list_of("authenticate.GithubAcademyUser"), [])

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f"Starting upload for hash {slug}")])
        self.bc.check.calls(
            logging.Logger.error.call_args_list,
            [
                call(
                    f"File {slug} has an unsupported origin or the provider had changed the file format", exc_info=True
                ),
            ],
        )

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])
        self.bc.check.calls(tasks.calculate_bill_amounts.delay.call_args_list, [])

    # Given: a csv and 1 ProvisioningBill
    # When: random csv is uploaded and the file exists
    # Then: the task should not create any bill or activity
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
    @patch("breathecode.provisioning.tasks.upload.delay", MagicMock(wraps=upload.delay))
    @patch("breathecode.provisioning.tasks.calculate_bill_amounts.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    def test_random_csv__file_exists__already_processed(self):
        csv = random_csv(10)
        slug = self.bc.fake.slug()
        provisioning_bill = {"hash": slug}
        model = self.bc.database.create(provisioning_bill=provisioning_bill)

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        with patch("requests.get", response_mock(content=[{"id": 1} for _ in range(10)])):
            with patch("breathecode.services.google_cloud.File.download", MagicMock(side_effect=csv_file_mock(csv))):

                upload(slug)

        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningBill"),
            [
                self.bc.format.to_dict(model.provisioning_bill),
            ],
        )
        self.assertEqual(self.bc.database.list_of("provisioning.ProvisioningUserConsumption"), [])
        self.assertEqual(self.bc.database.list_of("authenticate.GithubAcademyUser"), [])

        self.bc.check.calls(
            logging.Logger.info.call_args_list,
            [
                call(f"Starting upload for hash {slug}"),
            ],
        )
        self.bc.check.calls(
            logging.Logger.error.call_args_list,
            [
                call(f"File {slug} already processed", exc_info=True),
            ],
        )

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])
        self.bc.check.calls(tasks.calculate_bill_amounts.delay.call_args_list, [])

    # Given: a csv and 1 ProvisioningBill
    # When: random csv is uploaded and the file exists
    # Then: the task should not create any bill or activity
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
    @patch("breathecode.provisioning.tasks.upload.delay", MagicMock(wraps=upload.delay))
    @patch("breathecode.provisioning.tasks.calculate_bill_amounts.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    def test_random_csv__file_exists__already_processed__(self):
        csv = random_csv(10)
        slug = self.bc.fake.slug()
        provisioning_bill = {
            "hash": slug,
            "status": random.choice(["DISPUTED", "IGNORED", "PAID"]),
        }
        model = self.bc.database.create(provisioning_bill=provisioning_bill)

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        with patch("requests.get", response_mock(content=[{"id": 1} for _ in range(10)])):
            with patch("breathecode.services.google_cloud.File.download", MagicMock(side_effect=csv_file_mock(csv))):

                upload(slug, force=True)

        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningBill"),
            [
                self.bc.format.to_dict(model.provisioning_bill),
            ],
        )
        self.assertEqual(self.bc.database.list_of("provisioning.ProvisioningUserConsumption"), [])
        self.assertEqual(self.bc.database.list_of("authenticate.GithubAcademyUser"), [])

        self.bc.check.calls(
            logging.Logger.info.call_args_list,
            [
                call(f"Starting upload for hash {slug}"),
            ],
        )
        self.bc.check.calls(
            logging.Logger.error.call_args_list,
            [
                call(
                    "Cannot force upload because there are bills with status DISPUTED, IGNORED or PAID", exc_info=True
                ),
            ],
        )

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])
        self.bc.check.calls(tasks.calculate_bill_amounts.delay.call_args_list, [])


class CodespacesTestSuite(ProvisioningTestCase):
    ...

    # Given: a csv with codespaces data
    # When: users does not exist and vendor not found
    # Then: the task should not create any bill or activity
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
    @patch("breathecode.provisioning.tasks.upload.delay", MagicMock(wraps=upload.delay))
    @patch("breathecode.provisioning.tasks.calculate_bill_amounts.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    def test_users_not_found(self):
        csv = codespaces_csv(10)

        slug = self.bc.fake.slug()
        with patch("requests.get", response_mock(content=[{"id": 1} for _ in range(10)])):
            with patch("breathecode.services.google_cloud.File.download", MagicMock(side_effect=csv_file_mock(csv))):

                upload(slug)

        self.assertEqual(self.bc.database.list_of("payments.Currency"), [currency_data()])
        self.assertEqual(self.bc.database.list_of("provisioning.ProvisioningBill"), [])
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionKind"),
            [
                provisioning_activity_kind_data(
                    {
                        "id": n + 1,
                        "product_name": csv["Product"][n],
                        "sku": str(csv["SKU"][n]),
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningPrice"),
            [
                provisioning_activity_price_data(
                    {
                        "currency_id": 1,
                        "id": n + 1,
                        "multiplier": csv["Multiplier"][n],
                        "price_per_unit": csv["Price Per Unit ($)"][n] * 1.3,
                        "unit_type": csv["Unit Type"][n],
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionEvent"),
            [
                provisioning_activity_item_data(
                    {
                        "id": n + 1,
                        "price_id": n + 1,
                        "quantity": float(csv["Quantity"][n]),
                        "registered_at": datetime.strptime(csv["Date"][n], "%Y-%m-%d").replace(tzinfo=pytz.UTC),
                        "repository_url": f"https://github.com/{csv['Owner'][n]}/{csv['Repository Slug'][n]}",
                        "task_associated_slug": csv["Repository Slug"][n],
                        "csv_row": n,
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningUserConsumption"),
            [
                provisioning_activity_data(
                    {
                        "id": n + 1,
                        "kind_id": n + 1,
                        "hash": slug,
                        "username": csv["Username"][n],
                        "processed_at": UTC_NOW,
                        "status": "ERROR",
                        "status_text": ", ".join(
                            [
                                "Provisioning vendor Codespaces not found",
                                f"We could not find enough information about {csv['Username'][n]}, mark this user user "
                                "as deleted if you don't recognize it",
                            ]
                        ),
                    }
                )
                for n in range(10)
            ],
        )

        self.assertEqual(self.bc.database.list_of("authenticate.GithubAcademyUser"), [])

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f"Starting upload for hash {slug}")])

        self.bc.check.calls(
            logging.Logger.error.call_args_list, [call(f"Organization {csv['Owner'][n]} not found") for n in range(10)]
        )

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])
        self.bc.check.calls(tasks.calculate_bill_amounts.delay.call_args_list, [])

    # Given: a csv with codespaces data, 20 AcademyAuthSettings, 20 Academy
    # When: users does not exist, vendor not found and
    #    -> each github organization have two AcademyAuthSettings
    # Then: the task should create 20 bills, 20 activities and two GithubAcademyUser per academy
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
    @patch("breathecode.provisioning.tasks.upload.delay", MagicMock(wraps=upload.delay))
    @patch("breathecode.provisioning.tasks.calculate_bill_amounts.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    def test_users_not_found__case1(self):
        csv = codespaces_csv(10)

        academy_auth_settings = []

        id = 0
        for owner in csv["Owner"]:
            academy_auth_settings.append({"github_username": owner, "academy_id": id + 1})
            academy_auth_settings.append({"github_username": owner, "academy_id": id + 2})
            id += 2

        github_academy_users = [
            {
                "user_id": 1,
                "academy_id": n + 1,
                "storage_action": "ADD",
                "storage_status": "SYNCHED",
            }
            for n in range(20)
        ]

        model = self.bc.database.create(
            academy_auth_settings=academy_auth_settings, academy=20, user=1, github_academy_user=github_academy_users
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        slug = self.bc.fake.slug()
        with patch("requests.get", response_mock(content=[{"id": 1} for _ in range(10)])):
            with patch("breathecode.services.google_cloud.File.download", MagicMock(side_effect=csv_file_mock(csv))):

                upload(slug)

        self.assertEqual(self.bc.database.list_of("payments.Currency"), [currency_data()])
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningBill"),
            [
                provisioning_bill_data(
                    {
                        "id": n + 1,
                        "academy_id": n + 1,
                        "vendor_id": None,
                        "hash": slug,
                        "total_amount": 0.0,
                        "status": "ERROR",
                    }
                )
                for n in range(20)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionKind"),
            [
                provisioning_activity_kind_data(
                    {
                        "id": n + 1,
                        "product_name": csv["Product"][n],
                        "sku": str(csv["SKU"][n]),
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningPrice"),
            [
                provisioning_activity_price_data(
                    {
                        "currency_id": 1,
                        "id": n + 1,
                        "multiplier": csv["Multiplier"][n],
                        "price_per_unit": csv["Price Per Unit ($)"][n] * 1.3,
                        "unit_type": csv["Unit Type"][n],
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionEvent"),
            [
                provisioning_activity_item_data(
                    {
                        "id": n + 1,
                        "price_id": n + 1,
                        "quantity": float(csv["Quantity"][n]),
                        "registered_at": datetime.strptime(csv["Date"][n], "%Y-%m-%d").replace(tzinfo=pytz.UTC),
                        "repository_url": f"https://github.com/{csv['Owner'][n]}/{csv['Repository Slug'][n]}",
                        "task_associated_slug": csv["Repository Slug"][n],
                        "csv_row": n,
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningUserConsumption"),
            [
                provisioning_activity_data(
                    {
                        "id": n + 1,
                        "kind_id": n + 1,
                        "hash": slug,
                        "username": csv["Username"][n],
                        "processed_at": UTC_NOW,
                        "status": "ERROR",
                        "status_text": ", ".join(
                            [
                                "Provisioning vendor Codespaces not found",
                                f"We could not find enough information about {csv['Username'][n]}, mark this user user "
                                "as deleted if you don't recognize it",
                            ]
                        ),
                    }
                )
                for n in range(10)
            ],
        )

        id = 0
        github_academy_users = self.bc.format.to_dict(model.github_academy_user)

        for n in range(10):
            github_academy_users.append(
                github_academy_user_data(
                    data={
                        "id": id + 1 + 20,
                        "academy_id": id + 1,
                        "storage_action": "IGNORE",
                        "storage_status": "PAYMENT_CONFLICT",
                        "username": csv["Username"][n],
                    }
                )
            )

            github_academy_users.append(
                github_academy_user_data(
                    data={
                        "id": id + 2 + 20,
                        "academy_id": id + 2,
                        "storage_action": "IGNORE",
                        "storage_status": "PAYMENT_CONFLICT",
                        "username": csv["Username"][n],
                    }
                )
            )

            id += 2

        self.assertEqual(self.bc.database.list_of("authenticate.GithubAcademyUser"), github_academy_users)

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f"Starting upload for hash {slug}")])
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])
        self.bc.check.calls(tasks.calculate_bill_amounts.delay.call_args_list, [])

    # Given: a csv with codespaces data, 20 AcademyAuthSettings, 20 Academy
    # When: users does not exist, vendor not found and
    #    -> each github organization have two AcademyAuthSettings
    # Then: the task should create 20 bills, 20 activities and two GithubAcademyUser per academy
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
    @patch("breathecode.provisioning.tasks.upload.delay", MagicMock(wraps=upload.delay))
    @patch("breathecode.provisioning.tasks.calculate_bill_amounts.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    def test_users_not_found__case2(self):
        csv = codespaces_csv(10)

        academy_auth_settings = []
        id = 0

        for owner in csv["Owner"]:
            academy_auth_settings.append({"github_username": owner, "academy_id": id + 1})
            academy_auth_settings.append({"github_username": owner, "academy_id": id + 2})
            id += 2

        credentials_github = [{"username": csv["Username"][n], "user_id": n + 1} for n in range(10)]
        github_academy_users = [
            {
                "user_id": 11,
                "academy_id": n + 1,
                "storage_action": "ADD",
                "storage_status": "SYNCHED",
            }
            for n in range(20)
        ]
        model = self.bc.database.create(
            academy_auth_settings=academy_auth_settings,
            academy=20,
            user=11,
            github_academy_user=github_academy_users,
            credentials_github=credentials_github,
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        slug = self.bc.fake.slug()
        with patch("requests.get", response_mock(content=[{"id": 1} for _ in range(10)])):
            with patch("breathecode.services.google_cloud.File.download", MagicMock(side_effect=csv_file_mock(csv))):

                upload(slug)

        self.assertEqual(self.bc.database.list_of("payments.Currency"), [currency_data()])
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningBill"),
            [
                provisioning_bill_data(
                    {
                        "id": n + 1,
                        "academy_id": n + 1,
                        "vendor_id": None,
                        "hash": slug,
                        "total_amount": 0.0,
                        "status": "ERROR",
                    }
                )
                for n in range(20)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionKind"),
            [
                provisioning_activity_kind_data(
                    {
                        "id": n + 1,
                        "product_name": csv["Product"][n],
                        "sku": str(csv["SKU"][n]),
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningPrice"),
            [
                provisioning_activity_price_data(
                    {
                        "currency_id": 1,
                        "id": n + 1,
                        "multiplier": csv["Multiplier"][n],
                        "price_per_unit": csv["Price Per Unit ($)"][n] * 1.3,
                        "unit_type": csv["Unit Type"][n],
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionEvent"),
            [
                provisioning_activity_item_data(
                    {
                        "id": n + 1,
                        "price_id": n + 1,
                        "quantity": float(csv["Quantity"][n]),
                        "registered_at": datetime.strptime(csv["Date"][n], "%Y-%m-%d").replace(tzinfo=pytz.UTC),
                        "repository_url": f"https://github.com/{csv['Owner'][n]}/{csv['Repository Slug'][n]}",
                        "task_associated_slug": csv["Repository Slug"][n],
                        "csv_row": n,
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningUserConsumption"),
            [
                provisioning_activity_data(
                    {
                        "id": n + 1,
                        "kind_id": n + 1,
                        "hash": slug,
                        "username": csv["Username"][n],
                        "processed_at": UTC_NOW,
                        "status": "ERROR",
                        "status_text": ", ".join(
                            [
                                "Provisioning vendor Codespaces not found",
                                f"We could not find enough information about {csv['Username'][n]}, mark this user user "
                                "as deleted if you don't recognize it",
                            ]
                        ),
                    }
                )
                for n in range(10)
            ],
        )

        id = 0
        github_academy_users = self.bc.format.to_dict(model.github_academy_user)

        for n in range(10):
            github_academy_users.append(
                github_academy_user_data(
                    data={
                        "id": id + 1 + 20,
                        "user_id": (id / 2) + 1,
                        "academy_id": id + 1,
                        "storage_action": "IGNORE",
                        "storage_status": "PAYMENT_CONFLICT",
                        "username": csv["Username"][n],
                    }
                )
            )

            github_academy_users.append(
                github_academy_user_data(
                    data={
                        "id": id + 2 + 20,
                        "user_id": (id / 2) + 1,
                        "academy_id": id + 2,
                        "storage_action": "IGNORE",
                        "storage_status": "PAYMENT_CONFLICT",
                        "username": csv["Username"][n],
                    }
                )
            )

            id += 2

        self.assertEqual(self.bc.database.list_of("authenticate.GithubAcademyUser"), github_academy_users)

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f"Starting upload for hash {slug}")])
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])
        self.bc.check.calls(tasks.calculate_bill_amounts.delay.call_args_list, [])

    # Given: a csv with codespaces data and 10 User, 10 GithubAcademyUser, 10 GithubAcademyUserLog
    #     -> and 1 ProvisioningVendor of type codespaces
    # When: all the data is correct
    # Then: the task should create 1 bills and 10 activities
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
    @patch("breathecode.provisioning.tasks.upload.delay", MagicMock(wraps=upload.delay))
    @patch("breathecode.provisioning.tasks.calculate_bill_amounts.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    def test_from_github_credentials__generate_anything(self):
        csv = codespaces_csv(10)

        github_academy_users = [
            {
                "username": x,
            }
            for x in csv["Username"]
        ]
        github_academy_user_logs = [
            {
                "storage_status": "SYNCHED",
                "storage_action": "ADD",
                "academy_user_id": n + 1,
            }
            for n in range(10)
        ]
        provisioning_vendor = {"name": "Codespaces"}
        model = self.bc.database.create(
            user=10,
            github_academy_user=github_academy_users,
            github_academy_user_log=github_academy_user_logs,
            provisioning_vendor=provisioning_vendor,
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        slug = self.bc.fake.slug()
        with patch("breathecode.services.google_cloud.File.download", MagicMock(side_effect=csv_file_mock(csv))):

            upload(slug)

        self.assertEqual(self.bc.database.list_of("payments.Currency"), [currency_data()])
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningBill"),
            [
                provisioning_bill_data(
                    {
                        "hash": slug,
                        "vendor_id": 1,
                    }
                ),
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionKind"),
            [
                provisioning_activity_kind_data(
                    {
                        "id": n + 1,
                        "product_name": csv["Product"][n],
                        "sku": str(csv["SKU"][n]),
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningPrice"),
            [
                provisioning_activity_price_data(
                    {
                        "currency_id": 1,
                        "id": n + 1,
                        "multiplier": csv["Multiplier"][n],
                        "price_per_unit": csv["Price Per Unit ($)"][n] * 1.3,
                        "unit_type": csv["Unit Type"][n],
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionEvent"),
            [
                provisioning_activity_item_data(
                    {
                        "id": n + 1,
                        "price_id": n + 1,
                        "vendor_id": 1,
                        "quantity": float(csv["Quantity"][n]),
                        "registered_at": datetime.strptime(csv["Date"][n], "%Y-%m-%d").replace(tzinfo=pytz.UTC),
                        "repository_url": f"https://github.com/{csv['Owner'][n]}/{csv['Repository Slug'][n]}",
                        "task_associated_slug": csv["Repository Slug"][n],
                        "csv_row": n,
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningUserConsumption"),
            [
                provisioning_activity_data(
                    {
                        "id": n + 1,
                        "kind_id": n + 1,
                        "hash": slug,
                        "username": csv["Username"][n],
                        "processed_at": UTC_NOW,
                        "status": "PERSISTED",
                    }
                )
                for n in range(10)
            ],
        )

        self.assertEqual(
            self.bc.database.list_of("authenticate.GithubAcademyUser"),
            self.bc.format.to_dict(model.github_academy_user),
        )

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f"Starting upload for hash {slug}")])
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])
        self.bc.check.calls(tasks.calculate_bill_amounts.delay.call_args_list, [call(slug)])

    # Given: a csv with codespaces data and 10 User, 10 GithubAcademyUser, 10 GithubAcademyUserLog,
    #     -> and 1 ProvisioningVendor of type codespaces
    # When: all the data is correct, and the amount of rows is greater than the limit
    # Then: the task should create 1 bills and 10 activities
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
    @patch("breathecode.provisioning.tasks.upload.delay", MagicMock(wraps=upload.delay))
    @patch("breathecode.provisioning.tasks.calculate_bill_amounts.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    @patch("breathecode.provisioning.tasks.PANDAS_ROWS_LIMIT", PropertyMock(return_value=3))
    def test_pagination(self):
        csv = codespaces_csv(10)

        limit = tasks.PANDAS_ROWS_LIMIT
        tasks.PANDAS_ROWS_LIMIT = 3

        github_academy_users = [
            {
                "username": x,
            }
            for x in csv["Username"]
        ]
        github_academy_user_logs = [
            {
                "storage_status": "SYNCHED",
                "storage_action": "ADD",
                "academy_user_id": n + 1,
            }
            for n in range(10)
        ]
        provisioning_vendor = {"name": "Codespaces"}
        model = self.bc.database.create(
            user=10,
            github_academy_user=github_academy_users,
            github_academy_user_log=github_academy_user_logs,
            provisioning_vendor=provisioning_vendor,
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        task_manager_id = get_last_task_manager_id(self.bc) + 1

        slug = self.bc.fake.slug()
        with patch("breathecode.services.google_cloud.File.download", MagicMock(side_effect=csv_file_mock(csv))):

            upload(slug)

        self.assertEqual(self.bc.database.list_of("payments.Currency"), [currency_data()])
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningBill"),
            [
                provisioning_bill_data(
                    {
                        "hash": slug,
                        "vendor_id": 1,
                    }
                ),
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionKind"),
            [
                provisioning_activity_kind_data(
                    {
                        "id": n + 1,
                        "product_name": csv["Product"][n],
                        "sku": str(csv["SKU"][n]),
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningPrice"),
            [
                provisioning_activity_price_data(
                    {
                        "currency_id": 1,
                        "id": n + 1,
                        "multiplier": csv["Multiplier"][n],
                        "price_per_unit": csv["Price Per Unit ($)"][n] * 1.3,
                        "unit_type": csv["Unit Type"][n],
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionEvent"),
            [
                provisioning_activity_item_data(
                    {
                        "id": n + 1,
                        "price_id": n + 1,
                        "vendor_id": 1,
                        "quantity": float(csv["Quantity"][n]),
                        "registered_at": datetime.strptime(csv["Date"][n], "%Y-%m-%d").replace(tzinfo=pytz.UTC),
                        "repository_url": f"https://github.com/{csv['Owner'][n]}/{csv['Repository Slug'][n]}",
                        "task_associated_slug": csv["Repository Slug"][n],
                        "csv_row": n,
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningUserConsumption"),
            [
                provisioning_activity_data(
                    {
                        "id": n + 1,
                        "kind_id": n + 1,
                        "hash": slug,
                        "username": csv["Username"][n],
                        "processed_at": UTC_NOW,
                        "status": "PERSISTED",
                    }
                )
                for n in range(10)
            ],
        )

        self.assertEqual(
            self.bc.database.list_of("authenticate.GithubAcademyUser"),
            self.bc.format.to_dict(model.github_academy_user),
        )

        self.bc.check.calls(
            logging.Logger.info.call_args_list, [call(f"Starting upload for hash {slug}") for _ in range(4)]
        )
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

        self.bc.check.calls(
            tasks.upload.delay.call_args_list,
            [
                call(slug, page=1, task_manager_id=task_manager_id),
                call(slug, page=2, task_manager_id=task_manager_id),
                call(slug, page=3, task_manager_id=task_manager_id),
            ],
        )

        self.bc.check.calls(tasks.calculate_bill_amounts.delay.call_args_list, [call(slug)])

        tasks.PANDAS_ROWS_LIMIT = limit

    # Given: a csv with codespaces data and 10 User, 10 GithubAcademyUser, 10 GithubAcademyUserLog
    #     -> and 1 ProvisioningVendor of type codespaces
    # When: all the data is correct, force = True
    # Then: the task should create 1 bills and 10 activities
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
    @patch("breathecode.provisioning.tasks.upload.delay", MagicMock(wraps=upload.delay))
    @patch("breathecode.provisioning.tasks.calculate_bill_amounts.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    def test_from_github_credentials__generate_anything__force(self):
        csv = codespaces_csv(10)

        slug = self.bc.fake.slug()
        github_academy_users = [
            {
                "username": x,
            }
            for x in csv["Username"]
        ]
        github_academy_user_logs = [
            {
                "storage_status": "SYNCHED",
                "storage_action": "ADD",
                "academy_user_id": n + 1,
            }
            for n in range(10)
        ]
        provisioning_vendor = {"name": "Codespaces"}
        provisioning_bill = {"hash": slug}
        model = self.bc.database.create(
            user=10,
            github_academy_user=github_academy_users,
            github_academy_user_log=github_academy_user_logs,
            provisioning_vendor=provisioning_vendor,
            provisioning_bill=provisioning_bill,
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        with patch("breathecode.services.google_cloud.File.download", MagicMock(side_effect=csv_file_mock(csv))):

            upload(slug, force=True)

        self.assertEqual(self.bc.database.list_of("payments.Currency"), [currency_data()])
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningBill"),
            [
                provisioning_bill_data(
                    {
                        "id": 2,
                        "hash": slug,
                        "vendor_id": 1,
                    }
                ),
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionKind"),
            [
                provisioning_activity_kind_data(
                    {
                        "id": n + 1,
                        "product_name": csv["Product"][n],
                        "sku": str(csv["SKU"][n]),
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningPrice"),
            [
                provisioning_activity_price_data(
                    {
                        "currency_id": 1,
                        "id": n + 1,
                        "multiplier": csv["Multiplier"][n],
                        "price_per_unit": csv["Price Per Unit ($)"][n] * 1.3,
                        "unit_type": csv["Unit Type"][n],
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionEvent"),
            [
                provisioning_activity_item_data(
                    {
                        "id": n + 1,
                        "price_id": n + 1,
                        "vendor_id": 1,
                        "quantity": float(csv["Quantity"][n]),
                        "registered_at": datetime.strptime(csv["Date"][n], "%Y-%m-%d").replace(tzinfo=pytz.UTC),
                        "repository_url": f"https://github.com/{csv['Owner'][n]}/{csv['Repository Slug'][n]}",
                        "task_associated_slug": csv["Repository Slug"][n],
                        "csv_row": n,
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningUserConsumption"),
            [
                provisioning_activity_data(
                    {
                        "id": n + 1,
                        "kind_id": n + 1,
                        "hash": slug,
                        "username": csv["Username"][n],
                        "processed_at": UTC_NOW,
                        "status": "PERSISTED",
                    }
                )
                for n in range(10)
            ],
        )

        self.assertEqual(
            self.bc.database.list_of("authenticate.GithubAcademyUser"),
            self.bc.format.to_dict(model.github_academy_user),
        )

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f"Starting upload for hash {slug}")])
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])
        self.bc.check.calls(tasks.calculate_bill_amounts.delay.call_args_list, [call(slug)])

    # Given: a csv with codespaces data and 10 User, 10 GithubAcademyUser, 10 GithubAcademyUserLog
    #     -> and 1 ProvisioningVendor of type codespaces
    # When: all the data is correct, GithubAcademyUser with PAYMENT_CONFLICT and IGNORE
    # Then: the task should create 1 bills and 10 activities
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
    @patch("breathecode.provisioning.tasks.upload.delay", MagicMock(wraps=upload.delay))
    @patch("breathecode.provisioning.tasks.calculate_bill_amounts.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    def test_from_github_credentials__generate_anything__case1(self):
        csv = codespaces_csv(10)

        github_academy_users = [
            {
                "username": x,
                "storage_status": "PAYMENT_CONFLICT",
                "storage_action": "IGNORE",
            }
            for x in csv["Username"]
        ]

        github_academy_users += [
            {
                "storage_status": "SYNCHED",
                "storage_action": "ADD",
                "user_id": 11,
            }
            for n in range(10)
        ]

        provisioning_vendor = {"name": "Codespaces"}
        model = self.bc.database.create(
            user=11, github_academy_user=github_academy_users, provisioning_vendor=provisioning_vendor
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        slug = self.bc.fake.slug()
        with patch("breathecode.services.google_cloud.File.download", MagicMock(side_effect=csv_file_mock(csv))):

            upload(slug)

        self.assertEqual(self.bc.database.list_of("payments.Currency"), [currency_data()])
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningBill"),
            [
                provisioning_bill_data(
                    {
                        "hash": slug,
                        "vendor_id": 1,
                    }
                ),
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionKind"),
            [
                provisioning_activity_kind_data(
                    {
                        "id": n + 1,
                        "product_name": csv["Product"][n],
                        "sku": str(csv["SKU"][n]),
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningPrice"),
            [
                provisioning_activity_price_data(
                    {
                        "currency_id": 1,
                        "id": n + 1,
                        "multiplier": csv["Multiplier"][n],
                        "price_per_unit": csv["Price Per Unit ($)"][n] * 1.3,
                        "unit_type": csv["Unit Type"][n],
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionEvent"),
            [
                provisioning_activity_item_data(
                    {
                        "id": n + 1,
                        "price_id": n + 1,
                        "vendor_id": 1,
                        "quantity": float(csv["Quantity"][n]),
                        "registered_at": datetime.strptime(csv["Date"][n], "%Y-%m-%d").replace(tzinfo=pytz.UTC),
                        "repository_url": f"https://github.com/{csv['Owner'][n]}/{csv['Repository Slug'][n]}",
                        "task_associated_slug": csv["Repository Slug"][n],
                        "csv_row": n,
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningUserConsumption"),
            [
                provisioning_activity_data(
                    {
                        "id": n + 1,
                        "kind_id": n + 1,
                        "hash": slug,
                        "username": csv["Username"][n],
                        "processed_at": UTC_NOW,
                        "status": "WARNING",
                        "status_text": (
                            f"We could not find enough information about {csv['Username'][n]}, mark this user user "
                            "as deleted if you don't recognize it"
                        ),
                    }
                )
                for n in range(10)
            ],
        )

        self.assertEqual(
            self.bc.database.list_of("authenticate.GithubAcademyUser"),
            self.bc.format.to_dict(model.github_academy_user),
        )

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f"Starting upload for hash {slug}")])
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])
        self.bc.check.calls(tasks.calculate_bill_amounts.delay.call_args_list, [call(slug)])


class GitpodTestSuite(ProvisioningTestCase):

    # Given: a csv with codespaces data
    # When: users does not exist
    # Then: the task should not create any bill, create an activity with wrong status
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
    @patch("breathecode.provisioning.tasks.upload.delay", MagicMock(wraps=upload.delay))
    @patch("breathecode.provisioning.tasks.calculate_bill_amounts.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    def test_users_not_found(self):
        csv = gitpod_csv(10)

        slug = self.bc.fake.slug()
        with patch("requests.get", response_mock(content=[{"id": 1} for _ in range(10)])):
            with patch("breathecode.services.google_cloud.File.download", MagicMock(side_effect=csv_file_mock(csv))):

                upload(slug)

        self.assertEqual(self.bc.database.list_of("payments.Currency"), [currency_data()])
        self.assertEqual(self.bc.database.list_of("provisioning.ProvisioningBill"), [])
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionKind"),
            [
                provisioning_activity_kind_data(
                    {
                        "id": n + 1,
                        "product_name": csv["kind"][n],
                        "sku": str(csv["kind"][n]),
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningPrice"),
            [
                provisioning_activity_price_data(
                    {
                        "currency_id": 1,
                        "id": 1,
                        "multiplier": 1.0,
                        "price_per_unit": 0.036 * 1.3,
                        "unit_type": "Credits",
                    }
                )
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionEvent"),
            [
                provisioning_activity_item_data(
                    {
                        "id": n + 1,
                        "price_id": 1,
                        "quantity": float(csv["credits"][n]),
                        "external_pk": str(csv["id"][n]),
                        "registered_at": self.bc.datetime.from_iso_string(csv["startTime"][n]),
                        "repository_url": csv["contextURL"][n],
                        "task_associated_slug": repo_name(csv["contextURL"][n]),
                        "csv_row": n,
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningUserConsumption"),
            [
                provisioning_activity_data(
                    {
                        "id": n + 1,
                        "kind_id": n + 1,
                        "hash": slug,
                        "username": csv["userName"][n],
                        "processed_at": UTC_NOW,
                        "status": "ERROR",
                        "status_text": ", ".join(
                            [
                                "Provisioning vendor Gitpod not found",
                                f"We could not find enough information about {csv['userName'][n]}, mark this user user "
                                "as deleted if you don't recognize it",
                            ]
                        ),
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(self.bc.database.list_of("authenticate.GithubAcademyUser"), [])

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f"Starting upload for hash {slug}")])
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])
        self.bc.check.calls(tasks.calculate_bill_amounts.delay.call_args_list, [])

    # Given: a csv with codespaces data and 10 User, 10 GithubAcademyUser and 10 GithubAcademyUserLog
    # When: vendor not found
    # Then: the task should not create any bill or activity
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
    @patch("breathecode.provisioning.tasks.upload.delay", MagicMock(wraps=upload.delay))
    @patch("breathecode.provisioning.tasks.calculate_bill_amounts.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    def test_from_github_credentials__vendor_not_found(self):
        csv = gitpod_csv(10)

        github_academy_users = [
            {
                "username": username,
            }
            for username in csv["userName"]
        ]
        github_academy_user_logs = [
            {
                "storage_status": "SYNCHED",
                "storage_action": "ADD",
                "academy_user_id": n + 1,
            }
            for n in range(10)
        ]
        model = self.bc.database.create(
            user=10, github_academy_user=github_academy_users, github_academy_user_log=github_academy_user_logs
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        slug = self.bc.fake.slug()
        with patch("breathecode.services.google_cloud.File.download", MagicMock(side_effect=csv_file_mock(csv))):

            upload(slug)

        self.assertEqual(self.bc.database.list_of("payments.Currency"), [currency_data()])
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningBill"),
            [
                provisioning_bill_data(
                    {
                        "hash": slug,
                        "status": "ERROR",
                    }
                ),
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionKind"),
            [
                provisioning_activity_kind_data(
                    {
                        "id": n + 1,
                        "product_name": csv["kind"][n],
                        "sku": str(csv["kind"][n]),
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningPrice"),
            [
                provisioning_activity_price_data(
                    {
                        "currency_id": 1,
                        "id": 1,
                        "multiplier": 1.0,
                        "price_per_unit": 0.036 * 1.3,
                        "unit_type": "Credits",
                    }
                )
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionEvent"),
            [
                provisioning_activity_item_data(
                    {
                        "id": n + 1,
                        "price_id": 1,
                        "vendor_id": None,
                        "quantity": float(csv["credits"][n]),
                        "external_pk": str(csv["id"][n]),
                        "registered_at": self.bc.datetime.from_iso_string(csv["startTime"][n]),
                        "repository_url": csv["contextURL"][n],
                        "task_associated_slug": repo_name(csv["contextURL"][n]),
                        "csv_row": n,
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningUserConsumption"),
            [
                provisioning_activity_data(
                    {
                        "id": n + 1,
                        "kind_id": n + 1,
                        "hash": slug,
                        "username": csv["userName"][n],
                        "processed_at": UTC_NOW,
                        "status": "ERROR",
                        "status_text": ", ".join(["Provisioning vendor Gitpod not found"]),
                    }
                )
                for n in range(10)
            ],
        )

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f"Starting upload for hash {slug}")])
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])
        self.bc.check.calls(tasks.calculate_bill_amounts.delay.call_args_list, [])

    # Given: a csv with codespaces data and 10 User, 10 GithubAcademyUser, 10 GithubAcademyUserLog
    #     -> and 1 ProvisioningVendor of type codespaces
    # When: all the data is correct
    # Then: the task should create 1 bills and 10 activities
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
    @patch("breathecode.provisioning.tasks.upload.delay", MagicMock(wraps=upload.delay))
    @patch("breathecode.provisioning.tasks.calculate_bill_amounts.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    def test_from_github_credentials__generate_anything(self):
        csv = gitpod_csv(10)

        github_academy_users = [
            {
                "username": username,
            }
            for username in csv["userName"]
        ]
        github_academy_user_logs = [
            {
                "storage_status": "SYNCHED",
                "storage_action": "ADD",
                "academy_user_id": n + 1,
            }
            for n in range(10)
        ]
        provisioning_vendor = {"name": "Gitpod"}
        model = self.bc.database.create(
            user=10,
            github_academy_user=github_academy_users,
            github_academy_user_log=github_academy_user_logs,
            provisioning_vendor=provisioning_vendor,
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        slug = self.bc.fake.slug()
        with patch("breathecode.services.google_cloud.File.download", MagicMock(side_effect=csv_file_mock(csv))):

            upload(slug)

        self.assertEqual(self.bc.database.list_of("payments.Currency"), [currency_data()])
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningBill"),
            [
                provisioning_bill_data(
                    {
                        "hash": slug,
                        "vendor_id": 1,
                    }
                ),
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionKind"),
            [
                provisioning_activity_kind_data(
                    {
                        "id": n + 1,
                        "product_name": csv["kind"][n],
                        "sku": str(csv["kind"][n]),
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningPrice"),
            [
                provisioning_activity_price_data(
                    {
                        "currency_id": 1,
                        "id": 1,
                        "multiplier": 1.0,
                        "price_per_unit": 0.036 * 1.3,
                        "unit_type": "Credits",
                    }
                )
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionEvent"),
            [
                provisioning_activity_item_data(
                    {
                        "id": n + 1,
                        "price_id": 1,
                        "vendor_id": 1,
                        "quantity": float(csv["credits"][n]),
                        "external_pk": str(csv["id"][n]),
                        "registered_at": self.bc.datetime.from_iso_string(csv["startTime"][n]),
                        "repository_url": csv["contextURL"][n],
                        "task_associated_slug": repo_name(csv["contextURL"][n]),
                        "csv_row": n,
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningUserConsumption"),
            [
                provisioning_activity_data(
                    {
                        "id": n + 1,
                        "kind_id": n + 1,
                        "hash": slug,
                        "username": csv["userName"][n],
                        "processed_at": UTC_NOW,
                        "status": "PERSISTED",
                    }
                )
                for n in range(10)
            ],
        )

        self.assertEqual(
            self.bc.database.list_of("authenticate.GithubAcademyUser"),
            self.bc.format.to_dict(model.github_academy_user),
        )

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f"Starting upload for hash {slug}")])
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])
        self.bc.check.calls(tasks.calculate_bill_amounts.delay.call_args_list, [call(slug)])

    # Given: a csv with codespaces data and 10 User, 10 GithubAcademyUser, 10 GithubAcademyUserLog
    #     -> and 1 ProvisioningVendor of type codespaces
    # When: all the data is correct, and the amount of rows is greater than the limit
    # Then: the task should create 1 bills and 10 activities
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
    @patch("breathecode.provisioning.tasks.upload.delay", MagicMock(wraps=upload.delay))
    @patch("breathecode.provisioning.tasks.calculate_bill_amounts.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    @patch("breathecode.provisioning.tasks.PANDAS_ROWS_LIMIT", PropertyMock(return_value=3))
    def test_pagination(self):
        csv = gitpod_csv(10)

        limit = tasks.PANDAS_ROWS_LIMIT
        tasks.PANDAS_ROWS_LIMIT = 3

        provisioning_vendor = {"name": "Gitpod"}
        github_academy_users = [
            {
                "username": username,
            }
            for username in csv["userName"]
        ]
        github_academy_user_logs = [
            {
                "storage_status": "SYNCHED",
                "storage_action": "ADD",
                "academy_user_id": n + 1,
            }
            for n in range(10)
        ]
        model = self.bc.database.create(
            user=10,
            github_academy_user=github_academy_users,
            github_academy_user_log=github_academy_user_logs,
            provisioning_vendor=provisioning_vendor,
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        task_manager_id = get_last_task_manager_id(self.bc) + 1

        slug = self.bc.fake.slug()
        with patch("breathecode.services.google_cloud.File.download", MagicMock(side_effect=csv_file_mock(csv))):

            upload(slug)

        self.assertEqual(self.bc.database.list_of("payments.Currency"), [currency_data()])
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningBill"),
            [
                provisioning_bill_data(
                    {
                        "hash": slug,
                        "vendor_id": 1,
                    }
                ),
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionKind"),
            [
                provisioning_activity_kind_data(
                    {
                        "id": n + 1,
                        "product_name": csv["kind"][n],
                        "sku": str(csv["kind"][n]),
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningPrice"),
            [
                provisioning_activity_price_data(
                    {
                        "currency_id": 1,
                        "id": 1,
                        "multiplier": 1.0,
                        "price_per_unit": 0.036 * 1.3,
                        "unit_type": "Credits",
                    }
                )
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionEvent"),
            [
                provisioning_activity_item_data(
                    {
                        "id": n + 1,
                        "price_id": 1,
                        "vendor_id": 1,
                        "quantity": float(csv["credits"][n]),
                        "external_pk": str(csv["id"][n]),
                        "registered_at": self.bc.datetime.from_iso_string(csv["startTime"][n]),
                        "repository_url": csv["contextURL"][n],
                        "task_associated_slug": repo_name(csv["contextURL"][n]),
                        "csv_row": n,
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningUserConsumption"),
            [
                provisioning_activity_data(
                    {
                        "id": n + 1,
                        "kind_id": n + 1,
                        "hash": slug,
                        "username": csv["userName"][n],
                        "processed_at": UTC_NOW,
                        "status": "PERSISTED",
                    }
                )
                for n in range(10)
            ],
        )

        self.assertEqual(
            self.bc.database.list_of("authenticate.GithubAcademyUser"),
            self.bc.format.to_dict(model.github_academy_user),
        )

        self.bc.check.calls(
            logging.Logger.info.call_args_list, [call(f"Starting upload for hash {slug}") for _ in range(4)]
        )
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

        self.bc.check.calls(
            tasks.upload.delay.call_args_list,
            [
                call(slug, page=1, task_manager_id=task_manager_id),
                call(slug, page=2, task_manager_id=task_manager_id),
                call(slug, page=3, task_manager_id=task_manager_id),
            ],
        )

        self.bc.check.calls(tasks.calculate_bill_amounts.delay.call_args_list, [call(slug)])

        tasks.PANDAS_ROWS_LIMIT = limit

    # Given: a csv with codespaces data and 10 User, 10 GithubAcademyUser, 10 GithubAcademyUserLog
    #     -> and 1 ProvisioningVendor of type codespaces
    # When: all the data is correct, without ProfileAcademy
    # Then: the task should create 1 bills and 10 activities per academy
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
    @patch("breathecode.provisioning.tasks.upload.delay", MagicMock(wraps=upload.delay))
    @patch("breathecode.provisioning.tasks.calculate_bill_amounts.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    def test_from_github_credentials__generate_anything__case1(self):
        csv = gitpod_csv(10)

        github_academy_users = [
            {
                "username": username,
            }
            for username in csv["userName"]
        ]
        github_academy_user_logs = [
            {
                "storage_status": "SYNCHED",
                "storage_action": "ADD",
                "academy_user_id": n + 1,
            }
            for n in range(10)
        ]
        provisioning_vendor = {"name": "Gitpod"}

        model = self.bc.database.create(
            user=10,
            academy=3,
            github_academy_user=github_academy_users,
            github_academy_user_log=github_academy_user_logs,
            provisioning_vendor=provisioning_vendor,
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        slug = self.bc.fake.slug()
        with patch("breathecode.services.google_cloud.File.download", MagicMock(side_effect=csv_file_mock(csv))):

            upload(slug)

        self.assertEqual(self.bc.database.list_of("payments.Currency"), [currency_data()])
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningBill"),
            [
                provisioning_bill_data(
                    {
                        "id": 1,
                        "academy_id": 1,
                        "vendor_id": 1,
                        "hash": slug,
                    }
                ),
                provisioning_bill_data(
                    {
                        "id": 2,
                        "academy_id": 2,
                        "vendor_id": 1,
                        "hash": slug,
                    }
                ),
                provisioning_bill_data(
                    {
                        "id": 3,
                        "academy_id": 3,
                        "vendor_id": 1,
                        "hash": slug,
                    }
                ),
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionKind"),
            [
                provisioning_activity_kind_data(
                    {
                        "id": n + 1,
                        "product_name": csv["kind"][n],
                        "sku": str(csv["kind"][n]),
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningPrice"),
            [
                provisioning_activity_price_data(
                    {
                        "currency_id": 1,
                        "id": 1,
                        "multiplier": 1.0,
                        "price_per_unit": 0.036 * 1.3,
                        "unit_type": "Credits",
                    }
                )
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionEvent"),
            [
                provisioning_activity_item_data(
                    {
                        "id": n + 1,
                        "price_id": 1,
                        "vendor_id": 1,
                        "quantity": float(csv["credits"][n]),
                        "external_pk": str(csv["id"][n]),
                        "registered_at": self.bc.datetime.from_iso_string(csv["startTime"][n]),
                        "repository_url": csv["contextURL"][n],
                        "task_associated_slug": repo_name(csv["contextURL"][n]),
                        "csv_row": n,
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningUserConsumption"),
            [
                provisioning_activity_data(
                    {
                        "id": n + 1,
                        "kind_id": n + 1,
                        "hash": slug,
                        "username": csv["userName"][n],
                        "processed_at": UTC_NOW,
                        "status": "PERSISTED",
                    }
                )
                for n in range(10)
            ],
        )

        self.assertEqual(
            self.bc.database.list_of("authenticate.GithubAcademyUser"),
            self.bc.format.to_dict(model.github_academy_user),
        )

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f"Starting upload for hash {slug}")])
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])
        self.bc.check.calls(tasks.calculate_bill_amounts.delay.call_args_list, [call(slug)])

    # Given: a csv with codespaces data and 10 User, 10 GithubAcademyUser, 10 GithubAcademyUserLog
    #     -> and 1 ProvisioningVendor of type codespaces
    # When: all the data is correct, with ProfileAcademy
    # Then: the task should create 1 bills and 10 activities per user's ProfileAcademy
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
    @patch("breathecode.provisioning.tasks.upload.delay", MagicMock(wraps=upload.delay))
    @patch("breathecode.provisioning.tasks.calculate_bill_amounts.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    @patch("breathecode.authenticate.signals.academy_invite_accepted.send_robust", MagicMock())
    def test_from_github_credentials__generate_anything__case2(self):
        csv = gitpod_csv(10)

        github_academy_users = [
            {
                "username": username,
            }
            for username in csv["userName"]
        ]
        github_academy_user_logs = [
            {
                "storage_status": "SYNCHED",
                "storage_action": "ADD",
                "academy_user_id": n + 1,
            }
            for n in range(10)
        ]
        provisioning_vendor = {"name": "Gitpod"}
        profile_academies = []

        for user_n in range(10):
            for academy_n in range(3):
                profile_academies.append(
                    {
                        "academy_id": academy_n + 1,
                        "user_id": user_n + 1,
                        "status": "ACTIVE",
                    }
                )

        credentials_github = [
            {
                "username": csv["userName"][n],
                "user_id": n + 1,
            }
            for n in range(10)
        ]

        model = self.bc.database.create(
            user=10,
            credentials_github=credentials_github,
            academy=3,
            profile_academy=profile_academies,
            github_academy_user=github_academy_users,
            github_academy_user_log=github_academy_user_logs,
            provisioning_vendor=provisioning_vendor,
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        slug = self.bc.fake.slug()

        with patch("breathecode.services.google_cloud.File.download", MagicMock(side_effect=csv_file_mock(csv))):

            upload(slug)

        self.assertEqual(self.bc.database.list_of("payments.Currency"), [currency_data()])
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningBill"),
            [
                provisioning_bill_data(
                    {
                        "id": 1,
                        "academy_id": 1,
                        "hash": slug,
                        "vendor_id": 1,
                    }
                ),
                provisioning_bill_data(
                    {
                        "id": 2,
                        "academy_id": 2,
                        "hash": slug,
                        "vendor_id": 1,
                    }
                ),
                provisioning_bill_data(
                    {
                        "id": 3,
                        "academy_id": 3,
                        "hash": slug,
                        "vendor_id": 1,
                    }
                ),
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionKind"),
            [
                provisioning_activity_kind_data(
                    {
                        "id": n + 1,
                        "product_name": csv["kind"][n],
                        "sku": str(csv["kind"][n]),
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningPrice"),
            [
                provisioning_activity_price_data(
                    {
                        "currency_id": 1,
                        "id": 1,
                        "multiplier": 1.0,
                        "price_per_unit": 0.036 * 1.3,
                        "unit_type": "Credits",
                    }
                )
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionEvent"),
            [
                provisioning_activity_item_data(
                    {
                        "id": n + 1,
                        "price_id": 1,
                        "vendor_id": 1,
                        "quantity": float(csv["credits"][n]),
                        "external_pk": str(csv["id"][n]),
                        "registered_at": self.bc.datetime.from_iso_string(csv["startTime"][n]),
                        "repository_url": csv["contextURL"][n],
                        "task_associated_slug": repo_name(csv["contextURL"][n]),
                        "csv_row": n,
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningUserConsumption"),
            [
                provisioning_activity_data(
                    {
                        "id": n + 1,
                        "kind_id": n + 1,
                        "hash": slug,
                        "username": csv["userName"][n],
                        "processed_at": UTC_NOW,
                        "status": "PERSISTED",
                    }
                )
                for n in range(10)
            ],
        )

        self.assertEqual(
            self.bc.database.list_of("authenticate.GithubAcademyUser"),
            self.bc.format.to_dict(model.github_academy_user),
        )

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f"Starting upload for hash {slug}")])
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])
        self.bc.check.calls(tasks.calculate_bill_amounts.delay.call_args_list, [call(slug)])

    # Given: a csv with codespaces data and 10 User, 10 GithubAcademyUser, 10 GithubAcademyUserLog
    #     -> and 1 ProvisioningVendor of type codespaces
    # When: all the data is correct, with ProfileAcademy
    # Then: the task should create 1 bills and 10 activities per user's ProfileAcademy
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
    @patch("breathecode.provisioning.tasks.upload.delay", MagicMock(wraps=upload.delay))
    @patch("breathecode.provisioning.tasks.calculate_bill_amounts.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    @patch("breathecode.authenticate.signals.academy_invite_accepted.send_robust", MagicMock())
    def test_from_github_credentials__generate_anything__case3(self):
        csv = gitpod_csv(10)

        github_academy_users = [
            {
                "username": username,
            }
            for username in csv["userName"]
        ]
        github_academy_user_logs = [
            {
                "storage_status": "SYNCHED",
                "storage_action": "ADD",
                "academy_user_id": n + 1,
            }
            for n in range(10)
        ]
        provisioning_vendor = {"name": "Gitpod"}
        profile_academies = []

        for user_n in range(10):
            for academy_n in range(3):
                profile_academies.append(
                    {
                        "academy_id": academy_n + 1,
                        "user_id": user_n + 1,
                        "status": "ACTIVE",
                    }
                )

        credentials_github = [
            {
                "username": csv["userName"][n],
                "user_id": n + 1,
            }
            for n in range(10)
        ]

        cohort_users = [
            {
                "user_id": n + 1,
                "cohort_id": 1,
            }
            for n in range(10)
        ]

        cohort = {
            "academy_id": 1,
            "kickoff_date": timezone.now() + timedelta(days=1),
            "ending_date": timezone.now() - timedelta(days=1),
        }

        model = self.bc.database.create(
            user=10,
            credentials_github=credentials_github,
            academy=3,
            cohort=cohort,
            cohort_user=cohort_users,
            profile_academy=profile_academies,
            github_academy_user=github_academy_users,
            github_academy_user_log=github_academy_user_logs,
            provisioning_vendor=provisioning_vendor,
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        slug = self.bc.fake.slug()

        y = [[model.academy[RANDOM_ACADEMIES[x]]] for x in range(10)]

        with patch("random.choices", MagicMock(side_effect=y)):
            with patch("breathecode.services.google_cloud.File.download", MagicMock(side_effect=csv_file_mock(csv))):

                upload(slug)

        academies = []

        for n in RANDOM_ACADEMIES:
            if n not in academies:
                academies.append(n)

        academies = list(academies)

        self.assertEqual(self.bc.database.list_of("payments.Currency"), [currency_data()])
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningBill"),
            [
                provisioning_bill_data(
                    {
                        "id": 1,
                        "academy_id": 1,
                        "hash": slug,
                        "vendor_id": 1,
                    }
                ),
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionKind"),
            [
                provisioning_activity_kind_data(
                    {
                        "id": n + 1,
                        "product_name": csv["kind"][n],
                        "sku": str(csv["kind"][n]),
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningPrice"),
            [
                provisioning_activity_price_data(
                    {
                        "currency_id": 1,
                        "id": 1,
                        "multiplier": 1.0,
                        "price_per_unit": 0.036 * 1.3,
                        "unit_type": "Credits",
                    }
                )
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionEvent"),
            [
                provisioning_activity_item_data(
                    {
                        "id": n + 1,
                        "price_id": 1,
                        "vendor_id": 1,
                        "quantity": float(csv["credits"][n]),
                        "external_pk": str(csv["id"][n]),
                        "registered_at": self.bc.datetime.from_iso_string(csv["startTime"][n]),
                        "repository_url": csv["contextURL"][n],
                        "task_associated_slug": repo_name(csv["contextURL"][n]),
                        "csv_row": n,
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningUserConsumption"),
            [
                provisioning_activity_data(
                    {
                        "id": n + 1,
                        "kind_id": n + 1,
                        "hash": slug,
                        "username": csv["userName"][n],
                        "processed_at": UTC_NOW,
                        "status": "PERSISTED",
                    }
                )
                for n in range(10)
            ],
        )

        self.assertEqual(
            self.bc.database.list_of("authenticate.GithubAcademyUser"),
            self.bc.format.to_dict(model.github_academy_user),
        )

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f"Starting upload for hash {slug}")])
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])
        self.bc.check.calls(tasks.calculate_bill_amounts.delay.call_args_list, [call(slug)])


class RigobotTestSuite(ProvisioningTestCase):

    # Given: a csv with codespaces data
    # When: users does not exist
    # Then: the task should not create any bill, create an activity with wrong status
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
    @patch("breathecode.provisioning.tasks.upload.delay", MagicMock(wraps=upload.delay))
    @patch("breathecode.provisioning.tasks.calculate_bill_amounts.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    def test_users_not_found(self):
        csv = rigobot_csv(10)

        self.bc.database.create(app={"slug": "rigobot"}, first_party_credentials={"app": {"rigobot": 10}})
        logging.Logger.info.call_args_list = []

        slug = self.bc.fake.slug()
        with patch("requests.get", response_mock(content=[{"id": 1} for _ in range(10)])):
            with patch("breathecode.services.google_cloud.File.download", MagicMock(side_effect=csv_file_mock(csv))):

                upload(slug)

        self.assertEqual(self.bc.database.list_of("payments.Currency"), [currency_data()])
        self.assertEqual(self.bc.database.list_of("provisioning.ProvisioningBill"), [])
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionKind"),
            [
                provisioning_activity_kind_data(
                    {
                        "id": n + 1,
                        "product_name": f'{csv["purpose"][n]} (type: {csv["pricing_type"][n]}, model: {csv["model"][n]})',
                        "sku": f'{csv["purpose_slug"][n]}--{csv["pricing_type"][n].lower()}--{csv["model"][n].lower()}',
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningPrice"),
            [
                provisioning_activity_price_data(
                    {
                        "currency_id": 1,
                        "id": 1,
                        "multiplier": 1.3,
                        "price_per_unit": 0.04 if csv["pricing_type"][0] == "OUTPUT" else 0.02,
                        "unit_type": "Tokens",
                    }
                ),
                provisioning_activity_price_data(
                    {
                        "currency_id": 1,
                        "id": 2,
                        "multiplier": 1.3,
                        "price_per_unit": 0.04 if csv["pricing_type"][0] != "OUTPUT" else 0.02,
                        "unit_type": "Tokens",
                    }
                ),
            ],
        )
        output_was_first = csv["pricing_type"][0] == "OUTPUT"
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionEvent"),
            [
                provisioning_activity_item_data(
                    {
                        "id": n + 1,
                        "price_id": (
                            (1 if output_was_first else 2)
                            if csv["pricing_type"][n] == "OUTPUT"
                            else (2 if output_was_first else 1)
                        ),
                        "quantity": float(csv["total_tokens"][n]),
                        "external_pk": str(csv["consumption_item_id"][n]),
                        "registered_at": self.bc.datetime.from_iso_string(csv["consumption_period_start"][n]),
                        "csv_row": n,
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningUserConsumption"),
            [
                provisioning_activity_data(
                    {
                        "id": n + 1,
                        "kind_id": n + 1,
                        "hash": slug,
                        "username": csv["github_username"][n],
                        "processed_at": UTC_NOW,
                        "status": "ERROR",
                        "status_text": ", ".join(
                            [
                                "Provisioning vendor Rigobot not found",
                                f"We could not find enough information about {csv['github_username'][n]}, mark this user user "
                                "as deleted if you don't recognize it",
                            ]
                        ),
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(self.bc.database.list_of("authenticate.GithubAcademyUser"), [])

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f"Starting upload for hash {slug}")])
        self.bc.check.calls(
            logging.Logger.error.call_args_list,
            [call("Organization not provided, in this case, all organizations will be used") for _ in range(10)],
        )

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])
        self.bc.check.calls(tasks.calculate_bill_amounts.delay.call_args_list, [])

    # Given: a csv with codespaces data and 10 User, 10 GithubAcademyUser and 10 GithubAcademyUserLog
    # When: vendor not found
    # Then: the task should not create any bill or activity
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
    @patch("breathecode.provisioning.tasks.upload.delay", MagicMock(wraps=upload.delay))
    @patch("breathecode.provisioning.tasks.calculate_bill_amounts.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    def test_from_github_credentials__vendor_not_found(self):
        csv = rigobot_csv(10)

        github_academy_users = [
            {
                "username": username,
            }
            for username in csv["github_username"]
        ]
        github_academy_user_logs = [
            {
                "storage_status": "SYNCHED",
                "storage_action": "ADD",
                "academy_user_id": n + 1,
            }
            for n in range(10)
        ]
        model = self.bc.database.create(
            user=10,
            app={"slug": "rigobot"},
            first_party_credentials={"app": {"rigobot": 10}},
            github_academy_user=github_academy_users,
            github_academy_user_log=github_academy_user_logs,
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        slug = self.bc.fake.slug()
        with patch("breathecode.services.google_cloud.File.download", MagicMock(side_effect=csv_file_mock(csv))):

            upload(slug)

        self.assertEqual(self.bc.database.list_of("payments.Currency"), [currency_data()])
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningBill"),
            [
                provisioning_bill_data(
                    {
                        "hash": slug,
                        "status": "ERROR",
                    }
                ),
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionKind"),
            [
                provisioning_activity_kind_data(
                    {
                        "id": n + 1,
                        "product_name": f'{csv["purpose"][n]} (type: {csv["pricing_type"][n]}, model: {csv["model"][n]})',
                        "sku": f'{csv["purpose_slug"][n]}--{csv["pricing_type"][n].lower()}--{csv["model"][n].lower()}',
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningPrice"),
            [
                provisioning_activity_price_data(
                    {
                        "currency_id": 1,
                        "id": 1,
                        "multiplier": 1.3,
                        "price_per_unit": 0.04 if csv["pricing_type"][0] == "OUTPUT" else 0.02,
                        "unit_type": "Tokens",
                    }
                ),
                provisioning_activity_price_data(
                    {
                        "currency_id": 1,
                        "id": 2,
                        "multiplier": 1.3,
                        "price_per_unit": 0.04 if csv["pricing_type"][0] != "OUTPUT" else 0.02,
                        "unit_type": "Tokens",
                    }
                ),
            ],
        )
        output_was_first = csv["pricing_type"][0] == "OUTPUT"
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionEvent"),
            [
                provisioning_activity_item_data(
                    {
                        "id": n + 1,
                        "price_id": (
                            (1 if output_was_first else 2)
                            if csv["pricing_type"][n] == "OUTPUT"
                            else (2 if output_was_first else 1)
                        ),
                        "quantity": float(csv["total_tokens"][n]),
                        "external_pk": str(csv["consumption_item_id"][n]),
                        "registered_at": self.bc.datetime.from_iso_string(csv["consumption_period_start"][n]),
                        "csv_row": n,
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningUserConsumption"),
            [
                provisioning_activity_data(
                    {
                        "id": n + 1,
                        "kind_id": n + 1,
                        "hash": slug,
                        "username": csv["github_username"][n],
                        "processed_at": UTC_NOW,
                        "status": "ERROR",
                        "status_text": ", ".join(["Provisioning vendor Rigobot not found"]),
                    }
                )
                for n in range(10)
            ],
        )

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f"Starting upload for hash {slug}")])
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])
        self.bc.check.calls(tasks.calculate_bill_amounts.delay.call_args_list, [])

    # Given: a csv with codespaces data and 10 User, 10 GithubAcademyUser, 10 GithubAcademyUserLog
    #     -> and 1 ProvisioningVendor of type codespaces
    # When: all the data is correct
    # Then: the task should create 1 bills and 10 activities
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
    @patch("breathecode.provisioning.tasks.upload.delay", MagicMock(wraps=upload.delay))
    @patch("breathecode.provisioning.tasks.calculate_bill_amounts.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    def test_from_github_credentials__generate_anything(self):
        csv = rigobot_csv(10)

        github_academy_users = [
            {
                "username": username,
            }
            for username in csv["github_username"]
        ]
        github_academy_user_logs = [
            {
                "storage_status": "SYNCHED",
                "storage_action": "ADD",
                "academy_user_id": n + 1,
            }
            for n in range(10)
        ]
        provisioning_vendor = {"name": "Rigobot"}
        model = self.bc.database.create(
            user=10,
            app={"slug": "rigobot"},
            first_party_credentials={"app": {"rigobot": 10}},
            github_academy_user=github_academy_users,
            github_academy_user_log=github_academy_user_logs,
            provisioning_vendor=provisioning_vendor,
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        slug = self.bc.fake.slug()
        with patch("breathecode.services.google_cloud.File.download", MagicMock(side_effect=csv_file_mock(csv))):

            upload(slug)

        self.assertEqual(self.bc.database.list_of("payments.Currency"), [currency_data()])
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningBill"),
            [
                provisioning_bill_data(
                    {
                        "hash": slug,
                        "vendor_id": 1,
                    }
                ),
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionKind"),
            [
                provisioning_activity_kind_data(
                    {
                        "id": n + 1,
                        "product_name": f'{csv["purpose"][n]} (type: {csv["pricing_type"][n]}, model: {csv["model"][n]})',
                        "sku": f'{csv["purpose_slug"][n]}--{csv["pricing_type"][n].lower()}--{csv["model"][n].lower()}',
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningPrice"),
            [
                provisioning_activity_price_data(
                    {
                        "currency_id": 1,
                        "id": 1,
                        "multiplier": 1.3,
                        "price_per_unit": 0.04 if csv["pricing_type"][0] == "OUTPUT" else 0.02,
                        "unit_type": "Tokens",
                    }
                ),
                provisioning_activity_price_data(
                    {
                        "currency_id": 1,
                        "id": 2,
                        "multiplier": 1.3,
                        "price_per_unit": 0.04 if csv["pricing_type"][0] != "OUTPUT" else 0.02,
                        "unit_type": "Tokens",
                    }
                ),
            ],
        )
        output_was_first = csv["pricing_type"][0] == "OUTPUT"
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionEvent"),
            [
                provisioning_activity_item_data(
                    {
                        "id": n + 1,
                        "price_id": (
                            (1 if output_was_first else 2)
                            if csv["pricing_type"][n] == "OUTPUT"
                            else (2 if output_was_first else 1)
                        ),
                        "quantity": float(csv["total_tokens"][n]),
                        "external_pk": str(csv["consumption_item_id"][n]),
                        "registered_at": self.bc.datetime.from_iso_string(csv["consumption_period_start"][n]),
                        "csv_row": n,
                        "vendor_id": 1,
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningUserConsumption"),
            [
                provisioning_activity_data(
                    {
                        "id": n + 1,
                        "kind_id": n + 1,
                        "hash": slug,
                        "username": csv["github_username"][n],
                        "processed_at": UTC_NOW,
                        "status": "PERSISTED",
                    }
                )
                for n in range(10)
            ],
        )

        self.assertEqual(
            self.bc.database.list_of("authenticate.GithubAcademyUser"),
            self.bc.format.to_dict(model.github_academy_user),
        )

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f"Starting upload for hash {slug}")])
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])
        self.bc.check.calls(tasks.calculate_bill_amounts.delay.call_args_list, [call(slug)])

    # Given: a csv with codespaces data and 10 User, 10 GithubAcademyUser, 10 GithubAcademyUserLog
    #     -> and 1 ProvisioningVendor of type codespaces
    # When: all the data is correct, and the amount of rows is greater than the limit
    # Then: the task should create 1 bills and 10 activities
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
    @patch("breathecode.provisioning.tasks.upload.delay", MagicMock(wraps=upload.delay))
    @patch("breathecode.provisioning.tasks.calculate_bill_amounts.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    @patch("breathecode.provisioning.tasks.PANDAS_ROWS_LIMIT", PropertyMock(return_value=3))
    def test_pagination(self):
        csv = rigobot_csv(10)

        limit = tasks.PANDAS_ROWS_LIMIT
        tasks.PANDAS_ROWS_LIMIT = 3

        provisioning_vendor = {"name": "Rigobot"}
        github_academy_users = [
            {
                "username": username,
            }
            for username in csv["github_username"]
        ]
        github_academy_user_logs = [
            {
                "storage_status": "SYNCHED",
                "storage_action": "ADD",
                "academy_user_id": n + 1,
            }
            for n in range(10)
        ]
        model = self.bc.database.create(
            user=10,
            app={"slug": "rigobot"},
            first_party_credentials={"app": {"rigobot": 10}},
            github_academy_user=github_academy_users,
            github_academy_user_log=github_academy_user_logs,
            provisioning_vendor=provisioning_vendor,
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        task_manager_id = get_last_task_manager_id(self.bc) + 1

        slug = self.bc.fake.slug()
        with patch("breathecode.services.google_cloud.File.download", MagicMock(side_effect=csv_file_mock(csv))):

            upload(slug)

        self.assertEqual(self.bc.database.list_of("payments.Currency"), [currency_data()])
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningBill"),
            [
                provisioning_bill_data(
                    {
                        "hash": slug,
                        "vendor_id": 1,
                    }
                ),
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionKind"),
            [
                provisioning_activity_kind_data(
                    {
                        "id": n + 1,
                        "product_name": f'{csv["purpose"][n]} (type: {csv["pricing_type"][n]}, model: {csv["model"][n]})',
                        "sku": f'{csv["purpose_slug"][n]}--{csv["pricing_type"][n].lower()}--{csv["model"][n].lower()}',
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningPrice"),
            [
                provisioning_activity_price_data(
                    {
                        "currency_id": 1,
                        "id": 1,
                        "multiplier": 1.3,
                        "price_per_unit": 0.04 if csv["pricing_type"][0] == "OUTPUT" else 0.02,
                        "unit_type": "Tokens",
                    }
                ),
                provisioning_activity_price_data(
                    {
                        "currency_id": 1,
                        "id": 2,
                        "multiplier": 1.3,
                        "price_per_unit": 0.04 if csv["pricing_type"][0] != "OUTPUT" else 0.02,
                        "unit_type": "Tokens",
                    }
                ),
            ],
        )
        output_was_first = csv["pricing_type"][0] == "OUTPUT"
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionEvent"),
            [
                provisioning_activity_item_data(
                    {
                        "id": n + 1,
                        "price_id": (
                            (1 if output_was_first else 2)
                            if csv["pricing_type"][n] == "OUTPUT"
                            else (2 if output_was_first else 1)
                        ),
                        "quantity": float(csv["total_tokens"][n]),
                        "external_pk": str(csv["consumption_item_id"][n]),
                        "registered_at": self.bc.datetime.from_iso_string(csv["consumption_period_start"][n]),
                        "csv_row": n,
                        "vendor_id": 1,
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningUserConsumption"),
            [
                provisioning_activity_data(
                    {
                        "id": n + 1,
                        "kind_id": n + 1,
                        "hash": slug,
                        "username": csv["github_username"][n],
                        "processed_at": UTC_NOW,
                        "status": "PERSISTED",
                    }
                )
                for n in range(10)
            ],
        )

        self.assertEqual(
            self.bc.database.list_of("authenticate.GithubAcademyUser"),
            self.bc.format.to_dict(model.github_academy_user),
        )

        self.bc.check.calls(
            logging.Logger.info.call_args_list, [call(f"Starting upload for hash {slug}") for _ in range(4)]
        )
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

        self.bc.check.calls(
            tasks.upload.delay.call_args_list,
            [
                call(slug, page=1, task_manager_id=task_manager_id),
                call(slug, page=2, task_manager_id=task_manager_id),
                call(slug, page=3, task_manager_id=task_manager_id),
            ],
        )

        self.bc.check.calls(tasks.calculate_bill_amounts.delay.call_args_list, [call(slug)])

        tasks.PANDAS_ROWS_LIMIT = limit

    # Given: a csv with codespaces data and 10 User, 10 GithubAcademyUser, 10 GithubAcademyUserLog
    #     -> and 1 ProvisioningVendor of type codespaces
    # When: all the data is correct, without ProfileAcademy
    # Then: the task should create 1 bills and 10 activities per academy
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
    @patch("breathecode.provisioning.tasks.upload.delay", MagicMock(wraps=upload.delay))
    @patch("breathecode.provisioning.tasks.calculate_bill_amounts.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    def test_from_github_credentials__generate_anything__case1(self):
        csv = rigobot_csv(10)

        github_academy_users = [
            {
                "username": username,
            }
            for username in csv["github_username"]
        ]
        github_academy_user_logs = [
            {
                "storage_status": "SYNCHED",
                "storage_action": "ADD",
                "academy_user_id": n + 1,
            }
            for n in range(10)
        ]
        provisioning_vendor = {"name": "Rigobot"}

        model = self.bc.database.create(
            user=10,
            academy_auth_settings=[{"academy_id": n + 1} for n in range(3)],
            academy=3,
            app={"slug": "rigobot"},
            first_party_credentials={"app": {"rigobot": 10}},
            github_academy_user=github_academy_users,
            github_academy_user_log=github_academy_user_logs,
            provisioning_vendor=provisioning_vendor,
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        slug = self.bc.fake.slug()
        with patch("breathecode.services.google_cloud.File.download", MagicMock(side_effect=csv_file_mock(csv))):

            upload(slug)

        self.assertEqual(self.bc.database.list_of("payments.Currency"), [currency_data()])
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningBill"),
            [
                provisioning_bill_data(
                    {
                        "id": 1,
                        "academy_id": 1,
                        "vendor_id": 1,
                        "hash": slug,
                    }
                ),
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionKind"),
            [
                provisioning_activity_kind_data(
                    {
                        "id": n + 1,
                        "product_name": f'{csv["purpose"][n]} (type: {csv["pricing_type"][n]}, model: {csv["model"][n]})',
                        "sku": f'{csv["purpose_slug"][n]}--{csv["pricing_type"][n].lower()}--{csv["model"][n].lower()}',
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningPrice"),
            [
                provisioning_activity_price_data(
                    {
                        "currency_id": 1,
                        "id": 1,
                        "multiplier": 1.3,
                        "price_per_unit": 0.04 if csv["pricing_type"][0] == "OUTPUT" else 0.02,
                        "unit_type": "Tokens",
                    }
                ),
                provisioning_activity_price_data(
                    {
                        "currency_id": 1,
                        "id": 2,
                        "multiplier": 1.3,
                        "price_per_unit": 0.04 if csv["pricing_type"][0] != "OUTPUT" else 0.02,
                        "unit_type": "Tokens",
                    }
                ),
            ],
        )
        output_was_first = csv["pricing_type"][0] == "OUTPUT"
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionEvent"),
            [
                provisioning_activity_item_data(
                    {
                        "id": n + 1,
                        "price_id": (
                            (1 if output_was_first else 2)
                            if csv["pricing_type"][n] == "OUTPUT"
                            else (2 if output_was_first else 1)
                        ),
                        "quantity": float(csv["total_tokens"][n]),
                        "external_pk": str(csv["consumption_item_id"][n]),
                        "registered_at": self.bc.datetime.from_iso_string(csv["consumption_period_start"][n]),
                        "csv_row": n,
                        "vendor_id": 1,
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningUserConsumption"),
            [
                provisioning_activity_data(
                    {
                        "id": n + 1,
                        "kind_id": n + 1,
                        "hash": slug,
                        "username": csv["github_username"][n],
                        "processed_at": UTC_NOW,
                        "status": "PERSISTED",
                    }
                )
                for n in range(10)
            ],
        )

        self.assertEqual(
            self.bc.database.list_of("authenticate.GithubAcademyUser"),
            self.bc.format.to_dict(model.github_academy_user),
        )

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f"Starting upload for hash {slug}")])
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])
        self.bc.check.calls(tasks.calculate_bill_amounts.delay.call_args_list, [call(slug)])

    # Given: a csv with codespaces data and 10 User, 10 GithubAcademyUser, 10 GithubAcademyUserLog
    #     -> and 1 ProvisioningVendor of type codespaces
    # When: all the data is correct, with ProfileAcademy
    # Then: the task should create 1 bills and 10 activities per user's ProfileAcademy
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
    @patch("breathecode.provisioning.tasks.upload.delay", MagicMock(wraps=upload.delay))
    @patch("breathecode.provisioning.tasks.calculate_bill_amounts.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    @patch("breathecode.authenticate.signals.academy_invite_accepted.send_robust", MagicMock())
    def test_from_github_credentials__generate_anything__case2(self):
        csv = rigobot_csv(10)

        github_academy_users = [
            {
                "username": username,
            }
            for username in csv["github_username"]
        ]
        github_academy_user_logs = [
            {
                "storage_status": "SYNCHED",
                "storage_action": "ADD",
                "academy_user_id": n + 1,
            }
            for n in range(10)
        ]
        provisioning_vendor = {"name": "Rigobot"}
        profile_academies = []

        for user_n in range(10):
            for academy_n in range(3):
                profile_academies.append(
                    {
                        "academy_id": academy_n + 1,
                        "user_id": user_n + 1,
                        "status": "ACTIVE",
                    }
                )

        credentials_github = [
            {
                "username": csv["github_username"][n],
                "user_id": n + 1,
            }
            for n in range(10)
        ]

        model = self.bc.database.create(
            user=10,
            academy_auth_settings=[{"academy_id": n + 1} for n in range(3)],
            credentials_github=credentials_github,
            app={"slug": "rigobot"},
            first_party_credentials={"app": {"rigobot": 10}},
            academy=3,
            profile_academy=profile_academies,
            github_academy_user=github_academy_users,
            github_academy_user_log=github_academy_user_logs,
            provisioning_vendor=provisioning_vendor,
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        slug = self.bc.fake.slug()

        with patch("breathecode.services.google_cloud.File.download", MagicMock(side_effect=csv_file_mock(csv))):

            upload(slug)

        self.assertEqual(self.bc.database.list_of("payments.Currency"), [currency_data()])
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningBill"),
            [
                provisioning_bill_data(
                    {
                        "id": 1,
                        "academy_id": 1,
                        "hash": slug,
                        "vendor_id": 1,
                    }
                ),
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionKind"),
            [
                provisioning_activity_kind_data(
                    {
                        "id": n + 1,
                        "product_name": f'{csv["purpose"][n]} (type: {csv["pricing_type"][n]}, model: {csv["model"][n]})',
                        "sku": f'{csv["purpose_slug"][n]}--{csv["pricing_type"][n].lower()}--{csv["model"][n].lower()}',
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningPrice"),
            [
                provisioning_activity_price_data(
                    {
                        "currency_id": 1,
                        "id": 1,
                        "multiplier": 1.3,
                        "price_per_unit": 0.04 if csv["pricing_type"][0] == "OUTPUT" else 0.02,
                        "unit_type": "Tokens",
                    }
                ),
                provisioning_activity_price_data(
                    {
                        "currency_id": 1,
                        "id": 2,
                        "multiplier": 1.3,
                        "price_per_unit": 0.04 if csv["pricing_type"][0] != "OUTPUT" else 0.02,
                        "unit_type": "Tokens",
                    }
                ),
            ],
        )
        output_was_first = csv["pricing_type"][0] == "OUTPUT"
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionEvent"),
            [
                provisioning_activity_item_data(
                    {
                        "id": n + 1,
                        "price_id": (
                            (1 if output_was_first else 2)
                            if csv["pricing_type"][n] == "OUTPUT"
                            else (2 if output_was_first else 1)
                        ),
                        "quantity": float(csv["total_tokens"][n]),
                        "external_pk": str(csv["consumption_item_id"][n]),
                        "registered_at": self.bc.datetime.from_iso_string(csv["consumption_period_start"][n]),
                        "csv_row": n,
                        "vendor_id": 1,
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningUserConsumption"),
            [
                provisioning_activity_data(
                    {
                        "id": n + 1,
                        "kind_id": n + 1,
                        "hash": slug,
                        "username": csv["github_username"][n],
                        "processed_at": UTC_NOW,
                        "status": "PERSISTED",
                    }
                )
                for n in range(10)
            ],
        )

        self.assertEqual(
            self.bc.database.list_of("authenticate.GithubAcademyUser"),
            self.bc.format.to_dict(model.github_academy_user),
        )

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f"Starting upload for hash {slug}")])
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])
        self.bc.check.calls(tasks.calculate_bill_amounts.delay.call_args_list, [call(slug)])

    # Given: a csv with codespaces data and 10 User, 10 GithubAcademyUser, 10 GithubAcademyUserLog
    #     -> and 1 ProvisioningVendor of type codespaces
    # When: all the data is correct, with ProfileAcademy
    # Then: the task should create 1 bills and 10 activities per user's ProfileAcademy
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
    @patch("breathecode.provisioning.tasks.upload.delay", MagicMock(wraps=upload.delay))
    @patch("breathecode.provisioning.tasks.calculate_bill_amounts.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    @patch("breathecode.authenticate.signals.academy_invite_accepted.send_robust", MagicMock())
    def test_from_github_credentials__generate_anything__case3(self):
        csv = rigobot_csv(10)

        github_academy_users = [
            {
                "username": username,
            }
            for username in csv["github_username"]
        ]
        github_academy_user_logs = [
            {
                "storage_status": "SYNCHED",
                "storage_action": "ADD",
                "academy_user_id": n + 1,
            }
            for n in range(10)
        ]
        provisioning_vendor = {"name": "Rigobot"}
        profile_academies = []

        for user_n in range(10):
            for academy_n in range(3):
                profile_academies.append(
                    {
                        "academy_id": academy_n + 1,
                        "user_id": user_n + 1,
                        "status": "ACTIVE",
                    }
                )

        credentials_github = [
            {
                "username": csv["github_username"][n],
                "user_id": n + 1,
            }
            for n in range(10)
        ]

        cohort_users = [
            {
                "user_id": n + 1,
                "cohort_id": 1,
            }
            for n in range(10)
        ]

        cohort = {
            "academy_id": 1,
            "kickoff_date": timezone.now() + timedelta(days=1),
            "ending_date": timezone.now() - timedelta(days=1),
        }

        model = self.bc.database.create(
            user=10,
            academy_auth_settings=[{"academy_id": n + 1} for n in range(3)],
            app={"slug": "rigobot"},
            first_party_credentials={"app": {"rigobot": 10}},
            credentials_github=credentials_github,
            academy=3,
            cohort=cohort,
            cohort_user=cohort_users,
            profile_academy=profile_academies,
            github_academy_user=github_academy_users,
            github_academy_user_log=github_academy_user_logs,
            provisioning_vendor=provisioning_vendor,
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        slug = self.bc.fake.slug()

        y = [[model.academy[RANDOM_ACADEMIES[x]]] for x in range(10)]

        with patch("random.choices", MagicMock(side_effect=y)):
            with patch("breathecode.services.google_cloud.File.download", MagicMock(side_effect=csv_file_mock(csv))):

                upload(slug)

        academies = []

        for n in RANDOM_ACADEMIES:
            if n not in academies:
                academies.append(n)

        academies = list(academies)

        self.assertEqual(self.bc.database.list_of("payments.Currency"), [currency_data()])
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningBill"),
            [
                provisioning_bill_data(
                    {
                        "id": 1,
                        "academy_id": RANDOM_ACADEMIES[0] + 1,
                        "hash": slug,
                        "vendor_id": 1,
                    }
                ),
                provisioning_bill_data(
                    {
                        "id": 2,
                        "academy_id": RANDOM_ACADEMIES[1] + 1,
                        "hash": slug,
                        "vendor_id": 1,
                    }
                ),
                provisioning_bill_data(
                    {
                        "id": 3,
                        "academy_id": RANDOM_ACADEMIES[2] + 1,
                        "hash": slug,
                        "vendor_id": 1,
                    }
                ),
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionKind"),
            [
                provisioning_activity_kind_data(
                    {
                        "id": n + 1,
                        "product_name": f'{csv["purpose"][n]} (type: {csv["pricing_type"][n]}, model: {csv["model"][n]})',
                        "sku": f'{csv["purpose_slug"][n]}--{csv["pricing_type"][n].lower()}--{csv["model"][n].lower()}',
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningPrice"),
            [
                provisioning_activity_price_data(
                    {
                        "currency_id": 1,
                        "id": 1,
                        "multiplier": 1.3,
                        "price_per_unit": 0.04 if csv["pricing_type"][0] == "OUTPUT" else 0.02,
                        "unit_type": "Tokens",
                    }
                ),
                provisioning_activity_price_data(
                    {
                        "currency_id": 1,
                        "id": 2,
                        "multiplier": 1.3,
                        "price_per_unit": 0.04 if csv["pricing_type"][0] != "OUTPUT" else 0.02,
                        "unit_type": "Tokens",
                    }
                ),
            ],
        )
        output_was_first = csv["pricing_type"][0] == "OUTPUT"
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionEvent"),
            [
                provisioning_activity_item_data(
                    {
                        "id": n + 1,
                        "price_id": (
                            (1 if output_was_first else 2)
                            if csv["pricing_type"][n] == "OUTPUT"
                            else (2 if output_was_first else 1)
                        ),
                        "quantity": float(csv["total_tokens"][n]),
                        "external_pk": str(csv["consumption_item_id"][n]),
                        "registered_at": self.bc.datetime.from_iso_string(csv["consumption_period_start"][n]),
                        "csv_row": n,
                        "vendor_id": 1,
                    }
                )
                for n in range(10)
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningUserConsumption"),
            [
                provisioning_activity_data(
                    {
                        "id": n + 1,
                        "kind_id": n + 1,
                        "hash": slug,
                        "username": csv["github_username"][n],
                        "processed_at": UTC_NOW,
                        "status": "PERSISTED",
                        "status_text": "",
                    }
                )
                for n in range(10)
            ],
        )

        self.assertEqual(
            self.bc.database.list_of("authenticate.GithubAcademyUser"),
            self.bc.format.to_dict(model.github_academy_user),
        )

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f"Starting upload for hash {slug}")])
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])
        self.bc.check.calls(tasks.calculate_bill_amounts.delay.call_args_list, [call(slug)])
