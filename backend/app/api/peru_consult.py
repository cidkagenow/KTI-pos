import os

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user

router = APIRouter()

API_BASE = "https://api.decolecta.com/v1"


def _get_token() -> str:
    token = os.environ.get("PERU_CONSULT_API_TOKEN")
    if not token:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Token de consulta no configurado")
    return token


@router.get("/ruc/{numero}")
async def lookup_ruc(numero: str, _=Depends(get_current_user)):
    if len(numero) != 11 or not numero.isdigit():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="RUC debe tener 11 dígitos")

    token = _get_token()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{API_BASE}/sunat/ruc",
                params={"numero": numero},
                headers={"Authorization": f"Bearer {token}"},
            )
    except httpx.RequestError:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Error al consultar SUNAT")

    if resp.status_code == 404 or not resp.json():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RUC no encontrado")
    if resp.status_code != 200:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Error en servicio SUNAT")

    data = resp.json()

    return {
        "business_name": data.get("razon_social", ""),
        "address": data.get("direccion", ""),
        "departamento": (data.get("departamento") or "").upper(),
        "provincia": (data.get("provincia") or "").upper(),
        "distrito": (data.get("distrito") or "").upper(),
    }


@router.get("/dni/{numero}")
async def lookup_dni(numero: str, _=Depends(get_current_user)):
    if len(numero) != 8 or not numero.isdigit():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="DNI debe tener 8 dígitos")

    token = _get_token()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{API_BASE}/reniec/dni",
                params={"numero": numero},
                headers={"Authorization": f"Bearer {token}"},
            )
    except httpx.RequestError:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Error al consultar RENIEC")

    if resp.status_code == 404 or not resp.json():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DNI no encontrado")
    if resp.status_code != 200:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Error en servicio RENIEC")

    data = resp.json()
    apellido_p = data.get("first_last_name", "")
    apellido_m = data.get("second_last_name", "")
    nombres = data.get("first_name", "")
    business_name = f"{apellido_p} {apellido_m}, {nombres}".strip(", ")

    return {"business_name": business_name}
