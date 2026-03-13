import json
from channels.generic.websocket import AsyncWebsocketConsumer

class MenuConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Join menu updates group
        self.group_name = 'menu_updates'
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Leave menu updates group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    # Receive message from group
    async def menu_update(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps(event))
