from random import randint
from channels.generic.websocket import (AsyncJsonWebsocketConsumer as OriginalAsyncJsonWebsocketConsumer,
                                        AsyncWebsocketConsumer as OriginalAsyncWebsocketConsumer,
                                        WebsocketConsumer as WebsocketConsumer)
from django.contrib.auth.models import AnonymousUser

MAX_INT = 1000000000000

__all__ = ['AsyncJsonWebsocketConsumer']


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

    ...


class AsyncBreathecodeConsumerMixin(CommonBreathecodeConsumerMixin):
    async def setup(self):
        """
        This configure all the related tasks in the `connect` method of consumer
        """
        super().setup()


class SyncBreathecodeConsumerMixin(CommonBreathecodeConsumerMixin):
    ...


class AsyncJsonWebsocketConsumer(OriginalAsyncJsonWebsocketConsumer, AsyncBreathecodeConsumerMixin):
    ...
