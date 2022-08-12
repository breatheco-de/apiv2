import traceback

from channels.db import database_sync_to_async
from channels.generic.websocket import JsonWebsocketConsumer, AsyncJsonWebsocketConsumer

from breathecode.authenticate.models import Token
from breathecode.authenticate.authentication import ExpiringTokenAuthentication
from .utils import FakeRequest

__all__ = ['ws_can_auth']


class SyncWsCanAuth:
    """This class contain the handlers to the JsonWebsocketConsumer"""
    def sync_wrapper(self, cls: JsonWebsocketConsumer, connect: callable):
        found_headers = [
            x for x in self.scope['headers'] if x[0] == b'authorization' or x[0] == 'authorization'
        ]
        if not found_headers:
            return connect(self)

        key, value = found_headers[0]
        request = FakeRequest({key: value})

        try:
            user, token = WsCanAuth.sync_get_token(None, request)

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


class AsyncWsCanAuth:
    """This class contain the handlers to the AsyncJsonWebsocketConsumer"""
    async def async_wrapper(self, cls: AsyncJsonWebsocketConsumer, connect: callable):
        found_headers = [
            x for x in self.scope['headers'] if x[0] == b'authorization' or x[0] == 'authorization'
        ]
        print(found_headers)
        if not found_headers:
            return await connect(self)

        key, value = found_headers[0]
        print('before fake request')
        request = FakeRequest({key: value})
        print('after fake request')

        try:
            print('before call async_get_token')
            user, token = await WsCanAuth.async_get_token(request)
            print('after call async_get_token')

        except Exception as e:
            print(e)
            await self.accept()
            await self.send_json({'details': e.detail, 'status_code': e.status_code}, close=True)
            return

        self.scope['user'] = user
        return await connect(self)

    @database_sync_to_async
    def async_get_token(self, request: FakeRequest) -> tuple[Token, bool]:
        print('in async_get_token')
        return ExpiringTokenAuthentication().authenticate(request)


class WsCanAuth(SyncWsCanAuth, AsyncWsCanAuth):
    """Class decorator use with the purpose of auth"""

    cls: JsonWebsocketConsumer | AsyncJsonWebsocketConsumer
    is_async: bool
    connect: callable

    def __init__(self, cls: JsonWebsocketConsumer | AsyncJsonWebsocketConsumer) -> None:
        self.is_async = issubclass(cls, AsyncJsonWebsocketConsumer)
        self.cls = cls
        self.connect = cls.connect
        connect = cls.connect

        print('is async', self.is_async)

        if self.is_async:
            cls.connect = lambda self: WsCanAuth.async_wrapper(self, cls, connect)
        else:
            cls.connect = lambda self: WsCanAuth.sync_wrapper(self, cls, connect)

        print('after connect', self.is_async)
        WsCanAuth.as_asgi = self.cls.as_asgi


def ws_can_auth(cls: JsonWebsocketConsumer | AsyncJsonWebsocketConsumer):
    """public decorator use with the purpose of auth"""

    WsCanAuth(cls)
    return cls
