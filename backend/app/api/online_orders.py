"""Authenticated management API for online orders — proxies to store server."""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from app.config import settings
from app.models.user import User
from app.schemas.online_order import CancelRequest
from app.api.deps import get_current_user
from app.services.store_sync import proxy_store_request

router = APIRouter()

VALID_STATUSES = ("PENDIENTE", "CONFIRMADO", "LISTO", "RECOGIDO", "CANCELADO")


def _ensure_store_configured():
    if not settings.STORE_SERVER_URL:
        raise HTTPException(status_code=503, detail="Servidor de tienda no configurado")


def _proxy_response(resp):
    """Convert httpx response to FastAPI response."""
    return JSONResponse(status_code=resp.status_code, content=resp.json())


@router.get("")
def list_online_orders(
    status_filter: str | None = Query(None, alias="status"),
    _user: User = Depends(get_current_user),
):
    _ensure_store_configured()
    params = {}
    if status_filter and status_filter in VALID_STATUSES:
        params["status"] = status_filter
    try:
        resp = proxy_store_request("GET", "/api/v1/orders", params=params)
        return _proxy_response(resp)
    except Exception:
        raise HTTPException(status_code=502, detail="Servidor de tienda no disponible")


@router.get("/stats")
def order_stats(
    _user: User = Depends(get_current_user),
):
    _ensure_store_configured()
    try:
        resp = proxy_store_request("GET", "/api/v1/orders/stats")
        return _proxy_response(resp)
    except Exception:
        raise HTTPException(status_code=502, detail="Servidor de tienda no disponible")


@router.get("/{order_id}")
def get_online_order(
    order_id: int,
    _user: User = Depends(get_current_user),
):
    _ensure_store_configured()
    try:
        resp = proxy_store_request("GET", f"/api/v1/orders/{order_id}")
        return _proxy_response(resp)
    except Exception:
        raise HTTPException(status_code=502, detail="Servidor de tienda no disponible")


@router.post("/{order_id}/confirm")
def confirm_order(
    order_id: int,
    user: User = Depends(get_current_user),
):
    _ensure_store_configured()
    try:
        resp = proxy_store_request(
            "POST",
            f"/api/v1/orders/{order_id}/confirm",
            json={"staff_name": user.full_name},
        )
        return _proxy_response(resp)
    except Exception:
        raise HTTPException(status_code=502, detail="Servidor de tienda no disponible")


@router.post("/{order_id}/ready")
def mark_ready(
    order_id: int,
    _user: User = Depends(get_current_user),
):
    _ensure_store_configured()
    try:
        resp = proxy_store_request("POST", f"/api/v1/orders/{order_id}/ready")
        return _proxy_response(resp)
    except Exception:
        raise HTTPException(status_code=502, detail="Servidor de tienda no disponible")


@router.post("/{order_id}/picked-up")
def mark_picked_up(
    order_id: int,
    _user: User = Depends(get_current_user),
):
    _ensure_store_configured()
    try:
        resp = proxy_store_request("POST", f"/api/v1/orders/{order_id}/picked-up")
        return _proxy_response(resp)
    except Exception:
        raise HTTPException(status_code=502, detail="Servidor de tienda no disponible")


@router.post("/{order_id}/cancel")
def cancel_order(
    order_id: int,
    body: CancelRequest,
    user: User = Depends(get_current_user),
):
    _ensure_store_configured()
    try:
        resp = proxy_store_request(
            "POST",
            f"/api/v1/orders/{order_id}/cancel",
            json={"reason": body.reason, "staff_name": user.full_name},
        )
        return _proxy_response(resp)
    except Exception:
        raise HTTPException(status_code=502, detail="Servidor de tienda no disponible")
