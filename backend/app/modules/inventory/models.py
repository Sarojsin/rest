from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    and_,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship, foreign, remote

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Ingredient(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ingredients"

    __table_args__ = (
        UniqueConstraint("restaurant_id", "name", name="uq_ingredients_restaurant_name"),
        UniqueConstraint("restaurant_id", "code", name="uq_ingredients_restaurant_code"),
        UniqueConstraint("restaurant_id", "sku", name="uq_ingredients_restaurant_sku"),
    )

    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurants.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sku: Mapped[str | None] = mapped_column(String(64), nullable=True)
    unit: Mapped[str] = mapped_column(String(32), nullable=False, default="pieces")
    base_unit: Mapped[str] = mapped_column(String(32), nullable=False, default="pieces")
    category: Mapped[str | None] = mapped_column(String(40), nullable=True)
    unit_conversions: Mapped[dict | None] = mapped_column(
        postgresql.JSONB(astext_type=Text()), nullable=True
    )
    current_stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    minimum_stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_per_unit_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    storage_location: Mapped[str | None] = mapped_column(String(80), nullable=True)
    branch_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("branches.id"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="IN_STOCK"
    )  # IN_STOCK, LOW_STOCK, OUT_OF_STOCK
    supplier_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("suppliers.id"), nullable=True
    )

    supplier: Mapped["Supplier | None"] = relationship(back_populates="ingredients")
    recipe_items: Mapped[list["RecipeIngredient"]] = relationship(
        back_populates="ingredient", cascade="all, delete-orphan"
    )
    stock_movements: Mapped[list["StockMovement"]] = relationship(
        back_populates="ingredient"
    )
    batch_items: Mapped[list["IngredientBatch"]] = relationship(
        back_populates="ingredient", cascade="all, delete-orphan"
    )
    po_items: Mapped[list["PurchaseOrderItem"]] = relationship(
        back_populates="ingredient"
    )

    @property
    def supplier_name(self) -> str | None:
        return self.supplier.name if self.supplier else None


class Supplier(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "suppliers"

    __table_args__ = (
        UniqueConstraint("restaurant_id", "name", name="uq_suppliers_restaurant_name"),
    )

    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurants.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(120), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tax_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True, default=5)
    average_delivery_days: Mapped[int | None] = mapped_column(Integer, nullable=True, default=3)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    ingredients: Mapped[list["Ingredient"]] = relationship(back_populates="supplier")
    purchase_orders: Mapped[list["PurchaseOrder"]] = relationship(
        back_populates="supplier"
    )


class PurchaseOrder(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "purchase_orders"

    __table_args__ = (
        UniqueConstraint("restaurant_id", "code", name="uq_purchase_orders_restaurant_code"),
    )

    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurants.id"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    supplier_id: Mapped[UUID] = mapped_column(ForeignKey("suppliers.id"), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="DRAFT"
    )  # DRAFT, SUBMITTED, RECEIVED, CANCELLED
    total_minor: Mapped[int] = mapped_column(Integer, default=0)
    purchase_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expected_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    received_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivered_by_membership_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("restaurant_memberships.id"), nullable=True
    )
    bill_photo_urls: Mapped[list[str] | None] = mapped_column(
        postgresql.ARRAY(Text()), nullable=True
    )
    supplier_is_walk_in: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    supplier: Mapped["Supplier"] = relationship(back_populates="purchase_orders")
    items: Mapped[list["PurchaseOrderItem"]] = relationship(
        back_populates="purchase_order", cascade="all, delete-orphan"
    )
    stock_movements: Mapped[list["StockMovement"]] = relationship(
        back_populates="purchase_order",
        primaryjoin=(
            "and_(foreign(StockMovement.reference_id) == remote(PurchaseOrder.id), "
            "StockMovement.reference_type == 'PO')"
        ),
    )

    @property
    def supplier_name(self) -> str | None:
        return self.supplier.name if self.supplier else None


class PurchaseOrderItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "purchase_order_items"

    __table_args__ = (
        UniqueConstraint(
            "purchase_order_id", "ingredient_id", name="uq_po_items_unique"
        ),
    )

    purchase_order_id: Mapped[UUID] = mapped_column(
        ForeignKey("purchase_orders.id"), nullable=False, index=True
    )
    ingredient_id: Mapped[UUID] = mapped_column(
        ForeignKey("ingredients.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    total_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    received_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    purchase_order: Mapped["PurchaseOrder"] = relationship(back_populates="items")
    ingredient: Mapped["Ingredient"] = relationship(back_populates="po_items")

    @property
    def ingredient_name(self) -> str | None:
        return self.ingredient.name if self.ingredient else None


class RecipeIngredient(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recipe_ingredients"

    __table_args__ = (
        UniqueConstraint("ingredient_id", "menu_item_id", name="uq_recipe_ingredients_unique"),
    )

    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurants.id"), nullable=False, index=True
    )
    ingredient_id: Mapped[UUID] = mapped_column(
        ForeignKey("ingredients.id"), nullable=False
    )
    menu_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("menu_items.id"), nullable=False, index=True
    )
    quantity_per_serving: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    quantity_per_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    ingredient: Mapped["Ingredient"] = relationship(back_populates="recipe_items")

    @property
    def ingredient_name(self) -> str | None:
        return self.ingredient.name if self.ingredient else None

    @property
    def ingredient_unit(self) -> str:
        return self.ingredient.unit if self.ingredient else "pieces"


class StockMovement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "stock_movements"

    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurants.id"), nullable=False, index=True
    )
    ingredient_id: Mapped[UUID] = mapped_column(
        ForeignKey("ingredients.id"), nullable=False, index=True
    )
    movement_type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # RECEIVE, ADJUST, DEDUCT, WASTE
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_balance: Mapped[int | None] = mapped_column(Integer, nullable=True)
    new_balance: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    reference_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True), nullable=True
    )  # polymorphic: references purchase_orders, orders, etc. per reference_type
    reference_type: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )  # PO, ORDER, ADJUST, MANUAL, TRANSFER
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    branch_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("branches.id"), nullable=True, index=True
    )
    batch_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("ingredient_batches.id"), nullable=True, index=True
    )
    recorded_by_membership_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurant_memberships.id"), nullable=False
    )

    ingredient: Mapped["Ingredient"] = relationship(back_populates="stock_movements")
    purchase_order: Mapped["PurchaseOrder | None"] = relationship(
        back_populates="stock_movements",
        primaryjoin=(
            "and_(foreign(StockMovement.reference_id) == remote(PurchaseOrder.id), "
            "StockMovement.reference_type == 'PO')"
        ),
    )
    batch: Mapped["IngredientBatch | None"] = relationship(
        back_populates="stock_movements"
    )

    @property
    def recorded_by(self) -> str:
        return str(self.recorded_by_membership_id)


class IngredientBatch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Batch-level tracking for an ingredient with expiry date (FEFO support)."""

    __tablename__ = "ingredient_batches"

    __table_args__ = (
        UniqueConstraint(
            "restaurant_id",
            "ingredient_id",
            "batch_no",
            name="uq_ingredient_batches_restaurant_ingredient_batch",
        ),
    )

    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurants.id"), nullable=False, index=True
    )
    ingredient_id: Mapped[UUID] = mapped_column(
        ForeignKey("ingredients.id"), nullable=False, index=True
    )
    batch_no: Mapped[str] = mapped_column(String(64), nullable=False)
    expiry_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_per_unit_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    ingredient: Mapped["Ingredient"] = relationship(back_populates="batch_items")
    stock_movements: Mapped[list["StockMovement"]] = relationship(
        back_populates="batch"
    )

    @property
    def is_expired(self) -> bool:
        if self.expiry_date is None:
            return False
        return datetime.now(UTC) > self.expiry_date


class StockCount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Blind stock count — a snapshot of expected vs counted quantities."""

    __tablename__ = "stock_counts"

    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurants.id"), nullable=False, index=True
    )
    branch_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("branches.id"), nullable=True, index=True
    )
    count_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="DRAFT"
    )  # DRAFT, COMPLETED
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_by_membership_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurant_memberships.id"), nullable=False
    )

    items: Mapped[list["StockCountItem"]] = relationship(
        back_populates="stock_count", cascade="all, delete-orphan"
    )


class StockCountItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Single ingredient line within a stock count."""

    __tablename__ = "stock_count_items"

    __table_args__ = (
        UniqueConstraint(
            "stock_count_id",
            "ingredient_id",
            name="uq_stock_count_items_count_ingredient",
        ),
    )

    stock_count_id: Mapped[UUID] = mapped_column(
        ForeignKey("stock_counts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ingredient_id: Mapped[UUID] = mapped_column(
        ForeignKey("ingredients.id"), nullable=False, index=True
    )
    expected_qty: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    counted_qty: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    variance_qty: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    stock_count: Mapped["StockCount"] = relationship(back_populates="items")
    ingredient: Mapped["Ingredient"] = relationship()
