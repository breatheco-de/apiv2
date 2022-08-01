from random import randint
from channels.generic.websocket import (AsyncJsonWebsocketConsumer as OriginalAsyncJsonWebsocketConsumer,
                                        JsonWebsocketConsumer)
from django.contrib.auth.models import AnonymousUser

from breathecode.utils.attr_dict import AttrDict
from breathecode.websocket.decorators.utils.header_parser import header_parser

MAX_INT = 1000000000000

__all__ = ['AsyncJsonWebsocketConsumer']
UNAUTHENTICATED = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}


class CommonBreathecodeConsumerMixin():
    def get_anonymous_user_id(self):
        """
        Get a unique id for a anonymous user, I you don't want to send or receive a message from other consumer
        consider use a scope.
        """

        return f'{randint(0, MAX_INT)}-{randint(0, MAX_INT)}-{randint(0, MAX_INT)}'

    def get_user_group_name(self, scopes: list[str] = []):
        """
        Get a unique id for be use as group name.
        """

        id = self.scope['user'].id
        result = ''

        for scope in sorted(scopes):
            result += scope + '__'

        result += f'user__{id}' if id else f'anonymous_user__{self.get_anonymous_user_id()}'

        return result

    def setup(self):
        if 'user' not in self.scope:
            self.scope['user'] = AnonymousUser()

        self.scope = AttrDict(**self.scope)
        self.scope.headers = header_parser(self.scope.headers)


class AsyncBreathecodeConsumerMixin(CommonBreathecodeConsumerMixin):
    async def setup(self):
        """
        This configure all the related tasks in the `connect` method of consumer
        """
        super().setup()


class SyncBreathecodeConsumerMixin(CommonBreathecodeConsumerMixin):
    def setup(self):
        """
        This configure all the related tasks in the `connect` method of consumer
        """
        super().setup()


class AsyncJsonWebsocketConsumer(OriginalAsyncJsonWebsocketConsumer, AsyncBreathecodeConsumerMixin):
    ...


class SyncJsonWebsocketConsumer(JsonWebsocketConsumer, SyncBreathecodeConsumerMixin):
    ...
