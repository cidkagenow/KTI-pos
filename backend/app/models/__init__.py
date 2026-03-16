# Import all models so Alembic can discover them via Base.metadata

from app.models.user import User
from app.models.client import Client
from app.models.product import Brand, Category, Product
from app.models.warehouse import Warehouse
from app.models.inventory import Inventory, InventoryMovement
from app.models.sale import DocumentSeries, Sale, SaleItem
from app.models.purchase import Supplier, PurchaseOrder, PurchaseOrderItem
from app.models.sunat import SunatDocument
from app.models.chat import ChatMessage
from app.models.trabajador import Trabajador, Asistencia
from app.models.online_order import OnlineOrder, OnlineOrderItem

__all__ = [
    "User",
    "Client",
    "Brand",
    "Category",
    "Product",
    "Warehouse",
    "Inventory",
    "InventoryMovement",
    "DocumentSeries",
    "Sale",
    "SaleItem",
    "Supplier",
    "PurchaseOrder",
    "PurchaseOrderItem",
    "SunatDocument",
    "ChatMessage",
    "Trabajador",
    "Asistencia",
    "OnlineOrder",
    "OnlineOrderItem",
]
