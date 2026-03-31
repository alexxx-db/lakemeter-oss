"""Calculation functions for export (hours, DBU/hr, serverless detection)."""
from .pricing import (
    INSTANCE_DBU_RATES, VECTOR_SEARCH_RATES, MODEL_SERVING_RATES,
)


def _calculate_hours_per_month(item) -> float:
    """Calculate hours per month from usage config.

    Priority: If run-based fields (runs_per_day, avg_runtime_minutes) are set,
    calculate from those. Only fall back to hours_per_month if no run-based data.
    This prevents hours_per_month=730 default from overriding user's run config.
    """
    if item.runs_per_day and item.avg_runtime_minutes:
        runs = float(item.runs_per_day)
        runtime = float(item.avg_runtime_minutes)
        days = float(item.days_per_month or 22)
        return (runs * runtime / 60) * days
    if item.hours_per_month:
        return float(item.hours_per_month)
    # No usage data provided — return 0 (consistent with frontend)
    return 0


def _calculate_dbu_per_hour(item, cloud: str = 'aws') -> tuple:
    """Calculate DBU per hour for a workload. Returns (dbu_per_hour, warnings)."""
    wt = item.workload_type or ''
    warnings = []

    if wt in ('JOBS', 'ALL_PURPOSE', 'DLT'):
        return _calc_compute_dbu(item, cloud, wt, warnings)
    elif wt == 'DBSQL':
        return _calc_dbsql_dbu(item, warnings)
    elif wt == 'VECTOR_SEARCH':
        return _calc_vector_search_dbu(item, cloud, warnings)
    elif wt == 'MODEL_SERVING':
        return _calc_model_serving_dbu(item, cloud, warnings)
    elif wt in ('FMAPI_DATABRICKS', 'FMAPI_PROPRIETARY'):
        return 0, warnings  # FMAPI uses token-based, not hour-based
    elif wt == 'LAKEBASE':
        cu = float(item.lakebase_cu or 0)
        nodes = float(item.lakebase_ha_nodes or 1)
        if cu == 0:
            warnings.append("Lakebase CU not specified")
        return cu * nodes, warnings
    elif wt == 'DATABRICKS_APPS':
        return 1.0, warnings
    return 0, warnings


def _calc_compute_dbu(item, cloud, wt, warnings):
    """Calculate DBU/hr for Jobs, All-Purpose, or DLT workloads."""
    driver_dbu = 0.25
    worker_dbu = 0.5
    driver_found = False
    worker_found = False
    if INSTANCE_DBU_RATES:
        cloud_instances = INSTANCE_DBU_RATES.get(cloud, {})
        if item.driver_node_type and item.driver_node_type in cloud_instances:
            driver_dbu = cloud_instances[item.driver_node_type].get('dbu_rate', 0.25)
            driver_found = True
        if item.worker_node_type and item.worker_node_type in cloud_instances:
            worker_dbu = cloud_instances[item.worker_node_type].get('dbu_rate', 0.5)
            worker_found = True
    if not driver_found and item.driver_node_type:
        warnings.append(f"Driver DBU rate not found for {item.driver_node_type}, using 0.25")
    if not worker_found and item.worker_node_type:
        warnings.append(f"Worker DBU rate not found for {item.worker_node_type}, using 0.5")

    num_workers = int(item.num_workers or 0)
    base_dbu = float(driver_dbu) + (float(worker_dbu) * num_workers)

    if item.serverless_enabled:
        base_dbu *= 2  # Serverless always has photon built-in (2x)
        # ALL_PURPOSE Serverless only supports Performance mode (always 2x)
        if wt == 'ALL_PURPOSE':
            mode_multiplier = 2
        else:
            mode_multiplier = 2 if item.serverless_mode == 'performance' else 1
        return base_dbu * mode_multiplier, warnings

    if item.photon_enabled:
        base_dbu *= 2
    return base_dbu, warnings


def _calc_dbsql_dbu(item, warnings):
    """Calculate DBU/hr for DBSQL workloads."""
    size_dbu = {
        '2X-Small': 4, 'X-Small': 6, 'Small': 12, 'Medium': 24,
        'Large': 40, 'X-Large': 80, '2X-Large': 144, '3X-Large': 272, '4X-Large': 528
    }
    wh_size = item.dbsql_warehouse_size
    if not wh_size or wh_size.strip() == '':
        wh_size = 'Small'
        warnings.append("Empty warehouse size, defaulting to Small")
    if wh_size not in size_dbu:
        warnings.append(f"Unknown DBSQL warehouse size '{wh_size}', using Small (12 DBU)")
        wh_size = 'Small'
    num_clusters = max(1, int(item.dbsql_num_clusters or 1))
    return float(size_dbu[wh_size] * num_clusters), warnings


def _calc_vector_search_dbu(item, cloud, warnings):
    """Calculate DBU/hr for Vector Search workloads."""
    capacity = max(float(item.vector_capacity_millions or 0), 0)
    if capacity == 0:
        warnings.append("Vector capacity not specified, using 0")
    mode = item.vector_search_mode or 'standard'
    key = f"{cloud}:{mode}"
    info = VECTOR_SEARCH_RATES.get(key, {})
    if not info:
        warnings.append(f"Vector Search rates not found for {key}, using defaults")
    dbu_rate = info.get('dbu_rate', 4.0 if mode == 'standard' else 18.29)
    divisor = info.get('input_divisor', 2000000)
    units = capacity * 1_000_000 / divisor if divisor else 0
    return units * dbu_rate, warnings


def _calc_model_serving_dbu(item, cloud, warnings):
    """Calculate DBU/hr for Model Serving workloads."""
    gpu_type = item.model_serving_gpu_type or 'cpu'
    key = f"{cloud}:{gpu_type}"
    info = MODEL_SERVING_RATES.get(key, {})
    if not info:
        warnings.append(f"Model Serving rate not found for {key}")
        return 0, warnings
    return info.get('dbu_rate', 0), warnings


def _is_serverless_workload(item) -> bool:
    """Check if workload is serverless (no VM costs)."""
    wt = item.workload_type or ''
    if wt in ('VECTOR_SEARCH', 'MODEL_SERVING', 'FMAPI_DATABRICKS', 'FMAPI_PROPRIETARY',
              'LAKEBASE', 'DATABRICKS_APPS'):
        return True
    if wt in ('JOBS', 'ALL_PURPOSE', 'DLT') and item.serverless_enabled:
        return True
    if wt == 'DBSQL' and (item.dbsql_warehouse_type or '').upper() == 'SERVERLESS':
        return True
    return False


