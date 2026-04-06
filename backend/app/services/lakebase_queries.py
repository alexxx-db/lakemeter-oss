"""
Shared Lakebase SQL query functions.
Used by reference and calculation route modules.
"""
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


def get_dbu_rate(db: Session, cloud: str, region: str, tier: str, product_type: str) -> Optional[Dict]:
    """Get DBU rate for a product type in a specific cloud/region/tier."""
    query = text("""
        SELECT dbu_price, dbu_per_hour
        FROM lakemeter.sync_pricing_dbu_rates
        WHERE UPPER(cloud) = UPPER(:cloud)
          AND UPPER(region) = UPPER(:region)
          AND UPPER(tier) = UPPER(:tier)
          AND UPPER(product_type) = UPPER(:product_type)
        LIMIT 1
    """)
    result = db.execute(query, {
        "cloud": cloud, "region": region, "tier": tier, "product_type": product_type,
    })
    row = result.fetchone()
    if not row:
        return None
    return {"dbu_price": float(row.dbu_price), "dbu_per_hour": float(row.dbu_per_hour) if row.dbu_per_hour else None}


def get_instance_info(db: Session, cloud: str, instance_type: str) -> Optional[Dict]:
    """Get instance specs (vCPU, memory, family, DBU rate)."""
    query = text("""
        SELECT instance_type, vcpus, memory_gb, instance_family, dbu_rate
        FROM lakemeter.sync_ref_instance_dbu_rates
        WHERE cloud = :cloud AND instance_type = :instance_type
    """)
    result = db.execute(query, {"cloud": cloud.upper(), "instance_type": instance_type})
    row = result.fetchone()
    if not row:
        return None
    return {
        "instance_type": row.instance_type,
        "vcpus": row.vcpus,
        "memory_gb": float(row.memory_gb),
        "instance_family": row.instance_family,
        "dbu_rate": float(row.dbu_rate),
    }


def get_vm_cost(
    db: Session, cloud: str, region: str, instance_type: str,
    pricing_tier: str = "on_demand", payment_option: str = "NA",
) -> Optional[float]:
    """Get VM cost per hour for a specific instance/region/pricing config."""
    query = text("""
        SELECT cost_per_hour
        FROM lakemeter.sync_pricing_vm_costs
        WHERE UPPER(cloud) = UPPER(:cloud)
          AND region = :region
          AND instance_type = :instance_type
          AND pricing_tier = :pricing_tier
          AND COALESCE(payment_option, 'NA') = :payment_option
        LIMIT 1
    """)
    result = db.execute(query, {
        "cloud": cloud, "region": region, "instance_type": instance_type,
        "pricing_tier": pricing_tier, "payment_option": payment_option,
    })
    row = result.fetchone()
    return float(row.cost_per_hour) if row else None


def get_product_type_for_pricing(
    db: Session, workload_type: str, serverless_enabled: bool = False,
    photon_enabled: bool = False, dlt_edition: str = None,
    dbsql_warehouse_type: str = None, fmapi_provider: str = None,
) -> Optional[str]:
    """Call the lakemeter.get_product_type_for_pricing() SQL function."""
    query = text("""
        SELECT lakemeter.get_product_type_for_pricing(
            :workload_type, :serverless_enabled, :photon_enabled,
            :dlt_edition, :dbsql_warehouse_type, :fmapi_provider
        ) as product_type
    """)
    result = db.execute(query, {
        "workload_type": workload_type.upper(),
        "serverless_enabled": serverless_enabled,
        "photon_enabled": photon_enabled,
        "dlt_edition": dlt_edition.upper() if dlt_edition else None,
        "dbsql_warehouse_type": dbsql_warehouse_type.upper() if dbsql_warehouse_type else None,
        "fmapi_provider": fmapi_provider.upper() if fmapi_provider else None,
    })
    row = result.fetchone()
    return row.product_type if row and row.product_type else None


def call_calculate_line_item_costs(db: Session, params: Dict[str, Any]):
    """
    Call the lakemeter.calculate_line_item_costs() PostgreSQL function.
    Accepts params dict with keys p1-p35 matching the 35 positional parameters.
    Returns a SQLAlchemy row object, or None on failure.
    """
    query = text("""
        SELECT
            dbu_per_hour, hours_per_month, dbu_per_month, dbu_price,
            dbu_cost_per_month, driver_vm_cost_per_hour, worker_vm_cost_per_hour,
            total_vm_cost_per_hour, driver_vm_cost_per_month,
            total_worker_vm_cost_per_month, vm_cost_per_month, cost_per_month
        FROM lakemeter.calculate_line_item_costs(
            :p1, :p2, :p3, :p4, :p5, :p6, :p7, :p8, :p9, :p10,
            :p11, :p12, :p13, :p14, :p15, :p16, :p17, :p18, :p19, :p20,
            :p21, :p22, :p23, :p24, :p25, :p26, :p27, :p28, :p29, :p30,
            :p31, :p32, :p33, :p34, :p35
        )
    """)
    try:
        result = db.execute(query, params)
        return result.fetchone()
    except Exception as e:
        logger.error(f"calculate_line_item_costs failed: {e}")
        raise


def get_sku_type(
    workload_type: str, serverless_enabled: bool = False,
    photon_enabled: bool = False, dlt_edition: str = None,
    dbsql_warehouse_type: str = None, fmapi_provider: str = None,
) -> str:
    """Determine the SKU product type based on workload configuration."""
    wt = workload_type.upper()

    if wt == "JOBS":
        if serverless_enabled:
            return "JOBS_SERVERLESS_COMPUTE"
        return "JOBS_COMPUTE_(PHOTON)" if photon_enabled else "JOBS_COMPUTE"

    if wt == "ALL_PURPOSE":
        if serverless_enabled:
            return "INTERACTIVE_SERVERLESS_COMPUTE"
        return "ALL_PURPOSE_COMPUTE_(PHOTON)" if photon_enabled else "ALL_PURPOSE_COMPUTE"

    if wt == "DLT":
        if serverless_enabled:
            return "DELTA_LIVE_TABLES_SERVERLESS"
        edition = (dlt_edition or "CORE").upper()
        base = f"DLT_{edition}_COMPUTE"
        return f"{base}_(PHOTON)" if photon_enabled else base

    if wt == "DBSQL":
        wh = (dbsql_warehouse_type or "CLASSIC").upper()
        if wh == "SERVERLESS":
            return "SERVERLESS_SQL_COMPUTE"
        return "SQL_PRO_COMPUTE" if wh == "PRO" else "SQL_COMPUTE"

    if wt == "VECTOR_SEARCH":
        return "VECTOR_SEARCH_ENDPOINT"
    if wt == "MODEL_SERVING":
        return "SERVERLESS_REAL_TIME_INFERENCE"
    if wt == "FMAPI_DATABRICKS":
        return "SERVERLESS_REAL_TIME_INFERENCE"
    if wt == "FMAPI_PROPRIETARY":
        return f"{fmapi_provider.upper()}_MODEL_SERVING" if fmapi_provider else "MODEL_SERVING"
    if wt == "LAKEBASE":
        return "DATABASE_SERVERLESS_COMPUTE"

    return "JOBS_COMPUTE"
