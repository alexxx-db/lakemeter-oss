# Databricks notebook source
# MAGIC %md
# MAGIC # 10: Enrich Product Coverage
# MAGIC
# MAGIC Extends actuals beyond the easy-to-meter Unity Catalog entities to the
# MAGIC four product surfaces customers asked for:
# MAGIC
# MAGIC - **SQL Warehouses**: classified directly from billing rows
# MAGIC   (`warehouse_id`, serverless SQL SKUs).
# MAGIC - **Model Serving**: classified from `endpoint_id` / `endpoint_name` and
# MAGIC   the `SERVERLESS_REAL_TIME_INFERENCE` SKU family (including `_LAUNCH`).
# MAGIC - **Genie**: Genie conversations run as queries on a SQL warehouse with
# MAGIC   `client_application` containing "Genie" in `system.query.history`.
# MAGIC   Their cost is the underlying warehouse compute; this notebook ingests
# MAGIC   per-user, per-warehouse Genie query activity so warehouse spend can be
# MAGIC   apportioned to Genie users. Genie One / Agents are free through
# MAGIC   2027-01-31 (negating correction records in billing, preserved by the
# MAGIC   actuals pipeline).
# MAGIC - **Dashboards (AI/BI)**: dashboard refreshes are warehouse queries with
# MAGIC   `client_application` containing "Dashboard"; ingested the same way so
# MAGIC   dashboard-driven warehouse load is visible per user and per warehouse.
# MAGIC
# MAGIC Outputs:
# MAGIC - `lakemeter.product_usage_daily`: all actuals re-classified into a
# MAGIC   `product_line` (sql_warehouse, model_serving, genie, dashboard, jobs,
# MAGIC   dlt_pipeline, interactive_cluster, foundation_model_api, other).
# MAGIC - `lakemeter.genie_query_daily`: per-day Genie query activity by user
# MAGIC   and warehouse (from `system.query.history`).
# MAGIC - `lakemeter.dashboard_query_daily`: same for AI/BI dashboards.
# MAGIC
# MAGIC All three are incremental with a shared watermark table
# MAGIC (`lakemeter.actuals_ingestion_state`) and trailing DELETE + INSERT
# MAGIC rebuild windows, matching the W1/W2 pipelines.

# COMMAND ----------

dbutils.widgets.text("instance_name", "lakemeter-customer")
dbutils.widgets.text("db_name", "lakemeter_pricing")
dbutils.widgets.text("secrets_scope", "lakemeter-secrets")
dbutils.widgets.text("reprocess_days", "14")
dbutils.widgets.text("initial_backfill_days", "30")

instance_name = dbutils.widgets.get("instance_name")
db_name = dbutils.widgets.get("db_name")
secrets_scope = dbutils.widgets.get("secrets_scope")
reprocess_days = int(dbutils.widgets.get("reprocess_days"))
initial_backfill_days = int(dbutils.widgets.get("initial_backfill_days"))

# COMMAND ----------

from datetime import date, timedelta

import psycopg2
import psycopg2.extras
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
instance = w.database.get_database_instance(instance_name)
cred = w.database.generate_database_credential(
    request_id=str(date.today()), instance_names=[instance_name]
)
conn = psycopg2.connect(
    host=instance.read_write_dns,
    port=5432,
    dbname=db_name,
    user=w.current_user.me().user_name,
    password=cred.token,
    sslmode="require",
)
conn.autocommit = True
cur = conn.cursor()

# COMMAND ----------

# MAGIC %md
# MAGIC ## DDL: product coverage tables

# COMMAND ----------

cur.execute("""
CREATE TABLE IF NOT EXISTS lakemeter.product_usage_daily (
    usage_date DATE NOT NULL,
    product_line TEXT NOT NULL,
    attributed_user TEXT NOT NULL,
    cost_center TEXT NOT NULL,
    sku_name TEXT,
    cloud TEXT,
    asset_type TEXT,
    asset_id TEXT,
    usage_unit TEXT,
    usage_quantity NUMERIC,
    list_cost NUMERIC,
    currency_code TEXT,
    record_count BIGINT,
    built_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS lakemeter.genie_query_daily (
    usage_date DATE NOT NULL,
    executed_by TEXT,
    warehouse_id TEXT,
    query_count BIGINT,
    total_duration_ms BIGINT,
    total_rows_produced BIGINT,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS lakemeter.dashboard_query_daily (
    usage_date DATE NOT NULL,
    executed_by TEXT,
    warehouse_id TEXT,
    query_count BIGINT,
    total_duration_ms BIGINT,
    total_rows_produced BIGINT,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cur.execute("""
CREATE INDEX IF NOT EXISTS idx_product_usage_date
    ON lakemeter.product_usage_daily (usage_date)
""")
cur.execute("""
CREATE INDEX IF NOT EXISTS idx_product_usage_line_date
    ON lakemeter.product_usage_daily (product_line, usage_date)
""")
cur.execute("""
CREATE INDEX IF NOT EXISTS idx_genie_query_user_date
    ON lakemeter.genie_query_daily (executed_by, usage_date)
""")
cur.execute("""
CREATE INDEX IF NOT EXISTS idx_dashboard_query_user_date
    ON lakemeter.dashboard_query_daily (executed_by, usage_date)
""")

print("DDL complete: product_usage_daily, genie_query_daily, dashboard_query_daily")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Watermarks and rebuild window

# COMMAND ----------

for pipeline in ("product_usage_daily", "genie_query_daily", "dashboard_query_daily"):
    cur.execute("""
    INSERT INTO lakemeter.actuals_ingestion_state (pipeline_name, watermark_date)
    VALUES (%s, NULL)
    ON CONFLICT (pipeline_name) DO NOTHING
    """, (pipeline,))

cur.execute("""
SELECT watermark_date FROM lakemeter.actuals_ingestion_state
WHERE pipeline_name = 'product_usage_daily'
""")
watermark = cur.fetchone()[0]

if watermark is None:
    window_start = date.today() - timedelta(days=initial_backfill_days)
else:
    window_start = watermark - timedelta(days=reprocess_days)

# One literal, valid in both Spark SQL and PostgreSQL.
window_start_sql = f"DATE '{window_start}'"
print(f"Rebuild window start: {window_start} (watermark: {watermark})")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Product-line classification (from attribution_daily)

# COMMAND ----------

# product_usage_daily re-classifies the attributed rollup into product
# lines. Genie and dashboard rows do not appear here from billing alone
# (their compute is billed to the warehouse); the genie_query_daily and
# dashboard_query_daily tables provide the per-user breakdown underneath.
cur.execute(f"""
DELETE FROM lakemeter.product_usage_daily
WHERE usage_date >= {window_start_sql}
""")
print(f"Deleted {cur.rowcount} existing product rows in the window")

cur.execute(f"""
INSERT INTO lakemeter.product_usage_daily (
    usage_date, product_line, attributed_user, cost_center,
    sku_name, cloud, asset_type, asset_id,
    usage_unit, usage_quantity, list_cost, currency_code, record_count
)
SELECT
    a.usage_date,
    CASE
        WHEN a.warehouse_id IS NOT NULL
          OR a.sku_name ILIKE '%SERVERLESS_SQL%'
          OR a.sku_name ILIKE '%SQL_COMPUTE%' THEN 'sql_warehouse'
        WHEN a.endpoint_id IS NOT NULL
          OR a.sku_name ILIKE 'SERVERLESS_REAL_TIME_INFERENCE%' THEN 'model_serving'
        WHEN a.dlt_pipeline_id IS NOT NULL THEN 'dlt_pipeline'
        WHEN a.job_id IS NOT NULL THEN 'jobs'
        WHEN a.cluster_id IS NOT NULL THEN 'interactive_cluster'
        WHEN a.sku_name ILIKE '%FOUNDATION_MODEL%'
          OR a.sku_name ILIKE '%FMAPI%' THEN 'foundation_model_api'
        ELSE 'other'
    END AS product_line,
    a.attributed_user,
    a.cost_center,
    a.sku_name,
    a.cloud,
    a.asset_type,
    a.asset_id,
    a.usage_unit,
    SUM(a.usage_quantity) AS usage_quantity,
    SUM(a.list_cost) AS list_cost,
    a.currency_code,
    SUM(a.record_count) AS record_count
FROM lakemeter.attribution_daily a
WHERE a.usage_date >= {window_start_sql}
GROUP BY
    a.usage_date,
    CASE
        WHEN a.warehouse_id IS NOT NULL
          OR a.sku_name ILIKE '%SERVERLESS_SQL%'
          OR a.sku_name ILIKE '%SQL_COMPUTE%' THEN 'sql_warehouse'
        WHEN a.endpoint_id IS NOT NULL
          OR a.sku_name ILIKE 'SERVERLESS_REAL_TIME_INFERENCE%' THEN 'model_serving'
        WHEN a.dlt_pipeline_id IS NOT NULL THEN 'dlt_pipeline'
        WHEN a.job_id IS NOT NULL THEN 'jobs'
        WHEN a.cluster_id IS NOT NULL THEN 'interactive_cluster'
        WHEN a.sku_name ILIKE '%FOUNDATION_MODEL%'
          OR a.sku_name ILIKE '%FMAPI%' THEN 'foundation_model_api'
        ELSE 'other'
    END,
    a.attributed_user, a.cost_center, a.sku_name, a.cloud,
    a.asset_type, a.asset_id, a.usage_unit, a.currency_code
""")
print(f"Inserted {cur.rowcount} product rows")

cur.execute(f"""
UPDATE lakemeter.actuals_ingestion_state
SET watermark_date = (SELECT MAX(usage_date) FROM lakemeter.product_usage_daily),
    last_run_at = CURRENT_TIMESTAMP,
    last_status = 'SUCCESS',
    last_error = NULL
WHERE pipeline_name = 'product_usage_daily'
""")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Genie and Dashboard query activity (from system.query.history)

# COMMAND ----------

# system.query.history is read with Spark; one query per product surface,
# each restricted to the rebuild window. client_application values are
# matched case-insensitively on a substring ("Genie", "Dashboard") to stay
# robust across Databricks client renames.
def load_query_activity(client_pattern, target_table, pipeline_name):
    df = spark.sql(f"""
        SELECT
            CAST(start_time AS DATE) AS usage_date,
            executed_by,
            warehouse_id,
            COUNT(*) AS query_count,
            SUM(total_duration_ms) AS total_duration_ms,
            SUM(rows_produced) AS total_rows_produced
        FROM system.query.history
        WHERE CAST(start_time AS DATE) >= {window_start_sql}
          AND LOWER(client_application) LIKE '%{client_pattern}%'
        GROUP BY CAST(start_time AS DATE), executed_by, warehouse_id
    """)
    rows = [
        (
            r.usage_date, r.executed_by, r.warehouse_id,
            int(r.query_count),
            int(r.total_duration_ms or 0),
            int(r.total_rows_produced or 0),
        )
        for r in df.collect()
    ]
    cur.execute(f"""
    DELETE FROM lakemeter.{target_table}
    WHERE usage_date >= {window_start_sql}
    """)
    if rows:
        psycopg2.extras.execute_values(
            cur,
            f\"\"\"
            INSERT INTO lakemeter.{target_table} (
                usage_date, executed_by, warehouse_id,
                query_count, total_duration_ms, total_rows_produced
            ) VALUES %s
            \"\"\",
            rows,
            page_size=1000,
        )
    cur.execute("""
    UPDATE lakemeter.actuals_ingestion_state
    SET watermark_date = %s,
        last_run_at = CURRENT_TIMESTAMP,
        last_status = 'SUCCESS',
        last_error = NULL
    WHERE pipeline_name = %s
    """, (date.today(), pipeline_name))
    print(f"{target_table}: {len(rows)} rows ingested for pattern '{client_pattern}'")
    return len(rows)

genie_rows = load_query_activity("genie", "genie_query_daily", "genie_query_daily")
dashboard_rows = load_query_activity("dashboard", "dashboard_query_daily", "dashboard_query_daily")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Coverage report

# COMMAND ----------

cur.execute("""
SELECT
    product_line,
    COUNT(*) AS rows,
    COALESCE(SUM(list_cost), 0) AS list_cost
FROM lakemeter.product_usage_daily
GROUP BY product_line
ORDER BY list_cost DESC NULLS LAST
""")
print("Product-line coverage (all time):")
for line, rows, cost in cur.fetchall():
    print(f"  {line:22s} rows={rows:8d} list_cost={float(cost):14.2f}")

cur.execute("""
SELECT COALESCE(SUM(list_cost), 0) FROM lakemeter.product_usage_daily
WHERE product_line = 'other'
""")
other_cost = float(cur.fetchone()[0])
cur.execute("SELECT COALESCE(SUM(list_cost), 0) FROM lakemeter.product_usage_daily")
total_cost = float(cur.fetchone()[0])
if total_cost and other_cost / total_cost > 0.20:
    print(f"WARNING: {other_cost / total_cost:.1%} of list cost is unclassified (product_line 'other', threshold 20%)")

cur.close()
conn.close()
print("Product coverage enrichment complete.")
