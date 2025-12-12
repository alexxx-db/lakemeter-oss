"""Line Item schemas."""
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
from decimal import Decimal
from pydantic import BaseModel


class LineItemBase(BaseModel):
    """Base line item schema."""
    workload_name: str
    workload_type: Optional[str] = None
    display_order: Optional[int] = 0
    
    # Serverless toggle
    is_serverless: Optional[bool] = False
    serverless_performance_mode: Optional[str] = None
    
    # Classic Compute Configuration
    driver_node_type: Optional[str] = None
    worker_node_type: Optional[str] = None
    num_workers: Optional[int] = 1
    autoscale_enabled: Optional[bool] = False
    autoscale_min_workers: Optional[int] = None
    autoscale_max_workers: Optional[int] = None
    photon_enabled: Optional[bool] = False
    
    # DLT Configuration
    dlt_edition: Optional[str] = None
    dlt_pipeline_mode: Optional[str] = None
    
    # DBSQL Configuration
    dbsql_warehouse_type: Optional[str] = None
    dbsql_warehouse_size: Optional[str] = None
    
    # Vector Search Configuration
    vector_search_endpoint_type: Optional[str] = None
    vector_search_mode: Optional[str] = None
    
    # Lakebase Configuration
    lakebase_instance_type: Optional[str] = None
    lakebase_storage_gb: Optional[int] = None
    
    # Foundation Model API Configuration
    fmapi_provider: Optional[str] = None
    fmapi_model: Optional[str] = None
    fmapi_endpoint_type: Optional[str] = None
    fmapi_context_length: Optional[str] = None
    fmapi_input_tokens_per_month: Optional[int] = None
    fmapi_output_tokens_per_month: Optional[int] = None
    
    # Usage Configuration
    hours_per_day: Optional[Decimal] = None
    days_per_month: Optional[int] = 22
    runs_per_day: Optional[int] = None
    avg_runtime_minutes: Optional[int] = None
    
    # Pricing Configuration
    vm_pricing_tier: Optional[str] = None
    vm_payment_option: Optional[str] = None
    spot_percentage: Optional[int] = 0
    
    # Selected SKU
    selected_sku: Optional[str] = None
    
    # Additional Configuration
    workload_config: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class LineItemCreate(LineItemBase):
    """Schema for creating a line item."""
    estimate_id: UUID


class LineItemUpdate(BaseModel):
    """Schema for updating a line item."""
    workload_name: Optional[str] = None
    workload_type: Optional[str] = None
    display_order: Optional[int] = None
    
    # Serverless toggle
    is_serverless: Optional[bool] = None
    serverless_performance_mode: Optional[str] = None
    
    # Classic Compute Configuration
    driver_node_type: Optional[str] = None
    worker_node_type: Optional[str] = None
    num_workers: Optional[int] = None
    autoscale_enabled: Optional[bool] = None
    autoscale_min_workers: Optional[int] = None
    autoscale_max_workers: Optional[int] = None
    photon_enabled: Optional[bool] = None
    
    # DLT Configuration
    dlt_edition: Optional[str] = None
    dlt_pipeline_mode: Optional[str] = None
    
    # DBSQL Configuration
    dbsql_warehouse_type: Optional[str] = None
    dbsql_warehouse_size: Optional[str] = None
    
    # Vector Search Configuration
    vector_search_endpoint_type: Optional[str] = None
    vector_search_mode: Optional[str] = None
    
    # Lakebase Configuration
    lakebase_instance_type: Optional[str] = None
    lakebase_storage_gb: Optional[int] = None
    
    # Foundation Model API Configuration
    fmapi_provider: Optional[str] = None
    fmapi_model: Optional[str] = None
    fmapi_endpoint_type: Optional[str] = None
    fmapi_context_length: Optional[str] = None
    fmapi_input_tokens_per_month: Optional[int] = None
    fmapi_output_tokens_per_month: Optional[int] = None
    
    # Usage Configuration
    hours_per_day: Optional[Decimal] = None
    days_per_month: Optional[int] = None
    runs_per_day: Optional[int] = None
    avg_runtime_minutes: Optional[int] = None
    
    # Pricing Configuration
    vm_pricing_tier: Optional[str] = None
    vm_payment_option: Optional[str] = None
    spot_percentage: Optional[int] = None
    
    # Selected SKU
    selected_sku: Optional[str] = None
    
    # Additional Configuration
    workload_config: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class LineItemResponse(LineItemBase):
    """Schema for line item response."""
    line_item_id: UUID
    estimate_id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
