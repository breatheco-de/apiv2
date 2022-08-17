import traceback

from channels.db import database_sync_to_async
from channels.generic.websocket import JsonWebsocketConsumer, AsyncJsonWebsocketConsumer

from breathecode.authenticate.models import Token
from breathecode.authenticate.authentication import ExpiringTokenAuthentication
from .utils import FakeRequest

__all__ = ['ws_auth']


class SyncWsAuth:
    """This class contain the handlers to the JsonWebsocketConsumer"""

    def sync_wrapper(self, cls: JsonWebsocketConsumer, connect: callable):
        found_headers = [
            x for x in self.scope['headers'] if x[0] == b'authorization' or x[0] == 'authorization'
        ]
        if not found_headers:
            self.accept()
            self.send_json({'details': 'No credentials provided.', 'status_code': 401}, close=True)
            return

        key, value = found_headers[0]
        request = FakeRequest({key: value})

        try:
            user, token = WsAuth.sync_get_token(None, request)

        except Exception as e:
            if not hasattr(e, 'detail'):
                print(traceback.print_exc())

                self.accept()
                self.send_json({'details': str(e), 'status_code': 500}, close=True)
                return

            self.accept()
            self.send_json({'details': e.detail, 'status_code': e.status_code}, close=True)
            return

        self.scope['user'] = user
        return connect(self)

    def sync_get_token(self, request: FakeRequest) -> tuple[Token, bool]:
        return ExpiringTokenAuthentication().authenticate(request)


class AsyncWsAuth:
    """This class contain the handlers to the AsyncJsonWebsocketConsumer"""

    async def async_wrapper(self, cls: AsyncJsonWebsocketConsumer, connect: callable):
        found_headers = [
            x for x in self.scope['headers'] if x[0] == b'authorization' or x[0] == 'authorization'
        ]
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

    @database_sync_to_async
    def async_get_token(self, request: FakeRequest) -> tuple[Token, bool]:
        return ExpiringTokenAuthentication().authenticate(request)


class WsAuth(SyncWsAuth, AsyncWsAuth):
    """Class decorator use with the purpose of auth"""

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


def ws_auth(cls: JsonWebsocketConsumer | AsyncJsonWebsocketConsumer):
    """public decorator use with the purpose of auth"""

    WsAuth(cls)
    return cls
