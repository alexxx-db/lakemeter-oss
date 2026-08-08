"""Live FinOps Actuals API — UC gold via SQL warehouse (ADR-012)."""
from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.databricks_auth import get_current_user, require_authenticated
from app.database import get_db
from app.models.estimate import Estimate
from app.models.line_item import LineItem
from app.models.sharing import Sharing
from app.models.user import User
from app.services import finops as finops_svc

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/finops",
    tags=["FinOps"],
    dependencies=[Depends(require_authenticated)],
)


def _estimate_for_user(estimate_id: UUID, user: User, db: Session) -> Estimate:
    estimate = (
        db.query(Estimate)
        .filter(Estimate.estimate_id == estimate_id, Estimate.is_deleted == False)
        .first()
    )
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")
    is_owner = estimate.owner_user_id == user.user_id
    is_shared = (
        db.query(Sharing)
        .filter(
            Sharing.estimate_id == estimate_id,
            Sharing.shared_with_user_id == user.user_id,
        )
        .first()
        is not None
    )
    if not is_owner and not is_shared:
        raise HTTPException(status_code=404, detail="Estimate not found")
    return estimate


@router.get("/metadata")
def get_finops_metadata():
    """Freshness / build metadata from finops_run_metadata."""
    data = finops_svc.fetch_metadata()
    return {"success": True, "data": data}


@router.get("/summary")
def get_finops_summary(
    days: int = Query(30, ge=1, le=730, description="Lookback days"),
    workspace_id: Optional[str] = Query(None, description="Optional workspace filter"),
):
    """Daily trend + product mix (list cost USD)."""
    data = finops_svc.fetch_summary(days=days, workspace_id=workspace_id)
    return {"success": True, "data": data}


@router.get("/top-skus")
def get_finops_top_skus(
    days: int = Query(30, ge=1, le=730),
    limit: int = Query(25, ge=1, le=100),
    workspace_id: Optional[str] = Query(None),
):
    """Top SKUs by list cost for the Actuals drivers table."""
    data = finops_svc.fetch_top_skus(
        days=days, limit=limit, workspace_id=workspace_id
    )
    return {"success": True, "data": data}


@router.get("/tags/{estimate_id}")
def get_finops_tags(
    estimate_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Suggested custom_tags for attributing usage to this estimate (P2)."""
    _estimate_for_user(estimate_id, current_user, db)
    line_items = (
        db.query(LineItem)
        .filter(LineItem.estimate_id == estimate_id)
        .order_by(LineItem.display_order)
        .all()
    )
    data = finops_svc.build_tag_pack(str(estimate_id), line_items)
    return {"success": True, "data": data}


@router.get("/variance/{estimate_id}")
def get_finops_variance(
    estimate_id: UUID,
    days: int = Query(30, ge=1, le=730),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Plan (Lakebase line items) vs tagged list actuals (UC gold)."""
    estimate = _estimate_for_user(estimate_id, current_user, db)
    line_items = (
        db.query(LineItem)
        .filter(LineItem.estimate_id == estimate_id)
        .order_by(LineItem.display_order)
        .all()
    )
    planned_monthly = sum(
        finops_svc.planned_monthly_from_response(li.cost_calculation_response)
        for li in line_items
    )
    actuals = finops_svc.fetch_estimate_actuals(str(estimate_id), days=days)
    data = finops_svc.build_variance(
        estimate_id=str(estimate_id),
        estimate_name=estimate.estimate_name,
        planned_monthly_usd=planned_monthly,
        days=days,
        actuals=actuals,
    )
    data["line_item_count"] = len(line_items)
    data["line_items_with_plan"] = sum(
        1
        for li in line_items
        if finops_svc.planned_monthly_from_response(li.cost_calculation_response) > 0
    )
    return {"success": True, "data": data}
