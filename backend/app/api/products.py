from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.product import Product
from backend.app.models.production_batch import ProductionBatch
from backend.app.schemas.product import ProductCreate, ProductUpdate, ProductResponse

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", response_model=List[ProductResponse])
def get_products(db: Session = Depends(get_db)):
    """Retrieve all products."""
    return db.query(Product).order_by(Product.name.asc()).all()


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Retrieve a single product by ID."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found",
        )
    return product


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    """Create a new product."""
    existing = db.query(Product).filter(Product.name.ilike(payload.name.strip())).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A product with name '{payload.name.strip()}' already exists.",
        )

    product = Product(
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, payload: ProductUpdate, db: Session = Depends(get_db)):
    """Update an existing product."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found",
        )

    if payload.name is not None:
        new_name = payload.name.strip()
        existing = (
            db.query(Product)
            .filter(Product.name.ilike(new_name), Product.id != product_id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A product with name '{new_name}' already exists.",
            )
        product.name = new_name

    if payload.description is not None:
        product.description = payload.description.strip() if payload.description else None

    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """Delete a product if not referenced by any production batch."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found",
        )

    # Check database relationship restriction
    referenced_count = db.query(ProductionBatch).filter(ProductionBatch.product_id == product_id).count()
    if referenced_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete product '{product.name}' because it is referenced by {referenced_count} production batch(es).",
        )

    db.delete(product)
    db.commit()
    return None
