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
        SELECT price_per_dbu
        FROM lakemeter.sync_pricing_dbu_rates
        WHERE UPPER(cloud) = UPPER(:cloud)
          AND UPPER(region) = UPPER(:region)
          AND UPPER(tier) = UPPER(:tier)
          AND (UPPER(product_type) = UPPER(:product_type) OR UPPER(sku_name) = UPPER(:product_type))
        LIMIT 1
    """)
    result = db.execute(query, {
        "cloud": cloud, "region": region, "tier": tier, "product_type": product_type,
    })
    row = result.fetchone()
    if not row:
        return None
    return {"dbu_price": float(row.price_per_dbu), "dbu_per_hour": None}


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


# Canonical parameter specification for lakemeter.calculate_line_item_costs().
# (semantic_key, sql_param_name, pg_type) — single source of truth replacing the
# fragile positional p1-p35 dicts that were duplicated across every calculator.
# Keep in sync with etl/lakebase_setup/functions/09_Main_Orchestrator.py.
LINE_ITEM_COST_PARAM_SPECS = [
    ("workload_type", "p_workload_type", "VARCHAR"),
    ("cloud", "p_cloud", "VARCHAR"),
    ("region", "p_region", "VARCHAR"),
    ("tier", "p_tier", "VARCHAR"),
    ("serverless_enabled", "p_serverless_enabled", "BOOLEAN"),
    ("photon_enabled", "p_photon_enabled", "BOOLEAN"),
    ("dlt_edition", "p_dlt_edition", "VARCHAR"),
    ("driver_node_type", "p_driver_node_type", "VARCHAR"),
    ("worker_node_type", "p_worker_node_type", "VARCHAR"),
    ("num_workers", "p_num_workers", "INT"),
    ("driver_pricing_tier", "p_driver_pricing_tier", "VARCHAR"),
    ("worker_pricing_tier", "p_worker_pricing_tier", "VARCHAR"),
    ("runs_per_day", "p_runs_per_day", "INT"),
    ("avg_runtime_minutes", "p_avg_runtime_minutes", "INT"),
    ("days_per_month", "p_days_per_month", "INT"),
    ("hours_per_month", "p_hours_per_month", "INT"),
    ("serverless_mode", "p_serverless_mode", "VARCHAR"),
    ("dbsql_warehouse_type", "p_dbsql_warehouse_type", "VARCHAR"),
    ("dbsql_warehouse_size", "p_dbsql_warehouse_size", "VARCHAR"),
    ("dbsql_num_clusters", "p_dbsql_num_clusters", "INT"),
    ("dbsql_vm_pricing_tier", "p_dbsql_vm_pricing_tier", "VARCHAR"),
    ("vector_search_mode", "p_vector_search_mode", "VARCHAR"),
    ("vector_search_capacity_millions", "p_vector_search_capacity_millions", "DECIMAL"),
    ("model_serving_gpu_type", "p_model_serving_gpu_type", "VARCHAR"),
    ("fmapi_model", "p_fmapi_model", "VARCHAR"),
    ("fmapi_provider", "p_fmapi_provider", "VARCHAR"),
    ("fmapi_endpoint_type", "p_fmapi_endpoint_type", "VARCHAR"),
    ("fmapi_context_length", "p_fmapi_context_length", "VARCHAR"),
    ("fmapi_rate_type", "p_fmapi_rate_type", "VARCHAR"),
    ("fmapi_quantity", "p_fmapi_quantity", "BIGINT"),
    ("lakebase_cu", "p_lakebase_cu", "INT"),
    ("lakebase_ha_nodes", "p_lakebase_ha_nodes", "INT"),
    ("driver_payment_option", "p_driver_payment_option", "VARCHAR"),
    ("worker_payment_option", "p_worker_payment_option", "VARCHAR"),
    ("dbsql_vm_payment_option", "p_dbsql_vm_payment_option", "VARCHAR"),
]

_SEMANTIC_KEYS = frozenset(key for key, _, _ in LINE_ITEM_COST_PARAM_SPECS)

_REQUIRED_PARAMS = ("workload_type", "cloud", "region", "tier")

_LINE_ITEM_COST_SQL = text(
    "SELECT "
    "dbu_per_hour, hours_per_month, dbu_per_month, dbu_price, "
    "dbu_cost_per_month, driver_vm_cost_per_hour, worker_vm_cost_per_hour, "
    "total_vm_cost_per_hour, driver_vm_cost_per_month, "
    "total_worker_vm_cost_per_month, vm_cost_per_month, cost_per_month "
    "FROM lakemeter.calculate_line_item_costs("
    + ", ".join(
        f"{sql_name} => CAST(:{semantic} AS {pg_type})"
        for semantic, sql_name, pg_type in LINE_ITEM_COST_PARAM_SPECS
    )
    + ")"
)


def call_calculate_line_item_costs(db: Session, params: Dict[str, Any]):
    """
    Call the lakemeter.calculate_line_item_costs() PostgreSQL function.

    Accepts a params dict keyed by SEMANTIC names (see LINE_ITEM_COST_PARAM_SPECS)
    and invokes the SQL function using PostgreSQL named-argument notation, so
    parameter order can never silently shift pricing. Unknown keys and missing
    required params are rejected before hitting the database.

    Returns a SQLAlchemy row object, or None on failure.
    """
    unknown = set(params) - _SEMANTIC_KEYS
    if unknown:
        raise ValueError(
            f"Unknown line-item cost params: {sorted(unknown)}. "
            f"Valid keys are defined in LINE_ITEM_COST_PARAM_SPECS."
        )
    missing = [key for key in _REQUIRED_PARAMS if not params.get(key)]
    if missing:
        raise ValueError(f"Missing required line-item cost params: {missing}")

    bind = {semantic: params.get(semantic) for semantic, _, _ in LINE_ITEM_COST_PARAM_SPECS}
    try:
        result = db.execute(_LINE_ITEM_COST_SQL, bind)
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
