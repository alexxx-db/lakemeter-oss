# Databricks notebook source
# MAGIC %md
# MAGIC # 14: Package Reporting (AI/BI Dashboard + Genie Space)
# MAGIC
# MAGIC Turns the W1-W4 Lakebase pipeline tables into a consumable reporting
# MAGIC package:
# MAGIC
# MAGIC 1. **UC reporting tables**: aggregated rollups are copied from
# MAGIC    Lakebase into Unity Catalog Delta tables
# MAGIC    (`<catalog>.<schema>.rpt_*`), because AI/BI dashboards and Genie
# MAGIC    spaces query Unity Catalog, not Lakebase directly. Rollups are
# MAGIC    small (daily grain), so a full overwrite each run is cheap and
# MAGIC    keeps UC in lockstep with Lakebase.
# MAGIC 2. **AI/BI dashboard**: the bundled template
# MAGIC    `reporting/lakemeter_costs.lvdash.json` is rendered with the target
# MAGIC    catalog/schema and written to a workspace path (default
# MAGIC    `/Workspace/Shared/lakemeter/lakemeter_costs.lvdash.json`), ready
# MAGIC    to import via the Dashboards UI or deploy API.
# MAGIC 3. **Genie space**: created (or updated) from the bundled template
# MAGIC    `reporting/lakemeter_genie_space.json` with instructions and sample
# MAGIC    questions tuned to the reporting tables.
# MAGIC
# MAGIC Genie One / Agents are free through 2027-01-31, so running the Genie
# MAGIC space itself does not add billable Genie usage during that window.

# COMMAND ----------

dbutils.widgets.text("instance_name", "lakemeter-customer")
dbutils.widgets.text("db_name", "lakemeter_pricing")
dbutils.widgets.text("secrets_scope", "lakemeter-secrets")
dbutils.widgets.text("reporting_catalog", "lakemeter_catalog")
dbutils.widgets.text("reporting_schema", "lakemeter")
dbutils.widgets.text("dashboard_parent_path", "/Workspace/Shared/lakemeter")
dbutils.widgets.text("genie_parent_path", "/Workspace/Shared/lakemeter")

instance_name = dbutils.widgets.get("instance_name")
db_name = dbutils.widgets.get("db_name")
secrets_scope = dbutils.widgets.get("secrets_scope")
catalog = dbutils.widgets.get("reporting_catalog")
schema = dbutils.widgets.get("reporting_schema")
dashboard_parent = dbutils.widgets.get("dashboard_parent_path")
genie_parent = dbutils.widgets.get("genie_parent_path")

# COMMAND ----------

from datetime import date
from pathlib import Path

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
# MAGIC ## Copy reporting rollups into Unity Catalog

# COMMAND ----------

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")

# Each entry: (UC table, Lakebase query, column names). Rollups are
# pre-aggregated in Lakebase, so the copy is a straight read; per-day
# grains stay small enough for a full overwrite per run.
REPORTS = [
    (
        # Self-contained: re-derives product_line from attribution_daily
        # with the same classification as the W3 enrichment, so no fragile
        # join between the two rollups is needed.
        "rpt_spend_daily",
        """
        SELECT usage_date, cost_center, attributed_user, attribution_confidence,
               CASE
                   WHEN a.asset_type = 'sql_warehouse'
                     OR a.sku_name ILIKE '%SERVERLESS_SQL%'
                     OR a.sku_name ILIKE '%SQL_COMPUTE%' THEN 'sql_warehouse'
                   WHEN a.asset_type = 'model_serving'
                     OR a.sku_name ILIKE 'SERVERLESS_REAL_TIME_INFERENCE%' THEN 'model_serving'
                   WHEN a.asset_type = 'dlt_pipeline' THEN 'dlt_pipeline'
                   WHEN a.asset_type = 'job' THEN 'jobs'
                   WHEN a.asset_type = 'cluster' THEN 'interactive_cluster'
                   WHEN a.sku_name ILIKE '%FOUNDATION_MODEL%'
                     OR a.sku_name ILIKE '%FMAPI%' THEN 'foundation_model_api'
                   ELSE 'other'
               END AS product_line,
               a.asset_type, a.currency_code,
               SUM(a.usage_quantity) AS usage_quantity,
               SUM(a.list_cost) AS list_cost,
               SUM(a.record_count) AS record_count
        FROM lakemeter.attribution_daily a
        GROUP BY usage_date, cost_center, attributed_user, attribution_confidence,
                 a.asset_type, a.currency_code
        """,
        ["usage_date", "cost_center", "attributed_user", "attribution_confidence",
         "product_line", "asset_type", "currency_code",
         "usage_quantity", "list_cost", "record_count"],
    ),
    (
        "rpt_spend_daily_by_product",
        """
        SELECT usage_date, product_line, currency_code,
               SUM(usage_quantity) AS usage_quantity,
               SUM(list_cost) AS list_cost,
               SUM(record_count) AS record_count
        FROM lakemeter.product_usage_daily
        GROUP BY usage_date, product_line, currency_code
        """,
        ["usage_date", "product_line", "currency_code",
         "usage_quantity", "list_cost", "record_count"],
    ),
    (
        "rpt_genie_queries_daily",
        """
        SELECT usage_date, executed_by, warehouse_id,
               SUM(query_count) AS query_count,
               SUM(total_duration_ms) AS total_duration_ms,
               SUM(total_rows_produced) AS total_rows_produced
        FROM lakemeter.genie_query_daily
        GROUP BY usage_date, executed_by, warehouse_id
        """,
        ["usage_date", "executed_by", "warehouse_id",
         "query_count", "total_duration_ms", "total_rows_produced"],
    ),
    (
        "rpt_dashboard_queries_daily",
        """
        SELECT usage_date, executed_by, warehouse_id,
               SUM(query_count) AS query_count,
               SUM(total_duration_ms) AS total_duration_ms,
               SUM(total_rows_produced) AS total_rows_produced
        FROM lakemeter.dashboard_query_daily
        GROUP BY usage_date, executed_by, warehouse_id
        """,
        ["usage_date", "executed_by", "warehouse_id",
         "query_count", "total_duration_ms", "total_rows_produced"],
    ),
    (
        "rpt_budget_alerts",
        """
        SELECT alert_month, scope_type, scope_key, mtd_cost, monthly_budget,
               severity, raised_at
        FROM lakemeter.budget_alerts
        """,
        ["alert_month", "scope_type", "scope_key", "mtd_cost", "monthly_budget",
         "severity", "raised_at"],
    ),
]

for table_name, query, columns in REPORTS:
    cur.execute(query)
    rows = [dict(zip(columns, r)) for r in cur.fetchall()]
    if rows:
        df = spark.createDataFrame(rows)
    else:
        # Keep the table present (with schema) even when a rollup is empty.
        df = spark.createDataFrame([], ", ".join(f"{name} STRING" for name in columns))
    df.write.mode("overwrite").saveAsTable(f"{catalog}.{schema}.{table_name}")
    print(f"{catalog}.{schema}.{table_name}: {len(rows)} rows")

cur.close()
conn.close()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Deploy the AI/BI dashboard definition

# COMMAND ----------

reporting_dir = Path.cwd() / "reporting"
dashboard_template = (reporting_dir / "lakemeter_costs.lvdash.json").read_text()
dashboard_rendered = dashboard_template.replace("${catalog}", catalog).replace("${schema}", schema)
assert "${catalog}" not in dashboard_rendered and "${schema}" not in dashboard_rendered

dbutils.fs.mkdirs(dashboard_parent)
dashboard_path = f"{dashboard_parent}/lakemeter_costs.lvdash.json"
dbutils.fs.put(dashboard_path, dashboard_rendered, True)
print(f"Dashboard definition written to {dashboard_path}")
print("Import it via the Dashboards UI (Create dashboard from file) or the lakeview API.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create or update the Genie space

# COMMAND ----------

import json

genie_template = (reporting_dir / "lakemeter_genie_space.json").read_text()
genie_rendered = genie_template.replace("${catalog}", catalog).replace("${schema}", schema)
assert "${catalog}" not in genie_rendered and "${schema}" not in genie_rendered
serialized = json.dumps(json.loads(genie_rendered))

# The Genie API creates a space from a serialized definition. If a space
# with the same title already exists in the parent folder, update it
# instead of duplicating.
GENIE_TITLE = "Lakemeter Cost Attribution"
dbutils.fs.mkdirs(genie_parent)

try:
    existing = None
    for space in w.genie.list_spaces():
        if space.title == GENIE_TITLE:
            existing = space
            break
    if existing:
        w.genie.update_space(space_id=existing.space_id, serialized_space=serialized)
        print(f"Updated Genie space {existing.space_id} ({GENIE_TITLE})")
    else:
        created = w.genie.create_space(
            warehouse_id=None,
            parent_path=genie_parent,
            title=GENIE_TITLE,
            description="Ask questions about Lakemeter actual spend, attribution, and budgets.",
            serialized_space=serialized,
        )
        print(f"Created Genie space {created.space_id} ({GENIE_TITLE})")
except Exception as e:
    # The Genie API is evolving; never fail the reporting package on it.
    # The rendered definition is left in the workspace for manual import.
    fallback_path = f"{genie_parent}/lakemeter_genie_space.rendered.json"
    dbutils.fs.put(fallback_path, genie_rendered, True)
    print(f"Genie space API call failed ({type(e).__name__}: {e})")
    print(f"Rendered space definition written to {fallback_path} for manual import.")

print("Reporting package complete.")
