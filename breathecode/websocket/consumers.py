# chat/consumers.py
from channels.generic.websocket import AsyncJsonWebsocketConsumer

# from channels.layers import ChannelLayerManager
from channels_redis.pubsub import RedisPubSubChannelLayer


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    channel_layer: RedisPubSubChannelLayer

    async def connect(self):
        # self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.user_group_name = f"notification_{self.user_id}"
        self.academy_group_name = f"notification_{self.user_id}_{self.academy_id}"

        self.user_id = 1
        self.academy_id = 1

        # Join room group
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)
        await self.channel_layer.group_add(f"notification_{self.user_id}_{self.academy_id}", self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):

        await self.channel_layer.group_discard(f"notification_{self.user_id}", self.channel_name)
        await self.channel_layer.group_discard(f"notification_{self.user_id}_{self.academy_id}", self.channel_name)
        ...
        # # Leave room group
        # await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    # Receive message from WebSocket
    async def receive_json(self, content):
        ...
        # text_data_json = json.loads(text_data)
        # message = text_data_json["message"]

        # # Send message to room group
        # await self.channel_layer.group_send(self.room_group_name, {"type": "chat.message", "message": message})

    # Receive message from room group
    async def chat_message(self, event):
        message = event["message"]

        # Send message to WebSocket
        await self.send_json({"message": message})
