-- Lakemeter FinOps P0 — gold cost_daily
-- Join semantics: ADR-012 / Databricks system.billing guidance
-- Placeholders: {{catalog}}, {{schema}}, {{lookback_days}}

CREATE SCHEMA IF NOT EXISTS {{catalog}}.{{schema}};

CREATE OR REPLACE TABLE {{catalog}}.{{schema}}.cost_daily AS
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
WHERE u.usage_date >= date_sub(current_date(), {{lookback_days}})
GROUP BY
  u.usage_date,
  CAST(u.workspace_id AS STRING),
  u.cloud,
  u.sku_name,
  u.billing_origin_product,
  u.usage_unit;

CREATE OR REPLACE TABLE {{catalog}}.{{schema}}.cost_by_product_daily AS
SELECT
  usage_date,
  workspace_id,
  cloud,
  billing_origin_product,
  SUM(usage_quantity) AS usage_quantity,
  SUM(list_cost_usd) AS list_cost_usd,
  SUM(usage_record_count) AS usage_record_count
FROM {{catalog}}.{{schema}}.cost_daily
GROUP BY
  usage_date,
  workspace_id,
  cloud,
  billing_origin_product;

-- P2: estimate-attributed spend (requires tagging contract — see TAGGING.md)
CREATE OR REPLACE TABLE {{catalog}}.{{schema}}.cost_by_estimate_daily AS
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
WHERE u.usage_date >= date_sub(current_date(), {{lookback_days}})
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
  u.sku_name;
