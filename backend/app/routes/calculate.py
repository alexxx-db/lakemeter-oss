"""
Calculation API Routes

Proxies cost calculation requests to the external Lakemeter API.
For local development without external API access, falls back to local calculations.
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

from app.external_api import LakemeterAPIClient, get_user_token
from app.config import settings, log_info, log_error

router = APIRouter(prefix="/calculate", tags=["Calculations"])


# ==================== Request Models ====================

class JobsClassicRequest(BaseModel):
    cloud: str
    region: str
    tier: str
    driver_node_type: str
    worker_node_type: str
    num_workers: int
    photon_enabled: bool = False
    driver_pricing_tier: str = "on_demand"
    worker_pricing_tier: str = "spot"
    driver_payment_option: str = "NA"
    worker_payment_option: str = "NA"
    # Usage - either run-based OR direct hours
    runs_per_day: Optional[int] = None
    avg_runtime_minutes: Optional[int] = None
    days_per_month: Optional[int] = None
    hours_per_month: Optional[float] = None


class JobsServerlessRequest(BaseModel):
    cloud: str
    region: str
    tier: str
    driver_node_type: str
    worker_node_type: str
    num_workers: int
    serverless_mode: str = "standard"
    # Usage
    runs_per_day: Optional[int] = None
    avg_runtime_minutes: Optional[int] = None
    days_per_month: Optional[int] = None
    hours_per_month: Optional[float] = None


class AllPurposeClassicRequest(BaseModel):
    cloud: str
    region: str
    tier: str
    driver_node_type: str
    worker_node_type: str
    num_workers: int
    photon_enabled: bool = False
    driver_pricing_tier: str = "on_demand"
    worker_pricing_tier: str = "spot"
    driver_payment_option: str = "NA"
    worker_payment_option: str = "NA"
    # Usage
    runs_per_day: Optional[int] = None
    avg_runtime_minutes: Optional[int] = None
    days_per_month: Optional[int] = None
    hours_per_month: Optional[float] = None


class AllPurposeServerlessRequest(BaseModel):
    cloud: str
    region: str
    tier: str
    driver_node_type: str
    worker_node_type: str
    num_workers: int
    serverless_mode: str = "standard"
    # Usage
    runs_per_day: Optional[int] = None
    avg_runtime_minutes: Optional[int] = None
    days_per_month: Optional[int] = None
    hours_per_month: Optional[float] = None


class DBSQLClassicProRequest(BaseModel):
    cloud: str
    region: str
    tier: str
    warehouse_type: str  # CLASSIC or PRO
    warehouse_size: str
    num_clusters: int = 1
    vm_pricing_tier: str = "on_demand"
    vm_payment_option: str = "NA"
    # Usage
    runs_per_day: Optional[int] = None
    avg_runtime_minutes: Optional[int] = None
    days_per_month: Optional[int] = None
    hours_per_month: Optional[float] = None


class DBSQLServerlessRequest(BaseModel):
    cloud: str
    region: str
    tier: str
    warehouse_size: str
    num_clusters: int = 1
    # Usage
    runs_per_day: Optional[int] = None
    avg_runtime_minutes: Optional[int] = None
    days_per_month: Optional[int] = None
    hours_per_month: Optional[float] = None


class DLTClassicRequest(BaseModel):
    cloud: str
    region: str
    tier: str
    dlt_edition: str  # CORE, PRO, ADVANCED
    photon_enabled: bool = False
    driver_node_type: str
    worker_node_type: str
    num_workers: int
    driver_pricing_tier: str = "on_demand"
    worker_pricing_tier: str = "spot"
    driver_payment_option: str = "NA"
    worker_payment_option: str = "NA"
    # Usage
    runs_per_day: Optional[int] = None
    avg_runtime_minutes: Optional[int] = None
    days_per_month: Optional[int] = None
    hours_per_month: Optional[float] = None


class DLTServerlessRequest(BaseModel):
    cloud: str
    region: str
    tier: str
    driver_node_type: str
    worker_node_type: str
    num_workers: int
    serverless_mode: str = "standard"
    # Usage
    runs_per_day: Optional[int] = None
    avg_runtime_minutes: Optional[int] = None
    days_per_month: Optional[int] = None
    hours_per_month: Optional[float] = None


class ModelServingRequest(BaseModel):
    cloud: str
    region: str
    tier: str
    gpu_type: str
    hours_per_month: float = 730


class FMAPIDatabricksRequest(BaseModel):
    cloud: str
    region: str
    tier: str
    model: str
    rate_type: str  # input_token, output_token, provisioned_scaling, provisioned_entry
    quantity: int


class FMAPIProprietaryRequest(BaseModel):
    cloud: str
    region: str
    tier: str
    provider: str  # openai, anthropic, google
    model: str
    endpoint_type: str = "global"
    context_length: str = "all"
    rate_type: str  # input_token, output_token, cache_read, cache_write, batch_inference
    quantity: int


class VectorSearchRequest(BaseModel):
    cloud: str
    region: str
    tier: str
    mode: str = "standard"
    vector_capacity_millions: float
    hours_per_month: float = 730


class LakebaseRequest(BaseModel):
    cloud: str
    region: str
    tier: str
    cu_size: int  # 1, 2, 4, or 8
    num_nodes: int = 1  # 1-3 for HA
    hours_per_month: float = 730


# ==================== Helper ====================

async def call_external_or_error(
    request: Request,
    api_method,
    data: Dict[str, Any],
    endpoint_name: str
) -> Dict[str, Any]:
    """
    Call external API with user token, or return error if no token.
    """
    user_token = get_user_token(request)
    client = LakemeterAPIClient(user_token=user_token)
    
    try:
        log_info(f"[Calculate] Calling {endpoint_name} with data: {data}")
        result = await api_method(data)
        log_info(f"[Calculate] {endpoint_name} result success")
        return result
    except Exception as e:
        import traceback
        error_msg = str(e)
        log_error(f"[Calculate] ERROR in {endpoint_name}: {error_msg}")
        log_error(f"[Calculate] Request data was: {data}")
        if not settings.is_production:
            traceback.print_exc()
        
        # If 401, explain the auth requirement
        if "401" in error_msg:
            raise HTTPException(
                status_code=401,
                detail={
                    "code": "AUTH_REQUIRED",
                    "message": "External API requires authentication. This works when deployed to Databricks Apps.",
                    "hint": "For local development, use the local calculation fallback or deploy to Databricks Apps."
                }
            )
        
        # Other errors
        raise HTTPException(
            status_code=500,
            detail={
                "code": "API_ERROR",
                "message": f"External API call to {endpoint_name} failed: {error_msg}",
                "request_data": data
            }
        )


# ==================== Endpoints ====================

@router.post("/jobs-classic")
async def calculate_jobs_classic(request: Request, data: JobsClassicRequest):
    """Calculate JOBS classic cost via external API."""
    client = LakemeterAPIClient(user_token=get_user_token(request))
    return await call_external_or_error(
        request, client.calculate_jobs_classic, data.model_dump(exclude_none=True), "jobs-classic"
    )


@router.post("/jobs-serverless")
async def calculate_jobs_serverless(request: Request, data: JobsServerlessRequest):
    """Calculate JOBS serverless cost via external API."""
    client = LakemeterAPIClient(user_token=get_user_token(request))
    return await call_external_or_error(
        request, client.calculate_jobs_serverless, data.model_dump(exclude_none=True), "jobs-serverless"
    )


@router.post("/all-purpose-classic")
async def calculate_all_purpose_classic(request: Request, data: AllPurposeClassicRequest):
    """Calculate All-Purpose classic cost via external API."""
    client = LakemeterAPIClient(user_token=get_user_token(request))
    return await call_external_or_error(
        request, client.calculate_all_purpose_classic, data.model_dump(exclude_none=True), "all-purpose-classic"
    )


@router.post("/all-purpose-serverless")
async def calculate_all_purpose_serverless(request: Request, data: AllPurposeServerlessRequest):
    """Calculate All-Purpose serverless cost via external API."""
    client = LakemeterAPIClient(user_token=get_user_token(request))
    return await call_external_or_error(
        request, client.calculate_all_purpose_serverless, data.model_dump(exclude_none=True), "all-purpose-serverless"
    )


@router.post("/dbsql-classic-pro")
async def calculate_dbsql_classic_pro(request: Request, data: DBSQLClassicProRequest):
    """Calculate DBSQL classic/pro cost via external API."""
    client = LakemeterAPIClient(user_token=get_user_token(request))
    return await call_external_or_error(
        request, client.calculate_dbsql_classic_pro, data.model_dump(exclude_none=True), "dbsql-classic-pro"
    )


@router.post("/dbsql-serverless")
async def calculate_dbsql_serverless(request: Request, data: DBSQLServerlessRequest):
    """Calculate DBSQL serverless cost via external API."""
    client = LakemeterAPIClient(user_token=get_user_token(request))
    return await call_external_or_error(
        request, client.calculate_dbsql_serverless, data.model_dump(exclude_none=True), "dbsql-serverless"
    )


@router.post("/dlt-classic")
async def calculate_dlt_classic(request: Request, data: DLTClassicRequest):
    """Calculate DLT classic cost via external API."""
    client = LakemeterAPIClient(user_token=get_user_token(request))
    return await call_external_or_error(
        request, client.calculate_dlt_classic, data.model_dump(exclude_none=True), "dlt-classic"
    )


@router.post("/dlt-serverless")
async def calculate_dlt_serverless(request: Request, data: DLTServerlessRequest):
    """Calculate DLT serverless cost via external API."""
    client = LakemeterAPIClient(user_token=get_user_token(request))
    return await call_external_or_error(
        request, client.calculate_dlt_serverless, data.model_dump(exclude_none=True), "dlt-serverless"
    )


@router.post("/model-serving")
async def calculate_model_serving(request: Request, data: ModelServingRequest):
    """Calculate Model Serving cost via external API."""
    client = LakemeterAPIClient(user_token=get_user_token(request))
    return await call_external_or_error(
        request, client.calculate_model_serving, data.model_dump(exclude_none=True), "model-serving"
    )


@router.post("/fmapi-databricks")
async def calculate_fmapi_databricks(request: Request, data: FMAPIDatabricksRequest):
    """Calculate FMAPI Databricks cost via external API."""
    client = LakemeterAPIClient(user_token=get_user_token(request))
    return await call_external_or_error(
        request, client.calculate_fmapi_databricks, data.model_dump(exclude_none=True), "fmapi-databricks"
    )


@router.post("/fmapi-proprietary")
async def calculate_fmapi_proprietary(request: Request, data: FMAPIProprietaryRequest):
    """Calculate FMAPI Proprietary cost via external API."""
    client = LakemeterAPIClient(user_token=get_user_token(request))
    return await call_external_or_error(
        request, client.calculate_fmapi_proprietary, data.model_dump(exclude_none=True), "fmapi-proprietary"
    )


@router.post("/vector-search")
async def calculate_vector_search(request: Request, data: VectorSearchRequest):
    """Calculate Vector Search cost via external API."""
    client = LakemeterAPIClient(user_token=get_user_token(request))
    return await call_external_or_error(
        request, client.calculate_vector_search, data.model_dump(exclude_none=True), "vector-search"
    )


@router.post("/lakebase")
async def calculate_lakebase(request: Request, data: LakebaseRequest):
    """Calculate Lakebase cost via external API."""
    client = LakemeterAPIClient(user_token=get_user_token(request))
    return await call_external_or_error(
        request, client.calculate_lakebase, data.model_dump(exclude_none=True), "lakebase"
    )

