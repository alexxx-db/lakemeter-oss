# Databricks notebook source
# MAGIC %md
# MAGIC # Step 8: Sync Actual Usage (Actuals Ingestion)
# MAGIC Reads `system.billing.usage` (joined to `system.billing.list_prices` for list
# MAGIC prices) and appends daily-grain actuals into Lakebase table
# MAGIC `lakemeter.actuals_usage_daily`. Incremental and idempotent: each run
# MAGIC reprocesses a trailing window (default 7 days) via DELETE + INSERT, so
# MAGIC late-arriving billing records and correction rows are picked up on rerun.
# MAGIC Runs on serverless compute (environment v5, psycopg2 pre-installed).
# MAGIC
# MAGIC Permissions: the identity running this notebook needs read access to
# MAGIC `system.billing.usage` and `system.billing.list_prices` (account admin, or
# MAGIC a principal granted `USE CATALOG`/`SELECT` on the `system` catalog).

# COMMAND ----------

dbutils.widgets.text("instance_name", "lakemeter-customer")
dbutils.widgets.text("db_name", "lakemeter_pricing")
dbutils.widgets.text("secrets_scope", "lakemeter-secrets")
dbutils.widgets.text("reprocess_days", "7")
dbutils.widgets.text("initial_backfill_days", "30")

instance_name = dbutils.widgets.get("instance_name")
db_name = dbutils.widgets.get("db_name")
secrets_scope = dbutils.widgets.get("secrets_scope")
reprocess_days = int(dbutils.widgets.get("reprocess_days"))
initial_backfill_days = int(dbutils.widgets.get("initial_backfill_days"))

print(f"Instance: {instance_name}")
print(f"Database: {db_name}")
print(f"Reprocess window: {reprocess_days} days; initial backfill: {initial_backfill_days} days")

# COMMAND ----------

import uuid
from datetime import date, timedelta

import psycopg2
import psycopg2.extras
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

instance = w.database.get_database_instance(instance_name)
instance_host = instance.read_write_dns
cred = w.database.generate_database_credential(request_id=str(uuid.uuid4()), instance_names=[instance_name])
owner_user = w.current_user.me().user_name

conn = psycopg2.connect(
    host=instance_host,
    port=5432,
    database=db_name,
    user=owner_user,
    password=cred.token,
    sslmode="require",
)
conn.autocommit = True
cur = conn.cursor()
print(f"Connected to Lakebase: {db_name}@{instance_host}")

# COMMAND ----------

# Create actuals tables (additive, safe to re-run)
cur.execute("""
    CREATE TABLE IF NOT EXISTS lakemeter.actuals_usage_daily (
        usage_date DATE NOT NULL,
        record_id TEXT,
        record_type TEXT,
        account_id TEXT,
        workspace_id TEXT,
        sku_name TEXT,
        cloud TEXT,
        usage_start_time TIMESTAMPTZ,
        usage_end_time TIMESTAMPTZ,
        usage_unit TEXT,
        usage_quantity NUMERIC,
        list_price NUMERIC,
        list_cost NUMERIC,
        currency_code TEXT,
        custom_tags JSONB,
        run_as TEXT,
        owned_by TEXT,
        created_by TEXT,
        warehouse_id TEXT,
        endpoint_id TEXT,
        endpoint_name TEXT,
        cluster_id TEXT,
        job_id TEXT,
        dlt_pipeline_id TEXT,
        node_type TEXT,
        ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
cur.execute("CREATE INDEX IF NOT EXISTS idx_actuals_date ON lakemeter.actuals_usage_daily(usage_date)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_actuals_sku ON lakemeter.actuals_usage_daily(sku_name)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_actuals_run_as ON lakemeter.actuals_usage_daily(run_as)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_actuals_ws_date ON lakemeter.actuals_usage_daily(workspace_id, usage_date)")

cur.execute("""
    CREATE TABLE IF NOT EXISTS lakemeter.actuals_ingestion_state (
        pipeline_name TEXT PRIMARY KEY,
        watermark_date DATE,
        last_run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_status TEXT,
        last_error TEXT
    )
""")
print("Actuals tables ready")

# COMMAND ----------

# Determine the reprocess window start:
#   first run  -> today - initial_backfill_days
#   later runs -> watermark - reprocess_days (overlap catches late/corrected records)
cur.execute("""
    INSERT INTO lakemeter.actuals_ingestion_state (pipeline_name, watermark_date)
    VALUES ('actuals_usage_daily', NULL)
    ON CONFLICT (pipeline_name) DO NOTHING
""")
cur.execute("SELECT watermark_date FROM lakemeter.actuals_ingestion_state WHERE pipeline_name = 'actuals_usage_daily'")
watermark = cur.fetchone()[0]
print(f"Current watermark: {watermark}")

if watermark is None:
    window_start = date.today() - timedelta(days=initial_backfill_days)
else:
    window_start = watermark - timedelta(days=reprocess_days)
window_start_sql = f"DATE '{window_start}'"
print(f"Reprocess window start: {window_start}")

# COMMAND ----------

# Extract from system.billing.usage, joined to list prices.
# Notes:
# - Correction records (record_type = 'CORRECTION'/'RESTATEMENT') carry negative
#   quantities; they are kept as-is so sums stay correct (e.g. Genie One/Agents
#   usage is billed and then negated while free through 2027-01-31).
# - Rows with no matching list price are kept with NULL list_price/list_cost;
#   the unpriced-row count is reported at the end as a data-quality signal.
# - Prices are matched on sku_name + usage_start_time within the price window.
usage_df = spark.sql(f"""
    SELECT
        u.usage_date,
        u.record_id,
        u.record_type,
        u.account_id,
        u.workspace_id,
        u.sku_name,
        u.cloud,
        u.usage_start_time,
        u.usage_end_time,
        u.usage_unit,
        CAST(u.usage_quantity AS DECIMAL(38,6)) AS usage_quantity,
        CAST(p.effective_list.default AS DECIMAL(38,6)) AS list_price,
        CAST(u.usage_quantity * p.effective_list.default AS DECIMAL(38,6)) AS list_cost,
        p.currency_code,
        to_json(u.custom_tags) AS custom_tags,
        u.identity_metadata.run_as AS run_as,
        u.identity_metadata.owned_by AS owned_by,
        u.identity_metadata.created_by AS created_by,
        u.usage_metadata.warehouse_id AS warehouse_id,
        u.usage_metadata.endpoint_id AS endpoint_id,
        u.usage_metadata.endpoint_name AS endpoint_name,
        u.usage_metadata.cluster_id AS cluster_id,
        u.usage_metadata.job_id AS job_id,
        u.usage_metadata.dlt_pipeline_id AS dlt_pipeline_id,
        u.usage_metadata.node_type AS node_type
    FROM system.billing.usage u
    LEFT JOIN system.billing.list_prices p
        ON u.sku_name = p.sku_name
        AND u.usage_start_time >= p.price_start_time
        AND (p.price_end_time IS NULL OR u.usage_start_time < p.price_end_time)
    WHERE u.usage_date >= {window_start_sql}
""")

rows = usage_df.collect()
print(f"Rows extracted from system.billing.usage: {len(rows)}")

# COMMAND ----------

# Idempotent load: delete the reprocess window, insert fresh rows, advance watermark
cur.execute(f"""
    DELETE FROM lakemeter.actuals_usage_daily
    WHERE usage_date >= {window_start_sql}
""")
print(f"Deleted existing rows in reprocess window")

if rows:
    insert_sql = """
        INSERT INTO lakemeter.actuals_usage_daily (
            usage_date, record_id, record_type, account_id, workspace_id,
            sku_name, cloud, usage_start_time, usage_end_time, usage_unit,
            usage_quantity, list_price, list_cost, currency_code, custom_tags,
            run_as, owned_by, created_by,
            warehouse_id, endpoint_id, endpoint_name, cluster_id, job_id,
            dlt_pipeline_id, node_type
        ) VALUES %s
    """
    values = [
        (
            r.usage_date, r.record_id, r.record_type, r.account_id, r.workspace_id,
            r.sku_name, r.cloud, r.usage_start_time, r.usage_end_time, r.usage_unit,
            r.usage_quantity, r.list_price, r.list_cost, r.currency_code, r.custom_tags,
            r.run_as, r.owned_by, r.created_by,
            r.warehouse_id, r.endpoint_id, r.endpoint_name, r.cluster_id, r.job_id,
            r.dlt_pipeline_id, r.node_type,
        )
        for r in rows
    ]
    psycopg2.extras.execute_values(cur, insert_sql, values, page_size=1000)
    print(f"Inserted {len(rows)} rows")

# COMMAND ----------

# Advance watermark to the max usage_date seen this run (or today if no rows)
cur.execute("""
    UPDATE lakemeter.actuals_ingestion_state
    SET watermark_date = (SELECT COALESCE(MAX(usage_date), CURRENT_DATE) FROM lakemeter.actuals_usage_daily),
        last_run_at = CURRENT_TIMESTAMP,
        last_status = 'SUCCESS',
        last_error = NULL
    WHERE pipeline_name = 'actuals_usage_daily'
""")

# Data-quality report
cur.execute("SELECT COUNT(*) FROM lakemeter.actuals_usage_daily WHERE list_price IS NULL")
unpriced = cur.fetchone()[0]
cur.execute("SELECT COUNT(*), MIN(usage_date), MAX(usage_date) FROM lakemeter.actuals_usage_daily")
total, min_d, max_d = cur.fetchone()
print(f"actuals_usage_daily: {total} rows, {min_d} .. {max_d}")
print(f"Unpriced rows (no list-price match): {unpriced}")
if total > 0 and unpriced / total > 0.2:
    print("WARNING: >20% of rows unpriced; check system.billing.list_prices coverage")

cur.close()
conn.close()
dbutils.notebook.exit(f"Actuals sync complete: {len(rows)} rows in window")
