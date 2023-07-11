from unittest.mock import patch, MagicMock, call
from django.http.request import HttpRequest
from django.urls import reverse_lazy

from ..mixins import MonitoringTestCase
# that 'import as' is thanks pytest think 'test_endpoint' is one fixture
from ...admin import test_endpoint as check_endpoint
from ...models import Endpoint
from rest_framework import status
from breathecode.monitoring import signals

CURRENT_MOCK = MagicMock()
CURRENT_PATH = 'breathecode.monitoring.tasks.test_endpoint'


# This tests check functions are called, remember that this functions are
# tested in tests_monitor.py, we just need check that functions are called
# correctly
class AcademyCohortTestSuite(MonitoringTestCase):

    # When: no signature
    # Then: return 403
    @patch('breathecode.monitoring.signals.stripe_webhook.send', MagicMock(return_value=None))
    def tests_no_signature(self):
        # model = self.bc.database.create()

        url = reverse_lazy('monitoring:stripe_webhook')
        response = self.client.post(url)

        json = response.json()
        expected = {'detail': 'not-allowed', 'status_code': 403}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.bc.database.list_of('monitoring.StripeEvent'), [])

    # When: invalid payload
    # Then: return 400
    @patch('breathecode.monitoring.signals.stripe_webhook.send', MagicMock(return_value=None))
    @patch('stripe.Webhook.construct_event', MagicMock(side_effect=ValueError('x')))
    def tests_invalid_payload(self):
        url = reverse_lazy('monitoring:stripe_webhook')
        self.bc.request.set_headers(stripe_signature='123')
        response = self.client.post(url)

        json = response.json()
        expected = {'detail': 'invalid-payload', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('monitoring.StripeEvent'), [])

    # When: invalid payload, inside action
    # Then: return 400
    @patch('breathecode.monitoring.signals.stripe_webhook.send', MagicMock(return_value=None))
    @patch('stripe.Webhook.construct_event', MagicMock(return_value={}))
    def tests_invalid_payload__inside_action(self):
        url = reverse_lazy('monitoring:stripe_webhook')
        self.bc.request.set_headers(stripe_signature='123')
        response = self.client.post(url)

        json = response.json()
        expected = {'detail': 'invalid-stripe-webhook-payload', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('monitoring.StripeEvent'), [])

    # When: success
    # Then: return 200
    @patch('breathecode.monitoring.signals.stripe_webhook.send', MagicMock(return_value=None))
    def tests_success(self):
        url = reverse_lazy('monitoring:stripe_webhook')
        self.bc.request.set_headers(stripe_signature='123')

        data = {
            'id': self.bc.fake.slug(),
            'type': self.bc.fake.slug(),
            'data': {
                'object': 'x'
            },
            'request': {
                'object': 'x'
            },
        }

        with patch('stripe.Webhook.construct_event', MagicMock(side_effect=[data])):
            response = self.client.post(url)

        json = response.json()
        expected = {'success': True}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data['stripe_id'] = data.pop('id')
        self.assertEqual(self.bc.database.list_of('monitoring.StripeEvent'), [
            {
                **data,
                'id': 1,
                'status': 'PENDING',
                'status_texts': {},
            },
        ])

        StripeEvent = self.bc.database.get_model('monitoring.StripeEvent')
        event = StripeEvent.objects.filter(id=1).first()

        self.bc.check.calls(signals.stripe_webhook.send.call_args_list, [
            call(event=event, sender=event.__class__),
        ])
