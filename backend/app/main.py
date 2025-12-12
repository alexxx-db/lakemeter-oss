"""FastAPI main application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
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
def get_instance_types(cloud: str):
    """Get available instance types for a cloud provider."""
    instance_types = {
        "aws": [
            {"id": "i3.xlarge", "name": "i3.xlarge", "vcpus": 4, "memory_gb": 30.5, "dbu_rate": 0.75},
            {"id": "i3.2xlarge", "name": "i3.2xlarge", "vcpus": 8, "memory_gb": 61, "dbu_rate": 1.5},
            {"id": "i3.4xlarge", "name": "i3.4xlarge", "vcpus": 16, "memory_gb": 122, "dbu_rate": 3.0},
            {"id": "i3.8xlarge", "name": "i3.8xlarge", "vcpus": 32, "memory_gb": 244, "dbu_rate": 6.0},
            {"id": "i3.16xlarge", "name": "i3.16xlarge", "vcpus": 64, "memory_gb": 488, "dbu_rate": 12.0},
            {"id": "m5.large", "name": "m5.large", "vcpus": 2, "memory_gb": 8, "dbu_rate": 0.25},
            {"id": "m5.xlarge", "name": "m5.xlarge", "vcpus": 4, "memory_gb": 16, "dbu_rate": 0.5},
            {"id": "m5.2xlarge", "name": "m5.2xlarge", "vcpus": 8, "memory_gb": 32, "dbu_rate": 1.0},
            {"id": "m5.4xlarge", "name": "m5.4xlarge", "vcpus": 16, "memory_gb": 64, "dbu_rate": 2.0},
            {"id": "r5.large", "name": "r5.large", "vcpus": 2, "memory_gb": 16, "dbu_rate": 0.35},
            {"id": "r5.xlarge", "name": "r5.xlarge", "vcpus": 4, "memory_gb": 32, "dbu_rate": 0.69},
            {"id": "r5.2xlarge", "name": "r5.2xlarge", "vcpus": 8, "memory_gb": 64, "dbu_rate": 1.38},
            {"id": "c5.xlarge", "name": "c5.xlarge", "vcpus": 4, "memory_gb": 8, "dbu_rate": 0.44},
            {"id": "c5.2xlarge", "name": "c5.2xlarge", "vcpus": 8, "memory_gb": 16, "dbu_rate": 0.88},
            {"id": "p3.2xlarge", "name": "p3.2xlarge (GPU)", "vcpus": 8, "memory_gb": 61, "dbu_rate": 5.5, "gpu": True},
            {"id": "p3.8xlarge", "name": "p3.8xlarge (GPU)", "vcpus": 32, "memory_gb": 244, "dbu_rate": 22.0, "gpu": True},
        ],
        "azure": [
            {"id": "Standard_DS3_v2", "name": "Standard_DS3_v2", "vcpus": 4, "memory_gb": 14, "dbu_rate": 0.75},
            {"id": "Standard_DS4_v2", "name": "Standard_DS4_v2", "vcpus": 8, "memory_gb": 28, "dbu_rate": 1.5},
            {"id": "Standard_DS5_v2", "name": "Standard_DS5_v2", "vcpus": 16, "memory_gb": 56, "dbu_rate": 3.0},
            {"id": "Standard_D4s_v3", "name": "Standard_D4s_v3", "vcpus": 4, "memory_gb": 16, "dbu_rate": 0.5},
            {"id": "Standard_D8s_v3", "name": "Standard_D8s_v3", "vcpus": 8, "memory_gb": 32, "dbu_rate": 1.0},
            {"id": "Standard_D16s_v3", "name": "Standard_D16s_v3", "vcpus": 16, "memory_gb": 64, "dbu_rate": 2.0},
            {"id": "Standard_E4s_v3", "name": "Standard_E4s_v3", "vcpus": 4, "memory_gb": 32, "dbu_rate": 0.69},
            {"id": "Standard_E8s_v3", "name": "Standard_E8s_v3", "vcpus": 8, "memory_gb": 64, "dbu_rate": 1.38},
            {"id": "Standard_L8s_v2", "name": "Standard_L8s_v2", "vcpus": 8, "memory_gb": 64, "dbu_rate": 1.5},
            {"id": "Standard_NC6s_v3", "name": "Standard_NC6s_v3 (GPU)", "vcpus": 6, "memory_gb": 112, "dbu_rate": 5.5, "gpu": True},
        ],
        "gcp": [
            {"id": "n1-standard-4", "name": "n1-standard-4", "vcpus": 4, "memory_gb": 15, "dbu_rate": 0.5},
            {"id": "n1-standard-8", "name": "n1-standard-8", "vcpus": 8, "memory_gb": 30, "dbu_rate": 1.0},
            {"id": "n1-standard-16", "name": "n1-standard-16", "vcpus": 16, "memory_gb": 60, "dbu_rate": 2.0},
            {"id": "n1-standard-32", "name": "n1-standard-32", "vcpus": 32, "memory_gb": 120, "dbu_rate": 4.0},
            {"id": "n1-highmem-4", "name": "n1-highmem-4", "vcpus": 4, "memory_gb": 26, "dbu_rate": 0.69},
            {"id": "n1-highmem-8", "name": "n1-highmem-8", "vcpus": 8, "memory_gb": 52, "dbu_rate": 1.38},
            {"id": "n2-standard-4", "name": "n2-standard-4", "vcpus": 4, "memory_gb": 16, "dbu_rate": 0.5},
            {"id": "n2-standard-8", "name": "n2-standard-8", "vcpus": 8, "memory_gb": 32, "dbu_rate": 1.0},
        ]
    }
    return instance_types.get(cloud, [])


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
    """Get available foundation models for FMAPI."""
    return [
        {"provider": "databricks", "models": [
            {"id": "dbrx-instruct", "name": "DBRX Instruct", "input_price_per_million": 0.75, "output_price_per_million": 2.25},
            {"id": "llama-3-70b-instruct", "name": "Llama 3 70B Instruct", "input_price_per_million": 1.00, "output_price_per_million": 3.00},
            {"id": "llama-3-8b-instruct", "name": "Llama 3 8B Instruct", "input_price_per_million": 0.10, "output_price_per_million": 0.25},
            {"id": "mixtral-8x7b-instruct", "name": "Mixtral 8x7B Instruct", "input_price_per_million": 0.50, "output_price_per_million": 1.00},
        ]},
        {"provider": "openai", "models": [
            {"id": "gpt-4o", "name": "GPT-4o", "input_price_per_million": 5.00, "output_price_per_million": 15.00},
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "input_price_per_million": 0.15, "output_price_per_million": 0.60},
            {"id": "gpt-4-turbo", "name": "GPT-4 Turbo", "input_price_per_million": 10.00, "output_price_per_million": 30.00},
        ]},
        {"provider": "anthropic", "models": [
            {"id": "claude-3-5-sonnet", "name": "Claude 3.5 Sonnet", "input_price_per_million": 3.00, "output_price_per_million": 15.00},
            {"id": "claude-3-opus", "name": "Claude 3 Opus", "input_price_per_million": 15.00, "output_price_per_million": 75.00},
            {"id": "claude-3-haiku", "name": "Claude 3 Haiku", "input_price_per_million": 0.25, "output_price_per_million": 1.25},
        ]},
    ]


