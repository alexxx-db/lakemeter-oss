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
    """Get VM costs from external API.
    
    Uses region_code format (e.g., ap-southeast-1).
    """
    client = LakemeterAPIClient(user_token=get_user_token(request))
    return await call_external_api(
        request,
        lambda: client.get_vm_costs(cloud, region, instance_type, pricing_tier, payment_option),
        "get_vm_costs"
    )


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

