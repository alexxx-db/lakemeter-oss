"""Export API routes for Excel download."""
import json
import os
from uuid import UUID
from io import BytesIO
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import xlsxwriter

from app.database import get_db
from app.models import Estimate, LineItem, User
from app.models.sharing import Sharing
from app.auth import get_current_user

router = APIRouter(prefix="/export", tags=["export"])

# ========== LOAD PRICING DATA FROM STATIC JSON ==========
_PRICING_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'static', 'pricing')


def _load_json(filename: str) -> dict:
    path = os.path.join(_PRICING_DIR, filename)
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return {}


# Load once at import time
_DBU_RATES_BY_REGION = _load_json('dbu-rates.json')
_INSTANCE_DBU_RATES = _load_json('instance-dbu-rates.json')
_MODEL_SERVING_RATES = _load_json('model-serving-rates.json')
_FMAPI_DB_RATES = _load_json('fmapi-databricks-rates.json')
_FMAPI_PROP_RATES = _load_json('fmapi-proprietary-rates.json')
_VECTOR_SEARCH_RATES = _load_json('vector-search-rates.json')
_DBSQL_RATES = _load_json('dbsql-rates.json')

# Fallback DBU $/DBU rates (aws:us-east-1:PREMIUM)
_FALLBACK_DBU_PRICES = {
    'JOBS_COMPUTE': 0.15, 'JOBS_COMPUTE_(PHOTON)': 0.15,
    'JOBS_SERVERLESS_COMPUTE': 0.39,
    'ALL_PURPOSE_COMPUTE': 0.55, 'ALL_PURPOSE_COMPUTE_(PHOTON)': 0.55,
    'INTERACTIVE_SERVERLESS_COMPUTE': 0.83, 'ALL_PURPOSE_SERVERLESS_COMPUTE': 0.83,
    'DLT_CORE_COMPUTE': 0.20, 'DLT_PRO_COMPUTE': 0.25, 'DLT_ADVANCED_COMPUTE': 0.36,
    'DELTA_LIVE_TABLES_SERVERLESS': 0.50,
    'SQL_COMPUTE': 0.22, 'SQL_PRO_COMPUTE': 0.55, 'SERVERLESS_SQL_COMPUTE': 0.70,
    'VECTOR_SEARCH_ENDPOINT': 0.088,
    'SERVERLESS_REAL_TIME_INFERENCE': 0.07,
    'OPENAI_MODEL_SERVING': 0.07, 'ANTHROPIC_MODEL_SERVING': 0.07, 'GEMINI_MODEL_SERVING': 0.07,
    'FOUNDATION_MODEL_TRAINING': 0.20,
    'DATABASE_SERVERLESS_COMPUTE': 0.40,
    'DATABRICKS_APPS_COMPUTE': 0.07,
}


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


def _get_dbu_price(cloud: str, region: str, tier: str, sku: str) -> tuple[float, bool]:
    """Look up $/DBU from pricing JSON. Returns (price, found) tuple."""
    key = f"{cloud}:{region}:{tier.upper()}"
    region_rates = _DBU_RATES_BY_REGION.get(key, {})
    if sku in region_rates:
        return region_rates[sku], True
    # Try without region specificity - find any matching cloud:*:tier
    for k, v in _DBU_RATES_BY_REGION.items():
        parts = k.split(':')
        if len(parts) == 3 and parts[0] == cloud and parts[2] == tier.upper() and sku in v:
            return v[sku], True
    # Fallback — mark as not found so notes can warn
    fallback = _FALLBACK_DBU_PRICES.get(sku, 0)
    return fallback, False


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


def _get_sku_type(item, cloud: str = 'aws') -> str:
    """Determine the SKU/product type for a line item."""
    wt = item.workload_type or ''

    if wt == 'JOBS':
        if item.serverless_enabled:
            return 'JOBS_SERVERLESS_COMPUTE'
        elif item.photon_enabled:
            return 'JOBS_COMPUTE_(PHOTON)'
        return 'JOBS_COMPUTE'
    elif wt == 'ALL_PURPOSE':
        if item.serverless_enabled:
            return 'ALL_PURPOSE_SERVERLESS_COMPUTE'
        elif item.photon_enabled:
            return 'ALL_PURPOSE_COMPUTE_(PHOTON)'
        return 'ALL_PURPOSE_COMPUTE'
    elif wt == 'DLT':
        if item.serverless_enabled:
            return 'DELTA_LIVE_TABLES_SERVERLESS'
        edition = (item.dlt_edition or 'CORE').upper()
        return f'DLT_{edition}_COMPUTE'
    elif wt == 'DBSQL':
        warehouse_type = (item.dbsql_warehouse_type or 'SERVERLESS').upper()
        if warehouse_type == 'SERVERLESS':
            return 'SERVERLESS_SQL_COMPUTE'
        elif warehouse_type == 'PRO':
            return 'SQL_PRO_COMPUTE'
        return 'SQL_COMPUTE'
    elif wt == 'VECTOR_SEARCH':
        return 'VECTOR_SEARCH_ENDPOINT'
    elif wt == 'MODEL_SERVING':
        return 'SERVERLESS_REAL_TIME_INFERENCE'
    elif wt in ('FMAPI_DATABRICKS', 'FMAPI_PROPRIETARY'):
        # Look up actual SKU from pricing data
        return _get_fmapi_sku(item, cloud)
    elif wt == 'LAKEBASE':
        return 'DATABASE_SERVERLESS_COMPUTE'
    elif wt == 'DATABRICKS_APPS':
        return 'DATABRICKS_APPS_COMPUTE'
    return 'JOBS_COMPUTE'


def _get_fmapi_sku(item, cloud: str) -> str:
    """Get the actual SKU product type for FMAPI from pricing JSON."""
    rate_type = item.fmapi_rate_type or 'input_token'
    model = item.fmapi_model or ''
    wt = item.workload_type or ''

    if wt == 'FMAPI_DATABRICKS':
        key = f"{cloud}:{model}:{rate_type}"
        info = _FMAPI_DB_RATES.get(key, {})
        return info.get('sku_product_type', 'SERVERLESS_REAL_TIME_INFERENCE')
    elif wt == 'FMAPI_PROPRIETARY':
        provider = item.fmapi_provider or ''
        endpoint = getattr(item, 'fmapi_endpoint_type', 'global') or 'global'
        context = getattr(item, 'fmapi_context_length', 'all') or 'all'
        key = f"{cloud}:{provider}:{model}:{endpoint}:{context}:{rate_type}"
        info = _FMAPI_PROP_RATES.get(key, {})
        return info.get('sku_product_type', 'OPENAI_MODEL_SERVING')
    return 'SERVERLESS_REAL_TIME_INFERENCE'


def _get_fmapi_dbu_per_million(item, cloud: str) -> tuple[float, bool]:
    """Get DBU per 1M tokens (or DBU/hr for provisioned) from pricing JSON.

    Returns (dbu_rate, found) tuple. found=False means no match in pricing data.
    """
    rate_type = item.fmapi_rate_type or 'input_token'
    model = item.fmapi_model or ''
    wt = item.workload_type or ''

    if wt == 'FMAPI_DATABRICKS':
        key = f"{cloud}:{model}:{rate_type}"
        info = _FMAPI_DB_RATES.get(key, {})
        if 'dbu_rate' in info:
            return info['dbu_rate'], True
        # Try case-insensitive match
        key_lower = key.lower().strip()
        for k, v in _FMAPI_DB_RATES.items():
            if k.lower().strip() == key_lower:
                return v.get('dbu_rate', 0), True
        return 0, False
    elif wt == 'FMAPI_PROPRIETARY':
        provider = item.fmapi_provider or ''
        endpoint = getattr(item, 'fmapi_endpoint_type', 'global') or 'global'
        context = getattr(item, 'fmapi_context_length', 'all') or 'all'
        key = f"{cloud}:{provider}:{model}:{endpoint}:{context}:{rate_type}"
        info = _FMAPI_PROP_RATES.get(key, {})
        if 'dbu_rate' in info:
            return info['dbu_rate'], True
        # Try case-insensitive match
        key_lower = key.lower().strip()
        for k, v in _FMAPI_PROP_RATES.items():
            if k.lower().strip() == key_lower:
                return v.get('dbu_rate', 0), True
        return 0, False
    return 0, False


def _is_fmapi_hourly(item, cloud: str) -> bool:
    """Check if FMAPI rate is hourly (provisioned) vs token-based."""
    rate_type = item.fmapi_rate_type or 'input_token'
    return rate_type in ('provisioned_scaling', 'provisioned_entry')


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


def _calculate_dbu_per_hour(item, cloud: str = 'aws') -> tuple[float, list[str]]:
    """Calculate DBU per hour for a workload. Returns (dbu_per_hour, warnings)."""
    wt = item.workload_type or ''
    warnings = []

    if wt in ('JOBS', 'ALL_PURPOSE', 'DLT'):
        driver_dbu = 0.25
        worker_dbu = 0.5
        driver_found = False
        worker_found = False
        if _INSTANCE_DBU_RATES:
            cloud_instances = _INSTANCE_DBU_RATES.get(cloud, {})
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
            # Serverless compute always has photon built-in (2x multiplier)
            base_dbu *= 2
            # ALL_PURPOSE Serverless only supports Performance mode (always 2x)
            # Jobs/DLT Serverless support both Standard (1x) and Performance (2x)
            if wt == 'ALL_PURPOSE':
                mode_multiplier = 2
            else:
                mode_multiplier = 2 if item.serverless_mode == 'performance' else 1
            return base_dbu * mode_multiplier, warnings

        if item.photon_enabled:
            base_dbu *= 2

        return base_dbu, warnings

    elif wt == 'DBSQL':
        size_dbu = {
            '2X-Small': 4, 'X-Small': 6, 'Small': 12, 'Medium': 24,
            'Large': 40, 'X-Large': 80, '2X-Large': 144, '3X-Large': 272, '4X-Large': 528
        }
        wh_size = item.dbsql_warehouse_size or 'Small'
        if wh_size not in size_dbu:
            warnings.append(f"Unknown DBSQL warehouse size '{wh_size}', using Small (12 DBU)")
            wh_size = 'Small'
        return float(size_dbu[wh_size] * int(item.dbsql_num_clusters or 1)), warnings

    elif wt == 'VECTOR_SEARCH':
        capacity = float(item.vector_capacity_millions or 0)
        if capacity == 0:
            warnings.append("Vector capacity not specified, using 0")
        mode = item.vector_search_mode or 'standard'
        key = f"{cloud}:{mode}"
        info = _VECTOR_SEARCH_RATES.get(key, {})
        if not info:
            warnings.append(f"Vector Search rates not found for {key}, using defaults")
        dbu_rate = info.get('dbu_rate', 4.0 if mode == 'standard' else 18.29)
        divisor = info.get('input_divisor', 2000000)
        units = capacity * 1_000_000 / divisor if divisor else 0
        return units * dbu_rate, warnings

    elif wt == 'MODEL_SERVING':
        gpu_type = item.model_serving_gpu_type or 'cpu'
        key = f"{cloud}:{gpu_type}"
        info = _MODEL_SERVING_RATES.get(key, {})
        if not info:
            warnings.append(f"Model Serving rate not found for {key}")
            return 0, warnings
        return info.get('dbu_rate', 0), warnings

    elif wt in ('FMAPI_DATABRICKS', 'FMAPI_PROPRIETARY'):
        return 0, warnings  # FMAPI uses token-based, not hour-based

    elif wt == 'LAKEBASE':
        cu = float(item.lakebase_cu or 0)
        nodes = float(item.lakebase_ha_nodes or 1)
        if cu == 0:
            warnings.append("Lakebase CU not specified")
        return cu * nodes, warnings

    elif wt == 'DATABRICKS_APPS':
        return 1.0, warnings  # 1 DBU/hr per app instance

    return 0, warnings


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


@router.get("/estimate/{estimate_id}/excel")
def export_estimate_to_excel(
    estimate_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export an estimate to Excel format with professional RFP-ready layout."""
    try:
        return _build_estimate_excel(estimate_id, current_user, db)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Export error: {str(e)}")


def _build_estimate_excel(estimate_id: UUID, current_user: User, db: Session):
    """Internal: build the Excel export for an estimate."""
    estimate = _check_estimate_access(estimate_id, current_user, db)
    line_items = sorted(estimate.line_items, key=lambda x: x.display_order or 0)

    cloud = (getattr(estimate, 'cloud', 'aws') or 'aws').lower()
    region = getattr(estimate, 'region', 'us-east-1') or 'us-east-1'
    tier = getattr(estimate, 'tier', 'PREMIUM') or 'PREMIUM'

    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})

    # ========== DEFINE FORMATS ==========
    title_format = workbook.add_format({
        'bold': True, 'font_size': 18, 'font_color': '#1e293b',
        'bottom': 2, 'bottom_color': '#f97316'
    })
    subtitle_format = workbook.add_format({
        'font_size': 11, 'font_color': '#64748b', 'italic': True
    })
    section_header_format = workbook.add_format({
        'bold': True, 'font_size': 12, 'font_color': 'white',
        'bg_color': '#1e293b', 'border': 1, 'align': 'left', 'valign': 'vcenter'
    })
    header_main_format = workbook.add_format({
        'bold': True, 'font_size': 10, 'font_color': 'white',
        'bg_color': '#f97316', 'border': 1, 'align': 'center',
        'valign': 'vcenter', 'text_wrap': True
    })
    header_dbu_format = workbook.add_format({
        'bold': True, 'font_size': 10, 'font_color': 'white',
        'bg_color': '#3b82f6', 'border': 1, 'align': 'center',
        'valign': 'vcenter', 'text_wrap': True
    })
    header_token_format = workbook.add_format({
        'bold': True, 'font_size': 10, 'font_color': 'white',
        'bg_color': '#06b6d4', 'border': 1, 'align': 'center',
        'valign': 'vcenter', 'text_wrap': True
    })
    header_discount_format = workbook.add_format({
        'bold': True, 'font_size': 10, 'font_color': 'white',
        'bg_color': '#ec4899', 'border': 1, 'align': 'center',
        'valign': 'vcenter', 'text_wrap': True
    })
    header_vm_format = workbook.add_format({
        'bold': True, 'font_size': 10, 'font_color': 'white',
        'bg_color': '#10b981', 'border': 1, 'align': 'center',
        'valign': 'vcenter', 'text_wrap': True
    })
    header_total_format = workbook.add_format({
        'bold': True, 'font_size': 10, 'font_color': 'white',
        'bg_color': '#8b5cf6', 'border': 1, 'align': 'center',
        'valign': 'vcenter', 'text_wrap': True
    })

    cell_format = workbook.add_format({'border': 1, 'valign': 'vcenter', 'text_wrap': True})
    cell_center = workbook.add_format({'border': 1, 'valign': 'vcenter', 'align': 'center'})
    cell_mono = workbook.add_format({'border': 1, 'valign': 'vcenter', 'font_name': 'Consolas', 'font_size': 9})
    number_format = workbook.add_format({'border': 1, 'valign': 'vcenter', 'num_format': '#,##0', 'align': 'right'})
    decimal_format = workbook.add_format({'border': 1, 'valign': 'vcenter', 'num_format': '#,##0.00', 'align': 'right'})
    decimal3_format = workbook.add_format({'border': 1, 'valign': 'vcenter', 'num_format': '#,##0.000', 'align': 'right'})
    currency_format = workbook.add_format({'border': 1, 'valign': 'vcenter', 'num_format': '$#,##0.00', 'align': 'right'})
    pct_format = workbook.add_format({'border': 1, 'valign': 'vcenter', 'num_format': '0%', 'align': 'center'})

    dbu_currency_format = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'num_format': '$#,##0.00', 'align': 'right', 'bg_color': '#eff6ff'
    })
    discount_currency_format = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'num_format': '$#,##0.00', 'align': 'right', 'bg_color': '#fdf2f8'
    })
    vm_currency_format = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'num_format': '$#,##0.00', 'align': 'right', 'bg_color': '#ecfdf5'
    })
    total_currency_format = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'num_format': '$#,##0.00', 'align': 'right',
        'bg_color': '#f5f3ff', 'bold': True
    })
    token_cell_format = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'align': 'center', 'bg_color': '#ecfeff'
    })
    token_num_format = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'num_format': '#,##0.0', 'align': 'right', 'bg_color': '#ecfeff'
    })
    token_dbu_format = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'num_format': '#,##0.000', 'align': 'right', 'bg_color': '#ecfeff'
    })

    total_label_format = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#f1f5f9', 'align': 'right'})
    total_dbu_value = workbook.add_format({
        'bold': True, 'border': 1, 'bg_color': '#dbeafe', 'num_format': '$#,##0.00', 'align': 'right'
    })
    total_vm_value = workbook.add_format({
        'bold': True, 'border': 1, 'bg_color': '#d1fae5', 'num_format': '$#,##0.00', 'align': 'right'
    })
    total_grand_value = workbook.add_format({
        'bold': True, 'border': 1, 'bg_color': '#ede9fe', 'num_format': '$#,##0.00', 'align': 'right'
    })
    total_dbu_num = workbook.add_format({
        'bold': True, 'border': 1, 'bg_color': '#f1f5f9', 'num_format': '#,##0', 'align': 'right'
    })

    label_format = workbook.add_format({'bold': True, 'font_color': '#64748b', 'align': 'right'})
    value_format = workbook.add_format({'font_color': '#1e293b'})
    notes_format = workbook.add_format({'font_size': 9, 'font_color': '#64748b', 'italic': True, 'text_wrap': True})
    serverless_format = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'align': 'center', 'font_color': '#059669', 'italic': True
    })

    def get_val(obj, key, default=''):
        val = getattr(obj, key, default)
        return val if val is not None else default

    # ========== COLUMN LAYOUT ==========
    # 0:  #
    # 1:  Workload Name
    # 2:  Type
    # 3:  Mode
    # 4:  Configuration
    # 5:  SKU
    # 6:  Driver Node
    # 7:  Worker Node
    # 8:  Workers
    # 9:  Driver Tier
    # 10: Worker Tier
    # 11: Hours/Mo
    # 12: Token Type          (FMAPI only)
    # 13: Tokens/Mo (M)       (FMAPI only)
    # 14: DBU/1M Tokens       (FMAPI only)
    # 15: DBU/Hr
    # 16: DBUs/Mo
    # 17: DBU Rate (List)
    # 18: Discount %
    # 19: DBU Rate (Disc.)
    # 20: DBU Cost (List)
    # 21: DBU Cost (Disc.)
    # 22: Driver VM $/Hr
    # 23: Worker VM $/Hr
    # 24: Driver VM Cost
    # 25: Worker VM Cost
    # 26: Total VM Cost
    # 27: Total Cost (List)
    # 28: Total Cost (Disc.)
    # 29: Notes

    NUM_COLS = 30
    max_col = NUM_COLS - 1

    sheet = workbook.add_worksheet('Databricks Estimate')

    widths = [
        4,   # 0: #
        22,  # 1: Name
        18,  # 2: Type
        12,  # 3: Mode
        30,  # 4: Config
        22,  # 5: SKU
        18,  # 6: Driver Node
        18,  # 7: Worker Node
        8,   # 8: Workers
        12,  # 9: Driver Tier
        12,  # 10: Worker Tier
        10,  # 11: Hours/Mo
        12,  # 12: Token Type
        12,  # 13: Tokens/Mo (M)
        12,  # 14: DBU/1M Tokens
        10,  # 15: DBU/Hr
        12,  # 16: DBUs/Mo
        10,  # 17: DBU Rate (List)
        9,   # 18: Discount %
        10,  # 19: DBU Rate (Disc.)
        14,  # 20: DBU Cost (List)
        14,  # 21: DBU Cost (Disc.)
        12,  # 22: Driver VM $/Hr
        12,  # 23: Worker VM $/Hr
        12,  # 24: Driver VM Cost
        12,  # 25: Worker VM Cost
        12,  # 26: Total VM Cost
        14,  # 27: Total Cost (List)
        14,  # 28: Total Cost (Disc.)
        25,  # 29: Notes
    ]
    for i, w in enumerate(widths):
        sheet.set_column(i, i, w)

    row = 0

    # ========== HEADER SECTION ==========
    estimate_name = get_val(estimate, 'estimate_name', 'Untitled Estimate')

    sheet.merge_range(row, 0, row, max_col, 'Databricks Pricing Estimate', title_format)
    row += 1
    sheet.merge_range(row, 0, row, max_col, estimate_name, subtitle_format)
    row += 2

    # ========== ESTIMATE DETAILS ==========
    sheet.merge_range(row, 0, row, max_col, 'ESTIMATE DETAILS', section_header_format)
    row += 1

    cloud_display = cloud.upper()
    region_display = region
    tier_display = tier.upper()
    status = get_val(estimate, 'status', 'draft').capitalize()
    version = get_val(estimate, 'version', 1)
    created_at = get_val(estimate, 'created_at', datetime.utcnow())
    updated_at = get_val(estimate, 'updated_at', datetime.utcnow())
    if isinstance(created_at, datetime):
        created_at = created_at.strftime('%Y-%m-%d')
    if isinstance(updated_at, datetime):
        updated_at = updated_at.strftime('%Y-%m-%d')

    info_data = [
        [('Cloud:', cloud_display), ('Region:', region_display), ('Tier:', tier_display), ('Status:', status)],
        [('Version:', str(version)), ('Created:', created_at), ('Updated:', updated_at)],
    ]
    for info_row in info_data:
        col = 0
        for label_text, value_text in info_row:
            sheet.write(row, col, label_text, label_format)
            sheet.write(row, col + 1, value_text, value_format)
            col += 4
        row += 1
    row += 1

    # ========== WORKLOADS TABLE ==========
    sheet.merge_range(row, 0, row, max_col, 'WORKLOADS & COST BREAKDOWN', section_header_format)
    row += 1

    headers = [
        ('#', header_main_format),            # 0
        ('Workload Name', header_main_format), # 1
        ('Type', header_main_format),          # 2
        ('Mode', header_main_format),          # 3
        ('Configuration', header_main_format), # 4
        ('SKU', header_main_format),           # 5
        ('Driver Node', header_vm_format),     # 6
        ('Worker Node', header_vm_format),     # 7
        ('Workers', header_vm_format),         # 8
        ('Driver Tier', header_vm_format),     # 9
        ('Worker Tier', header_vm_format),     # 10
        ('Hours/Mo', header_dbu_format),       # 11
        ('Token Type', header_token_format),   # 12
        ('Tokens/Mo (M)', header_token_format),# 13
        ('DBU/1M Tokens', header_token_format),# 14
        ('DBU/Hr', header_dbu_format),         # 15
        ('DBUs/Mo', header_dbu_format),        # 16
        ('DBU Rate\n(List)', header_dbu_format),      # 17
        ('Discount %', header_discount_format),       # 18
        ('DBU Rate\n(Disc.)', header_discount_format), # 19
        ('DBU Cost\n(List)', header_dbu_format),       # 20
        ('DBU Cost\n(Disc.)', header_discount_format), # 21
        ('Driver\nVM $/Hr', header_vm_format),  # 22
        ('Worker\nVM $/Hr', header_vm_format),  # 23
        ('Driver\nVM Cost', header_vm_format),  # 24
        ('Worker\nVM Cost', header_vm_format),  # 25
        ('Total\nVM Cost', header_vm_format),   # 26
        ('Total Cost\n(List)', header_total_format),   # 27
        ('Total Cost\n(Disc.)', header_total_format),  # 28
        ('Notes', header_main_format),          # 29
    ]

    for col, (header, fmt) in enumerate(headers):
        sheet.write(row, col, header, fmt)

    header_row = row
    row += 1
    data_start_row = row

    # ========== HELPER: column letter from index ==========
    from xlsxwriter.utility import xl_col_to_name as _col

    def _write_row(sheet, row, row_data, is_fmapi_token, is_serverless, is_storage_row=False):
        """Write a single export row with formulas for all computed cells.

        row_data dict keys:
            idx, name, type_display, mode, config, sku, driver_node, worker_node,
            num_workers, driver_tier, worker_tier, hours_per_month, token_type,
            token_quantity_millions, dbu_per_million, dbu_per_hour, dbu_rate,
            discount_pct, driver_vm_cost_per_hour, worker_vm_cost_per_hour, notes
        """
        r = row + 1  # 1-indexed for Excel formulas

        # Col 0-5: static fields
        sheet.write(row, 0, row_data['idx'], cell_center)
        sheet.write(row, 1, row_data['name'], cell_format)
        sheet.write(row, 2, row_data['type_display'], cell_format)
        if is_serverless:
            sheet.write(row, 3, "Serverless", serverless_format)
        else:
            sheet.write(row, 3, "Classic", cell_center)
        sheet.write(row, 4, row_data['config'], cell_format)
        sheet.write(row, 5, row_data['sku'], cell_mono)

        # Col 6-10: VM config
        if is_serverless:
            for c in range(6, 11):
                sheet.write(row, c, '-', serverless_format)
        else:
            sheet.write(row, 6, row_data.get('driver_node', '-'), cell_mono)
            sheet.write(row, 7, row_data.get('worker_node', '-'), cell_mono)
            sheet.write(row, 8, row_data['num_workers'], number_format)
            sheet.write(row, 9, row_data.get('driver_tier', '-'), cell_center)
            sheet.write(row, 10, row_data.get('worker_tier', '-'), cell_center)

        # Col 11: Hours/Mo
        if is_fmapi_token:
            sheet.write(row, 11, 'N/A', token_cell_format)
        elif is_storage_row:
            sheet.write(row, 11, 'N/A', cell_center)
        else:
            sheet.write(row, 11, row_data['hours_per_month'], decimal_format)

        # Col 12-14: Token columns
        if is_fmapi_token:
            sheet.write(row, 12, row_data.get('token_type', ''), token_cell_format)
            sheet.write(row, 13, row_data['token_quantity_millions'], token_num_format)
            sheet.write(row, 14, row_data['dbu_per_million'], token_dbu_format)
        else:
            sheet.write(row, 12, '-', cell_center)
            sheet.write(row, 13, '-', cell_center)
            sheet.write(row, 14, '-', cell_center)

        # Col 15: DBU/Hr
        if is_fmapi_token:
            sheet.write(row, 15, 'N/A', token_cell_format)
        elif is_storage_row:
            sheet.write(row, 15, 'N/A', cell_center)
        else:
            sheet.write(row, 15, row_data['dbu_per_hour'], decimal_format)

        # Col 16: DBUs/Mo — FORMULA
        # For token-based: =N*O (tokens/mo × DBU/1M tokens)
        # For hour-based: =P*L (DBU/hr × hours/mo)
        # For storage rows: direct value (no DBU calc)
        total_dbus_month = row_data.get('total_dbus_month', 0)
        if is_storage_row:
            sheet.write(row, 16, 0, number_format)
        elif is_fmapi_token:
            formula = f'={_col(13)}{r}*{_col(14)}{r}'
            sheet.write_formula(row, 16, formula, number_format, total_dbus_month)
        else:
            formula = f'={_col(15)}{r}*{_col(11)}{r}'
            sheet.write_formula(row, 16, formula, number_format, total_dbus_month)

        # Col 17: DBU Rate (List)
        dbu_rate = row_data['dbu_rate']
        sheet.write(row, 17, dbu_rate, currency_format)

        # Col 18: Discount %
        discount_pct = row_data['discount_pct']
        sheet.write(row, 18, discount_pct, pct_format)

        # Col 19: DBU Rate (Disc.) — FORMULA: =R*(1-S)
        discounted_rate = dbu_rate * (1 - discount_pct)
        formula = f'={_col(17)}{r}*(1-{_col(18)}{r})'
        sheet.write_formula(row, 19, formula, currency_format, discounted_rate)

        # Col 20: DBU Cost (List) — FORMULA: =Q*R
        dbu_cost_list = total_dbus_month * dbu_rate
        if is_storage_row:
            # Storage: direct dollar cost, not DBU-based
            storage_cost = row_data.get('storage_cost_monthly', 0)
            sheet.write(row, 20, storage_cost, dbu_currency_format)
        else:
            formula = f'={_col(16)}{r}*{_col(17)}{r}'
            sheet.write_formula(row, 20, formula, dbu_currency_format, dbu_cost_list)

        # Col 21: DBU Cost (Disc.) — FORMULA: =Q*T
        dbu_cost_disc = total_dbus_month * discounted_rate
        if is_storage_row:
            storage_cost = row_data.get('storage_cost_monthly', 0)
            formula = f'={_col(20)}{r}*(1-{_col(18)}{r})'
            sheet.write_formula(row, 21, formula, discount_currency_format, storage_cost * (1 - discount_pct))
        else:
            formula = f'={_col(16)}{r}*{_col(19)}{r}'
            sheet.write_formula(row, 21, formula, discount_currency_format, dbu_cost_disc)

        # Col 22-26: VM costs
        driver_vm_hr = row_data.get('driver_vm_cost_per_hour', 0)
        worker_vm_hr = row_data.get('worker_vm_cost_per_hour', 0)
        hours = row_data.get('hours_per_month', 0)
        nw = row_data.get('num_workers', 1)

        if is_serverless or is_storage_row:
            for c in range(22, 27):
                sheet.write(row, c, 0, vm_currency_format)
        else:
            sheet.write(row, 22, driver_vm_hr, currency_format)
            sheet.write(row, 23, worker_vm_hr, currency_format)
            # Col 24: Driver VM Cost — FORMULA: =W*L
            driver_vm_total = driver_vm_hr * hours
            formula = f'={_col(22)}{r}*{_col(11)}{r}'
            sheet.write_formula(row, 24, formula, vm_currency_format, driver_vm_total)
            # Col 25: Worker VM Cost — FORMULA: =X*L*I
            worker_vm_total = worker_vm_hr * hours * nw
            formula = f'={_col(23)}{r}*{_col(11)}{r}*{_col(8)}{r}'
            sheet.write_formula(row, 25, formula, vm_currency_format, worker_vm_total)
            # Col 26: Total VM Cost — FORMULA: =Y+Z
            formula = f'={_col(24)}{r}+{_col(25)}{r}'
            sheet.write_formula(row, 26, formula, vm_currency_format, driver_vm_total + worker_vm_total)

        # Col 27: Total Cost (List) — FORMULA: =U+AA
        vm_total = 0
        if not is_serverless and not is_storage_row:
            vm_total = driver_vm_hr * hours + worker_vm_hr * hours * nw
        if is_storage_row:
            storage_cost = row_data.get('storage_cost_monthly', 0)
            formula = f'={_col(20)}{r}+{_col(26)}{r}'
            sheet.write_formula(row, 27, formula, total_currency_format, storage_cost)
        else:
            formula = f'={_col(20)}{r}+{_col(26)}{r}'
            sheet.write_formula(row, 27, formula, total_currency_format, dbu_cost_list + vm_total)

        # Col 28: Total Cost (Disc.) — FORMULA: =V+AA
        if is_storage_row:
            storage_cost = row_data.get('storage_cost_monthly', 0)
            formula = f'={_col(21)}{r}+{_col(26)}{r}'
            sheet.write_formula(row, 28, formula, total_currency_format, storage_cost * (1 - discount_pct))
        else:
            formula = f'={_col(21)}{r}+{_col(26)}{r}'
            sheet.write_formula(row, 28, formula, total_currency_format, dbu_cost_disc + vm_total)

        # Col 29: Notes
        sheet.write(row, 29, row_data.get('notes', ''), cell_format)

    # ========== WRITE LINE ITEMS ==========
    for idx, item in enumerate(line_items):
        wt = item.workload_type or 'JOBS'
        sku = _get_sku_type(item, cloud)
        dbu_rate, dbu_rate_found = _get_dbu_price(cloud, region, tier, sku)
        dbu_per_hour, dbu_warnings = _calculate_dbu_per_hour(item, cloud)
        is_serverless = _is_serverless_workload(item)
        is_fmapi = wt in ('FMAPI_DATABRICKS', 'FMAPI_PROPRIETARY')
        is_fmapi_token = is_fmapi and item.fmapi_rate_type in ('input_token', 'output_token', 'input', 'output')
        is_fmapi_provisioned = is_fmapi and item.fmapi_rate_type in ('provisioned_scaling', 'provisioned_entry')

        # Build notes
        user_notes = get_val(item, 'notes', '') or ''
        auto_notes = list(dbu_warnings)  # Start with DBU calc warnings
        if not dbu_rate_found:
            auto_notes.append(f"DBU rate not found for {sku}, using fallback ${dbu_rate:.2f}")

        # Calculate hours and FMAPI specifics
        if is_fmapi_token:
            hours_per_month = 0
            token_quantity_millions = float(item.fmapi_quantity or 0)
            dbu_per_million, fmapi_found = _get_fmapi_dbu_per_million(item, cloud)
            if not fmapi_found:
                auto_notes.append(f"FMAPI rate not found for {item.fmapi_model or 'unknown model'}")
            total_dbus_month = token_quantity_millions * dbu_per_million
            token_type = 'Input' if item.fmapi_rate_type in ('input_token', 'input') else 'Output'
        elif is_fmapi_provisioned:
            hours_per_month = float(item.fmapi_quantity or 0)
            dbu_per_million = 0
            token_quantity_millions = 0
            dbu_per_hour, fmapi_found = _get_fmapi_dbu_per_million(item, cloud)
            if not fmapi_found:
                auto_notes.append(f"FMAPI rate not found for {item.fmapi_model or 'unknown model'}")
            total_dbus_month = dbu_per_hour * hours_per_month
            token_type = ''
        else:
            hours_per_month = _calculate_hours_per_month(item)
            token_quantity_millions = 0
            dbu_per_million = 0
            total_dbus_month = dbu_per_hour * hours_per_month
            token_type = ''

        discount_pct = 0.0

        # VM costs
        driver_vm_cost_per_hour = 0
        worker_vm_cost_per_hour = 0
        num_workers = int(item.num_workers or 0)
        if not is_serverless and wt in ('JOBS', 'ALL_PURPOSE', 'DLT'):
            driver_vm_cost_per_hour = 0.20
            worker_vm_cost_per_hour = 0.10

        # Combine notes
        notes_parts = []
        if user_notes:
            notes_parts.append(user_notes)
        if auto_notes:
            notes_parts.append(' | '.join(auto_notes))
        combined_notes = ' — '.join(notes_parts) if notes_parts else ''

        # Base row data
        base_row = {
            'idx': idx + 1,
            'name': get_val(item, 'workload_name', f'Workload {idx + 1}'),
            'type_display': _get_workload_display_name(wt),
            'config': _get_workload_config_details(item),
            'sku': sku,
            'driver_node': get_val(item, 'driver_node_type', '-') or '-',
            'worker_node': get_val(item, 'worker_node_type', '-') or '-',
            'num_workers': num_workers,
            'driver_tier': _get_pricing_tier_display(item.driver_pricing_tier) if hasattr(item, 'driver_pricing_tier') else '-',
            'worker_tier': _get_pricing_tier_display(item.worker_pricing_tier) if hasattr(item, 'worker_pricing_tier') else '-',
            'hours_per_month': hours_per_month,
            'token_type': token_type if is_fmapi_token else '',
            'token_quantity_millions': token_quantity_millions,
            'dbu_per_million': dbu_per_million,
            'dbu_per_hour': dbu_per_hour,
            'total_dbus_month': total_dbus_month,
            'dbu_rate': dbu_rate,
            'discount_pct': discount_pct,
            'driver_vm_cost_per_hour': driver_vm_cost_per_hour,
            'worker_vm_cost_per_hour': worker_vm_cost_per_hour,
            'notes': combined_notes,
        }

        # Write the main compute row
        _write_row(sheet, row, base_row, is_fmapi_token, is_serverless)
        row += 1

        # === LAKEBASE: additional storage row ===
        if wt == 'LAKEBASE':
            storage_gb = float(item.lakebase_storage_gb or 0)
            storage_rate, _ = _get_dbu_price(cloud, region, tier, 'DATABRICKS_STORAGE')
            storage_cost = storage_gb * storage_rate

            storage_row = {
                'idx': '',
                'name': get_val(item, 'workload_name', f'Workload {idx + 1}'),
                'type_display': 'Lakebase (Storage)',
                'config': f'Storage: {storage_gb:.0f} GB',
                'sku': 'DATABRICKS_STORAGE',
                'driver_node': '-', 'worker_node': '-',
                'num_workers': 0,
                'driver_tier': '-', 'worker_tier': '-',
                'hours_per_month': 0,
                'token_type': '', 'token_quantity_millions': 0,
                'dbu_per_million': 0, 'dbu_per_hour': 0,
                'total_dbus_month': 0,
                'dbu_rate': storage_rate,
                'discount_pct': discount_pct,
                'driver_vm_cost_per_hour': 0, 'worker_vm_cost_per_hour': 0,
                'notes': f'${storage_rate}/GB/month × {storage_gb:.0f} GB',
                'storage_cost_monthly': storage_cost,
            }
            _write_row(sheet, row, storage_row, False, True, is_storage_row=True)
            row += 1

        # === VECTOR SEARCH: additional storage row ===
        if wt == 'VECTOR_SEARCH':
            capacity_m = float(item.vector_capacity_millions or 1)
            # Vector Search storage: estimate based on capacity
            # ~1KB per vector embedding, so capacity_m * 1e6 * 1KB = capacity_m GB
            estimated_storage_gb = capacity_m  # rough: 1M vectors ≈ 1 GB
            storage_rate, _ = _get_dbu_price(cloud, region, tier, 'DATABRICKS_STORAGE')
            storage_cost = estimated_storage_gb * storage_rate

            storage_row = {
                'idx': '',
                'name': get_val(item, 'workload_name', f'Workload {idx + 1}'),
                'type_display': 'Vector Search (Storage)',
                'config': f'Storage: ~{estimated_storage_gb:.1f} GB ({capacity_m:.0f}M vectors)',
                'sku': 'DATABRICKS_STORAGE',
                'driver_node': '-', 'worker_node': '-',
                'num_workers': 0,
                'driver_tier': '-', 'worker_tier': '-',
                'hours_per_month': 0,
                'token_type': '', 'token_quantity_millions': 0,
                'dbu_per_million': 0, 'dbu_per_hour': 0,
                'total_dbus_month': 0,
                'dbu_rate': storage_rate,
                'discount_pct': discount_pct,
                'driver_vm_cost_per_hour': 0, 'worker_vm_cost_per_hour': 0,
                'notes': f'${storage_rate}/GB/month × ~{estimated_storage_gb:.1f} GB',
                'storage_cost_monthly': storage_cost,
            }
            _write_row(sheet, row, storage_row, False, True, is_storage_row=True)
            row += 1

    data_end_row = row - 1

    # ========== TOTALS ROW ==========
    row += 1
    sheet.merge_range(row, 0, row, 15, 'TOTALS:', total_label_format)

    # DBUs/Mo total (col 16)
    if data_end_row >= data_start_row:
        ds = data_start_row + 1
        de = data_end_row + 1
        sheet.write_formula(row, 16, f'=SUM({_col(16)}{ds}:{_col(16)}{de})', total_dbu_num)
        for c in [17, 18, 19]:
            sheet.write(row, c, '', total_label_format)
        sheet.write_formula(row, 20, f'=SUM({_col(20)}{ds}:{_col(20)}{de})', total_dbu_value)
        sheet.write_formula(row, 21, f'=SUM({_col(21)}{ds}:{_col(21)}{de})', total_dbu_value)
        sheet.write(row, 22, '', total_label_format)
        sheet.write(row, 23, '', total_label_format)
        sheet.write_formula(row, 24, f'=SUM({_col(24)}{ds}:{_col(24)}{de})', total_vm_value)
        sheet.write_formula(row, 25, f'=SUM({_col(25)}{ds}:{_col(25)}{de})', total_vm_value)
        sheet.write_formula(row, 26, f'=SUM({_col(26)}{ds}:{_col(26)}{de})', total_vm_value)
        sheet.write_formula(row, 27, f'=SUM({_col(27)}{ds}:{_col(27)}{de})', total_grand_value)
        sheet.write_formula(row, 28, f'=SUM({_col(28)}{ds}:{_col(28)}{de})', total_grand_value)
        sheet.write(row, 29, '', total_label_format)
    else:
        for c in range(16, 20):
            sheet.write(row, c, '', total_label_format)
        for c in [20, 21, 24, 25, 26, 27, 28]:
            sheet.write(row, c, 0, total_dbu_value if c <= 21 else (total_vm_value if c <= 26 else total_grand_value))
        for c in [22, 23, 29]:
            sheet.write(row, c, '', total_label_format)

    totals_row = row
    row += 2

    # ========== COST SUMMARY ==========
    sheet.merge_range(row, 0, row, 7, 'COST SUMMARY', section_header_format)
    row += 1

    summary_headers = ['', 'DBU Cost\n(List)', 'DBU Cost\n(Disc.)', 'Driver VM', 'Worker VM', 'Total VM', 'Total (List)', 'Total (Disc.)']
    summary_fmts = [header_main_format, header_dbu_format, header_discount_format,
                    header_vm_format, header_vm_format, header_vm_format, header_total_format, header_total_format]
    for col, (h, f) in enumerate(zip(summary_headers, summary_fmts)):
        sheet.write(row, col, h, f)
    row += 1

    # Monthly: col20=DBU List, col21=DBU Disc, col24=Driver VM, col25=Worker VM, col26=Total VM, col27=Total List, col28=Total Disc
    sheet.write(row, 0, 'Monthly', cell_format)
    tr = totals_row + 1
    sheet.write_formula(row, 1, f'={_col(20)}{tr}', dbu_currency_format)
    sheet.write_formula(row, 2, f'={_col(21)}{tr}', discount_currency_format)
    sheet.write_formula(row, 3, f'={_col(24)}{tr}', vm_currency_format)
    sheet.write_formula(row, 4, f'={_col(25)}{tr}', vm_currency_format)
    sheet.write_formula(row, 5, f'={_col(26)}{tr}', vm_currency_format)
    sheet.write_formula(row, 6, f'={_col(27)}{tr}', total_currency_format)
    sheet.write_formula(row, 7, f'={_col(28)}{tr}', total_currency_format)
    monthly_row = row
    row += 1

    sheet.write(row, 0, 'Annual', cell_format)
    for c in range(1, 8):
        col_letter = chr(ord('B') + c - 1)
        sheet.write_formula(row, c, f'={col_letter}{monthly_row+1}*12',
                            [dbu_currency_format, discount_currency_format,
                             vm_currency_format, vm_currency_format, vm_currency_format,
                             total_currency_format, total_currency_format][c-1])
    row += 2

    # DBU Summary
    sheet.merge_range(row, 0, row, 1, 'Total DBUs/Month:', label_format)
    if data_end_row >= data_start_row:
        sheet.write_formula(row, 2, f'=SUM({_col(16)}{data_start_row+1}:{_col(16)}{data_end_row+1})', total_dbu_num)
    else:
        sheet.write(row, 2, 0, total_dbu_num)
    row += 2

    # ========== LEGEND ==========
    sheet.merge_range(row, 0, row, 7, 'LEGEND', section_header_format)
    row += 1

    legend_items = [
        ('Blue columns', 'DBU-related costs (Databricks compute units)'),
        ('Cyan columns', 'Token-based pricing (FMAPI workloads)'),
        ('Pink columns', 'Discount pricing (Discounted DBU Rate & Cost)'),
        ('Green columns', 'VM infrastructure costs (cloud provider)'),
        ('Purple columns', 'Total cost (DBU + VM)'),
        ('Serverless', 'No VM costs - compute is fully managed by Databricks'),
    ]
    for label_text, desc in legend_items:
        sheet.write(row, 0, f'• {label_text}:', label_format)
        sheet.merge_range(row, 1, row, 7, desc, value_format)
        row += 1
    row += 1

    # ========== ASSUMPTIONS & NOTES ==========
    sheet.merge_range(row, 0, row, max_col, 'ASSUMPTIONS & NOTES', section_header_format)
    row += 1

    assumptions = [
        "• This estimate is based on list pricing. Actual costs may vary based on negotiated discounts.",
        "• DBU rates are based on the selected cloud provider, region, and tier.",
        "• VM costs use default estimates. For exact VM pricing, consult your cloud provider.",
        "• FMAPI token workloads: cost = Tokens/Mo(M) × DBU/1M Tokens × $/DBU. No hourly usage.",
        "• Provisioned FMAPI workloads use Hours/Mo × DBU/Hr × $/DBU.",
        "• Discount % column is reserved for negotiated discounts (default 0% = list price).",
        "• Serverless workloads have no VM costs - compute is included in the DBU rate.",
        f"• Estimate exported: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}",
    ]
    for assumption in assumptions:
        sheet.merge_range(row, 0, row, max_col, assumption, notes_format)
        row += 1

    row += 1
    footer_format = workbook.add_format({'font_size': 9, 'font_color': '#94a3b8', 'align': 'center'})
    sheet.merge_range(row, 0, row, max_col,
                      f'Generated by Lakemeter • Databricks Pricing Calculator • {datetime.now().year}', footer_format)

    sheet.freeze_panes(header_row + 1, 2)
    sheet.set_landscape()
    sheet.fit_to_pages(1, 0)
    sheet.set_margins(left=0.25, right=0.25, top=0.5, bottom=0.5)

    workbook.close()
    output.seek(0)

    import re
    safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', estimate_name)[:50]
    filename = f"Databricks_Estimate_{safe_name}_{datetime.now().strftime('%Y%m%d')}.xlsx"

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/estimates/excel")
def export_all_estimates_to_excel(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export all estimates summary to Excel."""
    from sqlalchemy import or_

    shared_estimate_ids = db.query(Sharing.estimate_id).filter(
        Sharing.shared_with_user_id == current_user.user_id
    ).subquery()

    estimates = db.query(Estimate).filter(
        Estimate.is_deleted == False,
        or_(
            Estimate.owner_user_id == current_user.user_id,
            Estimate.estimate_id.in_(shared_estimate_ids)
        )
    ).order_by(Estimate.updated_at.desc()).all()

    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})

    header_format = workbook.add_format({
        'bold': True, 'bg_color': '#f97316', 'font_color': 'white', 'border': 1
    })
    cell_format = workbook.add_format({'border': 1})

    sheet = workbook.add_worksheet('All Estimates')

    headers = ['Estimate Name', 'Cloud', 'Region', 'Tier', 'Status', 'Version', 'Created', 'Updated']
    widths_list = [40, 15, 20, 15, 15, 10, 20, 20]

    for i, width in enumerate(widths_list):
        sheet.set_column(i, i, width)

    for col, header in enumerate(headers):
        sheet.write(0, col, header, header_format)

    def get_val_summary(obj, key, default=''):
        return getattr(obj, key, default) or default

    for r, est in enumerate(estimates, start=1):
        created = get_val_summary(est, 'created_at', '')
        updated = get_val_summary(est, 'updated_at', '')
        if isinstance(created, datetime):
            created = created.strftime('%Y-%m-%d %H:%M')
        if isinstance(updated, datetime):
            updated = updated.strftime('%Y-%m-%d %H:%M')

        sheet.write(r, 0, get_val_summary(est, 'estimate_name', ''), cell_format)
        sheet.write(r, 1, get_val_summary(est, 'cloud', ''), cell_format)
        sheet.write(r, 2, get_val_summary(est, 'region', ''), cell_format)
        sheet.write(r, 3, get_val_summary(est, 'tier', ''), cell_format)
        sheet.write(r, 4, get_val_summary(est, 'status', ''), cell_format)
        sheet.write(r, 5, get_val_summary(est, 'version', 1), cell_format)
        sheet.write(r, 6, created, cell_format)
        sheet.write(r, 7, updated, cell_format)

    workbook.close()
    output.seek(0)

    filename = f"Databricks_Estimates_Export_{datetime.now().strftime('%Y%m%d')}.xlsx"

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
