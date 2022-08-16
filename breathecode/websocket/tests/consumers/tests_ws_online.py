import asyncio
from django.core.cache import cache

from breathecode.websocket.consumers import OnlineStatusConsumer
from ..mixins import WebsocketTestCase

from channels.routing import URLRouter
from django.urls import path

from channels.testing import WebsocketCommunicator

# Alder Lake 12900H timeout
ALDER_LAKE_TIMEOUT = 0.006

# double of minimum time * 3 (3 is the diff between Intel 7700HQ and 12900H)
# if you want give support to a processor more slower, calculate the diff using
# https://browser.geekbench.com/search?q=12900h
MAX_TIMEOUT = ALDER_LAKE_TIMEOUT * 2 * 3
ROUTER = URLRouter([
    path('testws/<str:academy_slug>/', OnlineStatusConsumer.as_asgi()),
])


class ConsumerTestSuite(WebsocketTestCase):

    async def test__anonymous_user__not_emit_responses(self):

        communicator = WebsocketCommunicator(ROUTER, '/testws/test/')
        connected, subprotocol = await communicator.connect()

        self.assertTrue(connected)

        with self.assertRaisesMessage(asyncio.TimeoutError, ''):
            await communicator.receive_json_from(MAX_TIMEOUT)

        # Close
        await communicator.disconnect()

    async def test__two_anonymous_user__not_emit_responses(self):

        communicator = WebsocketCommunicator(ROUTER, '/testws/test/')
        connected, subprotocol = await communicator.connect()

        self.assertTrue(connected)

        with self.assertRaisesMessage(asyncio.TimeoutError, ''):
            message = await communicator.receive_json_from(MAX_TIMEOUT)

        communicator = WebsocketCommunicator(ROUTER, '/testws/test/')
        connected, subprotocol = await communicator.connect()

        self.assertTrue(connected)

        with self.assertRaisesMessage(asyncio.TimeoutError, ''):
            message = await communicator.receive_json_from(MAX_TIMEOUT)

        # Close
        await communicator.disconnect()

    async def test__anonymous_user__get_one_element_from_history(self):
        communicator = WebsocketCommunicator(ROUTER, '/testws/test/')
        connected, subprotocol = await communicator.connect()

        self.assertTrue(connected)

        cache.set('breathecode-online-status', [1])
        message = await communicator.receive_json_from(MAX_TIMEOUT)

        self.assertEqual(message, {'status': 'connected', 'id': 1})

        with self.assertRaisesMessage(asyncio.TimeoutError, ''):
            await communicator.receive_json_from(MAX_TIMEOUT)

        await communicator.disconnect()

    async def test__anonymous_user__get_two_elements_from_history(self):
        communicator = WebsocketCommunicator(ROUTER, '/testws/test/')
        connected, subprotocol = await communicator.connect()

        self.assertTrue(connected)
        cache.set('breathecode-online-status', [1, 2])

        message1 = await communicator.receive_json_from(MAX_TIMEOUT)
        message2 = await communicator.receive_json_from(MAX_TIMEOUT)

        self.assertEqual(message1, {'status': 'connected', 'id': 1})
        self.assertEqual(message2, {'status': 'connected', 'id': 2})

        with self.assertRaisesMessage(asyncio.TimeoutError, ''):
            await communicator.receive_json_from(MAX_TIMEOUT)

        await communicator.disconnect()

    async def test__auth_user__get_one_element_from_history(self):
        model = await self.bc.database.async_create(user=1, token=1)

        communicator = WebsocketCommunicator(ROUTER, '/testws/test/',
                                             [('authorization', f'Token {model.token.key}')])
        connected, subprotocol = await communicator.connect()

        self.assertTrue(connected)
        cache.set('breathecode-online-status', [2])

        message1 = await communicator.receive_json_from(MAX_TIMEOUT)

        self.assertEqual(message1, {'status': 'connected', 'id': 2})

        with self.assertRaisesMessage(asyncio.TimeoutError, ''):
            await communicator.receive_json_from(MAX_TIMEOUT)

        await communicator.disconnect()

    async def test__auth_user__get_one_element_from_history__disconnect_user(self):
        model = await self.bc.database.async_create(user=1, token=1)
        cache.set('breathecode-online-status', [2, 3])

        communicator = WebsocketCommunicator(ROUTER, '/testws/test/',
                                             [('authorization', f'Token {model.token.key}')])
        connected, subprotocol = await communicator.connect()

        from channels.layers import get_channel_layer

        channel_layer = get_channel_layer()

        await channel_layer.group_send('breathecode-online-status', {'type': 'disconnected', 'id': 3})

        self.assertTrue(connected)

        message1 = await communicator.receive_json_from(MAX_TIMEOUT)
        message2 = await communicator.receive_json_from(MAX_TIMEOUT)
        message3 = await communicator.receive_json_from(MAX_TIMEOUT)

        self.assertEqual(message1, {'status': 'disconnected', 'id': 3})
        self.assertEqual(message2, {'status': 'connected', 'id': 2})
        self.assertEqual(message3, {'status': 'connected', 'id': 3})

        with self.assertRaisesMessage(asyncio.TimeoutError, ''):
            await communicator.receive_json_from(MAX_TIMEOUT)

        await communicator.disconnect()
