"""Seed default data: warehouse, document series, walk-in client."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.warehouse import Warehouse
from app.models.sale import DocumentSeries
from app.models.client import Client

db = SessionLocal()

if not db.query(Warehouse).first():
    db.add(Warehouse(name="ALMACEN PRINCIPAL"))
    print("Almacen creado")

if not db.query(DocumentSeries).first():
    db.add(DocumentSeries(doc_type="BOLETA", series="B001", next_number=1))
    db.add(DocumentSeries(doc_type="FACTURA", series="F001", next_number=1))
    print("Series creadas: B001, F001")

if not db.query(Client).filter(Client.is_walk_in == True).first():
    db.add(Client(doc_type="NONE", business_name="CLIENTES VARIOS", is_walk_in=True))
    print("Cliente CLIENTES VARIOS creado")

db.commit()
print("Listo!")
