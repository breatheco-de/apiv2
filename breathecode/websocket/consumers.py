# chat/consumers.py
from .utils import AsyncJsonWebsocketConsumer
from django.core.cache import cache

from breathecode.websocket.decorators import ws_auth, ws_can_auth, ws_capable_of, ws_has_permission


# @ws_auth
# @ws_capable_of('read_student')
# @ws_has_permission('delete_assetalias')
@ws_can_auth
class CohortConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.setup()
        await self.accept()


@ws_can_auth
class OnlineStatusConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.setup()

        await self.accept()

        self.user_id = self.scope['user'].id
        self.groups = {
            'breathecode': f'breathecode-online-status',
            'user': self.get_user_group_name(scopes=['breathecode']),
        }

        print('check channel name', self.channel_name)

        # Join room group
        for room_name in self.groups.values():
            await self.channel_layer.group_add(room_name, self.channel_name)

        await self.channel_layer.group_send(self.groups['user'], {'type': 'history'})

        if self.scope['user'].id:
            currents = cache.get(self.groups['breathecode']) or []
            cache.set(self.groups['breathecode'], list(set([*currents, self.scope['user'].id])))

        await self.channel_layer.group_send(self.groups['breathecode'], {
            'type': 'connected',
            'id': self.user_id,
        })

    async def disconnect(self, close_code):
        currents = cache.get(self.groups['breathecode'])
        currents.remove(self.scope['user'].id)
        cache.set(self.groups['breathecode'], currents)

        await self.channel_layer.group_discard(self.groups['user'], self.channel_name)
        await self.channel_layer.group_send(self.groups['breathecode'], {
            'type': 'disconnected',
            'id': self.user_id
        })

    async def history(self, event):
        currents = cache.get(self.groups['breathecode']) or []

        for current in currents:
            if current == self.user_id:
                continue

            await self.channel_layer.group_send(self.groups['breathecode'], {
                'type': 'connected',
                'id': current
            })

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
