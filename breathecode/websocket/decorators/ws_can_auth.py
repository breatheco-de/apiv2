import traceback
from urllib.parse import parse_qsl
from django.contrib.auth.models import User

from channels.db import database_sync_to_async
from channels.generic.websocket import JsonWebsocketConsumer, AsyncJsonWebsocketConsumer
from breathecode.authenticate.exceptions import TokenNotFound

from breathecode.authenticate.models import Token

__all__ = ['ws_can_auth']


class SyncWsCanAuth:
    """This class contain the handlers to the JsonWebsocketConsumer"""

    def sync_wrapper(self, cls: JsonWebsocketConsumer, connect: callable):
        querystring = dict(parse_qsl(self.scope['query_string'].decode('utf-8')))

        if 'token' not in querystring:
            return connect(self)

        try:
            user = WsCanAuth.sync_get_token(None, querystring['token'])

        except TokenNotFound as e:
            self.accept()
            self.send_json({'details': str(e), 'status_code': 401}, close=True)
            return

        except Exception as e:
            if not hasattr(e, 'detail'):
                self.accept()
                self.send_json({'details': str(e), 'status_code': 500}, close=True)
                return

            self.accept()
            self.send_json({'details': e.detail, 'status_code': e.status_code}, close=True)
            return

        self.scope['user'] = user
        return connect(self)

    def sync_get_token(self, token: str) -> User:
        return Token.validate_and_destroy(token)


class AsyncWsCanAuth:
    """This class contain the handlers to the AsyncJsonWebsocketConsumer"""

    async def async_wrapper(self, cls: AsyncJsonWebsocketConsumer, connect: callable):
        querystring = dict(parse_qsl(self.scope['query_string'].decode('utf-8')))

        if 'token' not in querystring:
            return await connect(self)

        try:
            user = await WsCanAuth.async_get_token(querystring['token'])

        except TokenNotFound as e:
            await self.accept()
            await self.send_json({'details': str(e), 'status_code': 401}, close=True)
            return

        except Exception as e:
            if not hasattr(e, 'detail'):
                self.accept()
                self.send_json({'details': str(e), 'status_code': 500}, close=True)
                return

            await self.accept()
            await self.send_json({'details': e.detail, 'status_code': e.status_code}, close=True)
            return

        self.scope['user'] = user
        return await connect(self)

    @database_sync_to_async
    def async_get_token(self, token: str) -> User:
        return Token.validate_and_destroy(token)


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

        if self.is_async:
            cls.connect = lambda self: WsCanAuth.async_wrapper(self, cls, connect)
        else:
            cls.connect = lambda self: WsCanAuth.sync_wrapper(self, cls, connect)

        WsCanAuth.as_asgi = self.cls.as_asgi


def ws_can_auth(cls: JsonWebsocketConsumer | AsyncJsonWebsocketConsumer):
    """public decorator use with the purpose of auth"""

    WsCanAuth(cls)
    return cls
