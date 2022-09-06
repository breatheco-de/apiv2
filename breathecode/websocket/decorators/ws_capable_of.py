from __future__ import annotations

import threading
from urllib.parse import parse_qsl
from channels.generic.websocket import JsonWebsocketConsumer, AsyncJsonWebsocketConsumer

from breathecode.utils.exceptions import ProgramingError
from breathecode.utils import capable_of
from channels.db import database_sync_to_async

from .ws_auth import ws_auth
from .utils import FakeRequest, header_parser

__all__ = ['ws_capable_of']


class SyncWsCapableOf:
    cls: JsonWebsocketConsumer | AsyncJsonWebsocketConsumer
    capability: str
    connect: callable

    def sync_wrapper(self: JsonWebsocketConsumer, instance: WsCapableOf):

        try:
            querystring = dict(parse_qsl(self.scope['query_string'].decode('utf-8')))
            request = FakeRequest(querystring)
            decorator = SyncWsCapableOf.sync_decorator(self, instance, request)
            request.set_user(self.scope['user'])
            decorator(request)

            return instance.cls

        except ProgramingError as e:
            raise e

        except Exception as e:
            self.accept()
            self.send_json(
                {
                    'details': str(e).replace("'Academy' header", "'academy' query param"),
                    'status_code': 403
                },
                close=True)
            return

    def sync_decorator(self, instance: WsCapableOf, request: FakeRequest):
        callback = lambda request, academy_id=None: SyncWsCapableOf.sync_post_decorator(
            self, instance, academy_id)

        return capable_of(instance.capability)(callback)

    def sync_post_decorator(self: JsonWebsocketConsumer, instance: WsCapableOf, academy_id: int):
        self.scope['academy_id'] = academy_id
        return instance.connect(self)


class AsyncWsCapableOf:
    cls: JsonWebsocketConsumer | AsyncJsonWebsocketConsumer
    capability: str
    connect: callable

    async def async_wrapper(self: AsyncJsonWebsocketConsumer, instance: WsCapableOf):

        try:
            querystring = dict(parse_qsl(self.scope['query_string'].decode('utf-8')))
            request = FakeRequest(querystring)
            request.set_user(self.scope['user'])
            event = threading.Event()
            await instance.async_decorator(self, request, event)
            await instance.await_for_connect(self, event)

            return instance.cls

        except ProgramingError as e:
            raise e

        except Exception as e:
            await self.accept()
            await self.send_json(
                {
                    'details': str(e).replace("'Academy' header", "'academy' query param"),
                    'status_code': 403
                },
                close=True)
            return

    @database_sync_to_async
    def async_decorator(self, consumer: AsyncJsonWebsocketConsumer, request: FakeRequest,
                        event: threading.Event):

        def callback(request, academy_id=None):
            consumer.scope['academy_id'] = academy_id
            event.set()

        decorator = capable_of(self.capability)(callback)
        return decorator(request)

    async def await_for_connect(self, consumer: AsyncJsonWebsocketConsumer, event: threading.Event):
        event.wait()
        return await self.connect(consumer)


class WsCapableOf(SyncWsCapableOf, AsyncWsCapableOf):
    as_asgi = JsonWebsocketConsumer.as_asgi
    cls: JsonWebsocketConsumer | AsyncJsonWebsocketConsumer
    is_async: bool
    capability: str
    connect: callable

    def __init__(self, capability: str):
        self.capability = capability

    def __call__(self, cls: JsonWebsocketConsumer | AsyncJsonWebsocketConsumer):
        if hasattr(self, 'cls'):
            return cls

        self.is_async = issubclass(cls, AsyncJsonWebsocketConsumer)
        self.cls = cls
        self.connect = cls.connect
        instance = self

        if self.is_async:
            cls.connect = lambda self: WsCapableOf.async_wrapper(self, instance)
        else:
            cls.connect = lambda self: WsCapableOf.sync_wrapper(self, instance)

        # WsCapableOf.as_asgi = self.cls.as_asgi
        ws_auth(cls)

        return cls


def ws_capable_of(capability: str):

    def wrapper(cls: JsonWebsocketConsumer | AsyncJsonWebsocketConsumer):
        return WsCapableOf(capability)(cls)

    return wrapper
