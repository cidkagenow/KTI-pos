"""Cuentas por Pagar — Accounts Payable for credit purchase orders."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db, get_current_user, require_admin
from app.models.purchase import PurchaseOrder, Supplier, SupplierPayment
from app.models.user import User

router = APIRouter()


# ── Schemas ──

class PaymentCreate(BaseModel):
    amount: float
    payment_date: str  # YYYY-MM-DD
    payment_method: str  # EFECTIVO, TRANSFERENCIA, YAPE
    reference: str | None = None
    notes: str | None = None


class PaymentOut(BaseModel):
    id: int
    purchase_order_id: int
    amount: float
    payment_date: date
    payment_method: str
    reference: str | None
    notes: str | None
    created_at: datetime
    creator_name: str


class AccountPayableOut(BaseModel):
    po_id: int
    supplier_id: int
    supplier_name: str
    supplier_ruc: str | None
    doc_type: str | None
    doc_number: str | None
    supplier_doc: str | None
    total: float
    paid: float
    balance: float
    received_at: datetime | None
    due_date: date | None
    status: str  # PENDIENTE, PARCIAL, PAGADO, VENCIDO
    days_overdue: int
    moneda: str | None
    payments: list[PaymentOut]


class SummaryOut(BaseModel):
    total_debt: float
    total_overdue: float
    total_due_soon: float
    count_pending: int
    count_overdue: int
    count_due_soon: int


# ── Helpers ──

def _payment_to_out(p: SupplierPayment) -> PaymentOut:
    return PaymentOut(
        id=p.id,
        purchase_order_id=p.purchase_order_id,
        amount=float(p.amount),
        payment_date=p.payment_date,
        payment_method=p.payment_method,
        reference=p.reference,
        notes=p.notes,
        created_at=p.created_at,
        creator_name=p.creator.full_name if p.creator else "",
    )


def _build_payable(po: PurchaseOrder) -> AccountPayableOut:
    total = float(po.total or 0)
    paid = sum(float(p.amount) for p in po.payments)
    balance = round(total - paid, 2)

    # Calculate due date
    due_date = None
    days_overdue = 0
    if po.received_at and po.supplier:
        due_date = (po.received_at + timedelta(days=po.supplier.credit_days)).date()
        if balance > 0 and date.today() > due_date:
            days_overdue = (date.today() - due_date).days

    # Derive status
    if balance <= 0:
        ap_status = "PAGADO"
    elif days_overdue > 0:
        ap_status = "VENCIDO"
    elif paid > 0:
        ap_status = "PARCIAL"
    else:
        ap_status = "PENDIENTE"

    return AccountPayableOut(
        po_id=po.id,
        supplier_id=po.supplier_id,
        supplier_name=po.supplier.business_name if po.supplier else "",
        supplier_ruc=po.supplier.ruc if po.supplier else None,
        doc_type=po.doc_type,
        doc_number=po.doc_number,
        supplier_doc=po.supplier_doc,
        total=total,
        paid=round(paid, 2),
        balance=balance,
        received_at=po.received_at,
        due_date=due_date,
        status=ap_status,
        days_overdue=days_overdue,
        moneda=po.moneda,
        payments=[_payment_to_out(p) for p in sorted(po.payments, key=lambda x: x.payment_date, reverse=True)],
    )


def _get_credit_pos(db: Session):
    return (
        db.query(PurchaseOrder)
        .options(
            joinedload(PurchaseOrder.supplier),
            joinedload(PurchaseOrder.payments).joinedload(SupplierPayment.creator),
        )
        .filter(
            PurchaseOrder.condicion == "CREDITO",
            PurchaseOrder.status == "RECEIVED",
        )
        .order_by(PurchaseOrder.id.desc())
        .all()
    )


# ── Endpoints ──

@router.get("", response_model=list[AccountPayableOut])
def list_accounts_payable(
    status_filter: str | None = Query(None),
    supplier_id: int | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    pos = _get_credit_pos(db)
    payables = [_build_payable(po) for po in pos]

    if supplier_id:
        payables = [p for p in payables if p.supplier_id == supplier_id]
    if status_filter:
        payables = [p for p in payables if p.status == status_filter]

    return payables


@router.get("/summary", response_model=SummaryOut)
def get_summary(
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    pos = _get_credit_pos(db)
    payables = [_build_payable(po) for po in pos]

    today = date.today()
    soon = today + timedelta(days=7)

    total_debt = sum(p.balance for p in payables if p.balance > 0)
    total_overdue = sum(p.balance for p in payables if p.status == "VENCIDO")
    total_due_soon = sum(
        p.balance for p in payables
        if p.due_date and p.balance > 0 and today <= p.due_date <= soon
    )

    return SummaryOut(
        total_debt=round(total_debt, 2),
        total_overdue=round(total_overdue, 2),
        total_due_soon=round(total_due_soon, 2),
        count_pending=sum(1 for p in payables if p.status in ("PENDIENTE", "PARCIAL")),
        count_overdue=sum(1 for p in payables if p.status == "VENCIDO"),
        count_due_soon=sum(1 for p in payables if p.due_date and p.balance > 0 and today <= p.due_date <= soon),
    )


@router.get("/{po_id}/payments", response_model=list[PaymentOut])
def get_payments(
    po_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    payments = (
        db.query(SupplierPayment)
        .options(joinedload(SupplierPayment.creator))
        .filter(SupplierPayment.purchase_order_id == po_id)
        .order_by(SupplierPayment.payment_date.desc())
        .all()
    )
    return [_payment_to_out(p) for p in payments]


@router.post("/{po_id}/payments", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def create_payment(
    po_id: int,
    data: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    po = (
        db.query(PurchaseOrder)
        .options(joinedload(PurchaseOrder.payments))
        .filter(PurchaseOrder.id == po_id)
        .first()
    )
    if not po:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Orden de compra no encontrada")
    if po.condicion != "CREDITO":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Solo ordenes a credito pueden registrar pagos")
    if po.status != "RECEIVED":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La orden debe estar recibida")

    total = float(po.total or 0)
    paid = sum(float(p.amount) for p in po.payments)
    balance = round(total - paid, 2)

    if data.amount <= 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El monto debe ser mayor a 0")
    if data.amount > balance + 0.01:  # small tolerance for rounding
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"El monto excede el saldo pendiente (S/ {balance:.2f})")

    try:
        payment_date = date.fromisoformat(data.payment_date)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Formato de fecha invalido (YYYY-MM-DD)")

    payment = SupplierPayment(
        purchase_order_id=po_id,
        amount=Decimal(str(data.amount)),
        payment_date=payment_date,
        payment_method=data.payment_method,
        reference=data.reference,
        notes=data.notes,
        created_by=current_user.id,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    # Eager load creator for response
    payment = (
        db.query(SupplierPayment)
        .options(joinedload(SupplierPayment.creator))
        .filter(SupplierPayment.id == payment.id)
        .first()
    )
    return _payment_to_out(payment)


@router.delete("/payments/{payment_id}")
def delete_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    payment = db.query(SupplierPayment).filter(SupplierPayment.id == payment_id).first()
    if not payment:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pago no encontrado")
    db.delete(payment)
    db.commit()
    return {"ok": True}
