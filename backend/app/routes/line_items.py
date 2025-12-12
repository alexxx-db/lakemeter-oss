"""Line Item API routes."""
from typing import List
from uuid import UUID, uuid4
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import LineItem, Estimate
from app.schemas import LineItemCreate, LineItemUpdate, LineItemResponse
from app.routes.estimates import get_demo_estimates, is_demo_mode

router = APIRouter(prefix="/line-items", tags=["line-items"])

# In-memory storage for demo mode
_demo_line_items: dict = {}


def _check_demo_mode(db: Session) -> bool:
    """Check if we should use demo mode."""
    try:
        db.execute("SELECT 1")
        return False
    except Exception:
        return True


@router.get("/estimate/{estimate_id}", response_model=List[LineItemResponse])
def list_line_items(
    estimate_id: UUID,
    db: Session = Depends(get_db)
):
    """List all line items for an estimate."""
    str_id = str(estimate_id)
    
    if _check_demo_mode(db):
        items = [item for item in _demo_line_items.values() if item.get("estimate_id") == str_id]
        return [LineItemResponse(**item) for item in sorted(items, key=lambda x: x.get("display_order", 0))]
    
    # Verify estimate exists
    estimate = db.query(Estimate).filter(
        Estimate.estimate_id == estimate_id,
        Estimate.is_deleted == False
    ).first()
    
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")
    
    items = db.query(LineItem).filter(
        LineItem.estimate_id == estimate_id
    ).order_by(LineItem.display_order).all()
    
    return items


@router.post("/", response_model=LineItemResponse, status_code=201)
def create_line_item(
    line_item: LineItemCreate,
    db: Session = Depends(get_db)
):
    """Create a new line item."""
    str_estimate_id = str(line_item.estimate_id)
    
    if _check_demo_mode(db):
        # Demo mode
        demo_estimates = get_demo_estimates()
        if str_estimate_id not in demo_estimates:
            raise HTTPException(status_code=404, detail="Estimate not found")
        
        new_id = str(uuid4())
        now = datetime.utcnow()
        
        # Get display order
        existing = [item for item in _demo_line_items.values() if item.get("estimate_id") == str_estimate_id]
        display_order = len(existing)
        
        item_data = line_item.model_dump()
        item_data["estimate_id"] = str_estimate_id
        _demo_line_items[new_id] = {
            "line_item_id": new_id,
            **item_data,
            "display_order": display_order,
            "created_at": now,
            "updated_at": now
        }
        return LineItemResponse(**_demo_line_items[new_id])
    
    # Verify estimate exists
    estimate = db.query(Estimate).filter(
        Estimate.estimate_id == line_item.estimate_id,
        Estimate.is_deleted == False
    ).first()
    
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")
    
    # Get max display order
    max_order = db.query(LineItem).filter(
        LineItem.estimate_id == line_item.estimate_id
    ).count()
    
    db_item = LineItem(**line_item.model_dump())
    if db_item.display_order == 0:
        db_item.display_order = max_order
    
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.get("/{line_item_id}", response_model=LineItemResponse)
def get_line_item(
    line_item_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a line item by ID."""
    str_id = str(line_item_id)
    
    if _check_demo_mode(db):
        if str_id in _demo_line_items:
            return LineItemResponse(**_demo_line_items[str_id])
        raise HTTPException(status_code=404, detail="Line item not found")
    
    item = db.query(LineItem).filter(
        LineItem.line_item_id == line_item_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Line item not found")
    
    return item


@router.put("/{line_item_id}", response_model=LineItemResponse)
def update_line_item(
    line_item_id: UUID,
    line_item_update: LineItemUpdate,
    db: Session = Depends(get_db)
):
    """Update a line item."""
    str_id = str(line_item_id)
    
    if _check_demo_mode(db):
        if str_id not in _demo_line_items:
            raise HTTPException(status_code=404, detail="Line item not found")
        
        update_data = line_item_update.model_dump(exclude_unset=True)
        _demo_line_items[str_id].update(update_data)
        _demo_line_items[str_id]["updated_at"] = datetime.utcnow()
        return LineItemResponse(**_demo_line_items[str_id])
    
    item = db.query(LineItem).filter(
        LineItem.line_item_id == line_item_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Line item not found")
    
    update_data = line_item_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{line_item_id}", status_code=204)
def delete_line_item(
    line_item_id: UUID,
    db: Session = Depends(get_db)
):
    """Delete a line item."""
    str_id = str(line_item_id)
    
    if _check_demo_mode(db):
        if str_id in _demo_line_items:
            del _demo_line_items[str_id]
        return
    
    item = db.query(LineItem).filter(
        LineItem.line_item_id == line_item_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Line item not found")
    
    db.delete(item)
    db.commit()


@router.post("/reorder", status_code=200)
def reorder_line_items(
    estimate_id: UUID,
    item_ids: List[UUID],
    db: Session = Depends(get_db)
):
    """Reorder line items for an estimate."""
    str_estimate_id = str(estimate_id)
    
    if _check_demo_mode(db):
        for index, item_id in enumerate(item_ids):
            str_item_id = str(item_id)
            if str_item_id in _demo_line_items and _demo_line_items[str_item_id].get("estimate_id") == str_estimate_id:
                _demo_line_items[str_item_id]["display_order"] = index
        return {"message": "Line items reordered successfully"}
    
    for index, item_id in enumerate(item_ids):
        item = db.query(LineItem).filter(
            LineItem.line_item_id == item_id,
            LineItem.estimate_id == estimate_id
        ).first()
        
        if item:
            item.display_order = index
    
    db.commit()
    return {"message": "Line items reordered successfully"}


# Export demo storage
def get_demo_line_items():
    return _demo_line_items
