from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.product_repository import ProductRepository
from app.schemas import product_schema
from app.api.v1.dependencies import get_current_user

router = APIRouter()

@router.post(
    "/products",
    response_model=product_schema.ProductInDB,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_current_user)]
)
def create_product(
    product: product_schema.ProductCreate,
    db: Session = Depends(get_db)
):
    """Create a new product."""
    repository = ProductRepository(db)
    return repository.create(product)

@router.get(
    "/products",
    response_model=List[product_schema.ProductInDB],
    dependencies=[Depends(get_current_user)]
)
def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    category: Optional[str] = None,
    status: Optional[bool] = Query(None, alias="is_active"),
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Retrieve a list of products with optional filtering."""
    repository = ProductRepository(db)
    return repository.get_all(
        skip=skip,
        limit=limit,
        category=category,
        is_active=status,
        search=search
    )

@router.get(
    "/products/{product_id}",
    response_model=product_schema.ProductInDB,
    dependencies=[Depends(get_current_user)]
)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Retrieve a single product by ID."""
    repository = ProductRepository(db)
    product = repository.get_by_id(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    return product

@router.patch(
    "/products/{product_id}",
    response_model=product_schema.ProductInDB,
    dependencies=[Depends(get_current_user)]
)
def update_product(
    product_id: int,
    product_update: product_schema.ProductUpdate,
    db: Session = Depends(get_db)
):
    """Update a product."""
    repository = ProductRepository(db)
    updated_product = repository.update(product_id, product_update)
    if not updated_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    return updated_product

@router.delete(
    "/products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_user)]
)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """Delete a product."""
    repository = ProductRepository(db)
    if not repository.delete(product_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    return None