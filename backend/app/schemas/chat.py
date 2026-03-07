from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ChatRequest(BaseModel):
    message: str


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    created_at: datetime


class ChatResponse(BaseModel):
    reply: str
    messages: list[ChatMessageOut]
