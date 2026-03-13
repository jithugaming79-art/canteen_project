import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)


class KitchenConsumer(AsyncWebsocketConsumer):
    @database_sync_to_async
    def is_authorized(self):
        """Check if user is authenticated kitchen/admin staff"""
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            return False
        return hasattr(user, 'profile') and user.profile.role in ['kitchen', 'admin']

    async def connect(self):
        # Reject unauthenticated / unauthorized users
        if not await self.is_authorized():
            logger.warning("WebSocket connection rejected: unauthorized user")
            await self.close()
            return

        # Join kitchen group
        self.group_name = 'kitchen_group'
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        # Join menu updates group
        await self.channel_layer.group_add(
            'menu_updates',
            self.channel_name
        )
        await self.accept()
        logger.info(f"WebSocket connected: {self.scope['user']} to {self.group_name}")

    async def disconnect(self, close_code):
        # Leave kitchen group
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
            # Leave menu updates group
            await self.channel_layer.group_discard(
                'menu_updates',
                self.channel_name
            )

    # Receive message from WebSocket (not used in this direction mostly)
    async def receive(self, text_data):
        pass

    # Receive message from group (Order Updates)
    async def order_update(self, event):
        message = event.get('message', '')
        data = event.get('data', {})

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'order_update',
            'message': message,
            'data': data
        }))

    # Receive message from group (Menu Updates)
    async def menu_update(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps(event))

