from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.database import get_db
from app.models.chat import ChatMessage
from app.models.user import User
from app.schemas.chat import (
    ChatMessageAdminOut,
    ChatMessageOut,
    ChatRequest,
    ChatResponse,
    ChatSessionOut,
)
from app.services.gemini_service import chat_with_gemini

router = APIRouter()


@router.post("", response_model=ChatResponse)
def send_message(
    body: ChatRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ua = (request.headers.get("user-agent") or "")[:300]

    # Load recent history for Gemini context (filtered by session)
    q = db.query(ChatMessage).filter(ChatMessage.user_id == current_user.id)
    if body.session_id:
        q = q.filter(ChatMessage.session_id == body.session_id)
    recent = q.order_by(ChatMessage.id.desc()).limit(50).all()
    recent.reverse()

    history = [{"role": m.role, "content": m.content} for m in recent]

    # Call Gemini
    reply = chat_with_gemini(db, current_user, body.message, history)

    # Persist messages (user first to guarantee lower ID)
    user_msg = ChatMessage(
        user_id=current_user.id,
        role="user",
        content=body.message,
        session_id=body.session_id,
        user_agent=ua,
    )
    db.add(user_msg)
    db.flush()

    model_msg = ChatMessage(
        user_id=current_user.id,
        role="model",
        content=reply,
        session_id=body.session_id,
        user_agent=ua,
    )
    db.add(model_msg)
    db.commit()

    # Return updated history (filtered by session)
    q2 = db.query(ChatMessage).filter(ChatMessage.user_id == current_user.id)
    if body.session_id:
        q2 = q2.filter(ChatMessage.session_id == body.session_id)
    messages = q2.order_by(ChatMessage.id.desc()).limit(100).all()
    messages.reverse()

    return ChatResponse(
        reply=reply,
        messages=[ChatMessageOut.model_validate(m) for m in messages],
    )


@router.get("/history", response_model=list[ChatMessageOut])
def get_history(
    session_id: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(ChatMessage).filter(ChatMessage.user_id == current_user.id)
    if session_id:
        q = q.filter(ChatMessage.session_id == session_id)
    messages = q.order_by(ChatMessage.id.desc()).limit(100).all()
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


# ── Admin endpoints ──────────────────────────────────────────────────


@router.get("/admin/sessions", response_model=list[ChatSessionOut])
def admin_sessions(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    rows = (
        db.query(
            ChatMessage.user_id,
            User.username,
            User.full_name,
            ChatMessage.session_id,
            sa_func.max(ChatMessage.user_agent).label("user_agent"),
            sa_func.count(ChatMessage.id).label("message_count"),
            sa_func.max(ChatMessage.created_at).label("last_message_at"),
        )
        .join(User, User.id == ChatMessage.user_id)
        .group_by(ChatMessage.user_id, User.username, User.full_name, ChatMessage.session_id)
        .order_by(sa_func.max(ChatMessage.created_at).desc())
        .all()
    )
    return [
        ChatSessionOut(
            user_id=r.user_id,
            username=r.username,
            full_name=r.full_name,
            session_id=r.session_id,
            user_agent=r.user_agent,
            message_count=r.message_count,
            last_message_at=r.last_message_at,
        )
        for r in rows
    ]


@router.get("/admin/history")
def admin_history(
    user_id: int | None = Query(None),
    session_id: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    q = (
        db.query(
            ChatMessage.id,
            ChatMessage.user_id,
            User.username,
            User.full_name,
            ChatMessage.role,
            ChatMessage.content,
            ChatMessage.session_id,
            ChatMessage.user_agent,
            ChatMessage.created_at,
        )
        .join(User, User.id == ChatMessage.user_id)
    )
    if user_id:
        q = q.filter(ChatMessage.user_id == user_id)
    if session_id:
        q = q.filter(ChatMessage.session_id == session_id)
    if date_from:
        q = q.filter(ChatMessage.created_at >= date_from)
    if date_to:
        q = q.filter(ChatMessage.created_at <= date_to)

    total = q.count()
    rows = (
        q.order_by(ChatMessage.id.asc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    data = [
        ChatMessageAdminOut(
            id=r.id,
            user_id=r.user_id,
            username=r.username,
            full_name=r.full_name,
            role=r.role,
            content=r.content,
            session_id=r.session_id,
            user_agent=r.user_agent,
            created_at=r.created_at,
        )
        for r in rows
    ]
    return {"data": data, "total": total, "page": page, "limit": limit}
