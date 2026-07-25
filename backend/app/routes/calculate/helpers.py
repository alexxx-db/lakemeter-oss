"""Shared helper functions for calculation endpoints."""


def get_sku_type(
    workload_type: str,
    serverless_enabled: bool = False,
    photon_enabled: bool = False,
    dlt_edition: str = None,
    dbsql_warehouse_type: str = None,
    fmapi_provider: str = None,
) -> str:
    """Determine the SKU product type based on workload configuration."""
    workload_upper = workload_type.upper()

    if workload_upper == "JOBS":
        if serverless_enabled:
            return "JOBS_SERVERLESS_COMPUTE"
        elif photon_enabled:
            return "JOBS_COMPUTE_(PHOTON)"
        else:
            return "JOBS_COMPUTE"

    elif workload_upper == "ALL_PURPOSE":
        if serverless_enabled:
            return "INTERACTIVE_SERVERLESS_COMPUTE"
        elif photon_enabled:
            return "ALL_PURPOSE_COMPUTE_(PHOTON)"
        else:
            return "ALL_PURPOSE_COMPUTE"

    elif workload_upper == "DLT":
        if serverless_enabled:
            return "DELTA_LIVE_TABLES_SERVERLESS"
        else:
            edition = (dlt_edition or "CORE").upper()
            base = f"DLT_{edition}_COMPUTE"
            return f"{base}_(PHOTON)" if photon_enabled else base

    elif workload_upper == "DBSQL":
        warehouse_type_upper = (dbsql_warehouse_type or "CLASSIC").upper()
        if warehouse_type_upper == "SERVERLESS":
            return "SERVERLESS_SQL_COMPUTE"
        elif warehouse_type_upper == "PRO":
            return "SQL_PRO_COMPUTE"
        else:
            return "SQL_COMPUTE"

    elif workload_upper == "VECTOR_SEARCH":
        return "VECTOR_SEARCH_ENDPOINT"

    elif workload_upper == "MODEL_SERVING":
        return "SERVERLESS_REAL_TIME_INFERENCE"

    elif workload_upper == "FMAPI_DATABRICKS":
        return "SERVERLESS_REAL_TIME_INFERENCE"

    elif workload_upper == "FMAPI_PROPRIETARY":
        if fmapi_provider:
            return f"{fmapi_provider.upper()}_MODEL_SERVING"
        return "MODEL_SERVING"

    elif workload_upper == "LAKEBASE":
        return "DATABASE_SERVERLESS_COMPUTE"

    else:
        return "JOBS_COMPUTE"


def build_sku_breakdown_classic(
    sku_type: str,
    dbu_cost: float,
    dbu_quantity: float,
    dbu_price: float,
    driver_vm_cost: float,
    worker_vm_cost: float,
    hours_per_month: float,
    driver_vm_price_per_hour: float,
    worker_vm_price_per_hour: float,
    driver_pricing_tier: str,
    worker_pricing_tier: str,
    num_workers: int,
):
    """Build flat-list SKU breakdown for classic compute workloads."""
    breakdown = []

    if dbu_cost > 0:
        breakdown.append({
            "type": "dbu",
            "sku": sku_type,
            "cost": round(dbu_cost, 2),
            "qty": round(dbu_quantity, 2),
            "usage_unit": "DBU",
            "unit_price_before_discount": round(dbu_price, 6),
        })

    if driver_vm_cost > 0:
        breakdown.append({
            "type": "vm",
            "sku": f"VM_{driver_pricing_tier.upper()}",
            "cost": round(driver_vm_cost, 2),
            "qty": round(hours_per_month, 2),
            "usage_unit": "DBU",
            "unit_price_before_discount": round(driver_vm_price_per_hour, 6),
        })

    if worker_vm_cost > 0 and num_workers > 0:
        breakdown.append({
            "type": "vm",
            "sku": f"VM_{worker_pricing_tier.upper()}",
            "cost": round(worker_vm_cost, 2),
            "qty": round(hours_per_month * num_workers, 2),
            "usage_unit": "DBU",
            "unit_price_before_discount": round(worker_vm_price_per_hour, 6),
        })

    return breakdown


def build_sku_breakdown_serverless(
    sku_type: str,
    dbu_cost: float,
    dbu_quantity: float,
    dbu_price: float,
):
    """Build flat-list SKU breakdown for serverless workloads (DBU only)."""
    breakdown = []
    if dbu_cost > 0:
        breakdown.append({
            "type": "dbu",
            "sku": sku_type,
            "cost": round(dbu_cost, 2),
            "qty": round(dbu_quantity, 2),
            "usage_unit": "DBU",
            "unit_price_before_discount": round(dbu_price, 6),
        })
    return breakdown


def build_cost_params(
    *,
    workload_type,
    cloud,
    region,
    tier,
    serverless_enabled=False,
    photon_enabled=False,
    dlt_edition=None,
    driver_node_type=None,
    worker_node_type=None,
    num_workers=0,
    driver_pricing_tier="on_demand",
    worker_pricing_tier="on_demand",
    runs_per_day=0,
    avg_runtime_minutes=0,
    days_per_month=30,
    hours_per_month=None,
    serverless_mode="standard",
    dbsql_warehouse_type=None,
    dbsql_warehouse_size=None,
    dbsql_num_clusters=1,
    dbsql_vm_pricing_tier="on_demand",
    vector_search_mode=None,
    vector_search_capacity_millions=0,
    model_serving_gpu_type=None,
    fmapi_model=None,
    fmapi_provider=None,
    fmapi_endpoint_type="global",
    fmapi_context_length="all",
    fmapi_rate_type="input_token",
    fmapi_quantity=0,
    lakebase_cu=0,
    lakebase_ha_nodes=1,
    driver_payment_option="NA",
    worker_payment_option="NA",
    dbsql_vm_payment_option="NA",
):
    """Build semantic params for lakemeter.calculate_line_item_costs().

    Single place that defines the defaults previously duplicated as positional
    p1-p35 dicts in every calculator endpoint. Cloud/tier are normalized to
    uppercase. Keys must match LINE_ITEM_COST_PARAM_SPECS in
    app.services.lakebase_queries.
    """
    return {
        "workload_type": workload_type,
        "cloud": cloud.upper(),
        "region": region,
        "tier": tier.upper(),
        "serverless_enabled": serverless_enabled,
        "photon_enabled": photon_enabled,
        "dlt_edition": dlt_edition,
        "driver_node_type": driver_node_type,
        "worker_node_type": worker_node_type,
        "num_workers": num_workers,
        "driver_pricing_tier": driver_pricing_tier,
        "worker_pricing_tier": worker_pricing_tier,
        "runs_per_day": runs_per_day,
        "avg_runtime_minutes": avg_runtime_minutes,
        "days_per_month": days_per_month,
        "hours_per_month": hours_per_month,
        "serverless_mode": serverless_mode,
        "dbsql_warehouse_type": dbsql_warehouse_type,
        "dbsql_warehouse_size": dbsql_warehouse_size,
        "dbsql_num_clusters": dbsql_num_clusters,
        "dbsql_vm_pricing_tier": dbsql_vm_pricing_tier,
        "vector_search_mode": vector_search_mode,
        "vector_search_capacity_millions": vector_search_capacity_millions,
        "model_serving_gpu_type": model_serving_gpu_type,
        "fmapi_model": fmapi_model,
        "fmapi_provider": fmapi_provider,
        "fmapi_endpoint_type": fmapi_endpoint_type,
        "fmapi_context_length": fmapi_context_length,
        "fmapi_rate_type": fmapi_rate_type,
        "fmapi_quantity": fmapi_quantity,
        "lakebase_cu": lakebase_cu,
        "lakebase_ha_nodes": lakebase_ha_nodes,
        "driver_payment_option": driver_payment_option,
        "worker_payment_option": worker_payment_option,
        "dbsql_vm_payment_option": dbsql_vm_payment_option,
    }
