# chat/consumers.py
import json
from random import randint
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.core.cache import cache

from breathecode.websocket.decorators import ws_auth, ws_can_auth, ws_capable_of, ws_has_permission
from django.contrib.auth.models import AnonymousUser

MAX_INT = 1000000000000


# @ws_auth
# @ws_capable_of('read_student')
# @ws_has_permission('delete_assetalias')
@ws_can_auth
class OnlineCohortConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        if 'user' not in self.scope:
            self.scope['user'] = AnonymousUser()

        self.cohort_slug = self.scope['url_route']['kwargs']['cohort_slug']
        self.user_id = self.scope['user'].id if 'user' in self.scope else AnonymousUser
        self.cohort_group_name = f'cohort-{self.cohort_slug}'
        self.user_group_name = f'user-{self.user_id}'

        # prevent a anonymous user has a repeated channel name
        if isinstance(self.scope['user'], AnonymousUser):
            self.user_group_name += f'-{randint(0, MAX_INT)}-{randint(0, MAX_INT)}-{randint(0, MAX_INT)}'

        # Join room group
        await self.channel_layer.group_add(self.cohort_group_name, self.channel_name)
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)

        await self.accept()

        await self.channel_layer.group_send(self.user_group_name, {'type': 'history'})

        currents = cache.get(self.cohort_group_name) or []
        if self.scope['user'].id:
            cache.set(self.cohort_group_name, list(set([*currents, self.scope['user'].id])))

        await self.channel_layer.group_send(self.cohort_group_name, {
            'type': 'connected',
            'id': self.user_id,
        })

    async def disconnect(self, close_code):
        currents = cache.get(self.cohort_group_name)
        currents.remove(self.scope['user'].id)
        cache.set(self.cohort_group_name, currents)

        await self.channel_layer.group_discard(self.user_group_name, self.channel_name)
        await self.channel_layer.group_send(self.cohort_group_name, {
            'type': 'disconnected',
            'id': self.user_id
        })

    async def history(self, event):
        currents = cache.get(self.cohort_group_name) or []

        for current in currents:
            if current == self.user_id:
                continue

            await self.channel_layer.group_send(self.cohort_group_name, {'type': 'connected', 'id': current})

    async def connected(self, event):
        if not event['id'] or event['id'] == self.user_id:
            return

        await self.send_json({
            'status': event['type'],
            'id': event['id'] or 0,
        })

    async def disconnected(self, event):
        if not event['id'] or event['id'] == self.user_id:
            return

        await self.send_json({
            'status': event['type'],
            'id': event['id'] or 0,
        })


@ws_can_auth
class OnlineFromAcademyConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        if 'user' not in self.scope:
            self.scope['user'] = AnonymousUser()

        self.academy_slug = self.scope['url_route']['kwargs']['academy_slug']
        self.user_id = self.scope['user'].id
        self.academy_group_name = f'academy-{self.academy_slug}'
        self.user_group_name = f'user-{self.user_id}'

        # prevent a anonymous user has a repeated channel name
        if isinstance(self.scope['user'], AnonymousUser):
            self.user_group_name += f'-{randint(0, MAX_INT)}-{randint(0, MAX_INT)}-{randint(0, MAX_INT)}'

        # Join room group
        await self.channel_layer.group_add(self.academy_group_name, self.channel_name)
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)

        await self.accept()

        await self.channel_layer.group_send(self.user_group_name, {'type': 'history'})

        currents = cache.get(self.academy_group_name) or []
        if self.scope['user'].id:
            cache.set(self.academy_group_name, list(set([*currents, self.scope['user'].id])))

        await self.channel_layer.group_send(self.academy_group_name, {
            'type': 'connected',
            'id': self.user_id,
        })

    async def disconnect(self, close_code):
        currents = cache.get(self.academy_group_name)
        currents.remove(self.scope['user'].id)
        cache.set(self.academy_group_name, currents)

        await self.channel_layer.group_discard(self.user_group_name, self.channel_name)
        await self.channel_layer.group_send(self.academy_group_name, {
            'type': 'disconnected',
            'id': self.user_id
        })

    async def history(self, event):
        currents = cache.get(self.academy_group_name) or []

        for current in currents:
            if current == self.user_id:
                continue

            await self.channel_layer.group_send(self.academy_group_name, {'type': 'connected', 'id': current})

    async def connected(self, event):
        if not event['id'] or event['id'] == self.user_id:
            return

        await self.send_json({
            'status': event['type'],
            'id': event['id'] or 0,
        })

    async def disconnected(self, event):
        if not event['id'] or event['id'] == self.user_id:
            return

        await self.send_json({
            'status': event['type'],
            'id': event['id'] or 0,
        })
