# Databricks notebook source
# MAGIC %md
# MAGIC # Refresh Pricing from Unity Catalog
# MAGIC Optional enterprise path: copy UC-governed pricing tables into Lakebase `sync_*` tables,
# MAGIC then rebuild SKU mapping and freshness metadata.
# MAGIC
# MAGIC Prerequisites:
# MAGIC - UC tables populated (see `etl/pricing_sync/` and Admin Guide → Pricing Data)
# MAGIC - Lakebase secrets (`lakebase-host`, `lakebase-user`) in the secrets scope
# MAGIC - Caller has SELECT on the UC source tables and write access to Lakebase
# MAGIC
# MAGIC Default source schema: `lakemeter_catalog.lakemeter`

# COMMAND ----------

import json
import time
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras
from databricks.sdk import WorkspaceClient

_start = time.time()

dbutils.widgets.text("project_id", "lakemeter-customer")
dbutils.widgets.text("db_name", "lakemeter_pricing")
dbutils.widgets.text("secrets_scope", "lakemeter-secrets")
dbutils.widgets.text("uc_catalog", "lakemeter_catalog")
dbutils.widgets.text("uc_schema", "lakemeter")

project_id = dbutils.widgets.get("project_id")
db_name = dbutils.widgets.get("db_name")
secrets_scope = dbutils.widgets.get("secrets_scope")
uc_catalog = dbutils.widgets.get("uc_catalog")
uc_schema = dbutils.widgets.get("uc_schema")
uc_prefix = f"{uc_catalog}.{uc_schema}"

print(f"UC source: {uc_prefix}")
print(f"Lakebase target: project={project_id} db={db_name}")

# COMMAND ----------

w = WorkspaceClient()

instance_host = dbutils.secrets.get(scope=secrets_scope, key="lakebase-host")
owner_user = dbutils.secrets.get(scope=secrets_scope, key="lakebase-user")
# Prefer Autoscaling endpoint credential when project_id is set
try:
    endpoint_name = f"{project_id}-ep"
    cred = w.postgres.generate_database_credential(endpoint=endpoint_name)
    password = cred.token
except Exception as e:
    print(f"Endpoint credential fallback ({e}); trying lakebase-password secret")
    password = dbutils.secrets.get(scope=secrets_scope, key="lakebase-password")

conn = psycopg2.connect(
    host=instance_host,
    port=5432,
    database=db_name,
    user=owner_user,
    password=password,
    sslmode="require",
)
conn.autocommit = True
cur = conn.cursor()
print(f"Connected to Lakebase: {db_name}@{instance_host}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## UC → Lakebase table map
# MAGIC Source tables follow `etl/pricing_sync` naming. Adjust SQL if your UC layout differs.

# COMMAND ----------

# (uc_relative_or_sql, lakebase_table, column_list)
# Columns must match Lakebase sync_* DDL from 03_load_pricing_data.
TRANSFERS = [
    (
        f"""
        SELECT sku_name, cloud, tier, product_type, sku_region, region,
               usage_unit, price_per_dbu, currency_code, pricing_type, fetched_at
        FROM {uc_prefix}.dbu_prices
        """,
        "sync_pricing_dbu_rates",
        [
            "sku_name", "cloud", "tier", "product_type", "sku_region", "region",
            "usage_unit", "price_per_dbu", "currency_code", "pricing_type", "fetched_at",
        ],
    ),
    (
        f"""
        SELECT cloud, region, instance_type, pricing_tier, payment_option,
               cost_per_hour, currency, source, fetched_at
        FROM {uc_prefix}.vm_costs
        """,
        "sync_pricing_vm_costs",
        [
            "cloud", "region", "instance_type", "pricing_tier", "payment_option",
            "cost_per_hour", "currency", "source", "fetched_at",
        ],
    ),
    (
        f"""
        SELECT cloud, instance_type, vcpus, memory_gb, dbu_rate,
               instance_family, COALESCE(is_active, true) AS is_active, source
        FROM {uc_prefix}.instance_rates
        """,
        "sync_ref_instance_dbu_rates",
        [
            "cloud", "instance_type", "vcpus", "memory_gb", "dbu_rate",
            "instance_family", "is_active", "source",
        ],
    ),
    (
        f"""
        SELECT cloud, sku_region, region_code
        FROM {uc_prefix}.sku_region_mapping
        """,
        "sync_ref_sku_region_map",
        ["cloud", "sku_region", "region_code"],
    ),
]

row_counts = {}
missing_sources = []

for select_sql, target_table, columns in TRANSFERS:
    fq_target = f"lakemeter.{target_table}"
    try:
        pdf = spark.sql(select_sql).toPandas()
    except Exception as e:
        missing_sources.append((target_table, str(e)))
        print(f"SKIP {target_table}: {e}")
        continue

    cur.execute(f"TRUNCATE TABLE {fq_target}")
    if len(pdf) == 0:
        row_counts[target_table] = 0
        print(f"WARN {fq_target}: 0 rows from UC")
        continue

    cols = ", ".join(columns)
    placeholders = ", ".join(["%s"] * len(columns))
    rows = [
        tuple(None if (isinstance(v, float) and v != v) else v for v in rec)
        for rec in pdf[columns].itertuples(index=False, name=None)
    ]
    psycopg2.extras.execute_batch(
        cur,
        f"INSERT INTO {fq_target} ({cols}) VALUES ({placeholders})",
        rows,
        page_size=1000,
    )
    row_counts[target_table] = len(rows)
    print(f"OK {fq_target}: {len(rows)} rows")

# COMMAND ----------

critical = [
    "sync_pricing_dbu_rates",
    "sync_pricing_vm_costs",
    "sync_ref_instance_dbu_rates",
]
empty_critical = [t for t in critical if row_counts.get(t, 0) == 0]
if empty_critical:
    raise RuntimeError(
        "UC pricing refresh failed — empty or missing critical tables: "
        f"{empty_critical}. Missing/errors: {missing_sources}"
    )

# COMMAND ----------

cur.execute("""
    CREATE TABLE IF NOT EXISTS lakemeter.pricing_metadata (
        id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
        loaded_at TIMESTAMPTZ NOT NULL,
        source TEXT NOT NULL,
        total_rows INTEGER NOT NULL DEFAULT 0,
        table_counts JSONB NOT NULL DEFAULT '{}'::jsonb,
        notes TEXT
    )
""")

loaded_at = datetime.now(timezone.utc)
total = sum(row_counts.values())
notes = (
    f"Loaded from Unity Catalog {uc_prefix}. "
    "Verify against official Databricks list prices before commercial use."
)
cur.execute(
    """
    INSERT INTO lakemeter.pricing_metadata (id, loaded_at, source, total_rows, table_counts, notes)
    VALUES (1, %s, %s, %s, %s::jsonb, %s)
    ON CONFLICT (id) DO UPDATE SET
        loaded_at = EXCLUDED.loaded_at,
        source = EXCLUDED.source,
        total_rows = EXCLUDED.total_rows,
        table_counts = EXCLUDED.table_counts,
        notes = EXCLUDED.notes
    """,
    (loaded_at, "unity_catalog", total, json.dumps(row_counts), notes),
)
print(f"Pricing freshness recorded: source=unity_catalog total_rows={total}")

cur.close()
conn.close()

# COMMAND ----------

sku_result = dbutils.notebook.run(
    "./04_create_sku_mapping",
    timeout_seconds=1800,
    arguments={
        "project_id": project_id,
        "db_name": db_name,
    },
)
print(f"SKU mapping result: {sku_result}")

elapsed = time.time() - _start
print(f"UC pricing refresh complete ({elapsed:.1f}s)")
dbutils.notebook.exit(f"PASS: UC pricing refreshed ({elapsed:.1f}s)")
