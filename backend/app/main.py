"""FastAPI main application entry point."""
from typing import Optional
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.routes import (
    estimates_router,
    line_items_router,
    workload_types_router,
    users_router,
    export_router,
    vm_pricing_router,
    salesforce_router
)

# Create FastAPI application
app = FastAPI(
    title="Lakemeter API",
    description="Databricks Pricing Calculator API - Estimate and manage Databricks workload costs",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

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


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "name": "Lakemeter API",
        "version": "1.0.0",
        "description": "Databricks Pricing Calculator API"
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


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
        print(f"Warning: Could not fetch cloud providers from database: {e}")
    
    # Return default if database query fails
    return DEFAULT_CLOUD_PROVIDERS


@app.get("/api/v1/reference/tiers")
def get_pricing_tiers():
    """Get available pricing tiers."""
    return [
        {"id": "standard", "name": "Standard", "description": "Standard tier for development and small workloads"},
        {"id": "premium", "name": "Premium", "description": "Premium tier with advanced features"},
        {"id": "enterprise", "name": "Enterprise", "description": "Enterprise tier with full features and support"},
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
        print(f"Warning: Could not fetch instance types from database: {e}")
    
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
    return [
        {"id": "2x-small", "name": "2X-Small", "dbu_per_hour": 2},
        {"id": "x-small", "name": "X-Small", "dbu_per_hour": 4},
        {"id": "small", "name": "Small", "dbu_per_hour": 8},
        {"id": "medium", "name": "Medium", "dbu_per_hour": 16},
        {"id": "large", "name": "Large", "dbu_per_hour": 32},
        {"id": "x-large", "name": "X-Large", "dbu_per_hour": 64},
        {"id": "2x-large", "name": "2X-Large", "dbu_per_hour": 128},
        {"id": "3x-large", "name": "3X-Large", "dbu_per_hour": 192},
        {"id": "4x-large", "name": "4X-Large", "dbu_per_hour": 256},
    ]


@app.get("/api/v1/reference/dlt-editions")
def get_dlt_editions():
    """Get available DLT editions."""
    return [
        {"id": "core", "name": "Core", "dbu_multiplier": 1.0},
        {"id": "pro", "name": "Pro", "dbu_multiplier": 1.5},
        {"id": "advanced", "name": "Advanced", "dbu_multiplier": 2.0},
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


