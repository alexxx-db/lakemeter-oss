"""Line Item model for estimate workloads."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON, BIGINT
from sqlalchemy.orm import relationship
from app.database import Base


class LineItem(Base):
    """Line Item model matching lakemeter.line_items table."""
    
    __tablename__ = "line_items"
    __table_args__ = {"schema": "lakemeter"}
    
    line_item_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    estimate_id = Column(UUID(as_uuid=True), ForeignKey("lakemeter.estimates.estimate_id"), nullable=False)
    display_order = Column(Integer, default=0)
    workload_name = Column(String(255), nullable=False)
    workload_type = Column(String(50), ForeignKey("lakemeter.ref_workload_types.workload_type"))
    
    # Serverless toggle
    is_serverless = Column(Boolean, default=False)
    serverless_performance_mode = Column(String(20))  # standard, optimized
    
    # Classic Compute Configuration
    driver_node_type = Column(String(100))
    worker_node_type = Column(String(100))
    num_workers = Column(Integer, default=1)
    autoscale_enabled = Column(Boolean, default=False)
    autoscale_min_workers = Column(Integer)
    autoscale_max_workers = Column(Integer)
    photon_enabled = Column(Boolean, default=False)
    
    # DLT Configuration
    dlt_edition = Column(String(20))  # core, pro, advanced
    dlt_pipeline_mode = Column(String(20))  # triggered, continuous
    
    # DBSQL Configuration
    dbsql_warehouse_type = Column(String(20))  # classic, pro, serverless
    dbsql_warehouse_size = Column(String(20))  # 2x-small, x-small, small, medium, large, x-large, etc.
    
    # Vector Search Configuration
    vector_search_endpoint_type = Column(String(50))
    vector_search_mode = Column(String(20))  # delta_sync, direct_access
    
    # Lakebase Configuration
    lakebase_instance_type = Column(String(50))
    lakebase_storage_gb = Column(Integer)
    
    # Foundation Model API Configuration
    fmapi_provider = Column(String(50))
    fmapi_model = Column(String(100))
    fmapi_endpoint_type = Column(String(20))
    fmapi_context_length = Column(String(20))
    fmapi_input_tokens_per_month = Column(BIGINT)
    fmapi_output_tokens_per_month = Column(BIGINT)
    
    # Usage Configuration
    hours_per_day = Column(Numeric(10, 2))
    days_per_month = Column(Integer, default=22)
    runs_per_day = Column(Integer)
    avg_runtime_minutes = Column(Integer)
    
    # Pricing Configuration
    vm_pricing_tier = Column(String(20))  # on-demand, 1yr, 3yr
    vm_payment_option = Column(String(20))  # no-upfront, partial-upfront, all-upfront
    spot_percentage = Column(Integer, default=0)
    
    # Computed SKU (based on workload type and configuration)
    selected_sku = Column(String(100))
    
    # Additional Configuration
    workload_config = Column(JSON)  # Flexible JSON for additional config
    notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    estimate = relationship("Estimate", back_populates="line_items")
    workload_type_ref = relationship("RefWorkloadType", back_populates="line_items")
    decision_records = relationship("DecisionRecord", back_populates="line_item", cascade="all, delete-orphan")


