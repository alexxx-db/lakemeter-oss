# Lakemeter Live FinOps (P0 gold)

**ADR:** [ADR-012](../../DECISIONS.md#adr-012-live-finops-is-a-separate-actuals-plane-not-lakebase-oltp)

Builds Unity Catalog gold tables from Databricks system billing tables for the
**actuals** plane. This is separate from the Lakebase pricing snapshot used by
the cost estimator (ADR-002 / ADR-003).

## Sources

| Table | Role |
|-------|------|
| `system.billing.usage` | Billable usage facts (truth for quantity) |
| `system.billing.list_prices` | Time-windowed list rates by SKU |

Join rule (required):

```text
usage.sku_name = list_prices.sku_name
AND usage.usage_end_time >= list_prices.price_start_time
AND (list_prices.price_end_time IS NULL
     OR usage.usage_end_time < list_prices.price_end_time)
```

Always group/retain `billing_origin_product` with `sku_name`.

## Output schema

Default: `{catalog}.lakemeter_finops`

| Table | Grain | Notes |
|-------|-------|-------|
| `cost_daily` | date × workspace × cloud × sku × origin × unit | List $ = qty × effective list default |
| `cost_by_product_daily` | date × workspace × cloud × origin | Rolled-up for UI |
| `cost_by_estimate_daily` | date × estimate tag × product/sku | Only rows with `lakemeter_estimate_id` |
| `finops_run_metadata` | one row per job run | Lookback, attribution %, as-of |

Tagging contract: [TAGGING.md](./TAGGING.md).

Dollars are **list cost**, not invoice. Commercial overlays are out of scope for P0.

## Deploy

```bash
cd etl/finops
databricks bundle validate --target dev
databricks bundle deploy --target dev
# Job ships PAUSED — enable schedule after confirming system.billing access
databricks bundle run lakemeter_finops_gold --target dev
```

Parameters:

| Parameter | Default | Meaning |
|-----------|---------|---------|
| `catalog` | `main` | UC catalog for gold |
| `schema` | `lakemeter_finops` | UC schema |
| `lookback_days` | `90` | Usage window ending today |

## Prerequisites

- Workspace access to `system.billing.usage` and `system.billing.list_prices`
- Privilege to create schema/tables in `{catalog}.{schema}`
- Serverless job environment (bundle default)

## App serving (P1)

The Lakemeter App reads gold via SQL warehouse Statement Execution (App SP):

| Env | Purpose |
|-----|---------|
| `FINOPS_WAREHOUSE_ID` | Warehouse the app SP can use |
| `FINOPS_CATALOG` | Default `main` |
| `FINOPS_SCHEMA` | Default `lakemeter_finops` |
| `FINOPS_AUTO_WAREHOUSE` | `true` only for local/dev discovery |

API (SSO):

- `GET /api/v1/finops/metadata|summary|top-skus`
- `GET /api/v1/finops/variance/{estimate_id}` — plan (Lakebase) vs tagged actuals

UI: **Actuals** (`/actuals`) including variance lookup.

Grant the app SP `SELECT` on `{catalog}.{schema}` (and `USE CATALOG` / `USE SCHEMA`). Do not grant `system.billing` to the App SP for App serving — gold is the surface.

## Out of scope (later phases)

- AI assist on overrun drivers; durable commercial rate cards
- Budgets / chargeback (P3)
- Syncing gold into Lakebase
