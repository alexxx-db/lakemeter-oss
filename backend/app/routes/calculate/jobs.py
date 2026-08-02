"""Jobs compute calculation endpoints (Classic + Serverless)."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.validators import (
    validate_cloud, validate_region, validate_tier, validate_instance_type,
    validate_pricing_tier, validate_payment_option, validate_pricing_payment_combination,
    validate_sku_specific_discounts,
)
from app.routes.calculate.helpers import get_sku_type, build_sku_breakdown_classic, build_sku_breakdown_serverless, build_cost_params
from app.routes.calculate.discount import (
    apply_discount_to_sku_breakdown, calculate_total_discount_summary, enhance_total_cost_with_discount,
)
from app.routes.calculate.schemas import JobsClassicCalculationRequest, JobsServerlessCalculationRequest
from app.services.lakebase_queries import call_calculate_line_item_costs, get_product_type_for_pricing

logger = logging.getLogger(__name__)
router = APIRouter()


def _validate_usage_params(request, require_runs=True):
    """Validate usage params. Returns (has_run_params, has_hours)."""
    if require_runs:
        has_run_params = all([
            getattr(request, 'runs_per_day', None) is not None,
            getattr(request, 'avg_runtime_minutes', None) is not None,
        ])
    else:
        has_run_params = all([
            getattr(request, 'hours_per_day', None) is not None,
        ])
    has_hours = request.hours_per_month is not None

    if not has_run_params and not has_hours:
        raise HTTPException(status_code=400, detail={
            "code": "MISSING_USAGE_PARAMETERS",
            "message": "Must provide either run-based parameters OR hours_per_month",
        })
    if has_run_params and has_hours:
        raise HTTPException(status_code=400, detail={
            "code": "CONFLICTING_USAGE_PARAMETERS",
            "message": "Cannot provide both run-based parameters and hours_per_month.",
        })
    return has_run_params, has_hours


def _validate_classic_inputs(request, db):
    """Validate common classic compute inputs."""
    error = validate_cloud(request.cloud)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    error = validate_region(request.cloud, request.region, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    error = validate_tier(request.cloud, request.tier, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    error = validate_instance_type(request.cloud, request.driver_node_type, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    error = validate_instance_type(request.cloud, request.worker_node_type, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    error = validate_pricing_tier(request.driver_pricing_tier, is_driver=True)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    error = validate_pricing_tier(request.worker_pricing_tier, is_driver=False)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    if request.driver_payment_option:
        error = validate_payment_option(request.driver_payment_option)
        if error:
            raise HTTPException(status_code=400, detail=error["error"])
    if request.worker_payment_option:
        error = validate_payment_option(request.worker_payment_option)
        if error:
            raise HTTPException(status_code=400, detail=error["error"])
    error = validate_pricing_payment_combination(request.cloud, request.driver_pricing_tier, request.driver_payment_option)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    error = validate_pricing_payment_combination(request.cloud, request.worker_pricing_tier, request.worker_payment_option)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])


def _validate_serverless_inputs(request, db):
    """Validate common serverless compute inputs."""
    error = validate_cloud(request.cloud)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    error = validate_region(request.cloud, request.region, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    error = validate_tier(request.cloud, request.tier, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])


@router.post("/calculate/jobs-classic", tags=["Cost Calculation"])
def calculate_jobs_classic_cost(
    request: JobsClassicCalculationRequest,
    db: Session = Depends(get_db),
):
    has_run_params, has_hours = _validate_usage_params(request)
    if has_run_params and request.days_per_month is None:
        request.days_per_month = 30

    _validate_classic_inputs(request, db)

    try:
        params = build_cost_params(
            workload_type="JOBS",
            cloud=request.cloud,
            region=request.region,
            tier=request.tier,
            photon_enabled=request.photon_enabled,
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
            db, "JOBS", False, request.photon_enabled, None, None, None
        )

        sku_breakdown = build_sku_breakdown_classic(
            sku_type=sku_type,
            dbu_cost=float(row.dbu_cost_per_month or 0),
            dbu_quantity=float(row.dbu_per_month or 0),
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
                "workload_type": "JOBS_CLASSIC",
                "sku_type": sku_type,
                "configuration": {
                    "cloud": request.cloud.upper(), "region": request.region, "tier": request.tier.upper(),
                    "driver_node_type": request.driver_node_type, "worker_node_type": request.worker_node_type,
                    "num_workers": request.num_workers, "photon_enabled": request.photon_enabled,
                    "driver_pricing_tier": request.driver_pricing_tier, "worker_pricing_tier": request.worker_pricing_tier,
                    "driver_payment_option": request.driver_payment_option, "worker_payment_option": request.worker_payment_option,
                },
                "usage": {
                    "runs_per_day": request.runs_per_day, "avg_runtime_minutes": request.avg_runtime_minutes,
                    "days_per_month": request.days_per_month, "hours_per_month": float(row.hours_per_month or 0),
                },
                "dbu_calculation": {
                    "dbu_per_hour": float(row.dbu_per_hour or 0), "dbu_per_month": float(row.dbu_per_month or 0),
                    "dbu_price": float(row.dbu_price or 0), "dbu_cost_per_month": float(row.dbu_cost_per_month or 0),
                },
                "vm_costs": {
                    "driver_vm_cost_per_hour": float(row.driver_vm_cost_per_hour or 0),
                    "worker_vm_cost_per_hour": float(row.worker_vm_cost_per_hour or 0),
                    "total_vm_cost_per_hour": float(row.total_vm_cost_per_hour or 0),
                    "driver_vm_cost_per_month": float(row.driver_vm_cost_per_month or 0),
                    "total_worker_vm_cost_per_month": float(row.total_worker_vm_cost_per_month or 0),
                    "vm_cost_per_month": float(row.vm_cost_per_month or 0),
                },
                "total_cost": {
                    "cost_per_month": float(row.cost_per_month or 0),
                    "breakdown": {
                        "dbu_cost": float(row.dbu_cost_per_month or 0),
                        "vm_cost": float(row.vm_cost_per_month or 0),
                    },
                },
                "sku_breakdown": sku_breakdown,
            },
        }

        if request.discount_config:
            response_data["data"]["total_cost"] = enhance_total_cost_with_discount(
                response_data["data"]["total_cost"], sku_breakdown
            )
            response_data["data"]["discount_summary"] = calculate_total_discount_summary(sku_breakdown)

        return response_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating JOBS Classic cost: {e}")
        return {"success": False, "error": {"code": "CALCULATION_ERROR", "message": str(e)}}


@router.post("/calculate/jobs-serverless", tags=["Cost Calculation"])
def calculate_jobs_serverless_cost(
    request: JobsServerlessCalculationRequest,
    db: Session = Depends(get_db),
):
    has_run_params, has_hours = _validate_usage_params(request)
    if has_run_params and request.days_per_month is None:
        request.days_per_month = 30

    _validate_serverless_inputs(request, db)

    try:
        serverless_multiplier = 2 if request.serverless_mode == "performance" else 1
        params = build_cost_params(
            workload_type="JOBS",
            cloud=request.cloud,
            region=request.region,
            tier=request.tier,
            serverless_enabled=True,
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

        sku_type = get_product_type_for_pricing(db, "JOBS", True, False, None, None, None)

        sku_breakdown = build_sku_breakdown_serverless(
            sku_type=sku_type,
            dbu_cost=float(row.dbu_cost_per_month or 0),
            dbu_quantity=float(row.dbu_per_month or 0),
            dbu_price=float(row.dbu_price or 0),
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
                "workload_type": "JOBS_SERVERLESS",
                "sku_type": sku_type,
                "configuration": {
                    "cloud": request.cloud.upper(), "region": request.region, "tier": request.tier.upper(),
                    "serverless_mode": request.serverless_mode,
                },
                "usage": {
                    "runs_per_day": request.runs_per_day, "avg_runtime_minutes": request.avg_runtime_minutes,
                    "days_per_month": request.days_per_month, "hours_per_month": float(row.hours_per_month or 0),
                },
                "dbu_calculation": {
                    "dbu_per_hour": float(row.dbu_per_hour or 0), "dbu_per_month": float(row.dbu_per_month or 0),
                    "dbu_price": float(row.dbu_price or 0), "dbu_cost_per_month": float(row.dbu_cost_per_month or 0),
                },
                "total_cost": {"cost_per_month": float(row.cost_per_month or 0)},
                "sku_breakdown": sku_breakdown,
            },
        }

        if request.discount_config:
            response_data["data"]["total_cost"] = enhance_total_cost_with_discount(
                response_data["data"]["total_cost"], sku_breakdown
            )
            response_data["data"]["discount_summary"] = calculate_total_discount_summary(sku_breakdown)

        return response_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating JOBS Serverless cost: {e}")
        return {"success": False, "error": {"code": "CALCULATION_ERROR", "message": str(e)}}
