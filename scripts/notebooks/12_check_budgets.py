# Databricks notebook source
# MAGIC %md
# MAGIC # 12: Check Budgets
# MAGIC
# MAGIC Compares month-to-date actual spend (from
# MAGIC `lakemeter.product_usage_daily`) against budgets defined in
# MAGIC `lakemeter.ref_budgets` and records breaches in
# MAGIC `lakemeter.budget_alerts`.
# MAGIC
# MAGIC Budget rows are scoped by `scope_type`:
# MAGIC - `cost_center` with the cost center as `scope_key`
# MAGIC - `product_line` with the product line as `scope_key`
# MAGIC - `overall` (scope_key ignored, use `all`)
# MAGIC
# MAGIC Severity: `WARN` at `warn_pct` of budget (default 80%), `CRITICAL` at
# MAGIC `critical_pct` (default 100%). Alerts are idempotent within a month:
# MAGIC each run replaces the current month's alert rows, so dashboards can
# MAGIC read the table directly without dedup logic.

# COMMAND ----------

dbutils.widgets.text("instance_name", "lakemeter-customer")
dbutils.widgets.text("db_name", "lakemeter_pricing")
dbutils.widgets.text("secrets_scope", "lakemeter-secrets")

instance_name = dbutils.widgets.get("instance_name")
db_name = dbutils.widgets.get("db_name")
secrets_scope = dbutils.widgets.get("secrets_scope")

# COMMAND ----------

from datetime import date

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

month_start = date.today().replace(day=1)
month_start_sql = f"DATE '{month_start}'"

# COMMAND ----------

cur.execute("""
SELECT scope_type, scope_key, monthly_budget, warn_pct, critical_pct
FROM lakemeter.ref_budgets
WHERE active
""")
budgets = cur.fetchall()
if not budgets:
    print("No active budgets in lakemeter.ref_budgets; nothing to check.")
    print("Insert rows like: ('cost_center', 'CC-101', 5000) or ('product_line', 'model_serving', 12000).")

# COMMAND ----------

# Idempotent within the month: rebuild this month's alerts from scratch.
cur.execute("""
DELETE FROM lakemeter.budget_alerts
WHERE alert_month = %s
""", (month_start,))
alerts = []

for scope_type, scope_key, monthly_budget, warn_pct, critical_pct in budgets:
    if scope_type == "cost_center":
        cur.execute(f"""
        SELECT COALESCE(SUM(list_cost), 0) FROM lakemeter.product_usage_daily
        WHERE usage_date >= {month_start_sql} AND cost_center = %s
        """, (scope_key,))
    elif scope_type == "product_line":
        cur.execute(f"""
        SELECT COALESCE(SUM(list_cost), 0) FROM lakemeter.product_usage_daily
        WHERE usage_date >= {month_start_sql} AND product_line = %s
        """, (scope_key,))
    elif scope_type == "overall":
        cur.execute(f"""
        SELECT COALESCE(SUM(list_cost), 0) FROM lakemeter.product_usage_daily
        WHERE usage_date >= {month_start_sql}
        """)
    else:
        print(f"Skipping unknown scope_type {scope_type!r} (key {scope_key})")
        continue

    mtd_cost = float(cur.fetchone()[0])
    budget = float(monthly_budget)
    ratio = mtd_cost / budget if budget else 0.0
    if ratio >= float(critical_pct):
        severity = "CRITICAL"
    elif ratio >= float(warn_pct):
        severity = "WARN"
    else:
        continue

    cur.execute("""
    INSERT INTO lakemeter.budget_alerts (
        alert_month, scope_type, scope_key, mtd_cost, monthly_budget, severity
    ) VALUES (%s, %s, %s, %s, %s, %s)
    """, (month_start, scope_type, scope_key, mtd_cost, monthly_budget, severity))
    alerts.append((severity, scope_type, scope_key, mtd_cost, budget, ratio))

# COMMAND ----------

if alerts:
    print(f"{len(alerts)} budget alert(s) for {month_start}:")
    for severity, scope_type, scope_key, mtd_cost, budget, ratio in sorted(alerts):
        print(f"  {severity:8s} {scope_type}/{scope_key}: {mtd_cost:.2f} of {budget:.2f} ({ratio:.0%})")
    if any(a[0] == "CRITICAL" for a in alerts):
        print("WARNING: at least one budget is in CRITICAL breach this month")
else:
    print(f"All budgets within thresholds for {month_start}.")

cur.close()
conn.close()
print("Budget check complete.")
