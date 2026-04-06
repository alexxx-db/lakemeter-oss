"""FMAPI calculation endpoints (Databricks + Proprietary token-based pricing)."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.validators import (
    validate_cloud, validate_region, validate_tier, validate_sku_specific_discounts,
)
from app.services.lakebase_queries import call_calculate_line_item_costs, get_product_type_for_pricing
from app.routes.calculate.helpers import build_sku_breakdown_serverless
from app.routes.calculate.discount import (
    apply_discount_to_sku_breakdown, calculate_total_discount_summary, enhance_total_cost_with_discount,
)
from app.routes.calculate.schemas import FMAPIDatabricksCalculationRequest, FMAPIProprietaryCalculationRequest

logger = logging.getLogger(__name__)
router = APIRouter()


def _build_fmapi_line_items(db, request, workload_type, provider=None, endpoint_type="global", context_length="all"):
    """Build line items for each token type (input, output, provisioned)."""
    line_items = []

    token_types = []
    if request.input_tokens_per_month and request.input_tokens_per_month > 0:
        token_types.append(("input_token", request.input_tokens_per_month))
    if request.output_tokens_per_month and request.output_tokens_per_month > 0:
        token_types.append(("output_token", request.output_tokens_per_month))
    if getattr(request, 'provisioned_hours_per_month', None) and request.provisioned_hours_per_month > 0:
        token_types.append(("provisioned_scaling", request.provisioned_hours_per_month))

    if not token_types:
        raise HTTPException(status_code=400, detail="Must provide at least one token quantity (input, output, or provisioned)")

    for rate_type, quantity in token_types:
        params = {
            "p1": workload_type, "p2": request.cloud.upper(), "p3": request.region, "p4": request.tier.upper(),
            "p5": True, "p6": False, "p7": None,
            "p8": None, "p9": None, "p10": 0,
            "p11": "on_demand", "p12": "on_demand",
            "p13": 0, "p14": 0, "p15": 30, "p16": None,
            "p17": "standard", "p18": None, "p19": None, "p20": 1,
            "p21": "on_demand", "p22": None, "p23": 0, "p24": None,
            "p25": request.model, "p26": provider,
            "p27": endpoint_type, "p28": context_length,
            "p29": rate_type, "p30": quantity,
            "p31": 0, "p32": 1,
            "p33": "NA", "p34": "NA", "p35": "NA",
        }
        row = call_calculate_line_item_costs(db, params)
        if not row:
            raise HTTPException(status_code=500, detail=f"No calculation result for rate_type={rate_type}")

        is_token = rate_type in ("input_token", "output_token")
        dbu_quantity = quantity / 1_000_000 if is_token else quantity

        line_items.append({
            "rate_type": rate_type,
            "quantity": quantity,
            "dbu_quantity": round(dbu_quantity, 6),
            "dbu_price": float(row.dbu_price or 0),
            "dbu_per_hour": float(row.dbu_per_hour or 0),
            "cost": float(row.cost_per_month or 0),
            "unit": "million_tokens" if is_token else "hours",
        })

    return line_items


@router.post("/calculate/fmapi-databricks", tags=["Cost Calculation"])
def calculate_fmapi_databricks_cost(
    request: FMAPIDatabricksCalculationRequest,
    db: Session = Depends(get_db),
):
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
        line_items = _build_fmapi_line_items(db, request, "FMAPI_DATABRICKS")

        sku_type = get_product_type_for_pricing(db, "FMAPI_DATABRICKS", True, False, None, None, None)
        total_cost = sum(item["cost"] for item in line_items)

        sku_breakdown = []
        for item in line_items:
            if item["cost"] > 0:
                sku_breakdown.append({
                    "type": "dbu",
                    "sku": sku_type or "SERVERLESS_REAL_TIME_INFERENCE",
                    "cost": round(item["cost"], 2),
                    "qty": round(item["dbu_quantity"], 6),
                    "usage_unit": item["unit"],
                    "unit_price_before_discount": round(item["dbu_price"], 6),
                    "rate_type": item["rate_type"],
                })

        if request.discount_config:
            if request.discount_config.sku_specific:
                error = validate_sku_specific_discounts(request.discount_config.sku_specific, db)
                if error:
                    raise HTTPException(status_code=400, detail=error["error"])
            sku_breakdown = apply_discount_to_sku_breakdown(sku_breakdown, request.discount_config, db)

        response_data = {
            "success": True,
            "data": {
                "workload_type": "FMAPI_DATABRICKS", "sku_type": sku_type,
                "configuration": {
                    "cloud": request.cloud.upper(), "region": request.region, "tier": request.tier.upper(),
                    "model": request.model,
                },
                "line_items": line_items,
                "total_cost": {"cost_per_month": round(total_cost, 2)},
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
        logger.error(f"Error calculating FMAPI Databricks cost: {e}")
        return {"success": False, "error": {"code": "CALCULATION_ERROR", "message": str(e)}}


@router.post("/calculate/fmapi-proprietary", tags=["Cost Calculation"])
def calculate_fmapi_proprietary_cost(
    request: FMAPIProprietaryCalculationRequest,
    db: Session = Depends(get_db),
):
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
        line_items = _build_fmapi_line_items(
            db, request, "FMAPI_PROPRIETARY",
            provider=request.provider,
            endpoint_type=request.endpoint_type,
            context_length=request.context_length or "all",
        )

        sku_type = get_product_type_for_pricing(
            db, "FMAPI_PROPRIETARY", True, False, None, None, request.provider
        )
        total_cost = sum(item["cost"] for item in line_items)

        sku_breakdown = []
        for item in line_items:
            if item["cost"] > 0:
                sku_breakdown.append({
                    "type": "dbu",
                    "sku": sku_type or f"{request.provider.upper()}_MODEL_SERVING",
                    "cost": round(item["cost"], 2),
                    "qty": round(item["dbu_quantity"], 6),
                    "usage_unit": item["unit"],
                    "unit_price_before_discount": round(item["dbu_price"], 6),
                    "rate_type": item["rate_type"],
                })

        if request.discount_config:
            if request.discount_config.sku_specific:
                error = validate_sku_specific_discounts(request.discount_config.sku_specific, db)
                if error:
                    raise HTTPException(status_code=400, detail=error["error"])
            sku_breakdown = apply_discount_to_sku_breakdown(sku_breakdown, request.discount_config, db)

        response_data = {
            "success": True,
            "data": {
                "workload_type": "FMAPI_PROPRIETARY", "sku_type": sku_type,
                "configuration": {
                    "cloud": request.cloud.upper(), "region": request.region, "tier": request.tier.upper(),
                    "provider": request.provider, "model": request.model,
                    "endpoint_type": request.endpoint_type,
                    "context_length": request.context_length,
                },
                "line_items": line_items,
                "total_cost": {"cost_per_month": round(total_cost, 2)},
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
        logger.error(f"Error calculating FMAPI Proprietary cost: {e}")
        return {"success": False, "error": {"code": "CALCULATION_ERROR", "message": str(e)}}
