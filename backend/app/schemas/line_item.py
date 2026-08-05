"""Line Item schemas."""
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict, model_validator


def map_ai_parse_api_fields(data: dict, provided_fields: set[str]) -> dict:
    """Map the public AI Parse fields onto storage columns while keeping UI columns."""
    if "ai_parse_mode" in provided_fields:
        mode = data.get("ai_parse_mode")
        storage_mode = mode
        if isinstance(mode, str):
            mode_l = mode.lower()
            data["ai_parse_mode"] = mode_l.removesuffix("_based")
            if mode_l in {"dbu", "pages"}:
                storage_mode = f"{mode_l}_based"
            elif mode_l in {"dbu_based", "pages_based"}:
                storage_mode = mode_l
        data["ai_parse_calculation_method"] = storage_mode

    if "ai_parse_pages_thousands" in provided_fields:
        pages_thousands = data.get("ai_parse_pages_thousands")
        data["ai_parse_num_pages"] = (
            pages_thousands * 1000 if pages_thousands is not None else None
        )

    return data


def map_shutterstock_fields(data: dict, provided_fields: set[str]) -> dict:
    """Keep shutterstock_images (UI) and shutterstock_imageai_num_images (legacy) aligned."""
    if "shutterstock_images" in provided_fields:
        images = data.get("shutterstock_images")
        if "shutterstock_imageai_num_images" not in provided_fields:
            data["shutterstock_imageai_num_images"] = images
    elif "shutterstock_imageai_num_images" in provided_fields:
        images = data.get("shutterstock_imageai_num_images")
        if "shutterstock_images" not in provided_fields:
            data["shutterstock_images"] = images
    return data


def map_lakeflow_connect_fields(data: dict, provided_fields: set[str]) -> dict:
    """Keep simplified Connect UI fields and legacy gateway instance column aligned."""
    if "lakeflow_connect_gateway_instance" in provided_fields:
        instance = data.get("lakeflow_connect_gateway_instance")
        if "lakeflow_connect_gateway_instance_type" not in provided_fields:
            data["lakeflow_connect_gateway_instance_type"] = instance
    elif "lakeflow_connect_gateway_instance_type" in provided_fields:
        instance = data.get("lakeflow_connect_gateway_instance_type")
        if "lakeflow_connect_gateway_instance" not in provided_fields:
            data["lakeflow_connect_gateway_instance"] = instance
    return data


def map_line_item_api_fields(data: dict, provided_fields: set[str]) -> dict:
    """Apply all public API ↔ storage column mappings for line items."""
    data = map_ai_parse_api_fields(data, provided_fields)
    data = map_shutterstock_fields(data, provided_fields)
    data = map_lakeflow_connect_fields(data, provided_fields)
    return data


class LineItemBase(BaseModel):
    """Base line item schema."""
    workload_name: str
    workload_type: Optional[str] = None
    display_order: Optional[int] = 0
    cloud: Optional[str] = None

    # Serverless toggle
    serverless_enabled: Optional[bool] = False
    serverless_mode: Optional[str] = None

    # Classic Compute Configuration
    photon_enabled: Optional[bool] = False
    driver_node_type: Optional[str] = None
    worker_node_type: Optional[str] = None
    num_workers: Optional[int] = 1

    # DLT Configuration
    dlt_edition: Optional[str] = None

    # DBSQL Configuration
    dbsql_warehouse_type: Optional[str] = None
    dbsql_warehouse_size: Optional[str] = None
    dbsql_num_clusters: Optional[int] = None
    dbsql_vm_pricing_tier: Optional[str] = None
    dbsql_vm_payment_option: Optional[str] = None

    # Vector Search Configuration
    vector_search_mode: Optional[str] = None
    vector_capacity_millions: Optional[int] = None
    vector_search_storage_gb: Optional[int] = None

    # Model Serving Configuration
    model_serving_gpu_type: Optional[str] = None
    model_serving_concurrency: Optional[int] = None
    model_serving_scale_out: Optional[str] = None
    model_servings_number_endpoints: Optional[int] = None

    # Foundation Model API Configuration (Proprietary)
    fmapi_provider: Optional[str] = None
    fmapi_model: Optional[str] = None
    fmapi_endpoint_type: Optional[str] = None
    fmapi_context_length: Optional[str] = None
    fmapi_rate_type: Optional[str] = None  # input_token, output_token, cache_read, cache_write
    fmapi_quantity: Optional[Decimal] = None  # quantity in millions (M)

    # Databricks Apps Configuration
    databricks_apps_size: Optional[str] = None
    databricks_apps_hours_per_month: Optional[float] = None
    databricks_apps_num_apps: Optional[int] = None

    # AI Parse Configuration
    ai_parse_calculation_method: Optional[str] = None
    ai_parse_complexity: Optional[str] = None
    ai_parse_dbu_quantity: Optional[float] = None
    ai_parse_num_pages: Optional[float] = None
    ai_parse_mode: Optional[str] = None
    ai_parse_pages_thousands: Optional[float] = None

    # Shutterstock ImageAI Configuration
    shutterstock_imageai_num_images: Optional[int] = None
    shutterstock_images: Optional[int] = None

    # Databricks Support Configuration
    databricks_support_tier: Optional[str] = None
    databricks_support_annual_commit: Optional[float] = None

    # Lakeflow Connect Configuration
    lakeflow_connect_connector_type: Optional[str] = None
    lakeflow_connect_pipeline_driver_node_type: Optional[str] = None
    lakeflow_connect_pipeline_worker_node_type: Optional[str] = None
    lakeflow_connect_pipeline_num_workers: Optional[int] = None
    lakeflow_connect_pipeline_serverless_mode: Optional[str] = None
    lakeflow_connect_pipeline_runs_per_day: Optional[int] = None
    lakeflow_connect_pipeline_avg_runtime_minutes: Optional[int] = None
    lakeflow_connect_pipeline_hours_per_month: Optional[float] = None
    lakeflow_connect_gateway_cloud: Optional[str] = None
    lakeflow_connect_gateway_instance_type: Optional[str] = None
    lakeflow_connect_gateway_num_workers: Optional[int] = None
    lakeflow_connect_gateway_hours_per_month: Optional[float] = None
    lakeflow_connect_pipeline_mode: Optional[str] = None
    lakeflow_connect_gateway_enabled: Optional[bool] = None
    lakeflow_connect_gateway_instance: Optional[str] = None

    # Lakebase Configuration
    lakebase_cu: Optional[float] = None
    lakebase_storage_gb: Optional[int] = None
    lakebase_ha_nodes: Optional[int] = None
    lakebase_backup_retention_days: Optional[int] = None
    lakebase_pitr_gb: Optional[int] = None
    lakebase_snapshot_gb: Optional[int] = None

    # Usage Configuration
    runs_per_day: Optional[int] = None
    avg_runtime_minutes: Optional[int] = None
    days_per_month: Optional[int] = 22
    hours_per_month: Optional[int] = None

    # Pricing Configuration
    driver_pricing_tier: Optional[str] = None
    worker_pricing_tier: Optional[str] = None
    driver_payment_option: Optional[str] = None
    worker_payment_option: Optional[str] = None

    # Additional Configuration
    workload_config: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None

    # Calculated results
    cost_calculation_response: Optional[Dict[str, Any]] = None
    calculation_completed_at: Optional[datetime] = None


class LineItemCreate(LineItemBase):
    """Schema for creating a line item."""
    estimate_id: UUID


class LineItemUpdate(BaseModel):
    """Schema for updating a line item."""
    workload_name: Optional[str] = None
    workload_type: Optional[str] = None
    display_order: Optional[int] = None
    cloud: Optional[str] = None

    # Serverless toggle
    serverless_enabled: Optional[bool] = None
    serverless_mode: Optional[str] = None

    # Classic Compute Configuration
    photon_enabled: Optional[bool] = None
    driver_node_type: Optional[str] = None
    worker_node_type: Optional[str] = None
    num_workers: Optional[int] = None

    # DLT Configuration
    dlt_edition: Optional[str] = None

    # DBSQL Configuration
    dbsql_warehouse_type: Optional[str] = None
    dbsql_warehouse_size: Optional[str] = None
    dbsql_num_clusters: Optional[int] = None
    dbsql_vm_pricing_tier: Optional[str] = None
    dbsql_vm_payment_option: Optional[str] = None

    # Vector Search Configuration
    vector_search_mode: Optional[str] = None
    vector_capacity_millions: Optional[int] = None
    vector_search_storage_gb: Optional[int] = None

    # Model Serving Configuration
    model_serving_gpu_type: Optional[str] = None
    model_serving_concurrency: Optional[int] = None
    model_serving_scale_out: Optional[str] = None
    model_servings_number_endpoints: Optional[int] = None

    # Foundation Model API Configuration (Proprietary)
    fmapi_provider: Optional[str] = None
    fmapi_model: Optional[str] = None
    fmapi_endpoint_type: Optional[str] = None
    fmapi_context_length: Optional[str] = None
    fmapi_rate_type: Optional[str] = None
    fmapi_quantity: Optional[Decimal] = None

    # Databricks Apps Configuration
    databricks_apps_size: Optional[str] = None
    databricks_apps_hours_per_month: Optional[float] = None
    databricks_apps_num_apps: Optional[int] = None

    # AI Parse Configuration
    ai_parse_calculation_method: Optional[str] = None
    ai_parse_complexity: Optional[str] = None
    ai_parse_dbu_quantity: Optional[float] = None
    ai_parse_num_pages: Optional[float] = None
    ai_parse_mode: Optional[str] = None
    ai_parse_pages_thousands: Optional[float] = None

    # Shutterstock ImageAI Configuration
    shutterstock_imageai_num_images: Optional[int] = None
    shutterstock_images: Optional[int] = None

    # Databricks Support Configuration
    databricks_support_tier: Optional[str] = None
    databricks_support_annual_commit: Optional[float] = None

    # Lakeflow Connect Configuration
    lakeflow_connect_connector_type: Optional[str] = None
    lakeflow_connect_pipeline_driver_node_type: Optional[str] = None
    lakeflow_connect_pipeline_worker_node_type: Optional[str] = None
    lakeflow_connect_pipeline_num_workers: Optional[int] = None
    lakeflow_connect_pipeline_serverless_mode: Optional[str] = None
    lakeflow_connect_pipeline_runs_per_day: Optional[int] = None
    lakeflow_connect_pipeline_avg_runtime_minutes: Optional[int] = None
    lakeflow_connect_pipeline_hours_per_month: Optional[float] = None
    lakeflow_connect_gateway_cloud: Optional[str] = None
    lakeflow_connect_gateway_instance_type: Optional[str] = None
    lakeflow_connect_gateway_num_workers: Optional[int] = None
    lakeflow_connect_gateway_hours_per_month: Optional[float] = None
    lakeflow_connect_pipeline_mode: Optional[str] = None
    lakeflow_connect_gateway_enabled: Optional[bool] = None
    lakeflow_connect_gateway_instance: Optional[str] = None

    # Lakebase Configuration
    lakebase_cu: Optional[float] = None
    lakebase_storage_gb: Optional[int] = None
    lakebase_ha_nodes: Optional[int] = None
    lakebase_backup_retention_days: Optional[int] = None
    lakebase_pitr_gb: Optional[int] = None
    lakebase_snapshot_gb: Optional[int] = None

    # Usage Configuration
    runs_per_day: Optional[int] = None
    avg_runtime_minutes: Optional[int] = None
    days_per_month: Optional[int] = None
    hours_per_month: Optional[int] = None

    # Pricing Configuration
    driver_pricing_tier: Optional[str] = None
    worker_pricing_tier: Optional[str] = None
    driver_payment_option: Optional[str] = None
    worker_payment_option: Optional[str] = None

    # Additional Configuration
    workload_config: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None

    # Calculated results
    cost_calculation_response: Optional[Dict[str, Any]] = None
    calculation_completed_at: Optional[datetime] = None


class LineItemResponse(LineItemBase):
    """Schema for line item response."""
    line_item_id: UUID
    estimate_id: UUID
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def populate_api_alias_fields(cls, value):
        """Expose frontend alias fields from legacy storage columns when needed."""
        if isinstance(value, dict):
            data = dict(value)
        else:
            data = {
                field_name: getattr(value, field_name, None)
                for field_name in cls.model_fields
            }
            # Include legacy columns that may not be in model_fields aliases
            for legacy in ("shutterstock_imageai_num_images", "ai_parse_calculation_method", "ai_parse_num_pages"):
                if legacy not in data:
                    data[legacy] = getattr(value, legacy, None)

        if data.get("ai_parse_mode") is None:
            storage_mode = data.get("ai_parse_calculation_method")
            if isinstance(storage_mode, str):
                data["ai_parse_mode"] = storage_mode.lower().removesuffix("_based")

        if data.get("ai_parse_pages_thousands") is None:
            num_pages = data.get("ai_parse_num_pages")
            if num_pages is not None:
                data["ai_parse_pages_thousands"] = float(num_pages) / 1000

        if data.get("shutterstock_images") is None:
            legacy_images = data.get("shutterstock_imageai_num_images")
            if legacy_images is not None:
                data["shutterstock_images"] = legacy_images

        return data

    model_config = ConfigDict(from_attributes=True)
