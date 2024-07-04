"""
Test /answer/:id
"""

import logging
import math
import os
import random
import re
from datetime import datetime, timedelta
from unittest.mock import MagicMock, PropertyMock, call, patch

import pandas as pd
from django.utils import timezone
from faker import Faker
from pytz import UTC

from breathecode.payments.services.stripe import Stripe
from breathecode.provisioning.tasks import calculate_bill_amounts

from ..mixins import ProvisioningTestCase

UTC_NOW = timezone.now()
STRIPE_PRICE_ID = f"price_{random.randint(1000, 9999)}"
CREDIT_PRICE = random.randint(1, 20)

GOOGLE_CLOUD_KEY = os.getenv("GOOGLE_CLOUD_KEY", None)
MONTHS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]

fake = Faker()
fake_url = fake.url()


def datetime_to_iso(date) -> str:
    return re.sub(r"\+00:00$", "Z", date.replace(tzinfo=UTC).isoformat())


def apply_get_env(configuration={}):

    def get_env(key, value=None):
        return configuration.get(key, value)

    return get_env


def csv_file_mock(obj):
    df = pd.DataFrame.from_dict(obj)

    def csv_file_mock_inner(file):
        df.to_csv(file)
        file.seek(0)

    return csv_file_mock_inner


def datetime_to_show_date(date) -> str:
    return date.strftime("%Y-%m-%d")


def codespaces_csv(lines=1, data={}):
    usernames = [fake.slug() for _ in range(lines)]
    dates = [datetime_to_show_date(UTC_NOW + timedelta(days=n)) for n in range(lines)]
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
    effective_times = [datetime_to_iso(UTC_NOW - timedelta(days=n)) for n in range(lines)]
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


class MakeBillsTestSuite(ProvisioningTestCase):
    # When: with no bills
    # Then: nothing happens
    @patch("breathecode.provisioning.tasks.calculate_bill_amounts.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    def test_no_bills(self):
        slug = self.bc.fake.slug()
        calculate_bill_amounts(slug)

        self.assertEqual(self.bc.database.list_of("provisioning.ProvisioningUserConsumption"), [])
        self.assertEqual(self.bc.database.list_of("provisioning.ProvisioningBill"), [])

        self.bc.check.calls(
            logging.Logger.info.call_args_list,
            [
                call(f"Starting calculate_bill_amounts for hash {slug}"),
                # retried
                call(f"Starting calculate_bill_amounts for hash {slug}"),
            ],
        )
        self.bc.check.calls(
            logging.Logger.error.call_args_list,
            [
                call(f"Does not exists bills for hash {slug}", exc_info=True),
            ],
        )

    # Given 1 ProvisioningBill
    # When: hash does not match
    # Then: nothing happens
    @patch("breathecode.provisioning.tasks.calculate_bill_amounts.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    def test_bill_but_hash_does_not_match(self):
        slug = self.bc.fake.slug()
        provisioning_bill = {"hash": slug, "total_amount": 0.0}
        model = self.bc.database.create(provisioning_bill=provisioning_bill, provisioning_vendor={"name": "Gitpod"})

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        bad_slug = self.bc.fake.slug()

        calculate_bill_amounts(bad_slug)

        self.assertEqual(self.bc.database.list_of("provisioning.ProvisioningUserConsumption"), [])
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningBill"),
            [
                self.bc.format.to_dict(model.provisioning_bill),
            ],
        )

        self.bc.check.calls(
            logging.Logger.info.call_args_list,
            [
                call(f"Starting calculate_bill_amounts for hash {bad_slug}"),
                # retried
                call(f"Starting calculate_bill_amounts for hash {bad_slug}"),
            ],
        )
        self.bc.check.calls(
            logging.Logger.error.call_args_list,
            [
                call(f"Does not exists bills for hash {bad_slug}", exc_info=True),
            ],
        )

    # Given 1 ProvisioningBill
    # When: hash match
    # Then: the bill keep with the amount 0 and the status changed to PAID
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
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
    def test_bill_exists(self):
        slug = self.bc.fake.slug()
        provisioning_bill = {"hash": slug, "total_amount": 0.0}
        csv = gitpod_csv(10)
        model = self.bc.database.create(provisioning_bill=provisioning_bill, provisioning_vendor={"name": "Gitpod"})

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        with patch("breathecode.services.google_cloud.File.download", MagicMock(side_effect=csv_file_mock(csv))):
            calculate_bill_amounts(slug)

        self.assertEqual(self.bc.database.list_of("provisioning.ProvisioningUserConsumption"), [])
        started = UTC_NOW.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=9)
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningBill"),
            [
                {
                    **self.bc.format.to_dict(model.provisioning_bill),
                    "status": "PAID",
                    "total_amount": 0.0,
                    "paid_at": UTC_NOW,
                    "started_at": started,
                    "ended_at": UTC_NOW.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=0),
                    "title": f"{MONTHS[started.month - 1]} {started.year}",
                },
            ],
        )

        self.bc.check.calls(
            logging.Logger.info.call_args_list, [call(f"Starting calculate_bill_amounts for hash {slug}")]
        )
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

    # Given 1 ProvisioningBill, 2 ProvisioningActivity and 1 ProvisioningVendor
    # When: hash match and the bill is PENDING and the activities have amount of 0
    #    -> provisioning vendor from gitpod
    # Then: the bill keep with the amount 0 and the status changed to PAID
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
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
    def test_bill_exists_and_activities__gitpod(self):
        slug = self.bc.fake.slug()
        provisioning_bill = {"hash": slug, "total_amount": 0.0}
        csv = gitpod_csv(10)

        provisioning_prices = [
            {
                "price_per_unit": 0,
            }
            for _ in range(2)
        ]

        provisioning_consumption_events = [
            {
                "quantity": 0,
                "price_id": n + 1,
            }
            for n in range(2)
        ]

        provisioning_user_consumptions = [
            {
                "status": random.choice(["PERSISTED", "WARNING"]),
            }
            for _ in range(2)
        ]

        amount = (
            sum(
                [
                    provisioning_prices[n]["price_per_unit"] * provisioning_consumption_events[n]["quantity"]
                    for n in range(2)
                ]
            )
            * 2
        )

        model = self.bc.database.create(
            provisioning_bill=provisioning_bill,
            provisioning_price=provisioning_prices,
            provisioning_vendor={"name": "Gitpod"},
            provisioning_consumption_event=provisioning_consumption_events,
            provisioning_user_consumption=provisioning_user_consumptions,
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        with patch("breathecode.services.google_cloud.File.download", MagicMock(side_effect=csv_file_mock(csv))):
            calculate_bill_amounts(slug)

        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningUserConsumption"),
            [
                {
                    **self.bc.format.to_dict(model.provisioning_user_consumption[0]),
                    "amount": amount / 2,
                },
                {
                    **self.bc.format.to_dict(model.provisioning_user_consumption[1]),
                    "amount": amount / 2,
                },
            ],
        )
        started = UTC_NOW.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=9)
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningBill"),
            [
                {
                    **self.bc.format.to_dict(model.provisioning_bill),
                    "status": "PAID",
                    "total_amount": 0.0,
                    "paid_at": UTC_NOW,
                    "started_at": UTC_NOW.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=9),
                    "ended_at": UTC_NOW.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=0),
                    "title": f"{MONTHS[started.month - 1]} {started.year}",
                },
            ],
        )

        self.bc.check.calls(
            logging.Logger.info.call_args_list, [call(f"Starting calculate_bill_amounts for hash {slug}")]
        )
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

    # Given 1 ProvisioningBill, 2 ProvisioningActivity and 1 ProvisioningVendor
    # When: hash match and the bill is PENDING and the activities have amount of 0
    #    -> provisioning vendor from codespaces
    # Then: the bill keep with the amount 0 and the status changed to PAID
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
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
    def test_bill_exists_and_activities__codespaces(self):
        slug = self.bc.fake.slug()
        provisioning_bill = {"hash": slug, "total_amount": 0.0}
        csv = codespaces_csv(10)

        provisioning_prices = [
            {
                "price_per_unit": 0,
            }
            for _ in range(2)
        ]

        provisioning_consumption_events = [
            {
                "quantity": 0,
                "price_id": n + 1,
            }
            for n in range(2)
        ]

        provisioning_user_consumptions = [
            {
                "status": random.choice(["PERSISTED", "WARNING"]),
            }
            for _ in range(2)
        ]

        amount = (
            sum(
                [
                    provisioning_prices[n]["price_per_unit"] * provisioning_consumption_events[n]["quantity"]
                    for n in range(2)
                ]
            )
            * 2
        )

        model = self.bc.database.create(
            provisioning_bill=provisioning_bill,
            provisioning_price=provisioning_prices,
            provisioning_vendor={"name": "Codespaces"},
            provisioning_consumption_event=provisioning_consumption_events,
            provisioning_user_consumption=provisioning_user_consumptions,
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        with patch("breathecode.services.google_cloud.File.download", MagicMock(side_effect=csv_file_mock(csv))):
            calculate_bill_amounts(slug)

        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningUserConsumption"),
            [
                {
                    **self.bc.format.to_dict(model.provisioning_user_consumption[0]),
                    "amount": amount / 2,
                },
                {
                    **self.bc.format.to_dict(model.provisioning_user_consumption[1]),
                    "amount": amount / 2,
                },
            ],
        )
        started = UTC_NOW.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=0)
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningBill"),
            [
                {
                    **self.bc.format.to_dict(model.provisioning_bill),
                    "status": "PAID",
                    "total_amount": 0.0,
                    "paid_at": UTC_NOW,
                    "started_at": started,
                    "ended_at": UTC_NOW.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=9),
                    "title": f"{MONTHS[started.month - 1]} {started.year}",
                },
            ],
        )

        self.bc.check.calls(
            logging.Logger.info.call_args_list, [call(f"Starting calculate_bill_amounts for hash {slug}")]
        )
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

    # Given 1 ProvisioningBill and 2 ProvisioningActivity
    # When: hash match and the bill is PENDING the activities have a random amount
    # Then: the bill amount is override with the sum of the activities
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "PROVISIONING_CREDIT_PRICE": CREDIT_PRICE,
                    "STRIPE_PRICE_ID": STRIPE_PRICE_ID,
                }
            )
        ),
    )
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
    def test_bill_exists_and_activities_with_random_amounts__bill_amount_is_override(self):
        slug = self.bc.fake.slug()
        provisioning_bill = {"hash": slug, "total_amount": random.random() * 1000}
        csv = gitpod_csv(10)

        provisioning_prices = [
            {
                "price_per_unit": random.random() * 100,
            }
            for _ in range(2)
        ]

        provisioning_consumption_events = [
            {
                "quantity": random.random() * 10,
                "price_id": n + 1,
            }
            for n in range(2)
        ]

        provisioning_user_consumptions = [
            {
                "status": "PERSISTED",
            }
            for _ in range(2)
        ]

        amount = (
            sum(
                [
                    provisioning_prices[n]["price_per_unit"] * provisioning_consumption_events[n]["quantity"]
                    for n in range(2)
                ]
            )
            * 2
        )
        q = sum([provisioning_consumption_events[n]["quantity"] for n in range(2)])
        model = self.bc.database.create(
            provisioning_bill=provisioning_bill,
            provisioning_price=provisioning_prices,
            provisioning_vendor={"name": "Gitpod"},
            provisioning_consumption_event=provisioning_consumption_events,
            provisioning_user_consumption=provisioning_user_consumptions,
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []
        stripe_id = self.bc.fake.slug()
        stripe_url = self.bc.fake.url()
        with patch(
            "breathecode.payments.services.stripe.Stripe.create_payment_link",
            MagicMock(return_value=(stripe_id, stripe_url)),
        ):
            with patch("breathecode.services.google_cloud.File.download", MagicMock(side_effect=csv_file_mock(csv))):
                calculate_bill_amounts(slug)

                quantity = math.ceil(amount / CREDIT_PRICE)
                new_amount = quantity * CREDIT_PRICE

                self.bc.check.calls(Stripe.create_payment_link.call_args_list, [call(STRIPE_PRICE_ID, quantity)])

        fee = new_amount - amount
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningUserConsumption"),
            [
                {
                    **self.bc.format.to_dict(model.provisioning_user_consumption[0]),
                    "amount": amount / 2,
                    "quantity": q,
                },
                {
                    **self.bc.format.to_dict(model.provisioning_user_consumption[1]),
                    "amount": amount / 2,
                    "quantity": q,
                },
            ],
        )
        started = UTC_NOW.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=9)
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningBill"),
            [
                {
                    **self.bc.format.to_dict(model.provisioning_bill),
                    "status": "DUE",
                    "total_amount": new_amount,
                    "fee": fee,
                    "paid_at": None,
                    "stripe_id": stripe_id,
                    "stripe_url": stripe_url,
                    "started_at": started,
                    "ended_at": UTC_NOW.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=0),
                    "title": f"{MONTHS[started.month - 1]} {started.year}",
                },
            ],
        )

        self.bc.check.calls(
            logging.Logger.info.call_args_list, [call(f"Starting calculate_bill_amounts for hash {slug}")]
        )
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

    # Given 1 ProvisioningBill and 2 ProvisioningActivity
    # When: hash match and the bill is DISPUTED, IGNORED or PAID and the activities have a random amount
    # Then: don't override the bill amount
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    def test_academy_reacted_to_bill(self):
        slug = self.bc.fake.slug()
        provisioning_bill = {
            "hash": slug,
            "total_amount": random.random() * 1000,
            "status": random.choice(["DISPUTED", "IGNORED", "PAID"]),
        }

        provisioning_prices = [
            {
                "price_per_unit": random.random() * 100,
            }
            for _ in range(2)
        ]

        provisioning_consumption_events = [
            {
                "quantity": random.random() * 10,
                "price_id": n + 1,
            }
            for n in range(2)
        ]

        provisioning_user_consumptions = [
            {
                "status": "PERSISTED",
            }
            for _ in range(2)
        ]

        model = self.bc.database.create(
            provisioning_bill=provisioning_bill,
            provisioning_price=provisioning_prices,
            provisioning_vendor={"name": "Gitpod"},
            provisioning_consumption_event=provisioning_consumption_events,
            provisioning_user_consumption=provisioning_user_consumptions,
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        calculate_bill_amounts(slug)

        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningUserConsumption"),
            [
                {
                    **self.bc.format.to_dict(model.provisioning_user_consumption[0]),
                },
                {
                    **self.bc.format.to_dict(model.provisioning_user_consumption[1]),
                },
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningBill"),
            [
                {
                    **self.bc.format.to_dict(model.provisioning_bill),
                },
            ],
        )

        self.bc.check.calls(
            logging.Logger.info.call_args_list,
            [
                call(f"Starting calculate_bill_amounts for hash {slug}"),
                # retried
                call(f"Starting calculate_bill_amounts for hash {slug}"),
            ],
        )
        self.bc.check.calls(
            logging.Logger.error.call_args_list,
            [
                call(f"Does not exists bills for hash {slug}", exc_info=True),
            ],
        )

    # Given 1 ProvisioningBill and 2 ProvisioningActivity
    # When: hash match and the bill is DISPUTED or IGNORED the activities have a random amount, force = True
    # Then: the bill amount is override with the sum of the activities
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "PROVISIONING_CREDIT_PRICE": CREDIT_PRICE,
                    "STRIPE_PRICE_ID": STRIPE_PRICE_ID,
                }
            )
        ),
    )
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
    def test_academy_reacted_to_bill__no_paid__force(self):
        slug = self.bc.fake.slug()
        provisioning_bill = {
            "hash": slug,
            "total_amount": random.random() * 1000,
            "status": random.choice(["DISPUTED", "IGNORED"]),
        }
        csv = gitpod_csv(10)

        provisioning_prices = [
            {
                "price_per_unit": random.random() * 100,
            }
            for _ in range(2)
        ]

        provisioning_consumption_events = [
            {
                "quantity": random.random() * 10,
                "price_id": n + 1,
            }
            for n in range(2)
        ]

        provisioning_user_consumptions = [
            {
                "status": "PERSISTED",
            }
            for _ in range(2)
        ]

        amount = (
            sum(
                [
                    provisioning_prices[n]["price_per_unit"] * provisioning_consumption_events[n]["quantity"]
                    for n in range(2)
                ]
            )
            * 2
        )
        q = sum([provisioning_consumption_events[n]["quantity"] for n in range(2)])
        model = self.bc.database.create(
            provisioning_bill=provisioning_bill,
            provisioning_price=provisioning_prices,
            provisioning_vendor={"name": "Gitpod"},
            provisioning_consumption_event=provisioning_consumption_events,
            provisioning_user_consumption=provisioning_user_consumptions,
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        stripe_id = self.bc.fake.slug()
        stripe_url = self.bc.fake.url()
        with patch(
            "breathecode.payments.services.stripe.Stripe.create_payment_link",
            MagicMock(return_value=(stripe_id, stripe_url)),
        ):
            with patch("breathecode.services.google_cloud.File.download", MagicMock(side_effect=csv_file_mock(csv))):
                calculate_bill_amounts(slug, force=True)

            quantity = math.ceil(amount / CREDIT_PRICE)
            new_amount = quantity * CREDIT_PRICE

            self.bc.check.calls(Stripe.create_payment_link.call_args_list, [call(STRIPE_PRICE_ID, quantity)])

        fee = new_amount - amount
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningUserConsumption"),
            [
                {
                    **self.bc.format.to_dict(model.provisioning_user_consumption[0]),
                    "amount": amount / 2,
                    "quantity": q,
                },
                {
                    **self.bc.format.to_dict(model.provisioning_user_consumption[1]),
                    "amount": amount / 2,
                    "quantity": q,
                },
            ],
        )
        started = UTC_NOW.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=9)
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningBill"),
            [
                {
                    **self.bc.format.to_dict(model.provisioning_bill),
                    "status": "DUE",
                    "total_amount": quantity * CREDIT_PRICE,
                    "fee": fee,
                    "paid_at": None,
                    "stripe_id": stripe_id,
                    "stripe_url": stripe_url,
                    "started_at": started,
                    "ended_at": UTC_NOW.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=0),
                    "title": f"{MONTHS[started.month - 1]} {started.year}",
                },
            ],
        )

        self.bc.check.calls(
            logging.Logger.info.call_args_list, [call(f"Starting calculate_bill_amounts for hash {slug}")]
        )
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

    # Given 1 ProvisioningBill and 2 ProvisioningActivity
    # When: hash match and the bill is PAID the activities have a random amount, force = True
    # Then: the bill amount is override with the sum of the activities
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    def test_academy_reacted_to_bill__paid__force(self):
        slug = self.bc.fake.slug()
        provisioning_bill = {
            "hash": slug,
            "total_amount": random.random() * 1000,
            "status": "PAID",
        }

        provisioning_prices = [
            {
                "price_per_unit": random.random() * 100,
            }
            for _ in range(2)
        ]

        provisioning_consumption_events = [
            {
                "quantity": random.random() * 10,
                "price_id": n + 1,
            }
            for n in range(2)
        ]

        provisioning_user_consumptions = [
            {
                "status": "PERSISTED",
            }
            for _ in range(2)
        ]

        model = self.bc.database.create(
            provisioning_bill=provisioning_bill,
            provisioning_price=provisioning_prices,
            provisioning_vendor={"name": "Gitpod"},
            provisioning_consumption_event=provisioning_consumption_events,
            provisioning_user_consumption=provisioning_user_consumptions,
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        calculate_bill_amounts(slug, force=True)

        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningUserConsumption"),
            [
                {
                    **self.bc.format.to_dict(model.provisioning_user_consumption[0]),
                },
                {
                    **self.bc.format.to_dict(model.provisioning_user_consumption[1]),
                },
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningBill"),
            [
                {
                    **self.bc.format.to_dict(model.provisioning_bill),
                    "status": "PAID",
                },
            ],
        )

        self.bc.check.calls(
            logging.Logger.info.call_args_list,
            [
                call(f"Starting calculate_bill_amounts for hash {slug}"),
                # retried
                call(f"Starting calculate_bill_amounts for hash {slug}"),
            ],
        )
        self.bc.check.calls(
            logging.Logger.error.call_args_list,
            [
                call(f"Does not exists bills for hash {slug}", exc_info=True),
            ],
        )
