"""CAT / AFOCAT API — certificate sales for public transport vehicles."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cat_sale import CatSale
from app.models.user import User
from app.api.deps import get_current_user
from app.services.afocat_client import get_afocat_client

router = APIRouter()


# ── Schemas ──

class PlacaLookupResponse(BaseModel):
    found: bool
    placa: str = ""
    año: int | None = None
    marca: str = ""
    modelo: str = ""
    asientos: int | None = None
    serie: str = ""
    categoria: str = ""
    clase: str = ""
    uso: str = ""
    precio: float = 0
    ap_extra: float = 0
    precio_total: float = 0
    vigencia_dias: int = 0
    vigente: bool = False
    n_tecnica: int | None = None
    error: str | None = None


class DniLookupResponse(BaseModel):
    found: bool
    ap_paterno: str = ""
    ap_materno: str = ""
    nombre: str = ""
    full_name: str = ""
    telefono: str = ""
    direccion: str = ""
    error: str | None = None


class CatSaleCreate(BaseModel):
    # Vehicle
    placa: str
    marca: str | None = None
    modelo: str | None = None
    año: int | None = None
    serie_vehiculo: str | None = None
    asientos: int | None = None
    categoria: str | None = None
    clase: str | None = None
    uso: str | None = None
    color_veh: str = ""
    idn_tecnica: int | None = None
    # Payment
    medio_pago: str = "Efectivo"
    monto_efectivo: float = 0
    monto_digital: float = 0
    # Customer
    customer_name: str
    ap_paterno: str = ""
    ap_materno: str = ""
    nom_razon: str = ""
    customer_dni: str | None = None
    customer_phone: str | None = None
    customer_address: str | None = None
    nacionalidad: str = "PERÚ"
    paradero: str = ""
    ambito: int = 200101
    n_ambito: str = "PIURA"
    ubigeo: int = 0
    n_ubigeo: str = ""
    # Pricing
    precio: float | None = None
    ap_extra: float | None = None
    total: float | None = None
    # Options
    emit_in_afocat: bool = True  # If True, calls AFOCAT API to emit real certificate
    notes: str | None = None


class CatSaleOut(BaseModel):
    id: int
    certificate_number: str | None
    placa: str
    marca: str | None
    modelo: str | None
    año: int | None
    serie_vehiculo: str | None
    asientos: int | None
    categoria: str | None
    clase: str | None
    uso: str | None
    customer_name: str
    customer_dni: str | None
    customer_phone: str | None
    customer_address: str | None
    fecha_desde: str | None
    fecha_hasta: str | None
    precio: float | None
    ap_extra: float | None
    total: float | None
    status: str
    sold_by: int | None
    notes: str | None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Endpoints ──

@router.get("/lookup-placa")
def lookup_placa(
    placa: str = Query(..., min_length=1),
    _user: User = Depends(get_current_user),
) -> PlacaLookupResponse:
    """Lookup vehicle data by plate number from AFOCAT system."""
    try:
        client = get_afocat_client()
        result = client.lookup_placa(placa)
        return PlacaLookupResponse(**result)
    except Exception as e:
        return PlacaLookupResponse(found=False, error=str(e))


@router.get("/lookup-dni")
def lookup_dni(
    dni: str = Query(..., min_length=8, max_length=11),
    _user: User = Depends(get_current_user),
) -> DniLookupResponse:
    """Lookup customer data by DNI — tries AFOCAT first, falls back to Peru Consult (RENIEC)."""
    import os
    import httpx as httpx_sync

    # Try AFOCAT first
    try:
        client = get_afocat_client()
        result = client.lookup_dni(dni)
        if result.get("found") and result.get("full_name", "").strip():
            return DniLookupResponse(**result)
    except Exception:
        pass

    # Fallback: DeColecta API (RENIEC) — same API used by client module
    token = os.environ.get("PERU_CONSULT_API_TOKEN", "")
    if token and len(dni) == 8:
        try:
            resp = httpx_sync.get(
                "https://api.decolecta.com/v1/reniec/dni",
                params={"numero": dni},
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                ap_paterno = data.get("first_last_name", "")
                ap_materno = data.get("second_last_name", "")
                nombre = data.get("first_name", "")
                full_name = f"{ap_paterno} {ap_materno} {nombre}".strip()
                if full_name:
                    return DniLookupResponse(
                        found=True,
                        ap_paterno=ap_paterno,
                        ap_materno=ap_materno,
                        nombre=nombre,
                        full_name=full_name,
                        telefono="",
                        direccion="",
                    )
        except Exception:
            pass

    return DniLookupResponse(found=False, error="DNI no encontrado")


@router.post("", response_model=CatSaleOut, status_code=status.HTTP_201_CREATED)
def create_cat_sale(
    data: CatSaleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Sell a CAT certificate — calls AFOCAT API to emit, then saves locally."""
    from datetime import date, timedelta

    cert_number = None
    pdf_cat_path = None
    pdf_boleta_path = None
    fecha_desde = date.today().strftime("%d/%m/%Y")
    fecha_hasta = (date.today() + timedelta(days=365)).strftime("%d/%m/%Y")

    if data.emit_in_afocat:
        try:
            client = get_afocat_client()

            result = client.sell_cat(
                ap_paterno=data.ap_paterno,
                ap_materno=data.ap_materno,
                nom_razon=data.nom_razon,
                nro_documento=data.customer_dni or "",
                nacionalidad=data.nacionalidad,
                telefono=data.customer_phone or "",
                direccion=data.customer_address or "",
                paradero=data.paradero,
                ambito=data.ambito,
                n_ambito=data.n_ambito,
                ubigeo=data.ubigeo,
                n_ubigeo=data.n_ubigeo,
                placa=data.placa,
                marca=data.marca or "",
                modelo=data.modelo or "",
                año=data.año or 0,
                asientos=data.asientos or 0,
                serie_vehiculo=data.serie_vehiculo or "",
                color_veh=data.color_veh,
                idn_tecnica=data.idn_tecnica or 0,
                precio=data.precio or 0,
                ap_extra=data.ap_extra or 0,
                medio_pago=data.medio_pago,
                monto_efectivo=data.monto_efectivo,
                monto_digital=data.monto_digital,
            )

            if not result.get("success"):
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"AFOCAT: {result.get('error', 'Error al vender CAT')}",
                )

            cert_number = result.get("certificate_number")
            pdf_cat_path = result.get("pdf_cat_url")
            pdf_boleta_path = result.get("pdf_cpe_url")

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"AFOCAT error: {str(e)}",
            )

    # Save locally
    sale = CatSale(
        certificate_number=cert_number,
        placa=data.placa.upper(),
        marca=data.marca,
        modelo=data.modelo,
        año=data.año,
        serie_vehiculo=data.serie_vehiculo,
        asientos=data.asientos,
        categoria=data.categoria,
        clase=data.clase,
        uso=data.uso,
        customer_name=data.customer_name,
        customer_dni=data.customer_dni,
        customer_phone=data.customer_phone,
        customer_address=data.customer_address,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        precio=data.precio,
        ap_extra=data.ap_extra,
        total=data.total,
        status="VENDIDO",
        pdf_cat_path=pdf_cat_path,
        pdf_boleta_path=pdf_boleta_path,
        sold_by=user.id,
        notes=data.notes,
    )
    db.add(sale)
    db.commit()
    db.refresh(sale)
    return sale


@router.get("", response_model=list[CatSaleOut])
def list_cat_sales(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """List all CAT sales, newest first."""
    sales = (
        db.query(CatSale)
        .order_by(CatSale.created_at.desc())
        .limit(200)
        .all()
    )
    return sales


@router.get("/renewals")
def get_renewals(
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Get CAT sales expiring within N days — for renewal reminders."""
    from datetime import date, timedelta

    today = date.today()
    cutoff = today + timedelta(days=days)

    sales = (
        db.query(CatSale)
        .filter(
            CatSale.status == "VENDIDO",
            CatSale.fecha_hasta.isnot(None),
        )
        .all()
    )

    renewals = []
    for sale in sales:
        try:
            expiry = datetime.strptime(sale.fecha_hasta, "%d/%m/%Y").date()
        except (ValueError, TypeError):
            try:
                expiry = datetime.strptime(sale.fecha_hasta, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                continue

        if today <= expiry <= cutoff:
            days_left = (expiry - today).days
            renewals.append({
                "id": sale.id,
                "placa": sale.placa,
                "customer_name": sale.customer_name,
                "customer_phone": sale.customer_phone,
                "fecha_hasta": sale.fecha_hasta,
                "days_left": days_left,
            })

    renewals.sort(key=lambda r: r["days_left"])
    return renewals
