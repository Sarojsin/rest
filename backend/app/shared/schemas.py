"""Shared transport-level base schemas (no domain vocabulary)."""

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class MoneyFields(BaseModel):
    amount_minor: int
    currency_code: str


class PaginatedMeta(BaseModel):
    total: int
    limit: int
    offset: int
