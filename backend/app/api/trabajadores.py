from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.trabajador import Trabajador, Asistencia
from app.schemas.trabajador import (
    TrabajadorCreate,
    TrabajadorUpdate,
    TrabajadorOut,
    AsistenciaOut,
    AsistenciaUpdate,
    AsistenciaBulkCreate,
)
from app.api.deps import get_current_user, require_admin
from app.models.user import User

router = APIRouter()


# ── Trabajadores CRUD ────────────────────────────────────────────────

@router.get("", response_model=list[TrabajadorOut])
def list_trabajadores(
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    return db.query(Trabajador).order_by(Trabajador.full_name).all()


@router.get("/active", response_model=list[TrabajadorOut])
def list_active_trabajadores(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return (
        db.query(Trabajador)
        .filter(Trabajador.is_active == True)
        .order_by(Trabajador.full_name)
        .all()
    )


@router.post("", response_model=TrabajadorOut, status_code=status.HTTP_201_CREATED)
def create_trabajador(
    data: TrabajadorCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    if data.dni:
        existing = db.query(Trabajador).filter(Trabajador.dni == data.dni).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe un trabajador con DNI {data.dni}",
            )
    trabajador = Trabajador(**data.model_dump())
    db.add(trabajador)
    db.commit()
    db.refresh(trabajador)
    return trabajador


@router.put("/{trabajador_id}", response_model=TrabajadorOut)
def update_trabajador(
    trabajador_id: int,
    data: TrabajadorUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    trabajador = db.query(Trabajador).filter(Trabajador.id == trabajador_id).first()
    if not trabajador:
        raise HTTPException(status_code=404, detail="Trabajador no encontrado")
    update_data = data.model_dump(exclude_unset=True)
    if "dni" in update_data and update_data["dni"]:
        existing = (
            db.query(Trabajador)
            .filter(Trabajador.dni == update_data["dni"], Trabajador.id != trabajador_id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe un trabajador con DNI {update_data['dni']}",
            )
    for key, value in update_data.items():
        setattr(trabajador, key, value)
    db.commit()
    db.refresh(trabajador)
    return trabajador


@router.delete("/{trabajador_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trabajador(
    trabajador_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    trabajador = db.query(Trabajador).filter(Trabajador.id == trabajador_id).first()
    if not trabajador:
        raise HTTPException(status_code=404, detail="Trabajador no encontrado")
    db.delete(trabajador)
    db.commit()


# ── Asistencia ───────────────────────────────────────────────────────

@router.get("/asistencia", response_model=list[AsistenciaOut])
def get_asistencia(
    fecha: date = Query(...),
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    rows = (
        db.query(Asistencia)
        .join(Trabajador, Asistencia.trabajador_id == Trabajador.id)
        .filter(Asistencia.date == fecha)
        .order_by(Trabajador.full_name)
        .all()
    )
    return [
        AsistenciaOut(
            id=r.id,
            trabajador_id=r.trabajador_id,
            trabajador_name=r.trabajador.full_name,
            date=r.date,
            check_in_time=r.check_in_time,
            check_out_time=r.check_out_time,
            status=r.status,
            notes=r.notes,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.post("/asistencia/bulk", response_model=list[AsistenciaOut])
def bulk_mark_asistencia(
    data: AsistenciaBulkCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    results = []
    for item in data.items:
        existing = (
            db.query(Asistencia)
            .filter(
                Asistencia.trabajador_id == item.trabajador_id,
                Asistencia.date == data.date,
            )
            .first()
        )
        if existing:
            existing.check_in_time = item.check_in_time
            existing.check_out_time = item.check_out_time
            existing.status = item.status
            existing.notes = item.notes
            results.append(existing)
        else:
            new_record = Asistencia(
                trabajador_id=item.trabajador_id,
                date=data.date,
                check_in_time=item.check_in_time,
                check_out_time=item.check_out_time,
                status=item.status,
                notes=item.notes,
            )
            db.add(new_record)
            results.append(new_record)
    db.commit()
    for r in results:
        db.refresh(r)
    return [
        AsistenciaOut(
            id=r.id,
            trabajador_id=r.trabajador_id,
            trabajador_name=r.trabajador.full_name,
            date=r.date,
            check_in_time=r.check_in_time,
            check_out_time=r.check_out_time,
            status=r.status,
            notes=r.notes,
            created_at=r.created_at,
        )
        for r in results
    ]


@router.put("/asistencia/{asistencia_id}", response_model=AsistenciaOut)
def update_asistencia(
    asistencia_id: int,
    data: AsistenciaUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    record = db.query(Asistencia).filter(Asistencia.id == asistencia_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Registro de asistencia no encontrado")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(record, key, value)
    db.commit()
    db.refresh(record)
    return AsistenciaOut(
        id=record.id,
        trabajador_id=record.trabajador_id,
        trabajador_name=record.trabajador.full_name,
        date=record.date,
        check_in_time=record.check_in_time,
        check_out_time=record.check_out_time,
        status=record.status,
        notes=record.notes,
        created_at=record.created_at,
    )
