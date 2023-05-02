from warnings import warn
import requests, json, os, time, logging
from django.dispatch import Signal
from breathecode.authenticate.models import User
from typing import Optional, TypedDict

from breathecode.services.emit.websocket_listener import WebsocketListener

__all__ = ['Emit']


class WebsocketConfig(TypedDict):
    url: str
    key: str
    secret: str
    timeout: int
    channel: str


class Websocket:

    def __init__(self, url='', key='', secret='', timeout=10, channel='default-stream') -> None:
        self.url = url or os.environ.get('EMIT_URL')
        self.key = key or os.environ.get('EMIT_KEY')
        self.secret = secret or os.environ.get('EMIT_SECRET')
        self.timeout = timeout
        self.channel = channel

    def _emit_pull_from(self, kind, pk, pull_from):
        raise NotImplementedError()

    def _emit_response(self, kind, pk, response):
        raise NotImplementedError()

    def _channels_emit_pull_from(self, kind, pk, pull_from: str):
        warn('Deprecated in favor of emit._emit_pull_from, remove it as soon as possible',
             DeprecationWarning,
             stacklevel=2)

        listener = WebsocketListener(self.channel)
        listener.emit({
            'type': 'pull_from',
            'kind': kind,
            'pk': pk,
            'url': pull_from,
        })

    def _channels_emit_response(self, kind, pk, response: dict):
        warn('Deprecated in favor of emit._emit_responses, remove it as soon as possible',
             DeprecationWarning,
             stacklevel=2)

        listener = WebsocketListener(self.channel)
        listener.emit({
            'type': 'resource-created',
            'kind': kind,
            'pk': pk,
            'data': response,
        })

    def send(self, kind, pk, pull_from: Optional[str] = None, response: Optional[str] = None):
        assert pull_from or response, 'You must specify at least one pull_from or responses'

        if pull_from:
            return self._channels_emit_pull_from(kind, pk, pull_from)

        return self._channels_emit_response(kind, pk, response)


class Emit:
    websocket: Websocket

    def __init__(self, websocket: Optional[WebsocketConfig] = None):
        if websocket is None:
            websocket = {}

        self.websocket = Websocket(**websocket)

    # send celery task
    @staticmethod
    def signal(signal: Signal, *args, **kwargs):
        return signal.send(*args, **kwargs)
