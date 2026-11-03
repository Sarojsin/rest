from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Ingredient(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ingredients"

    __table_args__ = (
        UniqueConstraint("restaurant_id", "name", name="uq_ingredients_restaurant_name"),
        UniqueConstraint("restaurant_id", "code", name="uq_ingredients_restaurant_code"),
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(32), nullable=True, unique=True)
    unit: Mapped[str] = mapped_column(String(32), nullable=False, default="pieces")  # kg, gram, litre, pieces
    current_stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    minimum_stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="IN_STOCK")  # IN_STOCK, LOW_STOCK, OUT_OF_STOCK
    restaurant_id: Mapped[UUID] = mapped_column(ForeignKey("restaurants.id"), nullable=False)
    supplier_id: Mapped[UUID | None] = mapped_column(ForeignKey("suppliers.id"), nullable=True)

    supplier: Mapped["Supplier"] = relationship(back_populates="ingredients")
    recipe_items: Mapped[list["RecipeIngredient"]] = relationship(back_populates="ingredient")
    stock_movements: Mapped[list["StockMovement"]] = relationship(back_populates="ingredient")


class Supplier(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "suppliers"

    __table_args__ = (
        UniqueConstraint("restaurant_id", "name", name="uq_suppliers_restaurant_name"),
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    contact_name: Mapped[str] = mapped_column(String(100), nullable=True)
    phone: Mapped[str] = mapped_column(String(32), nullable=True)
    email: Mapped[str] = mapped_column(String(120), nullable=True)
    address: Mapped[str] = mapped_column(Text, nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=True)
    state: Mapped[str] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str] = mapped_column(String(20), nullable=True)
    country: Mapped[str] = mapped_column(String(100), nullable=True)
    tax_id: Mapped[str] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=True, default=5)  # 1-5
    average_delivery_days: Mapped[int] = mapped_column(Integer, nullable=True, default=3)
    notes: Mapped[str] = mapped_column(Text, nullable=True)


class PurchaseOrder(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "purchase_orders"

    __table_args__ = (
        UniqueConstraint("restaurant_id", "code", name="uq_purchase_orders_restaurant_code"),
    )

    code: Mapped[str] = mapped_column(String(32), nullable=False)
    supplier_id: Mapped[UUID] = mapped_column(ForeignKey("suppliers.id"), nullable=False)
    restaurant_id: Mapped[UUID] = mapped_column(ForeignKey("restaurants.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")  # DRAFT, SUBMITTED, RECEIVED, CANCELLED
    total_minor: Mapped[int] = mapped_column(Integer, default=0)  # total in currency minor units
    expected_date: Mapped[datetime | None] = mapped_column(nullable=True)
    received_date: Mapped[datetime | None] = mapped_column(nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    delivered_by_membership_id: Mapped[UUID | None] = mapped_column(nullable=True)

    supplier: Mapped["Supplier"] = relationship(back_populates="purchase_orders")
    items: Mapped[list["PurchaseOrderItem"]] = relationship(back_populates="purchase_order")
    stock_movements: Mapped[list["StockMovement"]] = relationship(back_populates="purchase_order")


class PurchaseOrderItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "purchase_order_items"

    __table_args__ = (
        UniqueConstraint("purchase_order_id", "ingredient_id", name="uq_po_items_unique"),
    )

    purchase_order_id: Mapped[UUID] = mapped_column(ForeignKey("purchase_orders.id"), nullable=False)
    ingredient_id: Mapped[UUID] = mapped_column(ForeignKey("ingredients.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    total_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    received_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    purchase_order: Mapped["PurchaseOrder"] = relationship(back_populates="items")
    ingredient: Mapped["Ingredient"] = relationship(back_populates="po_items")


class RecipeIngredient(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recipe_ingredients"

    __table_args__ = (
        UniqueConstraint("ingredient_id", "menu_item_id", name="uq_recipe_ingredients_unique"),
    )

    ingredient_id: Mapped[UUID] = mapped_column(ForeignKey("ingredients.id"), nullable=False)
    menu_item_id: Mapped[UUID] = mapped_column(ForeignKey("menu_items.id"), nullable=False)
    quantity_per_serving: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_per_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    ingredient: Mapped["Ingredient"] = relationship(back_populates="recipe_items")
    menu_item: Mapped["MenuItem"] = relationship(back_populates="recipe_items")


class StockMovement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "stock_movements"

    movement_type: Mapped[str] = mapped_column(String(32), nullable=False)  # RECEIVE, ADJUST, DEDUCT, WASTE
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    new_balance: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(100), nullable=True)
    reference_id: Mapped[UUID | None] = mapped_column(ForeignKey("purchase_orders.id"), nullable=True)
    reference_type: Mapped[str] = mapped_column(String(32), nullable=True)  # PO, ORDER, ADJUST, MANUAL
    recorded_by_membership_id: Mapped[UUID] = mapped_column(ForeignKey("restaurant_memberships.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False)

    ingredient: Mapped["Ingredient"] = relationship(back_populates="stock_movements")
    purchase_order: Mapped["PurchaseOrder"] = relationship(back_populates="stock_movements")
    recorded_by: Mapped["RestaurantMembership"] = relationship(back_populates="stock_movements")