from breathecode.tests.mixins.breathecode_mixin.breathecode import fake

from breathecode.websocket.decorators import ws_auth
from breathecode.websocket.utils import AsyncJsonWebsocketConsumer, SyncJsonWebsocketConsumer
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

ASYNC_RESPONSE = {fake.slug(): fake.slug()}
SYNC_RESPONSE = {fake.slug(): fake.slug()}


@ws_auth
class AsyncConsumer(AsyncJsonWebsocketConsumer):

    async def connect(self):
        await self.setup()
        await self.accept()
        await self.send_json({**ASYNC_RESPONSE, 'hash': hash(self.scope['user'])}, close=True)


@ws_auth
class SyncConsumer(SyncJsonWebsocketConsumer):

    def connect(self):
        self.setup()
        self.accept()
        self.send_json({**SYNC_RESPONSE, 'hash': hash(self.scope['user'])}, close=True)


ROUTER = URLRouter([
    path('testws/async/', AsyncConsumer.as_asgi()),
    path('testws/sync/', SyncConsumer.as_asgi()),
])


class ConsumerTestSuite(WebsocketTestCase):

    async def test__async__without_token(self):

        communicator = WebsocketCommunicator(ROUTER, 'testws/async/')
        connected, subprotocol = await communicator.connect()

        self.assertTrue(connected)

        message = await communicator.receive_json_from(MAX_TIMEOUT)

        self.assertEqual(message, {'details': 'No credentials provided.', 'status_code': 401})

        # Close
        await communicator.disconnect()

    async def test__async__bad_token(self):

        communicator = WebsocketCommunicator(ROUTER, 'testws/async/',
                                             [('authorization', f'Token {self.bc.fake.slug()}')])
        connected, subprotocol = await communicator.connect()

        self.assertTrue(connected)

        message = await communicator.receive_json_from(MAX_TIMEOUT)

        self.assertEqual(message, {
            'details': {
                'error': 'Invalid or Inactive Token',
                'is_authenticated': 'False'
            },
            'status_code': 401
        })

        # Close
        await communicator.disconnect()

    async def test__async__with_token(self):
        model = await self.bc.database.async_create(token=1, user=1)

        communicator = WebsocketCommunicator(ROUTER, 'testws/async/',
                                             [('authorization', f'Token {model.token.key}')])
        connected, subprotocol = await communicator.connect()

        self.assertTrue(connected)

        message = await communicator.receive_json_from(MAX_TIMEOUT)

        self.assertEqual(message, {**ASYNC_RESPONSE, 'hash': hash(model.user)})

        # Close
        await communicator.disconnect()

    async def test__sync__without_token(self):

        communicator = WebsocketCommunicator(ROUTER, 'testws/sync/')
        connected, subprotocol = await communicator.connect()

        self.assertTrue(connected)

        message = await communicator.receive_json_from(MAX_TIMEOUT)

        self.assertEqual(message, {'details': 'No credentials provided.', 'status_code': 401})

        # Close
        await communicator.disconnect()

    async def test__sync__bad_token(self):

        communicator = WebsocketCommunicator(ROUTER, 'testws/sync/',
                                             [('authorization', f'Token {self.bc.fake.slug()}')])
        connected, subprotocol = await communicator.connect()

        self.assertTrue(connected)

        message = await communicator.receive_json_from(MAX_TIMEOUT)

        self.assertEqual(message, {
            'details': {
                'error': 'Invalid or Inactive Token',
                'is_authenticated': 'False'
            },
            'status_code': 401
        })

        # Close
        await communicator.disconnect()

    async def test__sync__with_token(self):
        model = await self.bc.database.async_create(token=1, user=1)

        communicator = WebsocketCommunicator(ROUTER, 'testws/sync/',
                                             [('authorization', f'Token {model.token.key}')])
        connected, subprotocol = await communicator.connect()

        self.assertTrue(connected)

        message = await communicator.receive_json_from(MAX_TIMEOUT)

        self.assertEqual(message, {**SYNC_RESPONSE, 'hash': hash(model.user)})

        # Close
        await communicator.disconnect()
