# Lakemeter FinOps tagging contract (P2)

Variance (estimate ↔ actual) only works when billable usage carries Lakemeter
tags. Apply these on jobs, clusters, warehouses, pipelines, or via **serverless
usage policies**.

## Required

| Tag key | Value | Notes |
|---------|-------|-------|
| `lakemeter_estimate_id` | Estimate UUID (string) | Must match `lakemeter.estimates.estimate_id` |

## Recommended

| Tag key | Value | Notes |
|---------|-------|-------|
| `lakemeter_workload_type` | e.g. `JOBS`, `DLT`, `DBSQL`, `MODEL_SERVING` | Align with Lakemeter workload types |
| `lakemeter_line_item_id` | Line-item UUID | Optional finer grain (future UI) |

## Gold output

Tagged usage lands in `{catalog}.{schema}.cost_by_estimate_daily`.
Unattributed spend remains in `cost_daily` / `cost_by_product_daily` and is
visible on the Actuals page; it simply cannot join to an estimate.

## Variance math (App)

- **Plan (period):** sum of line-item `cost_calculation_response.total_cost.cost_per_month` × `(days / 30)`.
- **Actual (period):** sum of `list_cost_usd` in `cost_by_estimate_daily` for that estimate id over the same window.
- **Variance:** `actual − plan` (positive = over plan). List basis only unless a commercial overlay is applied in the UI.

## Examples

Jobs (cluster/job tags):

```text
lakemeter_estimate_id = 550e8400-e29b-41d4-a716-446655440000
lakemeter_workload_type = JOBS
```

Serverless usage policy: add the same keys so serverless SKUs inherit attribution.
