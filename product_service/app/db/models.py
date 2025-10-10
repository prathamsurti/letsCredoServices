from datetime import datetime
from sqlalchemy import Boolean, Column, Integer, String, Text, Numeric, ForeignKey, DateTime ,func 
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=True)
    supplier_id = Column(Integer, ForeignKey('suppliers.id'), nullable=True)
    base_price = Column(Numeric, nullable=False)
    stock_quantity = Column(Integer, nullable=False)
    min_order_quantity = Column(Integer, nullable=True)
    is_active = Column(Boolean, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    category = relationship("Category", back_populates="products")
    supplier = relationship("Supplier", back_populates="products")
    bulk_pricing_tiers = relationship("BulkPricingTier", back_populates="product")
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)

    # Relationships
    products = relationship("Product", back_populates="category")

class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)

    # Relationships
    products = relationship("Product", back_populates="supplier")

class BulkPricingTier(Base):
    __tablename__ = "bulk_pricing_tiers"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=True)
    min_quantity = Column(Integer, nullable=False)
    discount_percentage = Column(Numeric, nullable=False)

    # Relationships
    product = relationship("Product", back_populates="bulk_pricing_tiers")