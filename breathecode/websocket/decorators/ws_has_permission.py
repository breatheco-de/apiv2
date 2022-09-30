from __future__ import annotations

import threading
from urllib.parse import parse_qsl
from channels.generic.websocket import JsonWebsocketConsumer, AsyncJsonWebsocketConsumer

from breathecode.utils.exceptions import ProgramingError
from breathecode.utils import has_permission
from channels.db import database_sync_to_async

from .ws_auth import ws_auth
from .utils import FakeRequest, header_parser

__all__ = ['ws_has_permission']


class SyncWsHasPermission:
    cls: JsonWebsocketConsumer | AsyncJsonWebsocketConsumer
    permission: str
    connect: callable

    def sync_wrapper(self: JsonWebsocketConsumer, instance: WsHasPermission):

        try:
            querystring = dict(parse_qsl(self.scope['query_string'].decode('utf-8')))
            request = FakeRequest(querystring)
            decorator = SyncWsHasPermission.sync_decorator(self, instance, request)
            request.set_user(self.scope['user'])
            decorator(request)

            return instance.cls

        except ProgramingError as e:
            raise e

        except Exception as e:
            self.accept()
            self.send_json({'details': str(e), 'status_code': 403}, close=True)
            return

    def sync_decorator(self, instance: WsHasPermission, request: FakeRequest):
        callback = lambda request, academy_id=None: SyncWsHasPermission.sync_post_decorator(
            self, instance, academy_id)

        return has_permission(instance.permission)(callback)

    def sync_post_decorator(self: JsonWebsocketConsumer, instance: WsHasPermission, academy_id: int):
        self.scope['academy_id'] = academy_id
        return instance.connect(self)


class AsyncWsHasPermission:
    cls: JsonWebsocketConsumer | AsyncJsonWebsocketConsumer
    permission: str
    connect: callable

    async def async_wrapper(self: AsyncJsonWebsocketConsumer, instance: WsHasPermission):

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
            await self.send_json({'details': str(e), 'status_code': 403}, close=True)
            return

    @database_sync_to_async
    def async_decorator(self, consumer: AsyncJsonWebsocketConsumer, request: FakeRequest,
                        event: threading.Event):

        def callback(request, academy_id=None):
            consumer.scope['academy_id'] = academy_id
            event.set()

        decorator = has_permission(self.permission)(callback)
        return decorator(request)

    async def await_for_connect(self, consumer: AsyncJsonWebsocketConsumer, event: threading.Event):
        event.wait()
        return await self.connect(consumer)


class WsHasPermission(SyncWsHasPermission, AsyncWsHasPermission):
    as_asgi = JsonWebsocketConsumer.as_asgi
    cls: JsonWebsocketConsumer | AsyncJsonWebsocketConsumer
    is_async: bool
    permission: str
    connect: callable

    def __init__(self, permission: str):
        self.permission = permission

    def __call__(self, cls: JsonWebsocketConsumer | AsyncJsonWebsocketConsumer):
        if hasattr(self, 'cls'):
            return cls

        self.is_async = issubclass(cls, AsyncJsonWebsocketConsumer)
        self.cls = cls
        self.connect = cls.connect
        instance = self

        if self.is_async:
            cls.connect = lambda self: WsHasPermission.async_wrapper(self, instance)
        else:
            cls.connect = lambda self: WsHasPermission.sync_wrapper(self, instance)

        ws_auth(cls)

        return cls


def ws_has_permission(permission: str):

    def wrapper(cls: JsonWebsocketConsumer | AsyncJsonWebsocketConsumer):
        return WsHasPermission(permission)(cls)

    return wrapper
