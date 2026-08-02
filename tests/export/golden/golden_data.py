"""Golden records for the canonical 9-workload combined estimate.

Every expected value below is derived INDEPENDENTLY from the static
pricing data (backend/static/pricing/*.json) and the documented
formulas — not copied from the code under test. If a pricing formula or
the static data changes intentionally, update these records IN THE SAME
PR and cite the new source. If a test here fails and you did not intend
a pricing change, the code regressed.

Sources:
- DBU $/DBU rates: backend/static/pricing/dbu-rates.json
  (aws:us-east-1:PREMIUM)
- Photon/serverless multipliers: referenced via _get_photon_multiplier
- DBSQL warehouse sizes: Databricks published t-shirt sizes
  (Small=12, Medium=24 DBU/hr per cluster)
- Vector Search: 1 endpoint unit per 2M vectors, 4.0 DBU/hr per unit
  (standard, aws); 3 units x 20 GB free storage
- Model Serving: gpu_medium_a10g_1x = 20.0 DBU/hr x concurrency 4
- FMAPI: fmapi-databricks-rates.json / fmapi-proprietary-rates.json
  (llama-3-3-70b input 7.143 DBU/M; claude-haiku-4-5 global/all output
  71.429 DBU/M)
- Lakebase: published Always-On autoscaling model (Databricks blog,
  May 2026) — baseline CU billed at 25% lower rate after 24h:
  min_cu x 0.230 DBU/CU-hr x 0.75 x ha_nodes (aws PREMIUM)
- Storage: DATABRICKS_STORAGE $0.023/DSU-GB; Lakebase 15 DSU/GB
"""

# One record per primary data row of the canonical combined estimate.
# hours='N/A' marks token-priced rows (no hour dimension).
GOLDEN_ROWS = [
    {
        # 0.5 base DBU/hr (frontend-matched fallback) x 2.9 serverless
        # photon multiplier x 2 performance mode = 2.9 DBU/hr
        'name': 'Jobs Serverless Perf',
        'sku': 'JOBS_SERVERLESS_COMPUTE',
        'hours': 200,
        'dbu_hr': 2.9,
        'rate': 0.35,
        'dbus_mo': 580.0,          # 2.9 x 200
        'dbu_cost': 203.00,        # 580 x 0.35
    },
    {
        # (0.5 driver + 0.5 x 2 workers) x 2.0 photon = 3.0 DBU/hr
        'name': 'All-Purpose Classic Photon',
        'sku': 'ALL_PURPOSE_COMPUTE_(PHOTON)',
        'hours': 730,
        'dbu_hr': 3.0,
        'rate': 0.55,
        'num_workers': 2,
        'dbus_mo': 2190.0,         # 3.0 x 730
        'dbu_cost': 1204.50,       # 2190 x 0.55
    },
    {
        # 0.5 base x 2.9 serverless multiplier x 1 standard mode = 1.45
        'name': 'DLT Pro Serverless',
        'sku': 'JOBS_SERVERLESS_COMPUTE',
        'hours': 100,
        'dbu_hr': 1.45,
        'rate': 0.35,
        'dbus_mo': 145.0,          # 1.45 x 100
        'dbu_cost': 50.75,         # 145 x 0.35
    },
    {
        # Medium warehouse = 24 DBU/hr x 1 cluster (published t-shirt size)
        'name': 'DBSQL Serverless Medium',
        'sku': 'SERVERLESS_SQL_COMPUTE',
        'hours': 500,
        'dbu_hr': 24.0,
        'rate': 0.70,
        'dbus_mo': 12000.0,        # 24 x 500
        'dbu_cost': 8400.00,       # 12000 x 0.70
    },
    {
        # 20.0 DBU/hr (A10G x1) x concurrency 4 = 80 DBU/hr
        'name': 'Model Serving GPU',
        'sku': 'SERVERLESS_REAL_TIME_INFERENCE',
        'hours': 200,
        'dbu_hr': 80.0,
        'rate': 0.07,
        'dbus_mo': 16000.0,        # 80 x 200
        'dbu_cost': 1120.00,       # 16000 x 0.07
    },
    {
        # 7.143 DBU/M input tokens x 100M = 714.3 DBU ($0.50/M effective)
        'name': 'FMAPI DB Llama Input',
        'sku': 'SERVERLESS_REAL_TIME_INFERENCE',
        'token_type': 'Input',
        'token_qty': 100,
        'dbu_per_m': 7.143,
        'rate': 0.07,
        'dbus_mo': 714.3,          # 100 x 7.143
        'dbu_cost': 50.001,        # 714.3 x 0.07
    },
    {
        # 71.429 DBU/M output tokens x 50M = 3571.45 DBU ($5.00/M effective)
        'name': 'FMAPI Anthropic Output',
        'sku': 'ANTHROPIC_MODEL_SERVING',
        'token_type': 'Output',
        'token_qty': 50,
        'dbu_per_m': 71.429,
        'rate': 0.07,
        'dbus_mo': 3571.45,        # 50 x 71.429
        'dbu_cost': 250.0015,      # 3571.45 x 0.07
    },
    {
        # ceil(5M / 2M per unit) = 3 units x 4.0 DBU/hr = 12 DBU/hr
        'name': 'Vector Search Standard 5M',
        'sku': 'SERVERLESS_REAL_TIME_INFERENCE',
        'hours': 730,
        'dbu_hr': 12.0,
        'rate': 0.07,
        'dbus_mo': 8760.0,         # 12 x 730
        'dbu_cost': 613.20,        # 8760 x 0.07
    },
    {
        # Published Always-On model: 4 CU x 0.230 DBU/CU-hr x 0.75
        # (25% baseline discount after 24h) x 2 HA nodes = 1.38 DBU/hr
        'name': 'Lakebase 4CU 2HA',
        'sku': 'DATABASE_SERVERLESS_COMPUTE',
        'hours': 730,
        'dbu_hr': 1.38,
        'rate': 0.40,
        'dbus_mo': 1007.4,         # 1.38 x 730
        'dbu_cost': 402.96,        # 1007.4 x 0.40
    },
]

# Storage sub-rows (written immediately after their parent row).
GOLDEN_STORAGE_ROWS = [
    {
        # 50 GB within the 60 GB free allowance (3 units x 20 GB) -> $0
        'parent': 'Vector Search Standard 5M',
        'type': 'Vector Search (Storage)',
        'sku': 'DATABRICKS_STORAGE',
        'rate': 0.023,
        'cost': 0,
        'note': ('50 GB total, 60 GB free (3 units × 20 GB), 0 GB billable '
                 '× $0.023/GB = $0.00/mo'),
    },
    {
        # 100 GB x 15.0 DSU/GB x $0.023/DSU = $34.50/mo
        'parent': 'Lakebase 4CU 2HA',
        'type': 'Lakebase (Storage)',
        'sku': 'DATABRICKS_STORAGE',
        'rate': 0.023,
        'cost': 34.5,
        'note': '100 GB × 15.0 DSU/GB × $0.023/DSU = $34.50/mo',
    },
]

# Grand totals across all 11 data rows (9 primary + 2 storage).
GOLDEN_TOTAL_DBUS_MO = sum(r['dbus_mo'] for r in GOLDEN_ROWS)  # 37168.4...
GOLDEN_TOTAL_DBU_COST = (
    sum(r['dbu_cost'] for r in GOLDEN_ROWS)
    + sum(s['cost'] for s in GOLDEN_STORAGE_ROWS)
)  # 12328.9125

# Static fallback reference for the VM golden cases (DEFAULT_VM_PRICING).
STATIC_I3_XLARGE_ON_DEMAND = 0.312
DB_INJECTED_VM_PRICE = 0.45
