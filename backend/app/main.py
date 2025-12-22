"""FastAPI main application entry point."""
import os
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings, setup_logging, log_info, log_warning, log_error
from app.database import get_db
from app.routes import (
    estimates_router,
    line_items_router,
    workload_types_router,
    users_router,
    export_router,
    vm_pricing_router,
    salesforce_router,
    calculate_router,
    reference_router
)

# Initialize logging based on environment
setup_logging()

# Create FastAPI application
# redirect_slashes=False prevents automatic redirects that break CORS
# Disable docs in production for cleaner deployment
app = FastAPI(
    title="Lakemeter API",
    description="Databricks Pricing Calculator API - Estimate and manage Databricks workload costs",
    version="1.0.0",
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    redirect_slashes=False
)

# Log startup info
log_info(f"Starting Lakemeter API (environment: {settings.environment})")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(estimates_router, prefix="/api/v1")
app.include_router(line_items_router, prefix="/api/v1")
app.include_router(workload_types_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(export_router, prefix="/api/v1")
app.include_router(vm_pricing_router, prefix="/api/v1")
app.include_router(salesforce_router, prefix="/api/v1")
app.include_router(calculate_router, prefix="/api/v1")
app.include_router(reference_router, prefix="/api/v1")


@app.get("/api")
def api_root():
    """API root endpoint."""
    return {
        "name": "Lakemeter API",
        "version": "1.0.0",
        "description": "Databricks Pricing Calculator API"
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/api/v1/debug/headers")
def debug_headers(request: Request):
    """Debug endpoint to see what headers Databricks Apps sends."""
    from app.auth.databricks_auth import debug_headers as get_debug_headers
    return get_debug_headers(request)


@app.get("/api/v1/debug/external-api")
async def debug_external_api(request: Request):
    """Debug endpoint to check external API authentication."""
    from app.external_api import get_user_token, get_sp_token, get_cli_token, ACCESS_TOKEN_HEADER
    
    result = {
        "x_forwarded_access_token_present": ACCESS_TOKEN_HEADER in request.headers,
        "sp_token_available": bool(get_sp_token()),
        "cli_token_available": bool(get_cli_token()),
        "final_token_available": bool(get_user_token(request)),
    }
    
    # Try to make a real calculation API call to test
    try:
        from app.external_api import LakemeterAPIClient
        client = LakemeterAPIClient(user_token=get_user_token(request))
        # Test with a simple calculation endpoint
        test_result = await client.calculate_lakebase({
            "cloud": "AWS",
            "region": "us-east-1",
            "tier": "PREMIUM",
            "cu_size": 4,
            "num_nodes": 2,
            "hours_per_month": 730
        })
        result["external_api_test"] = "SUCCESS"
        result["test_cost"] = test_result.get("data", {}).get("total_cost", {}).get("cost_per_month", "N/A")
    except Exception as e:
        result["external_api_test"] = f"FAILED: {str(e)}"
    
    return result


@app.get("/api/v1/debug/database")
def debug_database():
    """Debug endpoint to check database connection status."""
    import os
    import uuid
    from app.auth.token_manager import token_manager
    
    result = {
        "environment_vars": {
            "DATABRICKS_HOST": os.getenv("DATABRICKS_HOST", "NOT SET"),
            "DATABRICKS_SECRETS_SCOPE": os.getenv("DATABRICKS_SECRETS_SCOPE", "NOT SET"),
            "LAKEBASE_INSTANCE_NAME": os.getenv("LAKEBASE_INSTANCE_NAME", "NOT SET"),
            "DB_HOST": os.getenv("DB_HOST", "NOT SET"),
            "DB_USER": os.getenv("DB_USER", "NOT SET"),
            "DB_NAME": os.getenv("DB_NAME", "NOT SET"),
        },
        "token_manager_status": "NOT INITIALIZED",
        "workspace_client_status": "NOT INITIALIZED",
        "sp_credentials_status": "NOT FETCHED",
        "token_status": "NO TOKEN",
        "token_error": None,
        "database_status": "NOT CONNECTED",
    }
    
    if token_manager:
        result["token_manager_status"] = "INITIALIZED"
        
        if token_manager._workspace_client:
            result["workspace_client_status"] = "INITIALIZED"
        
        if token_manager._sp_client_id and token_manager._sp_client_secret:
            result["sp_credentials_status"] = "FETCHED"
            result["sp_client_id_preview"] = token_manager._sp_client_id[:8] + "..." if token_manager._sp_client_id else None
        
        # Try to generate token and capture error
        try:
            from databricks.sdk import WorkspaceClient
            sp_client = WorkspaceClient(
                host=token_manager.databricks_host,
                client_id=token_manager._sp_client_id,
                client_secret=token_manager._sp_client_secret
            )
            credential = sp_client.database.generate_database_credential(
                request_id=str(uuid.uuid4()),
                instance_names=[token_manager.lakebase_instance_name]
            )
            if credential and credential.token:
                result["token_status"] = f"GENERATED (length: {len(credential.token)})"
                token_manager._token = credential.token
        except Exception as e:
            result["token_status"] = "GENERATION FAILED"
            result["token_error"] = str(e)
        
        # Try to test database connection
        try:
            from app.database import engine, refresh_engine
            
            # If engine is None, try to refresh it now that we have a token
            if engine is None:
                result["database_status"] = "ENGINE IS NONE - attempting refresh..."
                try:
                    refresh_engine()
                    from app.database import engine as new_engine
                    if new_engine:
                        from sqlalchemy import text
                        with new_engine.connect() as conn:
                            conn.execute(text("SELECT 1"))
                        result["database_status"] = "CONNECTED (after refresh)"
                except Exception as refresh_err:
                    result["database_status"] = f"REFRESH FAILED: {str(refresh_err)}"
            else:
                from sqlalchemy import text
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                result["database_status"] = "CONNECTED"
        except Exception as e:
            result["database_status"] = f"ERROR: {str(e)}"
    
    return result


# Reference data endpoints
from fastapi import Depends
from sqlalchemy.orm import Session
from sqlalchemy import distinct
from app.database import get_db
from app.models.sku_region_map import SKURegionMap

# Default cloud providers for fallback
DEFAULT_CLOUD_PROVIDERS = [
    {"id": "aws", "name": "Amazon Web Services", "regions": [
        {"id": "us-east-1", "name": "US East (N. Virginia)"},
        {"id": "us-east-2", "name": "US East (Ohio)"},
        {"id": "us-west-1", "name": "US West (N. California)"},
        {"id": "us-west-2", "name": "US West (Oregon)"},
        {"id": "eu-west-1", "name": "Europe (Ireland)"},
        {"id": "eu-west-2", "name": "Europe (London)"},
        {"id": "eu-central-1", "name": "Europe (Frankfurt)"},
        {"id": "ap-southeast-1", "name": "Asia Pacific (Singapore)"},
        {"id": "ap-southeast-2", "name": "Asia Pacific (Sydney)"},
        {"id": "ap-northeast-1", "name": "Asia Pacific (Tokyo)"},
    ]},
    {"id": "azure", "name": "Microsoft Azure", "regions": [
        {"id": "eastus", "name": "East US"},
        {"id": "eastus2", "name": "East US 2"},
        {"id": "westus", "name": "West US"},
        {"id": "westus2", "name": "West US 2"},
        {"id": "westeurope", "name": "West Europe"},
        {"id": "northeurope", "name": "North Europe"},
        {"id": "uksouth", "name": "UK South"},
        {"id": "southeastasia", "name": "Southeast Asia"},
        {"id": "australiaeast", "name": "Australia East"},
    ]},
    {"id": "gcp", "name": "Google Cloud Platform", "regions": [
        {"id": "us-central1", "name": "Iowa"},
        {"id": "us-east1", "name": "South Carolina"},
        {"id": "us-east4", "name": "Northern Virginia"},
        {"id": "us-west1", "name": "Oregon"},
        {"id": "europe-west1", "name": "Belgium"},
        {"id": "europe-west2", "name": "London"},
        {"id": "asia-southeast1", "name": "Singapore"},
        {"id": "australia-southeast1", "name": "Sydney"},
    ]},
]

CLOUD_DISPLAY_NAMES = {
    "AWS": "Amazon Web Services",
    "AZURE": "Microsoft Azure",
    "GCP": "Google Cloud Platform"
}


def _format_region_name(sku_region: str) -> str:
    """Convert SKU region like 'US_EAST_N_VIRGINIA' to 'US East (N. Virginia)'."""
    # First, title case the whole string
    name = sku_region.replace("_", " ").title()
    
    # Keep common abbreviations in uppercase
    abbreviations = ["Us", "Uk", "Ap", "Eu", "Uae", "Sa", "Me", "Ca"]
    for abbr in abbreviations:
        name = name.replace(abbr + " ", abbr.upper() + " ")
        # Also handle at start of string
        if name.startswith(abbr + " "):
            name = abbr.upper() + name[len(abbr):]
    
    return name


@app.get("/api/v1/reference/clouds")
def get_cloud_providers(db: Session = Depends(get_db)):
    """Get available cloud providers with regions from Lakebase."""
    try:
        # Get all cloud/region combinations from the SKU region map
        results = db.query(
            SKURegionMap.cloud,
            SKURegionMap.sku_region,
            SKURegionMap.region_code
        ).order_by(SKURegionMap.cloud, SKURegionMap.sku_region).all()
        
        if results:
            # Group by cloud provider
            cloud_regions = {}
            for row in results:
                cloud = row.cloud.upper()
                if cloud not in cloud_regions:
                    cloud_regions[cloud] = []
                cloud_regions[cloud].append({
                    "id": row.region_code,  # e.g., "us-east-1"
                    "name": _format_region_name(row.sku_region)  # e.g., "Us East N Virginia"
                })
            
            # Build response with consistent cloud order
            providers = []
            for cloud_key in ["AWS", "AZURE", "GCP"]:
                if cloud_key in cloud_regions:
                    providers.append({
                        "id": cloud_key.lower(),
                        "name": CLOUD_DISPLAY_NAMES.get(cloud_key, cloud_key),
                        "regions": cloud_regions[cloud_key]
                    })
            
            return providers
    except Exception as e:
        log_warning(f"Could not fetch cloud providers from database: {e}")
    
    # Return default if database query fails
    return DEFAULT_CLOUD_PROVIDERS


@app.get("/api/v1/regions")
def get_regions(cloud: str, db: Session = Depends(get_db)):
    """Get available regions for a cloud provider from Lakebase.
    
    Queries the SKU region map table directly.
    
    Returns regions in the format:
    {
        "success": true,
        "data": {
            "cloud": "AWS",
            "count": 17,
            "regions": [{"region_code": "us-east-1", "sku_region": "US_EAST_N_VIRGINIA"}, ...]
        }
    }
    """
    try:
        # Get regions from SKU region map in Lakebase
        results = db.query(
            SKURegionMap.region_code,
            SKURegionMap.sku_region
        ).filter(
            SKURegionMap.cloud == cloud.upper()
        ).order_by(SKURegionMap.sku_region).all()
        
        regions = [
            {
                "region_code": row.region_code,
                "sku_region": row.sku_region
            }
            for row in results
        ]
        
        return {
            "success": True,
            "data": {
                "cloud": cloud.upper(),
                "count": len(regions),
                "regions": regions
            }
        }
    except Exception as e:
        log_error(f"Error fetching regions from Lakebase: {e}")
        return {
            "success": False,
            "data": {
                "cloud": cloud.upper(),
                "count": 0,
                "regions": []
            }
        }


@app.get("/api/v1/reference/tiers")
def get_pricing_tiers():
    """Get available pricing tiers."""
    return [
        {"id": "standard", "name": "Standard", "description": "Standard tier for development and small workloads"},
        {"id": "premium", "name": "Premium", "description": "Premium tier with advanced features"},
        {"id": "enterprise", "name": "Enterprise", "description": "Enterprise tier with full features and support"},
    ]


# ============================================================================
# Reference Data Endpoints (for frontend store compatibility)
# ============================================================================

@app.get("/api/v1/reference/clouds")
def get_clouds_reference():
    """Get available cloud providers."""
    return [
        {"id": "aws", "name": "Amazon Web Services"},
        {"id": "azure", "name": "Microsoft Azure"},
        {"id": "gcp", "name": "Google Cloud Platform"},
    ]


@app.get("/api/v1/dbsql/warehouse-sizes")
def get_dbsql_warehouse_sizes_endpoint():
    """Get DBSQL warehouse sizes."""
    return [
        {"id": "2X-Small", "name": "2X-Small", "dbu_per_hour": 2},
        {"id": "X-Small", "name": "X-Small", "dbu_per_hour": 4},
        {"id": "Small", "name": "Small", "dbu_per_hour": 8},
        {"id": "Medium", "name": "Medium", "dbu_per_hour": 16},
        {"id": "Large", "name": "Large", "dbu_per_hour": 32},
        {"id": "X-Large", "name": "X-Large", "dbu_per_hour": 64},
        {"id": "2X-Large", "name": "2X-Large", "dbu_per_hour": 128},
        {"id": "3X-Large", "name": "3X-Large", "dbu_per_hour": 256},
        {"id": "4X-Large", "name": "4X-Large", "dbu_per_hour": 512},
    ]


@app.get("/api/v1/dlt/editions")
def get_dlt_editions():
    """Get DLT editions."""
    return [
        {"id": "CORE", "name": "Core"},
        {"id": "PRO", "name": "Pro"},
        {"id": "ADVANCED", "name": "Advanced"},
    ]


@app.get("/api/v1/serverless/modes")
def get_serverless_modes():
    """Get serverless modes."""
    return [
        {"mode": "standard", "multiplier": 1.0, "description": "Standard serverless mode"},
        {"mode": "performance", "multiplier": 1.3, "description": "Performance serverless mode with higher throughput"},
    ]


@app.get("/api/v1/instances/types")
def get_instance_types_endpoint(cloud: str, region: Optional[str] = None, db: Session = Depends(get_db)):
    """Get available instance types for a cloud provider."""
    from app.models.instance_dbu_rates import InstanceDBURates
    
    try:
        query = db.query(InstanceDBURates).filter(
            InstanceDBURates.cloud == cloud.upper(),
            InstanceDBURates.is_active == True
        )
        
        results = query.order_by(
            InstanceDBURates.instance_family, 
            InstanceDBURates.vcpus,
            InstanceDBURates.instance_type
        ).all()
        
        if results:
            return [
                {
                    "id": r.instance_type,
                    "name": r.instance_type,
                    "vcpus": r.vcpus or 0,
                    "memory_gb": r.memory_gb or 0,
                    "dbu_rate": r.dbu_rate or 0,
                    "instance_family": r.instance_family or "General Purpose"
                }
                for r in results
            ]
    except Exception as e:
        log_warning(f"Could not fetch instance types from database: {e}")
    
    # Fallback
    return [
        {"id": "m5.xlarge", "name": "m5.xlarge", "vcpus": 4, "memory_gb": 16, "dbu_rate": 0.5, "instance_family": "General Purpose"},
        {"id": "m5.2xlarge", "name": "m5.2xlarge", "vcpus": 8, "memory_gb": 32, "dbu_rate": 1.0, "instance_family": "General Purpose"},
        {"id": "c5.xlarge", "name": "c5.xlarge", "vcpus": 4, "memory_gb": 8, "dbu_rate": 0.5, "instance_family": "Compute Optimized"},
    ]


@app.get("/api/v1/instances/families")
def get_instance_families():
    """Get instance family categories."""
    return ["General Purpose", "Compute Optimized", "Memory Optimized", "Storage Optimized", "GPU"]


@app.get("/api/v1/model-serving/gpu-types")
def get_model_serving_gpu_types_endpoint(cloud: str):
    """Get GPU types for model serving."""
    gpu_types = {
        "aws": [
            {"id": "cpu", "name": "CPU", "dbu_per_hour": 1},
            {"id": "gpu_small_t4", "name": "GPU Small - T4", "dbu_per_hour": 10.48},
            {"id": "gpu_medium_a10g_1x", "name": "GPU Medium - A10G 1x", "dbu_per_hour": 20},
            {"id": "gpu_medium_a10g_4x", "name": "GPU Medium - A10G 4x", "dbu_per_hour": 112},
            {"id": "gpu_medium_a10g_8x", "name": "GPU Medium - A10G 8x", "dbu_per_hour": 290.8},
            {"id": "gpu_xlarge_a100_40gb_8x", "name": "GPU XLarge - A100 40GB 8x", "dbu_per_hour": 538.4},
            {"id": "gpu_xlarge_a100_80gb_8x", "name": "GPU XLarge - A100 80GB 8x", "dbu_per_hour": 628},
        ],
        "azure": [
            {"id": "cpu", "name": "CPU", "dbu_per_hour": 1},
            {"id": "gpu_small_t4", "name": "GPU Small - T4", "dbu_per_hour": 10.48},
            {"id": "gpu_xlarge_a100_80gb_1x", "name": "GPU XLarge - A100 80GB 1x", "dbu_per_hour": 78.5},
            {"id": "gpu_2xlarge_a100_80gb_2x", "name": "GPU 2XLarge - A100 80GB 2x", "dbu_per_hour": 157},
            {"id": "gpu_4xlarge_a100_80gb_4x", "name": "GPU 4XLarge - A100 80GB 4x", "dbu_per_hour": 314},
        ],
        "gcp": [
            {"id": "cpu", "name": "CPU", "dbu_per_hour": 1},
            {"id": "gpu_medium_g2_standard_8", "name": "GPU Medium - G2 Standard 8", "dbu_per_hour": 5},
        ],
    }
    return gpu_types.get(cloud.lower(), [{"id": "cpu", "name": "CPU", "dbu_per_hour": 1}])


@app.get("/api/v1/photon/multipliers")
def get_photon_multipliers(cloud: str, sku_type: Optional[str] = None):
    """Get Photon multipliers by SKU type."""
    multipliers = [
        {"sku_type": "JOBS", "multiplier": 2.0, "category": "Compute"},
        {"sku_type": "ALL_PURPOSE", "multiplier": 2.0, "category": "Compute"},
        {"sku_type": "DLT", "multiplier": 2.0, "category": "Pipelines"},
        {"sku_type": "DBSQL", "multiplier": 1.0, "category": "SQL"},
    ]
    if sku_type:
        return [m for m in multipliers if m["sku_type"].upper() == sku_type.upper()]
    return multipliers


@app.get("/api/v1/dbsql/warehouse-types")
def get_dbsql_warehouse_types():
    """Get DBSQL warehouse types."""
    return ["CLASSIC", "PRO", "SERVERLESS"]


@app.get("/api/v1/fmapi/databricks-models/list")
def get_fmapi_databricks_models_list():
    """Get list of Databricks FMAPI model names."""
    return [
        "llama-4-maverick",
        "llama-3-3-70b",
        "llama-3-1-8b",
        "llama-3-2-3b",
        "llama-3-2-1b",
        "gpt-oss-120b",
        "gpt-oss-20b",
        "gemma-3-12b",
        "bge-large",
        "gte",
    ]


@app.get("/api/v1/pricing/dbu-rates")
def get_dbu_rates(cloud: str, region: str, tier: str, product_type: Optional[str] = None):
    """Get DBU rates for pricing calculations.
    
    Returns DBU prices per product type for the given cloud/region/tier combination.
    """
    # Default DBU rates by product type and tier
    # These are representative rates - actual rates come from lakemeter.sync_product_dbu_rates
    base_rates = {
        "PREMIUM": {
            "JOBS": 0.15,
            "JOBS_LIGHT": 0.07,
            "ALL_PURPOSE": 0.55,
            "DLT_CORE": 0.20,
            "DLT_PRO": 0.25,
            "DLT_ADVANCED": 0.36,
            "DBSQL_CLASSIC": 0.22,
            "DBSQL_PRO": 0.55,
            "DBSQL_SERVERLESS": 0.70,
            "MODEL_SERVING": 0.07,
            "VECTOR_SEARCH": 0.07,
            "FMAPI_DATABRICKS": 0.07,
            "FMAPI_PROPRIETARY": 0.07,
            "LAKEBASE": 0.07,
        },
        "STANDARD": {
            "JOBS": 0.10,
            "JOBS_LIGHT": 0.05,
            "ALL_PURPOSE": 0.40,
            "DLT_CORE": 0.15,
            "DLT_PRO": 0.20,
            "DLT_ADVANCED": 0.30,
            "DBSQL_CLASSIC": 0.15,
            "DBSQL_PRO": 0.40,
            "DBSQL_SERVERLESS": 0.55,
            "MODEL_SERVING": 0.05,
            "VECTOR_SEARCH": 0.05,
            "FMAPI_DATABRICKS": 0.05,
            "FMAPI_PROPRIETARY": 0.05,
            "LAKEBASE": 0.05,
        },
        "ENTERPRISE": {
            "JOBS": 0.20,
            "JOBS_LIGHT": 0.10,
            "ALL_PURPOSE": 0.65,
            "DLT_CORE": 0.25,
            "DLT_PRO": 0.30,
            "DLT_ADVANCED": 0.42,
            "DBSQL_CLASSIC": 0.30,
            "DBSQL_PRO": 0.65,
            "DBSQL_SERVERLESS": 0.85,
            "MODEL_SERVING": 0.10,
            "VECTOR_SEARCH": 0.10,
            "FMAPI_DATABRICKS": 0.10,
            "FMAPI_PROPRIETARY": 0.10,
            "LAKEBASE": 0.10,
        },
    }
    
    tier_upper = tier.upper()
    rates = base_rates.get(tier_upper, base_rates["PREMIUM"])
    
    if product_type:
        # Return single rate for specified product type
        price = rates.get(product_type.upper(), 0.10)
        return [{"product_type": product_type.upper(), "dbu_price": price, "currency": "USD"}]
    
    # Return all rates
    return [
        {"product_type": pt, "dbu_price": price, "currency": "USD"}
        for pt, price in rates.items()
    ]


@app.get("/api/v1/pricing/product-types")
def get_product_types(cloud: str, region: str, tier: str):
    """Get available product types for DBU pricing."""
    return [
        "JOBS", "JOBS_LIGHT", "ALL_PURPOSE",
        "DLT_CORE", "DLT_PRO", "DLT_ADVANCED",
        "DBSQL_CLASSIC", "DBSQL_PRO", "DBSQL_SERVERLESS",
        "MODEL_SERVING", "VECTOR_SEARCH",
        "FMAPI_DATABRICKS", "FMAPI_PROPRIETARY", "LAKEBASE"
    ]


@app.get("/api/v1/reference/instance-types/{cloud}")
def get_instance_types(cloud: str, region: Optional[str] = None, db: Session = Depends(get_db)):
    """Get available instance types for a cloud provider with family grouping.
    
    Fetches from lakemeter.sync_ref_instance_dbu_rates table which has vcpus, memory_gb, and instance_family.
    """
    from app.models.instance_dbu_rates import InstanceDBURates
    
    try:
        # Query instance types with full details from the reference table
        query = db.query(InstanceDBURates).filter(
            InstanceDBURates.cloud == cloud.upper(),
            InstanceDBURates.is_active == True
        )
        
        results = query.order_by(
            InstanceDBURates.instance_family, 
            InstanceDBURates.vcpus,
            InstanceDBURates.instance_type
        ).all()
        
        if results:
            return [
                {
                    "id": r.instance_type,
                    "name": r.instance_type,
                    "vcpus": r.vcpus or 0,
                    "memory_gb": r.memory_gb or 0,
                    "dbu_rate": r.dbu_rate or 0,
                    "instance_family": r.instance_family or "General Purpose"
                }
                for r in results
            ]
    except Exception as e:
        log_warning(f"Could not fetch instance types from database: {e}")

    # Fallback to hardcoded list if database query fails
    fallback_instance_types = {
        "aws": [
            {"id": "i3.xlarge", "name": "i3.xlarge", "vcpus": 4, "memory_gb": 30.5, "dbu_rate": 0.75, "instance_family": "Storage Optimized"},
            {"id": "i3.2xlarge", "name": "i3.2xlarge", "vcpus": 8, "memory_gb": 61, "dbu_rate": 1.5, "instance_family": "Storage Optimized"},
            {"id": "m5.large", "name": "m5.large", "vcpus": 2, "memory_gb": 8, "dbu_rate": 0.25, "instance_family": "General Purpose"},
            {"id": "m5.xlarge", "name": "m5.xlarge", "vcpus": 4, "memory_gb": 16, "dbu_rate": 0.5, "instance_family": "General Purpose"},
            {"id": "m5.2xlarge", "name": "m5.2xlarge", "vcpus": 8, "memory_gb": 32, "dbu_rate": 1.0, "instance_family": "General Purpose"},
            {"id": "c5.xlarge", "name": "c5.xlarge", "vcpus": 4, "memory_gb": 8, "dbu_rate": 0.5, "instance_family": "Compute Optimized"},
            {"id": "c5.2xlarge", "name": "c5.2xlarge", "vcpus": 8, "memory_gb": 16, "dbu_rate": 1.0, "instance_family": "Compute Optimized"},
            {"id": "r5.large", "name": "r5.large", "vcpus": 2, "memory_gb": 16, "dbu_rate": 0.35, "instance_family": "Memory Optimized"},
            {"id": "r5.xlarge", "name": "r5.xlarge", "vcpus": 4, "memory_gb": 32, "dbu_rate": 0.69, "instance_family": "Memory Optimized"},
        ],
        "azure": [
            {"id": "Standard_DS3_v2", "name": "Standard_DS3_v2", "vcpus": 4, "memory_gb": 14, "dbu_rate": 0.75, "instance_family": "General Purpose"},
            {"id": "Standard_DS4_v2", "name": "Standard_DS4_v2", "vcpus": 8, "memory_gb": 28, "dbu_rate": 1.5, "instance_family": "General Purpose"},
            {"id": "Standard_D4s_v3", "name": "Standard_D4s_v3", "vcpus": 4, "memory_gb": 16, "dbu_rate": 0.5, "instance_family": "General Purpose"},
            {"id": "Standard_D8s_v3", "name": "Standard_D8s_v3", "vcpus": 8, "memory_gb": 32, "dbu_rate": 1.0, "instance_family": "General Purpose"},
            {"id": "Standard_E4s_v3", "name": "Standard_E4s_v3", "vcpus": 4, "memory_gb": 32, "dbu_rate": 0.75, "instance_family": "Memory Optimized"},
            {"id": "Standard_F4s_v2", "name": "Standard_F4s_v2", "vcpus": 4, "memory_gb": 8, "dbu_rate": 0.5, "instance_family": "Compute Optimized"},
        ],
        "gcp": [
            {"id": "n1-standard-4", "name": "n1-standard-4", "vcpus": 4, "memory_gb": 15, "dbu_rate": 0.5, "instance_family": "General Purpose"},
            {"id": "n1-standard-8", "name": "n1-standard-8", "vcpus": 8, "memory_gb": 30, "dbu_rate": 1.0, "instance_family": "General Purpose"},
            {"id": "n2-standard-4", "name": "n2-standard-4", "vcpus": 4, "memory_gb": 16, "dbu_rate": 0.5, "instance_family": "General Purpose"},
            {"id": "n2-standard-8", "name": "n2-standard-8", "vcpus": 8, "memory_gb": 32, "dbu_rate": 1.0, "instance_family": "General Purpose"},
            {"id": "n2-highmem-4", "name": "n2-highmem-4", "vcpus": 4, "memory_gb": 32, "dbu_rate": 0.75, "instance_family": "Memory Optimized"},
            {"id": "n2-highcpu-4", "name": "n2-highcpu-4", "vcpus": 4, "memory_gb": 4, "dbu_rate": 0.4, "instance_family": "Compute Optimized"},
        ]
    }
    return fallback_instance_types.get(cloud.lower(), [])


@app.get("/api/v1/reference/dbsql-sizes")
def get_dbsql_warehouse_sizes():
    """Get available SQL Warehouse sizes."""
    # Values must match database CHECK constraint: chk_dbsql_warehouse_size
    return [
        {"id": "2X-Small", "name": "2X-Small", "dbu_per_hour": 2},
        {"id": "X-Small", "name": "X-Small", "dbu_per_hour": 4},
        {"id": "Small", "name": "Small", "dbu_per_hour": 8},
        {"id": "Medium", "name": "Medium", "dbu_per_hour": 16},
        {"id": "Large", "name": "Large", "dbu_per_hour": 32},
        {"id": "X-Large", "name": "X-Large", "dbu_per_hour": 64},
        {"id": "2X-Large", "name": "2X-Large", "dbu_per_hour": 128},
        {"id": "3X-Large", "name": "3X-Large", "dbu_per_hour": 192},
        {"id": "4X-Large", "name": "4X-Large", "dbu_per_hour": 256},
    ]


@app.get("/api/v1/reference/dlt-editions")
def get_dlt_editions():
    """Get available DLT editions."""
    # Values must match database CHECK constraint: chk_dlt_edition
    return [
        {"id": "CORE", "name": "Core", "dbu_multiplier": 1.0},
        {"id": "PRO", "name": "Pro", "dbu_multiplier": 1.5},
        {"id": "ADVANCED", "name": "Advanced", "dbu_multiplier": 2.0},
    ]


@app.get("/api/v1/reference/fmapi-models")
def get_foundation_models():
    """Get available foundation models for FMAPI (legacy endpoint)."""
    # Keep for backwards compatibility
    return [
        {"provider": "databricks", "models": [
            {"id": "llama-4-maverick", "name": "Llama 4 Maverick"},
            {"id": "llama-3-3-70b", "name": "Llama 3.3 70B"},
        ]},
        {"provider": "openai", "models": [
            {"id": "gpt-5", "name": "GPT-5"},
            {"id": "gpt-5-mini", "name": "GPT-5 Mini"},
        ]},
        {"provider": "anthropic", "models": [
            {"id": "claude-sonnet-4-5", "name": "Claude Sonnet 4.5"},
            {"id": "claude-opus-4", "name": "Claude Opus 4"},
        ]},
    ]


# ============================================================================
# Model Serving GPU Types (by cloud)
# Source: lakemeter.sync_product_serverless_rates WHERE product = 'model_serving'
# ============================================================================
@app.get("/api/v1/reference/model-serving-gpu-types/{cloud}")
def get_model_serving_gpu_types(cloud: str):
    """Get available Model Serving GPU types for a cloud provider."""
    gpu_types = {
        "aws": [
            {"id": "cpu", "name": "CPU", "dbu_per_hour": 1, "description": "1 concurrent request/hr = 1 DBU/hr"},
            {"id": "gpu_small_t4", "name": "GPU Small - T4", "dbu_per_hour": 10.48, "description": "Small - T4 or equivalent"},
            {"id": "gpu_medium_a10g_1x", "name": "GPU Medium - A10G x1", "dbu_per_hour": 20, "description": "Medium - A10G x 1GPU"},
            {"id": "gpu_medium_a10g_4x", "name": "GPU Medium 4X - A10G x4", "dbu_per_hour": 112, "description": "Medium 4X - A10G x 4GPU"},
            {"id": "gpu_medium_a10g_8x", "name": "GPU Medium 8X - A10G x8", "dbu_per_hour": 290.8, "description": "Medium 8X - A10G x 8GPU"},
            {"id": "gpu_xlarge_a100_40gb_8x", "name": "GPU XLarge - A100 40GB x8", "dbu_per_hour": 538.4, "description": "XLarge - A100 40GB x 8GPU"},
            {"id": "gpu_xlarge_a100_80gb_8x", "name": "GPU XLarge - A100 80GB x8", "dbu_per_hour": 628, "description": "XLarge - A100 80GB x 8GPU"},
        ],
        "azure": [
            {"id": "cpu", "name": "CPU", "dbu_per_hour": 1, "description": "1 concurrent request/hr = 1 DBU/hr"},
            {"id": "gpu_small_t4", "name": "GPU Small - T4", "dbu_per_hour": 10.48, "description": "Small - T4 or equivalent"},
            {"id": "gpu_xlarge_a100_80gb_1x", "name": "GPU XLarge - A100 80GB x1", "dbu_per_hour": 78.6, "description": "XLarge - A100 80GB x 1GPU"},
            {"id": "gpu_2xlarge_a100_80gb_2x", "name": "GPU 2XLarge - A100 80GB x2", "dbu_per_hour": 157.2, "description": "2XLarge - A100 80GB x 2GPU"},
            {"id": "gpu_4xlarge_a100_80gb_4x", "name": "GPU 4XLarge - A100 80GB x4", "dbu_per_hour": 314.4, "description": "4XLarge - A100 80GB x 4GPU"},
        ],
        "gcp": [
            {"id": "cpu", "name": "CPU", "dbu_per_hour": 1, "description": "1 concurrent request/hr = 1 DBU/hr"},
            {"id": "gpu_medium_g2_standard_8", "name": "GPU Medium - G2 Standard 8 x1", "dbu_per_hour": 5, "description": "Medium - G2 Standard 8 x 1GPU"},
        ],
    }
    return gpu_types.get(cloud.lower(), [{"id": "cpu", "name": "CPU", "dbu_per_hour": 1}])


# ============================================================================
# Foundation Models (Databricks)
# Source: lakemeter.sync_product_fmapi_databricks
# ============================================================================
@app.get("/api/v1/reference/fmapi-databricks")
def get_fmapi_databricks():
    """Get Foundation Models (Databricks) configuration options."""
    return {
        "model_types": [
            {"id": "llm", "name": "LLMs", "has_output_tokens": True},
            {"id": "embedding", "name": "Embedding Models", "has_output_tokens": False},
        ],
        "models": {
            "llm": [
                {"id": "llama-4-maverick", "name": "Llama 4 Maverick"},
                {"id": "llama-3-3-70b", "name": "Llama 3.3 70B"},
                {"id": "llama-3-1-8b", "name": "Llama 3.1 8B"},
                {"id": "llama-3-2-3b", "name": "Llama 3.2 3B"},
                {"id": "llama-3-2-1b", "name": "Llama 3.2 1B"},
                {"id": "gpt-oss-120b", "name": "GPT-OSS 120B"},
                {"id": "gpt-oss-20b", "name": "GPT-OSS 20B"},
                {"id": "gemma-3-12b", "name": "Gemma 3 12B"},
            ],
            "embedding": [
                {"id": "bge-large", "name": "BGE Large"},
                {"id": "gte", "name": "GTE"},
            ],
        },
        "inference_types": [
            {"id": "pay_per_token", "name": "Pay-Per-Token", "description": "Pay based on input/output tokens"},
            {"id": "provisioned_throughput", "name": "Provisioned Throughput", "description": "Reserved capacity with hourly billing"},
            {"id": "batch_inference", "name": "Batch Inference", "description": "Batch processing at lower cost"},
        ],
    }


# ============================================================================
# Foundation Models (Proprietary)
# Source: lakemeter.sync_product_fmapi_proprietary
# ============================================================================
@app.get("/api/v1/reference/fmapi-proprietary")
def get_fmapi_proprietary():
    """Get Foundation Models (Proprietary) configuration options."""
    return {
        "providers": [
            {
                "id": "anthropic",
                "name": "Anthropic",
                "models": [
                    {"id": "claude-sonnet-4-5", "name": "Claude Sonnet 4.5"},
                    {"id": "claude-sonnet-4-1", "name": "Claude Sonnet 4.1"},
                    {"id": "claude-sonnet-4", "name": "Claude Sonnet 4"},
                    {"id": "claude-sonnet-3-7", "name": "Claude Sonnet 3.7"},
                    {"id": "claude-opus-4-5", "name": "Claude Opus 4.5"},
                    {"id": "claude-opus-4-1", "name": "Claude Opus 4.1"},
                    {"id": "claude-opus-4", "name": "Claude Opus 4"},
                    {"id": "claude-haiku-4-5", "name": "Claude Haiku 4.5"},
                ],
            },
            {
                "id": "openai",
                "name": "OpenAI",
                "models": [
                    {"id": "gpt-5", "name": "GPT-5"},
                    {"id": "gpt-5-1", "name": "GPT-5.1"},
                    {"id": "gpt-5-mini", "name": "GPT-5 Mini"},
                    {"id": "gpt-5-nano", "name": "GPT-5 Nano"},
                ],
            },
            {
                "id": "google",
                "name": "Google",
                "models": [
                    {"id": "gemini-2-5-pro", "name": "Gemini 2.5 Pro"},
                    {"id": "gemini-2-5-flash", "name": "Gemini 2.5 Flash"},
                ],
            },
        ],
        "endpoint_types": [
            {"id": "global", "name": "Global"},
            {"id": "in_geo", "name": "In-Geo (Regional)"},
        ],
        "context_lengths": [
            {"id": "all", "name": "All"},
            {"id": "short", "name": "Short"},
            {"id": "long", "name": "Long"},
        ],
    }


# =============================================================================
# Static File Serving for Combined Frontend + Backend Deployment
# Must be AFTER all API routes
# =============================================================================

# Path to static files (React build)
STATIC_DIR = Path(__file__).parent.parent / "static"

# Check if static directory exists (production deployment)
if STATIC_DIR.exists() and (STATIC_DIR / "index.html").exists():
    log_info(f"Static files found at {STATIC_DIR}, enabling SPA serving")
    
    # Mount static assets (JS, CSS, images)
    if (STATIC_DIR / "assets").exists():
        app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")
    
    # Serve static files at root (favicon, etc.)
    @app.get("/favicon.ico")
    async def favicon():
        favicon_path = STATIC_DIR / "favicon.ico"
        if favicon_path.exists():
            return FileResponse(favicon_path)
        return FileResponse(STATIC_DIR / "databricks-icon.svg")
    
    @app.get("/databricks-icon.svg")
    async def databricks_icon():
        return FileResponse(STATIC_DIR / "databricks-icon.svg")
    
    # Serve index.html at root
    @app.get("/")
    async def serve_root():
        """Serve React SPA at root."""
        return FileResponse(STATIC_DIR / "index.html")
    
    # SPA catch-all handler - serve index.html for non-API routes
    # This must be the LAST route defined
    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        """Serve React SPA for all non-API routes."""
        # Don't intercept API routes
        if full_path.startswith("api/"):
            return {"error": "Not found"}, 404
        
        # Serve index.html for client-side routing
        return FileResponse(STATIC_DIR / "index.html")

else:
    log_info("Static files not found - running in API-only mode (local development)")
    
    # In local dev mode, serve API info at root
    @app.get("/")
    def root():
        """Root endpoint (local dev only)."""
        return {
            "name": "Lakemeter API",
            "version": "1.0.0",
            "description": "Databricks Pricing Calculator API",
            "mode": "API-only (frontend served separately)"
        }
