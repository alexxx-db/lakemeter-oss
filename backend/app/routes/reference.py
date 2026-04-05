"""
Reference Data API Routes

Proxies reference data requests to the external Lakemeter API.
Provides dropdown data for clouds, regions, instances, GPU types, FMAPI models, etc.
"""
from typing import Optional
from fastapi import APIRouter, Request, HTTPException

from app.external_api import LakemeterAPIClient, get_user_token

router = APIRouter(prefix="/reference", tags=["Reference Data"])


async def call_external_api(request: Request, api_method, endpoint_name: str):
    """Call external API with error handling."""
    user_token = get_user_token(request)
    
    if not user_token:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "AUTH_REQUIRED",
                "message": "No authentication token available.",
                "hint": "For local dev, run: databricks auth login --host <your-workspace-url>"
            }
        )
    
    client = LakemeterAPIClient(user_token=user_token)
    
    try:
        return await api_method()
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg:
            raise HTTPException(
                status_code=401,
                detail={
                    "code": "EXTERNAL_AUTH_FAILED",
                    "message": "External API authentication failed. Token may have expired.",
                    "hint": "Re-run: databricks auth login --host <your-workspace-url>"
                }
            )
        raise HTTPException(
            status_code=500,
            detail={"code": "API_ERROR", "message": f"{endpoint_name} failed: {error_msg}"}
        )


# ==================== Cloud & Region ====================
# Note: /clouds endpoint is in main.py with hardcoded values since external API doesn't have it

@router.get("/regions")
async def get_regions(request: Request, cloud: str):
    """Get regions for a cloud provider."""
    client = LakemeterAPIClient(user_token=get_user_token(request))
    return await call_external_api(
        request, 
        lambda: client.get_regions(cloud), 
        "get_regions"
    )


@router.get("/pricing-tiers")
async def get_pricing_tiers(request: Request, cloud: str):
    """Get available pricing tiers for a cloud."""
    client = LakemeterAPIClient(user_token=get_user_token(request))
    return await call_external_api(
        request,
        lambda: client.get_pricing_tiers(cloud),
        "get_pricing_tiers"
    )


# ==================== Instance Types ====================

@router.get("/instances/types")
async def get_instance_types(
    request: Request,
    cloud: str,
    region: Optional[str] = None,
    min_vcpus: Optional[int] = None,
    max_vcpus: Optional[int] = None
):
    """Get available instance types with optional filtering."""
    client = LakemeterAPIClient(user_token=get_user_token(request))
    return await call_external_api(
        request,
        lambda: client.get_instance_types(cloud, region, min_vcpus, max_vcpus),
        "get_instance_types"
    )


@router.get("/instances/families")
async def get_instance_families(request: Request):
    """Get instance family categories (compute optimized, memory optimized, etc.)."""
    client = LakemeterAPIClient(user_token=get_user_token(request))
    return await call_external_api(request, client.get_instance_families, "get_instance_families")


@router.get("/instances/vm-costs")
async def get_vm_costs(
    request: Request,
    cloud: str,
    region: str,
    instance_type: Optional[str] = None,
    pricing_tier: Optional[str] = None,
    payment_option: Optional[str] = None
):
    """Get VM costs from local DEFAULT_VM_PRICING data (no external API)."""
    from app.routes.vm_pricing import DEFAULT_VM_PRICING
    cloud_lc = cloud.lower()
    vm_prices = DEFAULT_VM_PRICING.get(cloud_lc, {})
    if not instance_type or instance_type not in vm_prices:
        return {"success": False, "data": {"pricing_options": []}}

    tiers = vm_prices[instance_type]
    pricing_options = []
    for tier_name, price in tiers.items():
        if pricing_tier and tier_name != pricing_tier:
            continue
        pricing_options.append({
            "pricing_tier": tier_name,
            "payment_option": "NA",
            "cost_per_hour": price,
        })
    # Generate reserved pricing from on-demand rate
    on_demand = tiers.get("on_demand", 0)
    for res_tier, factor in [("1yr_reserved", 0.72), ("3yr_reserved", 0.50)]:
        if res_tier not in tiers and (not pricing_tier or pricing_tier == res_tier):
            for po in ["no_upfront", "partial_upfront", "all_upfront"]:
                if payment_option and payment_option not in ("NA", po):
                    continue
                po_discount = {"no_upfront": 1.0, "partial_upfront": 0.93, "all_upfront": 0.85}
                pricing_options.append({
                    "pricing_tier": res_tier,
                    "payment_option": po,
                    "cost_per_hour": round(on_demand * factor * po_discount[po], 4),
                })
    return {
        "success": True,
        "data": {
            "cloud": cloud.upper(),
            "region": region,
            "instance_type": instance_type,
            "instance_specs": {},
            "pricing_options": pricing_options,
        },
    }


# ==================== DBSQL ====================

@router.get("/dbsql/warehouse-sizes")
async def get_dbsql_warehouse_sizes(request: Request):
    """Get DBSQL warehouse sizes."""
    client = LakemeterAPIClient(user_token=get_user_token(request))
    return await call_external_api(request, client.get_dbsql_warehouse_sizes, "get_dbsql_warehouse_sizes")


# ==================== Model Serving ====================

@router.get("/model-serving/gpu-types")
async def get_gpu_types(request: Request, cloud: str):
    """Get GPU types for model serving."""
    client = LakemeterAPIClient(user_token=get_user_token(request))
    return await call_external_api(
        request,
        lambda: client.get_gpu_types(cloud),
        "get_gpu_types"
    )


# ==================== FMAPI Models ====================

@router.get("/fmapi/databricks-models")
async def get_fmapi_databricks_models(request: Request):
    """Get available Databricks FMAPI models."""
    client = LakemeterAPIClient(user_token=get_user_token(request))
    return await call_external_api(
        request,
        client.get_fmapi_databricks_models,
        "get_fmapi_databricks_models"
    )


@router.get("/fmapi/proprietary-models")
async def get_fmapi_proprietary_models(request: Request, provider: Optional[str] = None):
    """Get available proprietary FMAPI models (OpenAI, Anthropic, Google)."""
    client = LakemeterAPIClient(user_token=get_user_token(request))
    return await call_external_api(
        request,
        lambda: client.get_fmapi_proprietary_models(provider),
        "get_fmapi_proprietary_models"
    )


# ==================== Pricing (DBU Rates for Regional Availability) ====================

@router.get("/dbu-rates")
async def get_dbu_rates(
    request: Request,
    cloud: str,
    region: str,
    tier: str
):
    """Get DBU rates from external API.
    
    Used to determine which workload types are available in a specific region.
    Returns all product types with DBU prices for the given cloud/region/tier.
    """
    client = LakemeterAPIClient(user_token=get_user_token(request))
    return await call_external_api(
        request,
        lambda: client.get_dbu_rates(cloud, region, tier),
        "get_dbu_rates"
    )


# ==================== Pricing Bundle ====================

@router.post("/pricing-bundle/regenerate")
async def regenerate_pricing_bundle():
    """
    Regenerate the static pricing bundle from Lakebase reference tables.
    
    This endpoint triggers the pricing bundle generation script which queries
    Lakebase and creates static JSON files for instant client-side calculations.
    
    Returns:
        dict: Status of the regeneration with file counts
    """
    import sys
    import os
    from pathlib import Path
    
    # Add scripts directory to path
    backend_dir = Path(__file__).parent.parent.parent
    scripts_dir = backend_dir / "scripts"
    sys.path.insert(0, str(scripts_dir))
    
    try:
        from generate_pricing_bundle import generate_all_pricing_bundles
        generate_all_pricing_bundles()
        
        # Check generated files
        pricing_dir = backend_dir / "static" / "pricing"
        files = list(pricing_dir.glob("*.json")) if pricing_dir.exists() else []
        
        return {
            "success": True,
            "message": "Pricing bundle regenerated successfully",
            "files_generated": len(files),
            "file_names": [f.name for f in files]
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": str(e),
                "message": "Failed to regenerate pricing bundle"
            }
        )


@router.get("/pricing-bundle/status")
async def get_pricing_bundle_status():
    """
    Check the status of the static pricing bundle.
    
    Returns:
        dict: Information about the pricing bundle files
    """
    from pathlib import Path
    import json
    from datetime import datetime
    
    backend_dir = Path(__file__).parent.parent.parent
    pricing_dir = backend_dir / "static" / "pricing"
    
    if not pricing_dir.exists():
        return {
            "exists": False,
            "message": "Pricing bundle not generated yet. Call POST /regenerate to create it."
        }
    
    manifest_path = pricing_dir / "manifest.json"
    if manifest_path.exists():
        with open(manifest_path) as f:
            manifest = json.load(f)
        return {
            "exists": True,
            "generated_at": manifest.get("generated_at"),
            "total_entries": manifest.get("total_entries"),
            "files": manifest.get("files", [])
        }
    
    files = list(pricing_dir.glob("*.json"))
    return {
        "exists": True,
        "files": [f.name for f in files],
        "count": len(files)
    }

