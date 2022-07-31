# authentication.py

from channels.generic.websocket import JsonWebsocketConsumer, AsyncJsonWebsocketConsumer
from breathecode.authenticate.models import Token

from breathecode.utils.exceptions import ProgramingError
from breathecode.authenticate.authentication import ExpiringTokenAuthentication
from breathecode.utils import capable_of
from channels.db import database_sync_to_async


class FakeRequest:
    META: dict
    headers: dict

    def __init__(self, obj: dict):
        self.META = {}
        self.headers = obj

        for key in obj:
            self.META[f'HTTP_{key.decode().upper()}'] = obj[key]


__all__ = ['ws_auth', 'ws_capable_of', 'WsAuth']


class WsAuth:
    cls: JsonWebsocketConsumer | AsyncJsonWebsocketConsumer
    is_async: bool
    connect: callable

    def __init__(self, cls: JsonWebsocketConsumer | AsyncJsonWebsocketConsumer) -> None:
        self.is_async = issubclass(cls, AsyncJsonWebsocketConsumer)
        self.cls = cls
        self.connect = cls.connect
        connect = cls.connect

        if self.is_async:
            cls.connect = lambda self: WsAuth.async_wrapper(self, cls, connect)
        else:
            cls.connect = lambda self: WsAuth.sync_wrapper(self, cls, connect)

        WsAuth.as_asgi = self.cls.as_asgi

    # def __call__(self):
    #     return self.cls

    def sync_wrapper(self, cls: JsonWebsocketConsumer, connect: callable):
        found_headers = [x for x in self.scope['headers'] if x[0] == b'authorization']
        if not found_headers:
            self.accept()
            self.send_json({'details': 'No credentials provided.', 'status_code': 401}, close=True)
            return

        key, value = found_headers[0]
        request = FakeRequest({key: value})

        try:
            user, token = WsAuth.sync_get_token(None, request)

        except Exception as e:
            self.accept()
            self.send_json({'details': e.detail, 'status_code': e.status_code}, close=True)
            return

        self.scope['user'] = user
        return connect(self)

    async def async_wrapper(self, cls: AsyncJsonWebsocketConsumer, connect: callable):
        found_headers = [x for x in self.scope['headers'] if x[0] == b'authorization']
        if not found_headers:
            await self.accept()
            await self.send_json({'details': 'No credentials provided.', 'status_code': 401}, close=True)
            return

        key, value = found_headers[0]
        request = FakeRequest({key: value})

        try:
            user, token = await WsAuth.async_get_token(request)

        except Exception as e:
            await self.accept()
            await self.send_json({'details': e.detail, 'status_code': e.status_code}, close=True)
            return

        self.scope['user'] = user
        return await connect(self)

    def sync_get_token(self, request: FakeRequest) -> tuple[Token, bool]:
        return ExpiringTokenAuthentication().authenticate(request)

    @database_sync_to_async
    def async_get_token(self, request: FakeRequest) -> tuple[Token, bool]:
        return ExpiringTokenAuthentication().authenticate(request)


def ws_auth(cls: JsonWebsocketConsumer | AsyncJsonWebsocketConsumer):
    WsAuth(cls)
    return cls


class AsyncWsCapableOf:
    as_asgi = JsonWebsocketConsumer.as_asgi
    cls: JsonWebsocketConsumer | AsyncJsonWebsocketConsumer
    is_async: bool
    capability: str
    connect: callable

    async def sync_wrapper(self, cls: AsyncJsonWebsocketConsumer, connect: callable):
        decorator = await self.async_decorator(ws_auth(capable_of(self.capability)))

        try:
            found_headers = [x for x in self.scope['headers'] if x[0] == b'authorization']
            key, value = found_headers[0]

            self.sync_decorator(lambda self, request=None, academy_id=None: self.sync_post_decorator(
                self, FakeRequest({key: value}), academy_id))

            return cls

        except ProgramingError as e:
            raise e

        except Exception as e:
            self.accept()
            self.send_json({'details': str(e), 'status_code': 403}, close=True)
            return

    async def async_wrapper(self, cls: AsyncJsonWebsocketConsumer, connect: callable):
        try:
            found_headers = [x for x in self.scope['headers'] if x[0] == b'authorization']
            key, value = found_headers[0]

            await self.async_decorator(lambda self, request=None, academy_id=None: self.async_post_decorator(
                self, FakeRequest({key: value}), academy_id))

            return cls

        except ProgramingError as e:
            raise e

        except Exception as e:
            self.accept()
            self.send_json({'details': str(e), 'status_code': 403}, close=True)
            return

    def sync_decorator(self, connect: callable):
        ws_auth(self.cls)
        return capable_of(self.capability)(connect)

        # capable_of(self.capability)(connect)
        # ws_auth(self.cls)
        # return self.cls

    @database_sync_to_async
    def async_decorator(self, connect: callable):
        ws_auth(self.cls)
        return capable_of(self.capability)(connect)

        # ws_auth(self.cls)
        # capable_of(self.capability)(connect)
        # return self.cls

    def sync_post_decorator(self: JsonWebsocketConsumer, request, connect: callable, academy_id: int):
        self.scope['academy_id'] = academy_id
        return connect(self)

    async def async_post_decorator(self: JsonWebsocketConsumer, request, connect: callable, academy_id: int):
        self.scope['academy_id'] = academy_id
        return await connect(self)


class WsCapableOf:
    as_asgi = JsonWebsocketConsumer.as_asgi
    cls: JsonWebsocketConsumer | AsyncJsonWebsocketConsumer
    is_async: bool
    capability: str
    connect: callable

    def __init__(self, capability: str):
        self.capability = capability

    def __call__(self, cls: JsonWebsocketConsumer | AsyncJsonWebsocketConsumer):
        self.is_async = issubclass(cls, AsyncJsonWebsocketConsumer)
        # self.as_asgi = JsonWebsocketConsumer.as_asgi
        connect = cls.connect

        if self.is_async:
            cls.connect = lambda self: WsCapableOf.async_wrapper(self, cls, connect)
        else:
            cls.connect = lambda self: WsCapableOf.sync_wrapper(self, cls, connect)

        WsAuth.as_asgi = self.cls.as_asgi

        return cls

    async def sync_wrapper(self, cls: AsyncJsonWebsocketConsumer, connect: callable):
        decorator = await self.async_decorator(ws_auth(capable_of(self.capability)))

        try:
            found_headers = [x for x in self.scope['headers'] if x[0] == b'authorization']
            key, value = found_headers[0]

            self.sync_decorator(lambda self, request=None, academy_id=None: self.sync_post_decorator(
                self, FakeRequest({key: value}), academy_id))

            return cls

        except ProgramingError as e:
            raise e

        except Exception as e:
            self.accept()
            self.send_json({'details': str(e), 'status_code': 403}, close=True)
            return

    async def async_wrapper(self, cls: AsyncJsonWebsocketConsumer, connect: callable):
        try:
            found_headers = [x for x in self.scope['headers'] if x[0] == b'authorization']
            key, value = found_headers[0]

            await self.async_decorator(lambda self, request=None, academy_id=None: self.async_post_decorator(
                self, FakeRequest({key: value}), academy_id))

            return cls

        except ProgramingError as e:
            raise e

        except Exception as e:
            self.accept()
            self.send_json({'details': str(e), 'status_code': 403}, close=True)
            return

    def sync_decorator(self, connect: callable):
        ws_auth(self.cls)
        return capable_of(self.capability)(connect)

        # capable_of(self.capability)(connect)
        # ws_auth(self.cls)
        # return self.cls

    @database_sync_to_async
    def async_decorator(self, connect: callable):
        ws_auth(self.cls)
        return capable_of(self.capability)(connect)

        # ws_auth(self.cls)
        # capable_of(self.capability)(connect)
        # return self.cls

    def sync_post_decorator(self: JsonWebsocketConsumer, request, connect: callable, academy_id: int):
        self.scope['academy_id'] = academy_id
        return connect(self)

    async def async_post_decorator(self: JsonWebsocketConsumer, request, connect: callable, academy_id: int):
        self.scope['academy_id'] = academy_id
        return await connect(self)


def ws_capable_of(capability: str):
    def wrapper(cls: JsonWebsocketConsumer | AsyncJsonWebsocketConsumer):
        return WsCapableOf(capability)(cls)

    return wrapper


# def ws_capable_of(capability):

#     def wrapper(cls: JsonWebsocketConsumer):

#         original_connect = cls.connect

#         def connect_wrapper(self: JsonWebsocketConsumer, request, academy_id: int):
#             self.scope['academy_id'] = academy_id
#             return original_connect(self)

#         def connect(self: JsonWebsocketConsumer):
#             decorator = ws_auth(capable_of(capability))

#             try:
#                 found_headers = [x for x in self.scope['headers'] if x[0] == b'authorization']
#                 key, value = found_headers[0]

#                 return decorator(lambda self, request=None, academy_id=None: connect_wrapper(
#                     self, FakeRequest({key: value}), academy_id))

#             except ProgramingError as e:
#                 raise e

#             except Exception as e:
#                 self.accept()
#                 self.send_json({'details': str(e), 'status_code': 403}, close=True)
#                 return

#         connect.__doc__ = cls.connect.__doc__
#         cls.connect = connect

#         return cls

#     return wrapper
