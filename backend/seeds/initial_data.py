"""Seed initial data for KTI POS."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import SessionLocal, engine, Base
from app.models import *
from app.utils.security import hash_password


def seed():
    db = SessionLocal()
    try:
        # Create tables if they don't exist
        Base.metadata.create_all(bind=engine)

        # Admin user
        if not db.query(User).filter(User.username == "admin").first():
            admin = User(
                username="admin",
                password_hash=hash_password("admin123"),
                full_name="Administrador",
                role="ADMIN",
            )
            db.add(admin)
            print("Created admin user (admin/admin123)")

        # Sales user
        if not db.query(User).filter(User.username == "ventas1").first():
            ventas = User(
                username="ventas1",
                password_hash=hash_password("ventas123"),
                full_name="Vendedor 1",
                role="VENTAS",
            )
            db.add(ventas)
            print("Created ventas user (ventas1/ventas123)")

        # Walk-in client
        if not db.query(Client).filter(Client.is_walk_in == True).first():
            walk_in = Client(
                doc_type="NONE",
                business_name="CLIENTES VARIOS",
                is_walk_in=True,
            )
            db.add(walk_in)
            print("Created walk-in client (CLIENTES VARIOS)")

        # Default warehouse
        if not db.query(Warehouse).filter(Warehouse.name == "ALMACEN PRINCIPAL").first():
            warehouse = Warehouse(name="ALMACEN PRINCIPAL")
            db.add(warehouse)
            print("Created default warehouse (ALMACEN PRINCIPAL)")

        # Document series
        series_data = [
            ("BOLETA", "B001"),
            ("BOLETA", "B005"),
            ("FACTURA", "F001"),
        ]
        for doc_type, series in series_data:
            if not db.query(DocumentSeries).filter(
                DocumentSeries.doc_type == doc_type,
                DocumentSeries.series == series,
            ).first():
                ds = DocumentSeries(doc_type=doc_type, series=series)
                db.add(ds)
                print(f"Created document series {doc_type} {series}")

        # Sample brands
        brand_names = ["CHEVRON", "LYS", "MOBIL", "CASTROL", "BOSCH", "NGK", "DENSO"]
        for name in brand_names:
            if not db.query(Brand).filter(Brand.name == name).first():
                db.add(Brand(name=name))
        print("Created sample brands")

        # Sample categories
        cat_names = ["ACEITES", "FILTROS", "BUJIAS", "FRENOS", "SUSPENSION", "ELECTRICO"]
        for name in cat_names:
            if not db.query(Category).filter(Category.name == name).first():
                db.add(Category(name=name))
        print("Created sample categories")

        db.commit()
        print("\nSeed data complete!")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
