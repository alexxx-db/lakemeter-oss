"""Estimate API routes."""
from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Estimate, LineItem
from app.schemas import (
    EstimateCreate, 
    EstimateUpdate, 
    EstimateResponse, 
    EstimateListResponse
)

router = APIRouter(prefix="/estimates", tags=["estimates"])

# In-memory storage for demo mode (when database is unavailable)
_demo_estimates: dict = {}
_demo_mode = False


def _check_demo_mode(db: Session) -> bool:
    """Check if we should use demo mode (no database)."""
    global _demo_mode
    try:
        # Try a simple query to test connection
        db.execute("SELECT 1")
        _demo_mode = False
        return False
    except Exception:
        _demo_mode = True
        return True


@router.get("/", response_model=List[EstimateListResponse])
def list_estimates(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status: Optional[str] = None,
    cloud: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all estimates with optional filtering."""
    if _check_demo_mode(db):
        # Return demo data
        estimates = list(_demo_estimates.values())
        return [
            EstimateListResponse(
                estimate_id=e["estimate_id"],
                estimate_name=e["estimate_name"],
                customer_name=e.get("customer_name"),
                cloud=e.get("cloud"),
                region=e.get("region"),
                tier=e.get("tier"),
                status=e.get("status", "draft"),
                version=e.get("version", 1),
                line_item_count=len(e.get("line_items", [])),
                created_at=e.get("created_at", datetime.utcnow()),
                updated_at=e.get("updated_at", datetime.utcnow())
            )
            for e in estimates
        ][skip:skip+limit]
    
    query = db.query(
        Estimate,
        func.count(LineItem.line_item_id).label("line_item_count")
    ).outerjoin(LineItem).filter(Estimate.is_deleted == False)
    
    if status:
        query = query.filter(Estimate.status == status)
    if cloud:
        query = query.filter(Estimate.cloud == cloud)
    
    query = query.group_by(Estimate.estimate_id)
    query = query.order_by(Estimate.updated_at.desc())
    results = query.offset(skip).limit(limit).all()
    
    return [
        EstimateListResponse(
            estimate_id=est.estimate_id,
            estimate_name=est.estimate_name,
            customer_name=est.customer_name,
            cloud=est.cloud,
            region=est.region,
            tier=est.tier,
            status=est.status,
            version=est.version,
            line_item_count=count,
            created_at=est.created_at,
            updated_at=est.updated_at
        )
        for est, count in results
    ]


@router.post("/", response_model=EstimateResponse, status_code=201)
def create_estimate(
    estimate: EstimateCreate,
    db: Session = Depends(get_db)
):
    """Create a new estimate."""
    if _check_demo_mode(db):
        # Demo mode - store in memory
        new_id = str(uuid4())
        now = datetime.utcnow()
        _demo_estimates[new_id] = {
            "estimate_id": new_id,
            **estimate.model_dump(),
            "version": 1,
            "is_deleted": False,
            "created_at": now,
            "updated_at": now,
            "line_items": []
        }
        return EstimateResponse(**_demo_estimates[new_id])
    
    db_estimate = Estimate(**estimate.model_dump())
    db.add(db_estimate)
    db.commit()
    db.refresh(db_estimate)
    return db_estimate


@router.get("/{estimate_id}", response_model=EstimateResponse)
def get_estimate(
    estimate_id: UUID,
    db: Session = Depends(get_db)
):
    """Get an estimate by ID."""
    str_id = str(estimate_id)
    
    if _check_demo_mode(db):
        if str_id in _demo_estimates:
            return EstimateResponse(**_demo_estimates[str_id])
        raise HTTPException(status_code=404, detail="Estimate not found")
    
    estimate = db.query(Estimate).filter(
        Estimate.estimate_id == estimate_id,
        Estimate.is_deleted == False
    ).first()
    
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")
    
    return estimate


@router.put("/{estimate_id}", response_model=EstimateResponse)
def update_estimate(
    estimate_id: UUID,
    estimate_update: EstimateUpdate,
    db: Session = Depends(get_db)
):
    """Update an estimate."""
    str_id = str(estimate_id)
    
    if _check_demo_mode(db):
        if str_id not in _demo_estimates:
            raise HTTPException(status_code=404, detail="Estimate not found")
        
        update_data = estimate_update.model_dump(exclude_unset=True)
        _demo_estimates[str_id].update(update_data)
        _demo_estimates[str_id]["version"] += 1
        _demo_estimates[str_id]["updated_at"] = datetime.utcnow()
        return EstimateResponse(**_demo_estimates[str_id])
    
    estimate = db.query(Estimate).filter(
        Estimate.estimate_id == estimate_id,
        Estimate.is_deleted == False
    ).first()
    
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")
    
    update_data = estimate_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(estimate, field, value)
    
    estimate.version += 1
    db.commit()
    db.refresh(estimate)
    return estimate


@router.delete("/{estimate_id}", status_code=204)
def delete_estimate(
    estimate_id: UUID,
    db: Session = Depends(get_db)
):
    """Soft delete an estimate."""
    str_id = str(estimate_id)
    
    if _check_demo_mode(db):
        if str_id in _demo_estimates:
            del _demo_estimates[str_id]
        return
    
    estimate = db.query(Estimate).filter(
        Estimate.estimate_id == estimate_id,
        Estimate.is_deleted == False
    ).first()
    
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")
    
    estimate.is_deleted = True
    db.commit()


@router.post("/{estimate_id}/duplicate", response_model=EstimateResponse, status_code=201)
def duplicate_estimate(
    estimate_id: UUID,
    db: Session = Depends(get_db)
):
    """Duplicate an estimate with all its line items."""
    str_id = str(estimate_id)
    
    if _check_demo_mode(db):
        if str_id not in _demo_estimates:
            raise HTTPException(status_code=404, detail="Estimate not found")
        
        original = _demo_estimates[str_id]
        new_id = str(uuid4())
        now = datetime.utcnow()
        _demo_estimates[new_id] = {
            **original,
            "estimate_id": new_id,
            "estimate_name": f"{original['estimate_name']} (Copy)",
            "version": 1,
            "status": "draft",
            "created_at": now,
            "updated_at": now,
            "line_items": []
        }
        return EstimateResponse(**_demo_estimates[new_id])
    
    original = db.query(Estimate).filter(
        Estimate.estimate_id == estimate_id,
        Estimate.is_deleted == False
    ).first()
    
    if not original:
        raise HTTPException(status_code=404, detail="Estimate not found")
    
    # Create new estimate
    new_estimate = Estimate(
        estimate_name=f"{original.estimate_name} (Copy)",
        owner_user_id=original.owner_user_id,
        customer_sfdc_id=original.customer_sfdc_id,
        customer_name=original.customer_name,
        uco_opportunity_id=original.uco_opportunity_id,
        cloud=original.cloud,
        region=original.region,
        tier=original.tier,
        status="draft",
        template_id=original.template_id,
        original_prompt=original.original_prompt
    )
    db.add(new_estimate)
    db.flush()
    
    # Duplicate line items
    for item in original.line_items:
        new_item = LineItem(
            estimate_id=new_estimate.estimate_id,
            display_order=item.display_order,
            workload_name=item.workload_name,
            workload_type=item.workload_type,
            is_serverless=item.is_serverless,
            driver_node_type=item.driver_node_type,
            worker_node_type=item.worker_node_type,
            num_workers=item.num_workers,
            autoscale_enabled=item.autoscale_enabled,
            autoscale_min_workers=item.autoscale_min_workers,
            autoscale_max_workers=item.autoscale_max_workers,
            photon_enabled=item.photon_enabled,
            dlt_edition=item.dlt_edition,
            dlt_pipeline_mode=item.dlt_pipeline_mode,
            dbsql_warehouse_type=item.dbsql_warehouse_type,
            dbsql_warehouse_size=item.dbsql_warehouse_size,
            hours_per_day=item.hours_per_day,
            days_per_month=item.days_per_month,
            runs_per_day=item.runs_per_day,
            avg_runtime_minutes=item.avg_runtime_minutes,
            vm_pricing_tier=item.vm_pricing_tier,
            vm_payment_option=item.vm_payment_option,
            spot_percentage=item.spot_percentage,
            workload_config=item.workload_config,
            notes=item.notes
        )
        db.add(new_item)
    
    db.commit()
    db.refresh(new_estimate)
    return new_estimate


# Export demo storage for line_items route
def get_demo_estimates():
    return _demo_estimates

def is_demo_mode():
    return _demo_mode
