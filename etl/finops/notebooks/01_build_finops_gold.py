# Databricks notebook source
# MAGIC %md
# MAGIC # Build FinOps gold (P0 + P2 attribution)
# MAGIC
# MAGIC Materializes `{catalog}.{schema}.cost_daily`, `cost_by_product_daily`, and
# MAGIC `cost_by_estimate_daily` (rows tagged with `custom_tags['lakemeter_estimate_id']`)
# MAGIC from `system.billing.usage` × time-windowed `system.billing.list_prices`.
# MAGIC
# MAGIC See ADR-012 and `etl/finops/README.md`. Dollars are **list cost**, not invoice.

# COMMAND ----------

dbutils.widgets.text("catalog", "main")
dbutils.widgets.text("schema", "lakemeter_finops")
dbutils.widgets.text("lookback_days", "90")

catalog = dbutils.widgets.get("catalog").strip()
schema = dbutils.widgets.get("schema").strip()
lookback_days = int(dbutils.widgets.get("lookback_days").strip() or "90")

if lookback_days < 1 or lookback_days > 730:
    raise ValueError(f"lookback_days must be 1..730, got {lookback_days}")

fqn = f"{catalog}.{schema}"
print(f"Building FinOps gold in {fqn} lookback_days={lookback_days}")

# COMMAND ----------

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {fqn}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## cost_daily
# MAGIC Join: sku_name + usage_end_time inside [price_start_time, price_end_time).

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE TABLE {fqn}.cost_daily AS
SELECT
  u.usage_date,
  CAST(u.workspace_id AS STRING) AS workspace_id,
  u.cloud,
  u.sku_name,
  u.billing_origin_product,
  u.usage_unit,
  SUM(u.usage_quantity) AS usage_quantity,
  SUM(
    u.usage_quantity * COALESCE(
      TRY_CAST(lp.pricing.effective_list.default AS DOUBLE),
      TRY_CAST(lp.pricing.default AS DOUBLE),
      0.0
    )
  ) AS list_cost_usd,
  COUNT(*) AS usage_record_count
FROM system.billing.usage AS u
LEFT JOIN system.billing.list_prices AS lp
  ON lp.sku_name = u.sku_name
 AND u.usage_end_time >= lp.price_start_time
 AND (lp.price_end_time IS NULL OR u.usage_end_time < lp.price_end_time)
WHERE u.usage_date >= date_sub(current_date(), {lookback_days})
GROUP BY
  u.usage_date,
  CAST(u.workspace_id AS STRING),
  u.cloud,
  u.sku_name,
  u.billing_origin_product,
  u.usage_unit
""")

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE TABLE {fqn}.cost_by_product_daily AS
SELECT
  usage_date,
  workspace_id,
  cloud,
  billing_origin_product,
  SUM(usage_quantity) AS usage_quantity,
  SUM(list_cost_usd) AS list_cost_usd,
  SUM(usage_record_count) AS usage_record_count
FROM {fqn}.cost_daily
GROUP BY
  usage_date,
  workspace_id,
  cloud,
  billing_origin_product
""")

# COMMAND ----------

# MAGIC %md
# MAGIC ## cost_by_estimate_daily (P2)
# MAGIC Only usage with `custom_tags['lakemeter_estimate_id']` set.
# MAGIC Tagging contract: see `etl/finops/TAGGING.md`.

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE TABLE {fqn}.cost_by_estimate_daily AS
SELECT
  u.usage_date,
  CAST(u.workspace_id AS STRING) AS workspace_id,
  u.cloud,
  u.custom_tags['lakemeter_estimate_id'] AS lakemeter_estimate_id,
  u.custom_tags['lakemeter_workload_type'] AS lakemeter_workload_type,
  u.custom_tags['lakemeter_line_item_id'] AS lakemeter_line_item_id,
  u.billing_origin_product,
  u.sku_name,
  SUM(u.usage_quantity) AS usage_quantity,
  SUM(
    u.usage_quantity * COALESCE(
      TRY_CAST(lp.pricing.effective_list.default AS DOUBLE),
      TRY_CAST(lp.pricing.default AS DOUBLE),
      0.0
    )
  ) AS list_cost_usd,
  COUNT(*) AS usage_record_count
FROM system.billing.usage AS u
LEFT JOIN system.billing.list_prices AS lp
  ON lp.sku_name = u.sku_name
 AND u.usage_end_time >= lp.price_start_time
 AND (lp.price_end_time IS NULL OR u.usage_end_time < lp.price_end_time)
WHERE u.usage_date >= date_sub(current_date(), {lookback_days})
  AND u.custom_tags['lakemeter_estimate_id'] IS NOT NULL
  AND TRIM(u.custom_tags['lakemeter_estimate_id']) != ''
GROUP BY
  u.usage_date,
  CAST(u.workspace_id AS STRING),
  u.cloud,
  u.custom_tags['lakemeter_estimate_id'],
  u.custom_tags['lakemeter_workload_type'],
  u.custom_tags['lakemeter_line_item_id'],
  u.billing_origin_product,
  u.sku_name
""")

# COMMAND ----------

cost_daily_rows = spark.table(f"{fqn}.cost_daily").count()
product_rows = spark.table(f"{fqn}.cost_by_product_daily").count()
estimate_rows = spark.table(f"{fqn}.cost_by_estimate_daily").count()
unpriced = spark.sql(
    f"""
    SELECT COUNT(*) AS c
    FROM {fqn}.cost_daily
    WHERE list_cost_usd = 0 AND usage_quantity > 0
    """
).collect()[0]["c"]

total_list = spark.sql(
    f"SELECT COALESCE(SUM(list_cost_usd), 0) AS c FROM {fqn}.cost_daily"
).collect()[0]["c"]
attributed_list = spark.sql(
    f"SELECT COALESCE(SUM(list_cost_usd), 0) AS c FROM {fqn}.cost_by_estimate_daily"
).collect()[0]["c"]
attributed_pct = (
    float(attributed_list) / float(total_list) * 100.0 if float(total_list) > 0 else 0.0
)

spark.sql(f"""
CREATE OR REPLACE TABLE {fqn}.finops_run_metadata AS
SELECT
  current_timestamp() AS built_at,
  '{catalog}' AS catalog_name,
  '{schema}' AS schema_name,
  {lookback_days} AS lookback_days,
  {cost_daily_rows} AS cost_daily_rows,
  {product_rows} AS cost_by_product_daily_rows,
  {estimate_rows} AS cost_by_estimate_daily_rows,
  {unpriced} AS unpriced_positive_usage_rows,
  CAST({float(total_list)} AS DOUBLE) AS total_list_cost_usd,
  CAST({float(attributed_list)} AS DOUBLE) AS attributed_list_cost_usd,
  CAST({attributed_pct} AS DOUBLE) AS attributed_pct,
  'list' AS cost_basis,
  'ADR-012 P2' AS build_version
""")

print(
    f"Done: cost_daily={cost_daily_rows} by_product={product_rows} "
    f"by_estimate={estimate_rows} unpriced={unpriced} "
    f"attributed_pct={attributed_pct:.1f}"
)
dbutils.notebook.exit(
    f"ok rows={cost_daily_rows} by_estimate={estimate_rows} "
    f"attributed_pct={attributed_pct:.1f} basis=list"
)
