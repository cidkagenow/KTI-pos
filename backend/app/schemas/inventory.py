from datetime import datetime

from pydantic import BaseModel, ConfigDict


class InventoryOut(BaseModel):
    id: int
    product_id: int
    product_code: str
    product_name: str
    warehouse_id: int
    warehouse_name: str
    quantity: int

    model_config = ConfigDict(from_attributes=True)


class InventoryAdjust(BaseModel):
    product_id: int
    warehouse_id: int
    new_quantity: int
    notes: str | None = None


class InventoryTransfer(BaseModel):
    product_id: int
    from_warehouse_id: int
    to_warehouse_id: int
    quantity: int


class MovementOut(BaseModel):
    id: int
    product_id: int
    product_name: str
    warehouse_id: int
    warehouse_name: str
    movement_type: str
    quantity: int
    reference_type: str | None
    reference_id: int | None
    notes: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
