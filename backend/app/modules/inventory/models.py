from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Ingredient(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ingredients"

    __table_args__ = (
        UniqueConstraint("restaurant_id", "name", name="uq_ingredients_restaurant_name"),
        UniqueConstraint("restaurant_id", "code", name="uq_ingredients_restaurant_code"),
    )

    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurants.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    unit: Mapped[str] = mapped_column(String(32), nullable=False, default="pieces")
    current_stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    minimum_stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
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

    supplier: Mapped["Supplier"] = relationship(back_populates="purchase_orders")
    items: Mapped[list["PurchaseOrderItem"]] = relationship(
        back_populates="purchase_order", cascade="all, delete-orphan"
    )
    stock_movements: Mapped[list["StockMovement"]] = relationship(
        back_populates="purchase_order"
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
    new_balance: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    reference_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("purchase_orders.id"), nullable=True
    )
    reference_type: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )  # PO, ORDER, ADJUST, MANUAL
    recorded_by_membership_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurant_memberships.id"), nullable=False
    )

    ingredient: Mapped["Ingredient"] = relationship(back_populates="stock_movements")
    purchase_order: Mapped["PurchaseOrder | None"] = relationship(
        back_populates="stock_movements"
    )

    @property
    def recorded_by(self) -> str:
        return str(self.recorded_by_membership_id)
