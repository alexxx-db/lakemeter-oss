# Databricks notebook source
# MAGIC %md
# MAGIC # 13: Export Chargeback
# MAGIC
# MAGIC Writes a monthly chargeback CSV (per cost center, per attributed user)
# MAGIC to a Unity Catalog volume, for import into Finance systems. Grain:
# MAGIC one row per month, cost center, attributed user, and asset type, with
# MAGIC usage quantity, list cost, and attribution confidence mix.
# MAGIC
# MAGIC Default month is the previous calendar month (run on the 1st). The
# MAGIC target volume is created if missing; files land at
# MAGIC `/Volumes/<catalog>/<schema>/<volume>/chargeback_YYYY-MM.csv`.

# COMMAND ----------

dbutils.widgets.text("instance_name", "lakemeter-customer")
dbutils.widgets.text("db_name", "lakemeter_pricing")
dbutils.widgets.text("secrets_scope", "lakemeter-secrets")
dbutils.widgets.text("export_month", "previous")
dbutils.widgets.text("export_catalog", "main")
dbutils.widgets.text("export_schema", "default")
dbutils.widgets.text("export_volume", "lakemeter_chargeback")

instance_name = dbutils.widgets.get("instance_name")
db_name = dbutils.widgets.get("db_name")
secrets_scope = dbutils.widgets.get("secrets_scope")
export_month = dbutils.widgets.get("export_month")
export_catalog = dbutils.widgets.get("export_catalog")
export_schema = dbutils.widgets.get("export_schema")
export_volume = dbutils.widgets.get("export_volume")

# COMMAND ----------

import calendar
import re
from datetime import date

import psycopg2
from databricks.sdk import WorkspaceClient

if export_month == "previous":
    today = date.today()
    year = today.year if today.month > 1 else today.year - 1
    month = today.month - 1 or 12
else:
    assert re.fullmatch(r"\d{4}-\d{2}", export_month), "export_month must be 'previous' or YYYY-MM"
    year, month = map(int, export_month.split("-"))

month_start = date(year, month, 1)
month_end = date(year, month, calendar.monthrange(year, month)[1])
month_start_sql = f"DATE '{month_start}'"
month_end_sql = f"DATE '{month_end}'"
print(f"Exporting chargeback for {month_start} to {month_end}")

# COMMAND ----------

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

cur.execute(f"""
SELECT
    cost_center,
    attributed_user,
    asset_type,
    currency_code,
    SUM(usage_quantity) AS usage_quantity,
    SUM(list_cost) AS list_cost,
    SUM(record_count) AS record_count,
    SUM(CASE WHEN attribution_confidence = 'HIGH' THEN list_cost ELSE 0 END) AS high_confidence_cost,
    SUM(CASE WHEN attribution_confidence = 'NONE' THEN list_cost ELSE 0 END) AS unattributed_cost
FROM lakemeter.attribution_daily
WHERE usage_date >= {month_start_sql} AND usage_date <= {month_end_sql}
GROUP BY cost_center, attributed_user, asset_type, currency_code
ORDER BY cost_center, list_cost DESC NULLS LAST
""")
cols = ["cost_center", "attributed_user", "asset_type", "currency_code",
        "usage_quantity", "list_cost", "record_count",
        "high_confidence_cost", "unattributed_cost"]
rows = [dict(zip(cols, r)) for r in cur.fetchall()]
cur.close()
conn.close()
print(f"{len(rows)} chargeback rows for {year}-{month:02d}")

# COMMAND ----------

# Write the CSV to the target UC volume (created if missing).
spark.sql(f"CREATE VOLUME IF NOT EXISTS {export_catalog}.{export_schema}.{export_volume}")
target_dir = f"/Volumes/{export_catalog}/{export_schema}/{export_volume}"

if rows:
    df = spark.createDataFrame(rows)
    (df.coalesce(1)
       .write
       .mode("overwrite")
       .option("header", "true")
       .csv(f"{target_dir}/chargeback_{year}-{month:02d}_staging"))
    # Rename the single part file to a stable name.
    part = [f for f in dbutils.fs.ls(f"{target_dir}/chargeback_{year}-{month:02d}_staging")
            if f.name.startswith("part-")][0]
    dbutils.fs.cp(part.path, f"{target_dir}/chargeback_{year}-{month:02d}.csv")
    dbutils.fs.rm(f"{target_dir}/chargeback_{year}-{month:02d}_staging", True)
    print(f"Wrote {target_dir}/chargeback_{year}-{month:02d}.csv")
else:
    print("No rows for the month; nothing written.")
