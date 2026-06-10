from ninja import Schema
from typing import Optional, List
from datetime import datetime
import uuid


class ConversationCreateSchema(Schema):
    participant_ids: List[uuid.UUID]
    subject: Optional[str] = ''


class ConversationOut(Schema):
    id: uuid.UUID
    subject: str
    is_active: bool
    created_at: datetime


class MessageOut(Schema):
    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_id: uuid.UUID
    content: str
    is_read: bool
    read_at: Optional[datetime]
    created_at: datetime
