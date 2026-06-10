import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close()
            return

        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'

        # Vérifier que l'utilisateur est participant
        is_participant = await self._check_participant(user, self.conversation_id)
        if not is_participant:
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        user = self.scope['user']
        try:
            data = json.loads(text_data)
            content = data.get('content', '').strip()
            if not content:
                return
        except (json.JSONDecodeError, KeyError):
            return

        message = await self._save_message(user, self.conversation_id, content)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message_id': str(message.id),
                'content': content,
                'sender_id': str(user.id),
                'sender_name': user.get_full_name(),
                'timestamp': message.created_at.isoformat(),
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def _check_participant(self, user, conversation_id):
        from .models import Conversation
        return Conversation.objects.filter(
            id=conversation_id, participants=user
        ).exists()

    @database_sync_to_async
    def _save_message(self, user, conversation_id, content):
        from .models import Conversation, Message
        conversation = Conversation.objects.get(id=conversation_id)
        return Message.objects.create(
            conversation=conversation,
            sender=user,
            content=content,
        )
