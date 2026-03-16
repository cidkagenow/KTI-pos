from datetime import date

from pydantic import BaseModel, ConfigDict


class BrandOut(BaseModel):
    id: int
    name: str
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class BrandCreate(BaseModel):
    name: str


class CategoryOut(BaseModel):
    id: int
    name: str
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class CategoryCreate(BaseModel):
    name: str


class ProductOut(BaseModel):
    id: int
    code: str
    name: str
    brand_id: int | None
    category_id: int | None
    brand_name: str | None
    category_name: str | None
    presentation: str | None
    unit_price: float
    wholesale_price: float | None
    cost_price: float | None
    min_stock: int
    comentario: str | None
    total_stock: int
    on_order_qty: int | None = None
    on_order_eta: date | None = None
    is_active: bool
    is_online: bool

    model_config = ConfigDict(from_attributes=True)


class ProductCreate(BaseModel):
    code: str
    name: str
    brand_id: int | None = None
    category_id: int | None = None
    presentation: str | None = None
    unit_price: float
    wholesale_price: float | None = None
    cost_price: float | None = None
    min_stock: int = 0
    comentario: str | None = None
    is_online: bool = False


class ProductUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    brand_id: int | None = None
    category_id: int | None = None
    presentation: str | None = None
    unit_price: float | None = None
    wholesale_price: float | None = None
    cost_price: float | None = None
    min_stock: int | None = None
    comentario: str | None = None
    is_active: bool | None = None
    is_online: bool | None = None


class ProductSearch(BaseModel):
    id: int
    code: str
    name: str
    brand_name: str | None
    presentation: str | None
    unit_price: float
    wholesale_price: float | None
    cost_price: float | None
    stock: int
    on_order_qty: int | None = None
    on_order_eta: date | None = None

    model_config = ConfigDict(from_attributes=True)
