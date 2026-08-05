"""DLT calculation endpoints (Classic + Serverless)."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.validators import validate_sku_specific_discounts
from app.services.lakebase_queries import call_calculate_line_item_costs, get_product_type_for_pricing
from app.routes.calculate.helpers import build_sku_breakdown_classic, build_sku_breakdown_serverless, build_cost_params
from app.routes.calculate.discount import (
    apply_discount_to_sku_breakdown, calculate_total_discount_summary, enhance_total_cost_with_discount,
)
from app.routes.calculate.jobs import _validate_usage_params, _validate_classic_inputs, _validate_serverless_inputs
from app.routes.calculate.schemas import DLTClassicCalculationRequest, DLTServerlessCalculationRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/calculate/dlt-classic", tags=["Cost Calculation"])
def calculate_dlt_classic_cost(
    request: DLTClassicCalculationRequest,
    db: Session = Depends(get_db),
):
    has_run_params, has_hours = _validate_usage_params(request)
    if has_run_params and request.days_per_month is None:
        request.days_per_month = 30

    _validate_classic_inputs(request, db)

    try:
        params = build_cost_params(
            workload_type="DLT",
            cloud=request.cloud,
            region=request.region,
            tier=request.tier,
            photon_enabled=request.photon_enabled,
            dlt_edition=request.dlt_edition.upper(),
            driver_node_type=request.driver_node_type,
            worker_node_type=request.worker_node_type,
            num_workers=request.num_workers,
            driver_pricing_tier=request.driver_pricing_tier,
            worker_pricing_tier=request.worker_pricing_tier,
            runs_per_day=request.runs_per_day if has_run_params else 0,
            avg_runtime_minutes=request.avg_runtime_minutes if has_run_params else 0,
            days_per_month=request.days_per_month if has_run_params else 30,
            hours_per_month=int(request.hours_per_month) if has_hours and request.hours_per_month is not None else None,
            driver_payment_option=request.driver_payment_option or "NA",
            worker_payment_option=request.worker_payment_option or "NA",
        )
        row = call_calculate_line_item_costs(db, params)
        if not row:
            raise HTTPException(status_code=500, detail="No calculation result returned")

        sku_type = get_product_type_for_pricing(
            db, "DLT", False, request.photon_enabled, request.dlt_edition, None, None
        )

        sku_breakdown = build_sku_breakdown_classic(
            sku_type=sku_type,
            dbu_cost=float(row.dbu_cost_per_month or 0), dbu_quantity=float(row.dbu_per_month or 0),
            dbu_price=float(row.dbu_price or 0),
            driver_vm_cost=float(row.driver_vm_cost_per_month or 0),
            worker_vm_cost=float(row.total_worker_vm_cost_per_month or 0),
            hours_per_month=float(row.hours_per_month or 0),
            driver_vm_price_per_hour=float(row.driver_vm_cost_per_hour or 0),
            worker_vm_price_per_hour=float(row.worker_vm_cost_per_hour or 0),
            driver_pricing_tier=request.driver_pricing_tier,
            worker_pricing_tier=request.worker_pricing_tier,
            num_workers=request.num_workers,
        )

        if request.discount_config and request.discount_config.sku_specific:
            error = validate_sku_specific_discounts(request.discount_config.sku_specific, db)
            if error:
                raise HTTPException(status_code=400, detail=error["error"])
        if request.discount_config:
            sku_breakdown = apply_discount_to_sku_breakdown(sku_breakdown, request.discount_config, db)

        response_data = {
            "success": True,
            "data": {
                "workload_type": "DLT", "sku_type": sku_type,
                "configuration": {
                    "cloud": request.cloud.upper(), "region": request.region, "tier": request.tier.upper(),
                    "dlt_edition": request.dlt_edition.upper(), "photon_enabled": request.photon_enabled,
                    "driver_node_type": request.driver_node_type, "worker_node_type": request.worker_node_type,
                    "num_workers": request.num_workers,
                },
                "usage": {"hours_per_month": float(row.hours_per_month or 0)},
                "dbu_calculation": {
                    "dbu_per_hour": float(row.dbu_per_hour or 0), "dbu_per_month": float(row.dbu_per_month or 0),
                    "dbu_price": float(row.dbu_price or 0), "dbu_cost_per_month": float(row.dbu_cost_per_month or 0),
                },
                "vm_costs": {
                    "driver_vm_cost_per_hour": float(row.driver_vm_cost_per_hour or 0),
                    "worker_vm_cost_per_hour": float(row.worker_vm_cost_per_hour or 0),
                    "total_vm_cost_per_hour": float(row.total_vm_cost_per_hour or 0),
                    "vm_cost_per_month": float(row.vm_cost_per_month or 0),
                },
                "total_cost": {
                    "cost_per_month": float(row.cost_per_month or 0),
                    "breakdown": {
                        "dbu_cost": float(row.dbu_cost_per_month or 0), "vm_cost": float(row.vm_cost_per_month or 0),
                    },
                },
                "sku_breakdown": sku_breakdown,
            },
        }

        if request.discount_config:
            response_data["data"]["total_cost"] = enhance_total_cost_with_discount(
                response_data["data"]["total_cost"], sku_breakdown)
            response_data["data"]["discount_summary"] = calculate_total_discount_summary(sku_breakdown)

        return response_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating DLT Classic cost: {e}")
        return {"success": False, "error": {"code": "CALCULATION_ERROR", "message": str(e)}}


@router.post("/calculate/dlt-serverless", tags=["Cost Calculation"])
def calculate_dlt_serverless_cost(
    request: DLTServerlessCalculationRequest,
    db: Session = Depends(get_db),
):
    has_run_params, has_hours = _validate_usage_params(request)
    if has_run_params and request.days_per_month is None:
        request.days_per_month = 30

    _validate_serverless_inputs(request, db)

    try:
        params = build_cost_params(
            workload_type="DLT",
            cloud=request.cloud,
            region=request.region,
            tier=request.tier,
            serverless_enabled=True,
            photon_enabled=True,
            driver_node_type=request.driver_node_type,
            worker_node_type=request.worker_node_type,
            num_workers=request.num_workers or 0,
            runs_per_day=request.runs_per_day if has_run_params else 0,
            avg_runtime_minutes=request.avg_runtime_minutes if has_run_params else 0,
            days_per_month=request.days_per_month if has_run_params else 30,
            hours_per_month=int(request.hours_per_month) if has_hours and request.hours_per_month is not None else None,
            serverless_mode=request.serverless_mode,
        )
        row = call_calculate_line_item_costs(db, params)
        if not row:
            raise HTTPException(status_code=500, detail="No calculation result returned")

        sku_type = get_product_type_for_pricing(db, "DLT", True, False, None, None, None)

        sku_breakdown = build_sku_breakdown_serverless(
            sku_type=sku_type, dbu_cost=float(row.dbu_cost_per_month or 0),
            dbu_quantity=float(row.dbu_per_month or 0), dbu_price=float(row.dbu_price or 0),
        )

        if request.discount_config and request.discount_config.sku_specific:
            error = validate_sku_specific_discounts(request.discount_config.sku_specific, db)
            if error:
                raise HTTPException(status_code=400, detail=error["error"])
        if request.discount_config:
            sku_breakdown = apply_discount_to_sku_breakdown(sku_breakdown, request.discount_config, db)

        response_data = {
            "success": True,
            "data": {
                "workload_type": "DLT_SERVERLESS", "sku_type": sku_type,
                "configuration": {
                    "cloud": request.cloud.upper(), "region": request.region, "tier": request.tier.upper(),
                    "serverless_mode": request.serverless_mode,
                },
                "usage": {"hours_per_month": float(row.hours_per_month or 0)},
                "dbu_calculation": {
                    "dbu_per_hour": float(row.dbu_per_hour or 0), "dbu_per_month": float(row.dbu_per_month or 0),
                    "dbu_price": float(row.dbu_price or 0), "dbu_cost_per_month": float(row.dbu_cost_per_month or 0),
                },
                "total_cost": {
                    "cost_per_month": float(row.cost_per_month or 0),
                    "note": "Serverless has no VM costs",
                },
                "sku_breakdown": sku_breakdown,
            },
        }

        if request.discount_config:
            response_data["data"]["total_cost"] = enhance_total_cost_with_discount(
                response_data["data"]["total_cost"], sku_breakdown)
            response_data["data"]["discount_summary"] = calculate_total_discount_summary(sku_breakdown)

        return response_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating DLT Serverless cost: {e}")
        return {"success": False, "error": {"code": "CALCULATION_ERROR", "message": str(e)}}
