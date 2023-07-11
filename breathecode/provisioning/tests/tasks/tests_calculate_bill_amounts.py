"""
Test /answer/:id
"""
import math
import random
from django.utils import timezone
from breathecode.provisioning.tasks import calculate_bill_amounts
import logging
from unittest.mock import patch, MagicMock, call
from breathecode.payments.services.stripe import Stripe

from ..mixins import ProvisioningTestCase

UTC_NOW = timezone.now()
STRIPE_PRICE_ID = f'price_{random.randint(1000, 9999)}'
CREDIT_PRICE = random.randint(1, 20)


def apply_get_env(configuration={}):

    def get_env(key, value=None):
        return configuration.get(key, value)

    return get_env


class MakeBillsTestSuite(ProvisioningTestCase):
    # When: with no bills
    # Then: nothing happens
    @patch('breathecode.provisioning.tasks.calculate_bill_amounts.delay', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_no_bills(self):
        slug = self.bc.fake.slug()
        calculate_bill_amounts(slug)

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [])
        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningActivity'), [])

        self.bc.check.calls(logging.Logger.info.call_args_list,
                            [call(f'Starting calculate_bill_amounts for hash {slug}')])
        self.bc.check.calls(logging.Logger.error.call_args_list, [
            call(f'Does not exists bills for hash {slug}'),
        ])

    # Given 1 ProvisioningBill
    # When: hash does not match
    # Then: nothing happens
    @patch('breathecode.provisioning.tasks.calculate_bill_amounts.delay', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_bill_but_hash_does_not_match(self):
        slug = self.bc.fake.slug()
        provisioning_bill = {'hash': slug, 'total_amount': 0.0}
        model = self.bc.database.create(provisioning_bill=provisioning_bill)

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        bad_slug = self.bc.fake.slug()

        calculate_bill_amounts(bad_slug)

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [
            self.bc.format.to_dict(model.provisioning_bill),
        ])
        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningActivity'), [])

        self.bc.check.calls(logging.Logger.info.call_args_list,
                            [call(f'Starting calculate_bill_amounts for hash {bad_slug}')])
        self.bc.check.calls(logging.Logger.error.call_args_list, [
            call(f'Does not exists bills for hash {bad_slug}'),
        ])

    # Given 1 ProvisioningBill
    # When: hash match
    # Then: the bill keep with the amount 0 and the status changed to PAID
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_bill_exists(self):
        slug = self.bc.fake.slug()
        provisioning_bill = {'hash': slug, 'total_amount': 0.0}
        model = self.bc.database.create(provisioning_bill=provisioning_bill)

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        calculate_bill_amounts(slug)

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [
            {
                **self.bc.format.to_dict(model.provisioning_bill),
                'status': 'PAID',
                'total_amount': 0.0,
                'paid_at': UTC_NOW,
            },
        ])
        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningActivity'), [])

        self.bc.check.calls(logging.Logger.info.call_args_list,
                            [call(f'Starting calculate_bill_amounts for hash {slug}')])
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

    # Given 1 ProvisioningBill and 2 ProvisioningActivity
    # When: hash match and the bill is PENDING and the activities have amount of 0
    # Then: the bill keep with the amount 0 and the status changed to PAID
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_bill_exists_and_activities(self):
        slug = self.bc.fake.slug()
        provisioning_bill = {'hash': slug, 'total_amount': 0.0}
        provisioning_activity = {
            'price_per_unit': 0.0,
            'quantity': 0.0,
            'status': 'PENDING',
        }
        model = self.bc.database.create(provisioning_bill=provisioning_bill,
                                        provisioning_activity=(2, provisioning_activity))

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        calculate_bill_amounts(slug)

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [
            {
                **self.bc.format.to_dict(model.provisioning_bill),
                'status': 'PAID',
                'total_amount': 0.0,
                'paid_at': UTC_NOW,
            },
        ])
        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningActivity'), [
            {
                **self.bc.format.to_dict(model.provisioning_activity[0]),
            },
            {
                **self.bc.format.to_dict(model.provisioning_activity[1]),
            },
        ])

        self.bc.check.calls(logging.Logger.info.call_args_list,
                            [call(f'Starting calculate_bill_amounts for hash {slug}')])
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

    # Given 1 ProvisioningBill and 2 ProvisioningActivity
    # When: hash match and the bill is PENDING the activities have a random amount
    # Then: the bill amount is override with the sum of the activities
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    @patch('os.getenv',
           MagicMock(side_effect=apply_get_env({
               'PROVISIONING_CREDIT_PRICE': CREDIT_PRICE,
               'STRIPE_PRICE_ID': STRIPE_PRICE_ID,
           })))
    def test_bill_exists_and_activities_with_random_amounts__bill_amount_is_override(self):
        slug = self.bc.fake.slug()
        provisioning_bill = {'hash': slug, 'total_amount': random.random() * 1000}
        provisioning_activities = [{
            'price_per_unit': random.random() * 100,
            'quantity': random.random() * 10,
            'status': 'PENDING',
        } for _ in range(2)]
        amount = sum(
            [activity['price_per_unit'] * activity['quantity'] for activity in provisioning_activities])
        model = self.bc.database.create(provisioning_bill=provisioning_bill,
                                        provisioning_activity=provisioning_activities)

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []
        stripe_id = self.bc.fake.slug()
        stripe_url = self.bc.fake.url()
        with patch('breathecode.payments.services.stripe.Stripe.create_payment_link',
                   MagicMock(return_value=(stripe_id, stripe_url))):
            calculate_bill_amounts(slug)

            quantity = math.ceil(amount / CREDIT_PRICE)
            new_amount = quantity * CREDIT_PRICE

            self.bc.check.calls(Stripe.create_payment_link.call_args_list, [call(STRIPE_PRICE_ID, quantity)])

        fee = new_amount - amount
        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [
            {
                **self.bc.format.to_dict(model.provisioning_bill),
                'status': 'DUE',
                'total_amount': new_amount,
                'fee': fee,
                'paid_at': None,
                'stripe_id': stripe_id,
                'stripe_url': stripe_url,
            },
        ])
        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningActivity'), [
            {
                **self.bc.format.to_dict(model.provisioning_activity[0]),
            },
            {
                **self.bc.format.to_dict(model.provisioning_activity[1]),
            },
        ])

        self.bc.check.calls(logging.Logger.info.call_args_list,
                            [call(f'Starting calculate_bill_amounts for hash {slug}')])
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

    # Given 1 ProvisioningBill and 2 ProvisioningActivity
    # When: hash match and the bill is DISPUTED, IGNORED or PAID and the activities have a random amount
    # Then: don't override the bill amount
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_academy_reacted_to_bill(self):
        slug = self.bc.fake.slug()
        provisioning_bill = {
            'hash': slug,
            'total_amount': random.random() * 1000,
            'status': random.choice(['DISPUTED', 'IGNORED', 'PAID']),
        }
        provisioning_activities = [{
            'price_per_unit': random.random() * 100,
            'quantity': random.random() * 10,
            'status': 'PENDING',
        } for _ in range(2)]
        model = self.bc.database.create(provisioning_bill=provisioning_bill,
                                        provisioning_activity=provisioning_activities)

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        calculate_bill_amounts(slug)

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [
            {
                **self.bc.format.to_dict(model.provisioning_bill),
            },
        ])
        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningActivity'), [
            {
                **self.bc.format.to_dict(model.provisioning_activity[0]),
            },
            {
                **self.bc.format.to_dict(model.provisioning_activity[1]),
            },
        ])

        self.bc.check.calls(logging.Logger.info.call_args_list, [
            call(f'Starting calculate_bill_amounts for hash {slug}'),
        ])
        self.bc.check.calls(logging.Logger.error.call_args_list, [
            call(f'Does not exists bills for hash {slug}'),
        ])

    # Given 1 ProvisioningBill and 2 ProvisioningActivity
    # When: hash match and the bill is DISPUTED or IGNORED the activities have a random amount, force = True
    # Then: the bill amount is override with the sum of the activities
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    @patch('os.getenv',
           MagicMock(side_effect=apply_get_env({
               'PROVISIONING_CREDIT_PRICE': CREDIT_PRICE,
               'STRIPE_PRICE_ID': STRIPE_PRICE_ID,
           })))
    def test_academy_reacted_to_bill__no_paid__force(self):
        slug = self.bc.fake.slug()
        provisioning_bill = {
            'hash': slug,
            'total_amount': random.random() * 1000,
            'status': random.choice(['DISPUTED', 'IGNORED']),
        }
        provisioning_activities = [{
            'price_per_unit': random.random() * 100,
            'quantity': random.random() * 10,
            'status': 'PENDING',
        } for _ in range(2)]
        amount = sum(
            [activity['price_per_unit'] * activity['quantity'] for activity in provisioning_activities])
        model = self.bc.database.create(provisioning_bill=provisioning_bill,
                                        provisioning_activity=provisioning_activities)

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        stripe_id = self.bc.fake.slug()
        stripe_url = self.bc.fake.url()
        with patch('breathecode.payments.services.stripe.Stripe.create_payment_link',
                   MagicMock(return_value=(stripe_id, stripe_url))):
            calculate_bill_amounts(slug, force=True)

            quantity = math.ceil(amount / CREDIT_PRICE)
            new_amount = quantity * CREDIT_PRICE

            self.bc.check.calls(Stripe.create_payment_link.call_args_list, [call(STRIPE_PRICE_ID, quantity)])

        fee = new_amount - amount
        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [
            {
                **self.bc.format.to_dict(model.provisioning_bill),
                'status': 'DUE',
                'total_amount': quantity * CREDIT_PRICE,
                'fee': fee,
                'paid_at': None,
                'stripe_id': stripe_id,
                'stripe_url': stripe_url,
            },
        ])
        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningActivity'), [
            {
                **self.bc.format.to_dict(model.provisioning_activity[0]),
            },
            {
                **self.bc.format.to_dict(model.provisioning_activity[1]),
            },
        ])

        self.bc.check.calls(logging.Logger.info.call_args_list,
                            [call(f'Starting calculate_bill_amounts for hash {slug}')])
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

    # Given 1 ProvisioningBill and 2 ProvisioningActivity
    # When: hash match and the bill is PAID the activities have a random amount, force = True
    # Then: the bill amount is override with the sum of the activities
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_academy_reacted_to_bill__paid__force(self):
        slug = self.bc.fake.slug()
        provisioning_bill = {
            'hash': slug,
            'total_amount': random.random() * 1000,
            'status': 'PAID',
        }
        provisioning_activities = [{
            'price_per_unit': random.random() * 100,
            'quantity': random.random() * 10,
            'status': 'PENDING',
        } for _ in range(2)]
        model = self.bc.database.create(provisioning_bill=provisioning_bill,
                                        provisioning_activity=provisioning_activities)

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        calculate_bill_amounts(slug, force=True)

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [
            {
                **self.bc.format.to_dict(model.provisioning_bill),
                'status': 'PAID',
            },
        ])
        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningActivity'), [
            {
                **self.bc.format.to_dict(model.provisioning_activity[0]),
            },
            {
                **self.bc.format.to_dict(model.provisioning_activity[1]),
            },
        ])

        self.bc.check.calls(logging.Logger.info.call_args_list, [
            call(f'Starting calculate_bill_amounts for hash {slug}'),
        ])
        self.bc.check.calls(logging.Logger.error.call_args_list, [
            call(f'Does not exists bills for hash {slug}'),
        ])
