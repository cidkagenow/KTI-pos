from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.chat import ChatMessage
from app.models.user import User
from app.schemas.chat import ChatMessageOut, ChatRequest, ChatResponse
from app.services.gemini_service import chat_with_gemini

router = APIRouter()


@router.post("", response_model=ChatResponse)
def send_message(
    body: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Load recent history for Gemini context
    recent = (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == current_user.id)
        .order_by(ChatMessage.id.desc())
        .limit(50)
        .all()
    )
    recent.reverse()

    history = [{"role": m.role, "content": m.content} for m in recent]

    # Call Gemini
    reply = chat_with_gemini(db, current_user, body.message, history)

    # Persist messages (user first to guarantee lower ID)
    user_msg = ChatMessage(
        user_id=current_user.id, role="user", content=body.message
    )
    db.add(user_msg)
    db.flush()

    model_msg = ChatMessage(
        user_id=current_user.id, role="model", content=reply
    )
    db.add(model_msg)
    db.commit()

    # Return updated history
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == current_user.id)
        .order_by(ChatMessage.id.desc())
        .limit(100)
        .all()
    )
    messages.reverse()

    return ChatResponse(
        reply=reply,
        messages=[ChatMessageOut.model_validate(m) for m in messages],
    )


@router.get("/history", response_model=list[ChatMessageOut])
def get_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == current_user.id)
        .order_by(ChatMessage.id.desc())
        .limit(100)
        .all()
    )
    messages.reverse()
    return [ChatMessageOut.model_validate(m) for m in messages]


@router.delete("/history")
def clear_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db.query(ChatMessage).filter(
        ChatMessage.user_id == current_user.id
    ).delete()
    db.commit()
    return {"ok": True}
