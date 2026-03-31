"""Calculation and display helper functions for export."""
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Estimate, User
from app.models.sharing import Sharing
from .pricing import (
    INSTANCE_DBU_RATES, VECTOR_SEARCH_RATES, MODEL_SERVING_RATES,
)


def _check_estimate_access(estimate_id: UUID, user: User, db: Session) -> Estimate:
    """Check if user has access to an estimate."""
    estimate = db.query(Estimate).filter(
        Estimate.estimate_id == estimate_id,
        Estimate.is_deleted == False
    ).first()
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")
    is_owner = estimate.owner_user_id == user.user_id
    is_shared = db.query(Sharing).filter(
        Sharing.estimate_id == estimate_id,
        Sharing.shared_with_user_id == user.user_id
    ).first() is not None
    if not is_owner and not is_shared:
        raise HTTPException(status_code=404, detail="Estimate not found")
    return estimate


def _get_workload_display_name(workload_type: str) -> str:
    """Get friendly display name for workload type."""
    names = {
        'JOBS': 'Lakeflow Job Compute',
        'ALL_PURPOSE': 'All-Purpose Compute',
        'DLT': 'Lakeflow Spark Declarative Pipelines',
        'DBSQL': 'Databricks SQL',
        'VECTOR_SEARCH': 'Vector Search',
        'MODEL_SERVING': 'Model Serving',
        'FMAPI_DATABRICKS': 'Foundation Models (Databricks)',
        'FMAPI_PROPRIETARY': 'Foundation Models (Proprietary)',
        'LAKEBASE': 'Lakebase',
        'DATABRICKS_APPS': 'Databricks Apps',
    }
    return names.get(workload_type, workload_type)


def _get_workload_config_details(item) -> str:
    """Get workload-specific configuration details for display."""
    wt = item.workload_type or ''
    details = []

    if wt in ('JOBS', 'ALL_PURPOSE', 'DLT') and item.serverless_enabled:
        serverless_mode = (item.serverless_mode or 'standard').capitalize()
        details.append(f"Mode: {serverless_mode}")

    if wt == 'DBSQL':
        if item.dbsql_warehouse_type:
            details.append(f"Type: {item.dbsql_warehouse_type}")
        if item.dbsql_warehouse_size:
            details.append(f"Size: {item.dbsql_warehouse_size}")
        if item.dbsql_num_clusters and item.dbsql_num_clusters > 1:
            details.append(f"Clusters: {item.dbsql_num_clusters}")
    elif wt == 'VECTOR_SEARCH':
        mode = item.vector_search_mode or 'standard'
        mode_display = 'Storage Optimized' if mode == 'storage_optimized' else 'Standard'
        details.append(f"Mode: {mode_display}")
        if item.vector_capacity_millions:
            details.append(f"Capacity: {item.vector_capacity_millions}M vectors")
    elif wt == 'MODEL_SERVING':
        if item.model_serving_gpu_type:
            gpu_names = {
                'cpu': 'CPU',
                'gpu_small_t4': 'Small (T4)',
                'gpu_medium_a10g_1x': 'Medium (A10G 1x)',
                'gpu_medium_a10g_4x': 'Medium (A10G 4x)',
                'gpu_medium_a10g_8x': 'Medium (A10G 8x)',
                'gpu_large_a10g_4x': 'Large (A10G 4x)',
                'gpu_medium_a100_1x': 'Medium (A100 1x)',
                'gpu_large_a100_2x': 'Large (A100 2x)',
                'gpu_xlarge_a100_40gb_8x': 'XLarge (A100 40GB 8x)',
                'gpu_xlarge_a100_80gb_8x': 'XLarge (A100 80GB 8x)',
                'gpu_xlarge_a100_80gb_1x': 'XLarge (A100 80GB 1x)',
                'gpu_2xlarge_a100_80gb_2x': '2XLarge (A100 80GB 2x)',
                'gpu_4xlarge_a100_80gb_4x': '4XLarge (A100 80GB 4x)',
            }
            details.append(f"GPU: {gpu_names.get(item.model_serving_gpu_type, item.model_serving_gpu_type)}")
    elif wt in ('FMAPI_DATABRICKS', 'FMAPI_PROPRIETARY'):
        if item.fmapi_model:
            details.append(f"Model: {item.fmapi_model}")
        if item.fmapi_rate_type:
            rate_type_display = {
                'input_token': 'Input Tokens',
                'output_token': 'Output Tokens',
                'provisioned_scaling': 'Provisioned Scaling',
                'provisioned_entry': 'Provisioned Entry',
            }
            details.append(f"Rate: {rate_type_display.get(item.fmapi_rate_type, item.fmapi_rate_type)}")
        if item.fmapi_quantity:
            if item.fmapi_rate_type in ('input_token', 'output_token'):
                details.append(f"Tokens: {float(item.fmapi_quantity):.1f}M/mo")
            else:
                details.append(f"Hours: {item.fmapi_quantity}")
    elif wt == 'LAKEBASE':
        if item.lakebase_cu:
            details.append(f"CU: {item.lakebase_cu}")
        if item.lakebase_ha_nodes:
            details.append(f"Nodes: {item.lakebase_ha_nodes}")
    elif wt == 'DLT':
        if item.dlt_edition:
            details.append(f"Edition: {item.dlt_edition.upper()}")
        if item.photon_enabled:
            details.append("Photon")
    elif wt == 'DATABRICKS_APPS':
        details.append("Managed App")

    return ' | '.join(details) if details else '-'


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
    wh_size = item.dbsql_warehouse_size or 'Small'
    if wh_size not in size_dbu:
        warnings.append(f"Unknown DBSQL warehouse size '{wh_size}', using Small (12 DBU)")
        wh_size = 'Small'
    return float(size_dbu[wh_size] * int(item.dbsql_num_clusters or 1)), warnings


def _calc_vector_search_dbu(item, cloud, warnings):
    """Calculate DBU/hr for Vector Search workloads."""
    capacity = float(item.vector_capacity_millions or 0)
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


def _get_pricing_tier_display(tier: str) -> str:
    displays = {
        'on_demand': 'On-Demand', 'spot': 'Spot',
        'reserved_1y': '1-Year Reserved', 'reserved_3y': '3-Year Reserved',
    }
    return displays.get(tier, tier or '-')
