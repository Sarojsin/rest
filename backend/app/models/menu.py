from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class MenuCategory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "menu_categories"

    restaurant_id: Mapped[UUID] = mapped_column(ForeignKey("restaurants.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PUBLISHED")

    items: Mapped[list["MenuItem"]] = relationship(back_populates="category")


class MenuItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "menu_items"

    restaurant_id: Mapped[UUID] = mapped_column(ForeignKey("restaurants.id"), nullable=False)
    category_id: Mapped[UUID] = mapped_column(ForeignKey("menu_categories.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    current_price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PUBLISHED")
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    image_emoji: Mapped[str] = mapped_column(String(8), default="")

    category: Mapped[MenuCategory] = relationship(back_populates="items")
