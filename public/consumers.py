"""
WebSocket consumers for real-time updates
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer


class GiveawayConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time giveaway updates.
    Clients can connect to receive live updates about giveaways.
    """
    
    async def connect(self):
        self.room_group_name = 'giveaway_updates'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send welcome message
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to giveaway updates'
        }))
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type', '')
            
            if message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong'
                }))
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))
    
    async def giveaway_update(self, event):
        """
        Handler for giveaway update messages.
        Called when a message is sent to the group.
        """
        await self.send(text_data=json.dumps({
            'type': 'giveaway_update',
            'data': event.get('data', {})
        }))

