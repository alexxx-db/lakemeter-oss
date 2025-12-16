"""Line Item API routes."""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.models import LineItem, Estimate, User
from app.models.sharing import Sharing
from app.schemas import LineItemCreate, LineItemUpdate, LineItemResponse
from app.auth import get_current_user

router = APIRouter(prefix="/line-items", tags=["line-items"])


def _check_estimate_access(
    estimate_id: UUID,
    user: User,
    db: Session,
    require_edit: bool = False
) -> Estimate:
    """
    Check if user has access to an estimate.
    
    Args:
        estimate_id: The estimate UUID
        user: The current user
        db: Database session
        require_edit: If True, user must have edit permission
    
    Returns:
        Estimate object
    
    Raises:
        HTTPException if no access
    """
    estimate = db.query(Estimate).filter(
        Estimate.estimate_id == estimate_id,
        Estimate.is_deleted == False
    ).first()
    
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")
    
    # Check ownership
    is_owner = estimate.owner_user_id == user.user_id
    
    if is_owner:
        return estimate
    
    # Check if shared with user
    sharing = db.query(Sharing).filter(
        Sharing.estimate_id == estimate_id,
        Sharing.shared_with_user_id == user.user_id
    ).first()
    
    if not sharing:
        raise HTTPException(status_code=404, detail="Estimate not found")
    
    if require_edit and sharing.permission != "edit":
        raise HTTPException(status_code=403, detail="You don't have edit permission for this estimate")
    
    return estimate


@router.get("/estimate/{estimate_id}", response_model=List[LineItemResponse])
def list_line_items(
    estimate_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all line items for an estimate the user has access to."""
    _check_estimate_access(estimate_id, current_user, db)
    
    items = db.query(LineItem).filter(
        LineItem.estimate_id == estimate_id
    ).order_by(LineItem.display_order).all()
    
    return items


@router.post("/", response_model=LineItemResponse, status_code=201)
def create_line_item(
    line_item: LineItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new line item. User must have edit access to the estimate."""
    _check_estimate_access(line_item.estimate_id, current_user, db, require_edit=True)
    
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a line item by ID if user has access to its estimate."""
    item = db.query(LineItem).filter(
        LineItem.line_item_id == line_item_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Line item not found")
    
    _check_estimate_access(item.estimate_id, current_user, db)
    
    return item


@router.put("/{line_item_id}", response_model=LineItemResponse)
def update_line_item(
    line_item_id: UUID,
    line_item_update: LineItemUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a line item. User must have edit access to the estimate."""
    item = db.query(LineItem).filter(
        LineItem.line_item_id == line_item_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Line item not found")
    
    _check_estimate_access(item.estimate_id, current_user, db, require_edit=True)
    
    update_data = line_item_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{line_item_id}", status_code=204)
def delete_line_item(
    line_item_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a line item. User must have edit access to the estimate."""
    item = db.query(LineItem).filter(
        LineItem.line_item_id == line_item_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Line item not found")
    
    _check_estimate_access(item.estimate_id, current_user, db, require_edit=True)
    
    db.delete(item)
    db.commit()


@router.post("/reorder", status_code=200)
def reorder_line_items(
    estimate_id: UUID,
    item_ids: List[UUID],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reorder line items. User must have edit access to the estimate."""
    _check_estimate_access(estimate_id, current_user, db, require_edit=True)
    
    for index, item_id in enumerate(item_ids):
        item = db.query(LineItem).filter(
            LineItem.line_item_id == item_id,
            LineItem.estimate_id == estimate_id
        ).first()
        
        if item:
            item.display_order = index
    
    db.commit()
    return {"message": "Line items reordered successfully"}
