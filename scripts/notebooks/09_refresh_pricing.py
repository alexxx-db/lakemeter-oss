# Databricks notebook source
# MAGIC %md
# MAGIC # Refresh Pricing Data
# MAGIC Reloads pricing into Lakebase and rebuilds SKU mapping.
# MAGIC Intended for the scheduled `lakemeter_pricing_refresh` job (and manual runs).
# MAGIC
# MAGIC `pricing_source`:
# MAGIC - `bundled_csv` (default) — installer CSV snapshot via `03_load_pricing_data`
# MAGIC - `unity_catalog` — UC-governed tables via `10_refresh_pricing_from_uc`
# MAGIC
# MAGIC Does not modify estimates or other application tables.

# COMMAND ----------

import time
_start = time.time()

dbutils.widgets.text("project_id", "lakemeter-customer")
dbutils.widgets.text("db_name", "lakemeter_pricing")
dbutils.widgets.text("secrets_scope", "lakemeter-secrets")
dbutils.widgets.text("pricing_source", "bundled_csv")
dbutils.widgets.text("uc_catalog", "lakemeter_catalog")
dbutils.widgets.text("uc_schema", "lakemeter")

project_id = dbutils.widgets.get("project_id")
db_name = dbutils.widgets.get("db_name")
secrets_scope = dbutils.widgets.get("secrets_scope")
pricing_source = (dbutils.widgets.get("pricing_source") or "bundled_csv").strip().lower()
uc_catalog = dbutils.widgets.get("uc_catalog")
uc_schema = dbutils.widgets.get("uc_schema")

print(f"Refreshing pricing for project={project_id} db={db_name} source={pricing_source}")

# COMMAND ----------

if pricing_source in ("unity_catalog", "uc", "unity"):
    load_result = dbutils.notebook.run(
        "./10_refresh_pricing_from_uc",
        timeout_seconds=3600,
        arguments={
            "project_id": project_id,
            "db_name": db_name,
            "secrets_scope": secrets_scope,
            "uc_catalog": uc_catalog,
            "uc_schema": uc_schema,
        },
    )
    print(f"UC load result: {load_result}")
else:
    # Bundled CSV path — 03 loads data; 04 rebuilds SKU mapping
    load_result = dbutils.notebook.run(
        "./03_load_pricing_data",
        timeout_seconds=3600,
        arguments={
            "project_id": project_id,
            "db_name": db_name,
            "secrets_scope": secrets_scope,
        },
    )
    print(f"CSV load result: {load_result}")

    sku_result = dbutils.notebook.run(
        "./04_create_sku_mapping",
        timeout_seconds=1800,
        arguments={
            "project_id": project_id,
            "db_name": db_name,
        },
    )
    print(f"SKU mapping result: {sku_result}")

# COMMAND ----------

elapsed = time.time() - _start
print(f"Pricing refresh complete ({elapsed:.1f}s) source={pricing_source}")
dbutils.notebook.exit(f"PASS: Pricing refreshed via {pricing_source} ({elapsed:.1f}s)")
