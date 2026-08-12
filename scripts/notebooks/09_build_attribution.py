# Databricks notebook source
# MAGIC %md
# MAGIC # 09: Build Attribution Rollup
# MAGIC
# MAGIC Builds `lakemeter.attribution_daily` from `lakemeter.actuals_usage_daily`
# MAGIC (loaded by 08_sync_actuals.py). Every actual usage record is attributed
# MAGIC to a single owner using the first available identity signal:
# MAGIC
# MAGIC 1. `run_as` (identity that executed the workload): confidence HIGH
# MAGIC 2. `owned_by` (resource owner): confidence MEDIUM
# MAGIC 3. `created_by` (resource creator): confidence MEDIUM
# MAGIC 4. `custom_tags['owner']`: confidence LOW
# MAGIC 5. fallback `UNATTRIBUTED`: confidence NONE
# MAGIC
# MAGIC Cost centers resolve through `lakemeter.ref_user_cost_center_map`
# MAGIC (maintained by the FinOps team), falling back to
# MAGIC `custom_tags['cost_center']`, then `UNMAPPED`.
# MAGIC
# MAGIC The build is incremental: a watermark in
# MAGIC `lakemeter.actuals_ingestion_state` (pipeline `attribution_daily`)
# MAGIC tracks progress and each run rebuilds a trailing reprocess window via
# MAGIC DELETE + INSERT, so late-arriving and restated billing records flow
# MAGIC through automatically and re-runs never duplicate rows.

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
# MAGIC ## DDL: attribution tables

# COMMAND ----------

cur.execute("""
CREATE TABLE IF NOT EXISTS lakemeter.attribution_daily (
    usage_date DATE NOT NULL,
    attributed_user TEXT NOT NULL,
    attribution_source TEXT NOT NULL,
    attribution_confidence TEXT NOT NULL,
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
CREATE TABLE IF NOT EXISTS lakemeter.ref_user_cost_center_map (
    user_email TEXT PRIMARY KEY,
    cost_center TEXT NOT NULL,
    department TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cur.execute("""
CREATE INDEX IF NOT EXISTS idx_attribution_date
    ON lakemeter.attribution_daily (usage_date)
""")
cur.execute("""
CREATE INDEX IF NOT EXISTS idx_attribution_user_date
    ON lakemeter.attribution_daily (attributed_user, usage_date)
""")
cur.execute("""
CREATE INDEX IF NOT EXISTS idx_attribution_cost_center
    ON lakemeter.attribution_daily (cost_center)
""")

print("DDL complete: attribution_daily, ref_user_cost_center_map, indexes")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Watermark and rebuild window

# COMMAND ----------

# The watermark for this pipeline lives alongside the ingestion watermark in
# lakemeter.actuals_ingestion_state (created by 08_sync_actuals.py).
cur.execute("""
INSERT INTO lakemeter.actuals_ingestion_state (pipeline_name, watermark_date)
VALUES ('attribution_daily', NULL)
ON CONFLICT (pipeline_name) DO NOTHING
""")
cur.execute("""
SELECT watermark_date FROM lakemeter.actuals_ingestion_state
WHERE pipeline_name = 'attribution_daily'
""")
watermark = cur.fetchone()[0]

if watermark is None:
    window_start = date.today() - timedelta(days=initial_backfill_days)
else:
    window_start = watermark - timedelta(days=reprocess_days)

# One literal, valid in both Spark SQL and PostgreSQL if ever reused there.
window_start_sql = f"DATE '{window_start}'"
print(f"Rebuild window start: {window_start} (watermark: {watermark})")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Rebuild the window

# COMMAND ----------

cur.execute(f"""
DELETE FROM lakemeter.attribution_daily
WHERE usage_date >= {window_start_sql}
""")
print(f"Deleted {cur.rowcount} existing attribution rows in the window")

# Attribution chain: first non-empty identity signal wins. The same CASE
# expression records which signal was used, and the confidence grade follows
# directly from the source.
cur.execute(f"""
INSERT INTO lakemeter.attribution_daily (
    usage_date, attributed_user, attribution_source, attribution_confidence,
    cost_center, sku_name, cloud, asset_type, asset_id,
    usage_unit, usage_quantity, list_cost, currency_code, record_count
)
WITH attributed AS (
    SELECT
        a.usage_date,
        COALESCE(
            NULLIF(a.run_as, ''),
            NULLIF(a.owned_by, ''),
            NULLIF(a.created_by, ''),
            NULLIF(a.custom_tags ->> 'owner', ''),
            'UNATTRIBUTED'
        ) AS attributed_user,
        CASE
            WHEN NULLIF(a.run_as, '') IS NOT NULL THEN 'run_as'
            WHEN NULLIF(a.owned_by, '') IS NOT NULL THEN 'owned_by'
            WHEN NULLIF(a.created_by, '') IS NOT NULL THEN 'created_by'
            WHEN NULLIF(a.custom_tags ->> 'owner', '') IS NOT NULL
                THEN 'custom_tags.owner'
            ELSE 'none'
        END AS attribution_source,
        CASE
            WHEN NULLIF(a.run_as, '') IS NOT NULL THEN 'HIGH'
            WHEN NULLIF(a.owned_by, '') IS NOT NULL
              OR NULLIF(a.created_by, '') IS NOT NULL THEN 'MEDIUM'
            WHEN NULLIF(a.custom_tags ->> 'owner', '') IS NOT NULL THEN 'LOW'
            ELSE 'NONE'
        END AS attribution_confidence,
        NULLIF(a.custom_tags ->> 'cost_center', '') AS tag_cost_center,
        a.sku_name,
        a.cloud,
        CASE
            WHEN a.warehouse_id IS NOT NULL THEN 'sql_warehouse'
            WHEN a.endpoint_id IS NOT NULL THEN 'model_serving'
            WHEN a.dlt_pipeline_id IS NOT NULL THEN 'dlt_pipeline'
            WHEN a.job_id IS NOT NULL THEN 'job'
            WHEN a.cluster_id IS NOT NULL THEN 'cluster'
            ELSE 'other'
        END AS asset_type,
        COALESCE(
            a.warehouse_id, a.endpoint_id, a.dlt_pipeline_id,
            a.job_id, a.cluster_id, a.endpoint_name
        ) AS asset_id,
        a.usage_unit,
        a.usage_quantity,
        a.list_cost,
        a.currency_code
    FROM lakemeter.actuals_usage_daily a
    WHERE a.usage_date >= {window_start_sql}
)
SELECT
    t.usage_date,
    t.attributed_user,
    t.attribution_source,
    t.attribution_confidence,
    COALESCE(m.cost_center, t.tag_cost_center, 'UNMAPPED') AS cost_center,
    t.sku_name,
    t.cloud,
    t.asset_type,
    t.asset_id,
    t.usage_unit,
    SUM(t.usage_quantity) AS usage_quantity,
    SUM(t.list_cost) AS list_cost,
    t.currency_code,
    COUNT(*) AS record_count
FROM attributed t
LEFT JOIN lakemeter.ref_user_cost_center_map m
    ON m.user_email = t.attributed_user
GROUP BY
    t.usage_date, t.attributed_user, t.attribution_source,
    t.attribution_confidence, COALESCE(m.cost_center, t.tag_cost_center, 'UNMAPPED'),
    t.sku_name, t.cloud, t.asset_type, t.asset_id, t.usage_unit, t.currency_code
""")
print(f"Inserted {cur.rowcount} attribution rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Advance the watermark and report coverage

# COMMAND ----------

cur.execute(f"""
UPDATE lakemeter.actuals_ingestion_state
SET watermark_date = (SELECT MAX(usage_date) FROM lakemeter.attribution_daily),
    last_run_at = CURRENT_TIMESTAMP,
    last_status = 'SUCCESS',
    last_error = NULL
WHERE pipeline_name = 'attribution_daily'
""")

cur.execute("""
SELECT
    attribution_confidence,
    COUNT(*) AS rows,
    COALESCE(SUM(list_cost), 0) AS list_cost
FROM lakemeter.attribution_daily
GROUP BY attribution_confidence
ORDER BY attribution_confidence
""")
coverage = cur.fetchall()
total_cost = sum(float(r[2]) for r in coverage)
print("Attribution coverage (all time):")
for confidence, rows, cost in coverage:
    share = (float(cost) / total_cost * 100) if total_cost else 0.0
    print(f"  {confidence:6s} rows={rows:8d} list_cost={float(cost):14.2f} ({share:5.1f}%)")

cur.execute("""
SELECT COALESCE(SUM(list_cost), 0) FROM lakemeter.attribution_daily
WHERE attributed_user = 'UNATTRIBUTED'
""")
unattributed_cost = float(cur.fetchone()[0])
if total_cost and unattributed_cost / total_cost > 0.20:
    print(f"WARNING: {unattributed_cost / total_cost:.1%} of list cost is UNATTRIBUTED (threshold 20%)")

cur.execute("""
SELECT attributed_user, SUM(list_cost) AS list_cost
FROM lakemeter.attribution_daily
WHERE cost_center = 'UNMAPPED' AND attributed_user <> 'UNATTRIBUTED'
GROUP BY attributed_user
ORDER BY list_cost DESC NULLS LAST
LIMIT 10
""")
unmapped = cur.fetchall()
if unmapped:
    print("Top attributed users without a cost-center mapping (add them to ref_user_cost_center_map):")
    for user, cost in unmapped:
        print(f"  {user}: {float(cost or 0):.2f}")

cur.close()
conn.close()
print("Attribution build complete.")
