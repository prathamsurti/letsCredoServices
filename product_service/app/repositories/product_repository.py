from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.db.models import Product
from app.schemas import product_schema

class ProductRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, product: product_schema.ProductCreate) -> Product:
        db_product = Product(
            **product.dict(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        self.db.add(db_product)
        self.db.commit()
        self.db.refresh(db_product)
        return db_product

    def get_by_id(self, product_id: int) -> Optional[Product]:
        return self.db.query(Product).filter(Product.id == product_id).first()

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None
    ) -> List[Product]:
        query = self.db.query(Product)

        # Apply filters if provided
        if category:
            query = query.filter(Product.category == category)
        
        if is_active is not None:
            query = query.filter(Product.is_active == is_active)
        
        if search:
            search_filter = or_(
                Product.name.ilike(f"%{search}%"),
                Product.description.ilike(f"%{search}%"),
                Product.supplier.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)

        # Apply pagination
        return query.offset(skip).limit(limit).all()

    def update(self, product_id: int, product_update: product_schema.ProductUpdate) -> Optional[Product]:
        db_product = self.get_by_id(product_id)
        if not db_product:
            return None

        # Update only provided fields
        update_data = product_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_product, field, value)
        
        db_product.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(db_product)
        return db_product

    def delete(self, product_id: int) -> bool:
        db_product = self.get_by_id(product_id)
        if not db_product:
            return False
        
        self.db.delete(db_product)
        self.db.commit()
        return True