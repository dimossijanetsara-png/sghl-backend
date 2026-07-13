from typing import List
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router
from ninja.errors import HttpError
from ninja.pagination import paginate
from apps.core.pagination import SGHLPagination

from apps.authentication.permissions import require_permission
from .models import Conversation, Message
from .schemas import ConversationCreateSchema, ConversationOut, MessageOut

router = Router()


@router.post('/conversations', response=ConversationOut)
def create_conversation(request, payload: ConversationCreateSchema):
    from django.contrib.auth import get_user_model
    User = get_user_model()

    participants = list(User.objects.filter(id__in=payload.participant_ids))
    if request.auth not in participants:
        participants.append(request.auth)

    conv = Conversation.objects.create(subject=payload.subject or '')
    conv.participants.set(participants)
    return conv


@router.get('/conversations', response=List[ConversationOut])
def list_conversations(request):
    return list(request.auth.conversations.filter(is_active=True))


@router.get('/conversations/{conv_id}/messages', response=List[MessageOut])
@paginate(SGHLPagination)
def list_messages(request, conv_id: str):
    conv = get_object_or_404(Conversation, id=conv_id)
    if not conv.participants.filter(id=request.auth.id).exists():
        raise HttpError(403, 'Acces refuse')
    # Marquer les messages non lus comme lus
    Message.objects.filter(
        conversation=conv, is_read=False
    ).exclude(sender=request.auth).update(is_read=True, read_at=timezone.now())
    return Message.objects.filter(conversation=conv)

