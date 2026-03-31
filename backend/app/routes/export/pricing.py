"""Pricing data loading and lookup functions for export."""
import json
import os

# ========== LOAD PRICING DATA FROM STATIC JSON ==========
_PRICING_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'static', 'pricing')


def _load_json(filename: str) -> dict:
    path = os.path.join(_PRICING_DIR, filename)
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return {}


# Load once at import time
DBU_RATES_BY_REGION = _load_json('dbu-rates.json')
INSTANCE_DBU_RATES = _load_json('instance-dbu-rates.json')
MODEL_SERVING_RATES = _load_json('model-serving-rates.json')
FMAPI_DB_RATES = _load_json('fmapi-databricks-rates.json')
FMAPI_PROP_RATES = _load_json('fmapi-proprietary-rates.json')
VECTOR_SEARCH_RATES = _load_json('vector-search-rates.json')
DBSQL_RATES = _load_json('dbsql-rates.json')

# Fallback DBU $/DBU rates (aws:us-east-1:PREMIUM)
FALLBACK_DBU_PRICES = {
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


def _get_dbu_price(cloud: str, region: str, tier: str, sku: str) -> tuple:
    """Look up $/DBU from pricing JSON. Returns (price, found) tuple."""
    key = f"{cloud}:{region}:{tier.upper()}"
    region_rates = DBU_RATES_BY_REGION.get(key, {})
    if sku in region_rates:
        return region_rates[sku], True
    # Try without region specificity - find any matching cloud:*:tier
    for k, v in DBU_RATES_BY_REGION.items():
        parts = k.split(':')
        if len(parts) == 3 and parts[0] == cloud and parts[2] == tier.upper() and sku in v:
            return v[sku], True
    # Fallback — mark as not found so notes can warn
    fallback = FALLBACK_DBU_PRICES.get(sku, 0)
    return fallback, False


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
        info = FMAPI_DB_RATES.get(key, {})
        return info.get('sku_product_type', 'SERVERLESS_REAL_TIME_INFERENCE')
    elif wt == 'FMAPI_PROPRIETARY':
        provider = item.fmapi_provider or ''
        endpoint = getattr(item, 'fmapi_endpoint_type', 'global') or 'global'
        default_ctx = 'long' if provider == 'google' else 'all'
        context = getattr(item, 'fmapi_context_length', default_ctx) or default_ctx
        key = f"{cloud}:{provider}:{model}:{endpoint}:{context}:{rate_type}"
        info = FMAPI_PROP_RATES.get(key, {})
        return info.get('sku_product_type', 'OPENAI_MODEL_SERVING')
    return 'SERVERLESS_REAL_TIME_INFERENCE'


def _get_fmapi_dbu_per_million(item, cloud: str) -> tuple:
    """Get DBU per 1M tokens (or DBU/hr for provisioned) from pricing JSON.

    Returns (dbu_rate, found) tuple. found=False means no match in pricing data.
    """
    rate_type = item.fmapi_rate_type or 'input_token'
    model = item.fmapi_model or ''
    wt = item.workload_type or ''

    if wt == 'FMAPI_DATABRICKS':
        key = f"{cloud}:{model}:{rate_type}"
        info = FMAPI_DB_RATES.get(key, {})
        if 'dbu_rate' in info:
            return info['dbu_rate'], True
        key_lower = key.lower().strip()
        for k, v in FMAPI_DB_RATES.items():
            if k.lower().strip() == key_lower:
                return v.get('dbu_rate', 0), True
        return 0, False
    elif wt == 'FMAPI_PROPRIETARY':
        provider = item.fmapi_provider or ''
        endpoint = getattr(item, 'fmapi_endpoint_type', 'global') or 'global'
        default_ctx = 'long' if provider == 'google' else 'all'
        context = getattr(item, 'fmapi_context_length', default_ctx) or default_ctx
        key = f"{cloud}:{provider}:{model}:{endpoint}:{context}:{rate_type}"
        info = FMAPI_PROP_RATES.get(key, {})
        if 'dbu_rate' in info:
            return info['dbu_rate'], True
        key_lower = key.lower().strip()
        for k, v in FMAPI_PROP_RATES.items():
            if k.lower().strip() == key_lower:
                return v.get('dbu_rate', 0), True
        return 0, False
    return 0, False


def _is_fmapi_hourly(item, cloud: str) -> bool:
    """Check if FMAPI rate is hourly (provisioned) vs token-based."""
    rate_type = item.fmapi_rate_type or 'input_token'
    return rate_type in ('provisioned_scaling', 'provisioned_entry', 'batch_inference')
