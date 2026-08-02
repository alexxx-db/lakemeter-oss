"""DBSQL calculation endpoints (Classic/Pro + Serverless)."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.validators import (
    validate_cloud, validate_region, validate_tier,
    validate_warehouse_type, validate_warehouse_size,
    validate_pricing_tier, validate_payment_option,
    validate_sku_specific_discounts,
)
from app.services.lakebase_queries import call_calculate_line_item_costs, get_product_type_for_pricing
from app.routes.calculate.helpers import build_sku_breakdown_classic, build_sku_breakdown_serverless, build_cost_params
from app.routes.calculate.discount import (
    apply_discount_to_sku_breakdown, calculate_total_discount_summary, enhance_total_cost_with_discount,
)
from app.routes.calculate.jobs import _validate_usage_params
from app.routes.calculate.schemas import DBSQLClassicProCalculationRequest, DBSQLServerlessCalculationRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/calculate/dbsql-classic-pro", tags=["Cost Calculation"])
def calculate_dbsql_classic_pro_cost(
    request: DBSQLClassicProCalculationRequest,
    db: Session = Depends(get_db),
):
    has_run_params, has_hours = _validate_usage_params(request, require_runs=False)
    if has_run_params and request.days_per_month is None:
        request.days_per_month = 30

    error = validate_cloud(request.cloud)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    error = validate_region(request.cloud, request.region, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    error = validate_tier(request.cloud, request.tier, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    error = validate_warehouse_type(request.warehouse_type)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    error = validate_warehouse_size(request.cloud, request.warehouse_type, request.warehouse_size, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])

    try:
        params = build_cost_params(
            workload_type="DBSQL",
            cloud=request.cloud,
            region=request.region,
            tier=request.tier,
            driver_pricing_tier=request.driver_pricing_tier,
            worker_pricing_tier=request.worker_pricing_tier,
            days_per_month=request.days_per_month or 30,
            hours_per_month=int(request.hours_per_month) if has_hours and request.hours_per_month is not None else None,
            dbsql_warehouse_type=request.warehouse_type.upper(),
            dbsql_warehouse_size=request.warehouse_size,
            dbsql_vm_pricing_tier=request.driver_pricing_tier,
            vector_search_mode=request.warehouse_size,
            driver_payment_option=request.driver_payment_option or "NA",
            worker_payment_option=request.worker_payment_option or "NA",
        )
        row = call_calculate_line_item_costs(db, params)
        if not row:
            raise HTTPException(status_code=500, detail="No calculation result returned")

        sku_type = get_product_type_for_pricing(
            db, "DBSQL", False, False, None, request.warehouse_type, None
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
            num_workers=0,
        )

        if request.discount_config:
            if request.discount_config.sku_specific:
                error = validate_sku_specific_discounts(request.discount_config.sku_specific, db)
                if error:
                    raise HTTPException(status_code=400, detail=error["error"])
            sku_breakdown = apply_discount_to_sku_breakdown(sku_breakdown, request.discount_config, db)

        response_data = {
            "success": True,
            "data": {
                "workload_type": f"DBSQL_{request.warehouse_type.upper()}", "sku_type": sku_type,
                "configuration": {
                    "cloud": request.cloud.upper(), "region": request.region, "tier": request.tier.upper(),
                    "warehouse_type": request.warehouse_type.upper(), "warehouse_size": request.warehouse_size,
                },
                "usage": {"hours_per_month": float(row.hours_per_month or 0)},
                "dbu_calculation": {
                    "dbu_per_hour": float(row.dbu_per_hour or 0), "dbu_per_month": float(row.dbu_per_month or 0),
                    "dbu_price": float(row.dbu_price or 0), "dbu_cost_per_month": float(row.dbu_cost_per_month or 0),
                },
                "vm_costs": {
                    "driver_vm_cost_per_hour": float(row.driver_vm_cost_per_hour or 0),
                    "worker_vm_cost_per_hour": float(row.worker_vm_cost_per_hour or 0),
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
        logger.error(f"Error calculating DBSQL Classic/Pro cost: {e}")
        return {"success": False, "error": {"code": "CALCULATION_ERROR", "message": str(e)}}


@router.post("/calculate/dbsql-serverless", tags=["Cost Calculation"])
def calculate_dbsql_serverless_cost(
    request: DBSQLServerlessCalculationRequest,
    db: Session = Depends(get_db),
):
    has_run_params, has_hours = _validate_usage_params(request, require_runs=False)
    if has_run_params and request.days_per_month is None:
        request.days_per_month = 30

    error = validate_cloud(request.cloud)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    error = validate_region(request.cloud, request.region, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    error = validate_tier(request.cloud, request.tier, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])

    try:
        params = build_cost_params(
            workload_type="DBSQL",
            cloud=request.cloud,
            region=request.region,
            tier=request.tier,
            serverless_enabled=True,
            days_per_month=request.days_per_month or 30,
            hours_per_month=int(request.hours_per_month) if has_hours and request.hours_per_month is not None else None,
            dbsql_warehouse_type="SERVERLESS",
            dbsql_warehouse_size=request.warehouse_size,
            vector_search_mode=request.warehouse_size,
        )
        row = call_calculate_line_item_costs(db, params)
        if not row:
            raise HTTPException(status_code=500, detail="No calculation result returned")

        sku_type = get_product_type_for_pricing(db, "DBSQL", True, False, None, "SERVERLESS", None)

        sku_breakdown = build_sku_breakdown_serverless(
            sku_type=sku_type, dbu_cost=float(row.dbu_cost_per_month or 0),
            dbu_quantity=float(row.dbu_per_month or 0), dbu_price=float(row.dbu_price or 0),
        )

        if request.discount_config:
            sku_breakdown = apply_discount_to_sku_breakdown(sku_breakdown, request.discount_config, db)

        response_data = {
            "success": True,
            "data": {
                "workload_type": "DBSQL_SERVERLESS", "sku_type": sku_type,
                "configuration": {
                    "cloud": request.cloud.upper(), "region": request.region, "tier": request.tier.upper(),
                    "warehouse_size": request.warehouse_size,
                },
                "usage": {"hours_per_month": float(row.hours_per_month or 0)},
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
                response_data["data"]["total_cost"], sku_breakdown)
            response_data["data"]["discount_summary"] = calculate_total_discount_summary(sku_breakdown)

        return response_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating DBSQL Serverless cost: {e}")
        return {"success": False, "error": {"code": "CALCULATION_ERROR", "message": str(e)}}
