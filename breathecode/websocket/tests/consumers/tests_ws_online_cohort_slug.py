import asyncio
from django.core.cache import cache

from breathecode.websocket.consumers import OnlineFromCohortConsumer
from ..mixins import WebsocketTestCase

from channels.routing import URLRouter
from django.urls import path

from channels.testing import WebsocketCommunicator

ROUTER = URLRouter([
    path('testws/<str:cohort_slug>/', OnlineFromCohortConsumer.as_asgi()),
])


class ConsumerTestSuite(WebsocketTestCase):
    async def test_ws_online_cohort_slug__anonymous_user__not_emit_responses(self):

        communicator = WebsocketCommunicator(ROUTER, '/testws/test/')
        connected, subprotocol = await communicator.connect()

        self.assertTrue(connected)

        with self.assertRaisesMessage(asyncio.TimeoutError, ''):
            await communicator.receive_json_from()

        # Close
        await communicator.disconnect()

    async def test_ws_online_cohort_slug__two_anonymous_user__not_emit_responses(self):

        communicator = WebsocketCommunicator(ROUTER, '/testws/test/')
        connected, subprotocol = await communicator.connect()

        self.assertTrue(connected)

        with self.assertRaisesMessage(asyncio.TimeoutError, ''):
            message = await communicator.receive_json_from()

        communicator = WebsocketCommunicator(ROUTER, '/testws/test/')
        connected, subprotocol = await communicator.connect()

        self.assertTrue(connected)

        with self.assertRaisesMessage(asyncio.TimeoutError, ''):
            message = await communicator.receive_json_from()

        # Close
        await communicator.disconnect()

    async def test_ws_online_cohort_slug__anonymous_user__get_one_element_from_history(self):
        communicator = WebsocketCommunicator(ROUTER, '/testws/test/')
        connected, subprotocol = await communicator.connect()

        self.assertTrue(connected)
        cache.set('cohort-test', [1])

        message = await communicator.receive_json_from()

        self.assertEqual(message, {'status': 'connected', 'id': 1})

        with self.assertRaisesMessage(asyncio.TimeoutError, ''):
            await communicator.receive_json_from()

        await communicator.disconnect()

    async def test_ws_online_cohort_slug__anonymous_user__get_two_elements_from_history(self):
        communicator = WebsocketCommunicator(ROUTER, '/testws/test/')
        connected, subprotocol = await communicator.connect()

        self.assertTrue(connected)
        cache.set('cohort-test', [1, 2])

        message1 = await communicator.receive_json_from()
        message2 = await communicator.receive_json_from()

        self.assertEqual(message1, {'status': 'connected', 'id': 1})
        self.assertEqual(message2, {'status': 'connected', 'id': 2})

        with self.assertRaisesMessage(asyncio.TimeoutError, ''):
            await communicator.receive_json_from()

        await communicator.disconnect()

    async def test_ws_online_cohort_slug__auth_user__get_one_element_from_history(self):
        model = await self.bc.database.async_create(user=1, token=1)

        communicator = WebsocketCommunicator(ROUTER, '/testws/test/',
                                             {'authorization': f'Token {model.token.key}'})
        connected, subprotocol = await communicator.connect()

        self.assertTrue(connected)
        cache.set('cohort-test', [2])

        message1 = await communicator.receive_json_from()

        self.assertEqual(message1, {'status': 'connected', 'id': 2})

        with self.assertRaisesMessage(asyncio.TimeoutError, ''):
            await communicator.receive_json_from()

        await communicator.disconnect()

    async def test_ws_online_cohort_slug__auth_user__get_one_element_from_history__disconnect_user(self):
        model = await self.bc.database.async_create(user=1, token=1)
        cache.set('cohort-test', [2, 3])

        communicator = WebsocketCommunicator(ROUTER, '/testws/test/',
                                             {'authorization': f'Token {model.token.key}'})
        connected, subprotocol = await communicator.connect()

        from channels.layers import get_channel_layer

        channel_layer = get_channel_layer()

        await channel_layer.group_send('cohort-test', {'type': 'disconnected', 'id': 3})

        self.assertTrue(connected)

        message1 = await communicator.receive_json_from()
        message2 = await communicator.receive_json_from()
        message3 = await communicator.receive_json_from()

        self.assertEqual(message1, {'status': 'disconnected', 'id': 3})
        self.assertEqual(message2, {'status': 'connected', 'id': 2})
        self.assertEqual(message3, {'status': 'connected', 'id': 3})

        with self.assertRaisesMessage(asyncio.TimeoutError, ''):
            await communicator.receive_json_from()

        await communicator.disconnect()
