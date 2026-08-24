---
sidebar_position: 5
---

# Live FinOps

Lakemeter’s **Actuals** plane answers “what did we spend?” using Databricks
system billing tables. It is separate from the Lakebase **estimate** pricing
snapshot (see [Pricing Data](./pricing-data)). Decision record: ADR-012 in
`DECISIONS.md`.

## Architecture

```text
system.billing.usage  ×  time-windowed list_prices
        │
        ▼
etl/finops gold job  →  {catalog}.lakemeter_finops.*
        │
        ▼
SQL warehouse (App SP SELECT)  →  App /actuals + /api/v1/finops/*
```

| Table | Purpose |
|-------|---------|
| `cost_daily` | Account spend by day / SKU / product |
| `cost_by_product_daily` | UI product mix |
| `cost_by_estimate_daily` | Spend tagged with `lakemeter_estimate_id` |
| `finops_run_metadata` | Freshness + attribution % |

Dollars are **list cost**, not invoice.

## Deploy gold

```bash
cd etl/finops
databricks bundle deploy --target dev
databricks bundle run lakemeter_finops_gold --target dev
```

The job ships **paused**. Enable the schedule after confirming `system.billing`
access. Details: [`etl/finops/README.md`](https://github.com/databrickslabs/lakemeter-oss/blob/main/etl/finops/README.md).

## App configuration

Set on the Databricks App (`app.yaml` / environment):

| Variable | Meaning |
|----------|---------|
| `FINOPS_WAREHOUSE_ID` | Warehouse the app SP can use |
| `FINOPS_CATALOG` | Default `main` |
| `FINOPS_SCHEMA` | Default `lakemeter_finops` |

Grant the app service principal `USE CATALOG`, `USE SCHEMA`, and `SELECT` on
gold only — not raw `system.billing` for App serving.

## Tagging (estimate ↔ actual)

Variance requires custom tags on workloads. Contract:
[`TAGGING.md`](https://github.com/databrickslabs/lakemeter-oss/blob/main/etl/finops/TAGGING.md).

| Tag | Required |
|-----|----------|
| `lakemeter_estimate_id` | Yes (estimate UUID) |
| `lakemeter_workload_type` | Recommended |
| `lakemeter_line_item_id` | Optional |

In the App, open an estimate → **FinOps tags** to copy key=value or JSON for
jobs, clusters, or serverless usage policies. Then re-run the gold job and use
**Actuals → Estimate ↔ actual variance**.

API helpers (SSO):

- `GET /api/v1/finops/metadata|summary|top-skus`
- `GET /api/v1/finops/tags/{estimate_id}`
- `GET /api/v1/finops/variance/{estimate_id}`
