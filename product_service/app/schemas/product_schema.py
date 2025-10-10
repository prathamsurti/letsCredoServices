from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field

class BulkPricingTierBase(BaseModel):
    min_quantity: int
    discount_percentage: Decimal

class CategoryBase(BaseModel):
    name: str

class CategoryInDB(CategoryBase):
    id: int

    class Config:
        from_attributes = True

class SupplierBase(BaseModel):
    name: str

class SupplierInDB(SupplierBase):
    id: int

    class Config:
        from_attributes = True

class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    category_id: Optional[int] = None
    supplier_id: Optional[int] = None
    base_price: Decimal
    stock_quantity: int = Field(ge=0)
    min_order_quantity: Optional[int] = Field(default=1, ge=1)
    is_active: bool = True

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    supplier_id: Optional[int] = None
    base_price: Optional[Decimal] = None
    stock_quantity: Optional[int] = Field(None, ge=0)
    min_order_quantity: Optional[int] = Field(None, ge=1)
    is_active: Optional[bool] = None

class ProductInDB(ProductBase):
    id: int
    created_at: Optional[datetime]
    category: Optional[CategoryInDB] = None
    supplier: Optional[SupplierInDB] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }