from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.models.client import Client
from app.models.user import User
from app.schemas.client import ClientOut, ClientCreate, ClientUpdate
from app.api.deps import get_current_user, require_admin

router = APIRouter()


@router.get("/search", response_model=list[ClientOut])
def search_clients(
    q: str = Query("", min_length=0),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Quick search for POS autocomplete (top 20 by business_name or doc_number)."""
    query = db.query(Client).filter(Client.is_active == True)
    if q:
        pattern = f"%{q}%"
        query = query.filter(
            or_(
                Client.business_name.ilike(pattern),
                Client.doc_number.ilike(pattern),
            )
        )
    clients = query.order_by(Client.business_name).limit(20).all()
    return [ClientOut.model_validate(c) for c in clients]


@router.get("", response_model=list[ClientOut])
def list_clients(
    search: str | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    query = db.query(Client).filter(Client.is_active == True)
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Client.business_name.ilike(pattern),
                Client.doc_number.ilike(pattern),
            )
        )
    clients = query.order_by(Client.business_name).all()
    return [ClientOut.model_validate(c) for c in clients]


@router.post("", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
def create_client(
    data: ClientCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    client = Client(**data.model_dump())
    db.add(client)
    db.commit()
    db.refresh(client)
    return ClientOut.model_validate(client)


@router.get("/{client_id}", response_model=ClientOut)
def get_client(
    client_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    client = db.query(Client).filter(Client.id == client_id).first()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado",
        )
    return ClientOut.model_validate(client)


@router.put("/{client_id}", response_model=ClientOut)
def update_client(
    client_id: int,
    data: ClientUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    client = db.query(Client).filter(Client.id == client_id).first()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado",
        )
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(client, key, value)
    db.commit()
    db.refresh(client)
    return ClientOut.model_validate(client)


@router.delete("/{client_id}", response_model=ClientOut)
def deactivate_client(
    client_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    client = db.query(Client).filter(Client.id == client_id).first()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado",
        )
    client.is_active = False
    db.commit()
    db.refresh(client)
    return ClientOut.model_validate(client)
