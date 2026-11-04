from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.shared.schemas import ORMModel

# ── Ingredient ──────────────────────────────────────────────────────────────

class IngredientOut(ORMModel):
    id: UUID
    name: str
    code: str | None
    unit: str
    current_stock: int
    minimum_stock: int
    status: str
    supplier_id: UUID | None
    supplier_name: str | None = None


class IngredientIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    code: str | None = Field(default=None, max_length=32)
    unit: str = Field(default="pieces", min_length=1, max_length=32)
    current_stock: int = Field(default=0, ge=0)
    minimum_stock: int = Field(default=0, ge=0)
    supplier_id: UUID | None = None


class IngredientUpdateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=120)
    code: str | None = Field(default=None, max_length=32)
    unit: str | None = Field(default=None, min_length=1, max_length=32)
    minimum_stock: int | None = Field(default=None, ge=0)
    supplier_id: UUID | None = None


# ── Supplier ────────────────────────────────────────────────────────────────

class SupplierOut(ORMModel):
    id: UUID
    name: str
    contact_name: str | None
    phone: str | None
    email: str | None
    address: str | None
    city: str | None
    state: str | None
    postal_code: str | None
    country: str | None
    tax_id: str | None
    is_active: bool
    rating: int | None
    average_delivery_days: int | None
    notes: str | None


class SupplierIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    contact_name: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
    tax_id: str | None = None
    is_active: bool = True
    rating: int | None = Field(default=None, ge=1, le=5)
    average_delivery_days: int | None = Field(default=None, ge=0)
    notes: str | None = None


# ── Purchase Order ──────────────────────────────────────────────────────────

class PurchaseOrderItemIn(BaseModel):
    ingredient_id: UUID
    quantity: int = Field(ge=1)
    unit_price_minor: int = Field(ge=0)


class PurchaseOrderItemOut(ORMModel):
    id: UUID
    ingredient_id: UUID
    ingredient_name: str | None = None
    quantity: int
    unit_price_minor: int
    total_minor: int
    received_quantity: int


class PurchaseOrderOut(ORMModel):
    id: UUID
    code: str
    status: str
    supplier_id: UUID
    supplier_name: str | None = None
    expected_date: datetime | None
    received_date: datetime | None
    notes: str | None
    total_minor: int
    items: list[PurchaseOrderItemOut] = []


class PurchaseOrderIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=32)
    supplier_id: UUID
    status: str | None = None
    expected_date: datetime | None = None
    notes: str | None = None
    items: list[PurchaseOrderItemIn] = Field(min_length=1, max_length=50)


# ── Recipe Ingredient ─────────────────────────────────────────────────────

class RecipeIngredientOut(ORMModel):
    id: UUID
    ingredient_id: UUID
    menu_item_id: UUID
    ingredient_name: str | None = None
    quantity_per_serving: int
    quantity_per_order: int
    ingredient_unit: str = "pieces"


class RecipeIngredientIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ingredient_id: UUID
    quantity_per_serving: int = Field(ge=1)
    quantity_per_order: int = Field(default=0, ge=0)


class RecipeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[RecipeIngredientIn] = Field(min_length=0, max_length=100)


# ── Stock Movement ──────────────────────────────────────────────────────────

class StockMovementOut(ORMModel):
    id: UUID
    ingredient_id: UUID
    movement_type: str
    quantity: int
    new_balance: int
    reason: str | None
    reference_type: str | None
    reference_id: UUID | None
    recorded_by: str | None = None
    created_at: datetime


class StockMovementIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ingredient_id: UUID
    movement_type: str = Field(..., pattern="^(RECEIVE|ADJUST|DEDUCT|WASTE)$")
    quantity: int
    reason: str | None = None
    reference_id: UUID | None = None
    reference_type: str | None = None  # PO, ORDER, ADJUST, MANUAL
