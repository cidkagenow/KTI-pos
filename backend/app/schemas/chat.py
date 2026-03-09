from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    created_at: datetime


class ChatResponse(BaseModel):
    reply: str
    messages: list[ChatMessageOut]


class ChatMessageAdminOut(BaseModel):
    id: int
    user_id: int
    username: str
    full_name: str
    role: str
    content: str
    session_id: str | None
    user_agent: str | None
    created_at: datetime


class ChatSessionOut(BaseModel):
    user_id: int
    username: str
    full_name: str
    session_id: str | None
    user_agent: str | None
    message_count: int
    last_message_at: datetime
