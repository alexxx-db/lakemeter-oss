---
sidebar_position: 4
---

# Pricing Data

Lakemeter estimates use **snapshot pricing** loaded into Lakebase, not a live FinOps feed. This page describes the default CSV path and the optional Unity Catalog (UC) publication path.

For **account actuals** (`system.billing.usage` → UC gold → App **Actuals** page), see the [Live FinOps](./finops) admin guide (ADR-012, `etl/finops/`). Set `FINOPS_WAREHOUSE_ID` on the app and grant the app SP `SELECT` on gold. That path does not replace this Lakebase pricing snapshot.

## Default: bundled CSV snapshot

New installs and the paused `lakemeter_pricing_refresh` job load flattened CSVs from `scripts/pricing_data/` via `03_load_pricing_data.py` (TRUNCATE + INSERT into `lakemeter.sync_*` tables). Freshness is recorded in `lakemeter.pricing_metadata` with `source=bundled_csv`.

The app surfaces “prices as of” through `GET /api/v1/pricing/freshness` and the Pricing page banner.

**When to use:** OSS installs, demos, and environments that accept periodic CSV updates from the repository.

## Optional: Unity Catalog–governed pricing

Enterprises that already curate list prices in UC can publish those tables into Lakebase instead of (or in addition to) the CSV bundle.

### Architecture

```text
System tables / cloud APIs / spreadsheets
        │
        ▼
etl/pricing_sync notebooks  →  UC tables (e.g. lakemeter_catalog.lakemeter.*)
        │
        ▼
10_refresh_pricing_from_uc  →  Lakebase sync_* + pricing_metadata (source=unity_catalog)
        │
        ▼
Lakemeter app (SSO) reads Lakebase for estimates
```

The historical Lakebase CDC sync design is documented in [`etl/pricing_sync/README.md`](https://github.com/databrickslabs/lakemeter-oss/blob/main/etl/pricing_sync/README.md). The installer path uses CSV for reliability; the UC notebook is the supported optional alternative for governed publication.

### Expected UC tables

`10_refresh_pricing_from_uc.py` reads these tables (configurable catalog/schema):

| UC table | Lakebase target |
|---|---|
| `dbu_prices` | `sync_pricing_dbu_rates` |
| `vm_costs` | `sync_pricing_vm_costs` |
| `instance_rates` | `sync_ref_instance_dbu_rates` |
| `sku_region_mapping` | `sync_ref_sku_region_map` |

Column names should match the SELECT lists in that notebook. Product-rate tables (DBSQL, FMAPI, serverless) can remain on the CSV path or be extended in the notebook when your UC layout includes them.

### Enabling UC refresh

1. Populate UC with `etl/pricing_sync` (or your own pipeline).
2. Confirm secrets `lakebase-host` and `lakebase-user` exist in the Lakemeter secrets scope.
3. Run the pricing refresh job with `pricing_source=unity_catalog` (and optional `uc_catalog` / `uc_schema`), or run `09_refresh_pricing` / `10_refresh_pricing_from_uc` manually.
4. Unpause `lakemeter_pricing_refresh` after validating freshness and estimate spot-checks.
5. Confirm `GET /api/v1/pricing/freshness` reports `source=unity_catalog`.

Job parameters are defined on `lakemeter_pricing_refresh` in `scripts/databricks.yml`.

## Quality gates

Both CSV and UC loaders fail the run if critical tables are empty (`sync_pricing_dbu_rates`, `sync_pricing_vm_costs`, `sync_ref_instance_dbu_rates`). Treat pricing as planning-grade until validated against [Databricks pricing](https://www.databricks.com/product/pricing) and customer commercial terms.

## Related

- [Installer Guide](./installer)
- [Deployment Inventory](./deployment-inventory)
- [Architecture](./architecture)
