---
sidebar_position: 11
---

# Lakeflow Connect Sizing

> **Lakemeter UI name:** Lakeflow Connect

Use this guide to model Lakeflow Connect ingestion cost in Lakemeter. It explains the estimator inputs and calculation behavior, not connector setup, CDC design, or product limits.

For current product guidance, start from the [official Databricks documentation](https://docs.databricks.com/). For current public rates, use the [Databricks pricing page](https://www.databricks.com/product/pricing) and the rates shown in Lakemeter.

## What Lakemeter estimates

A Lakeflow Connect workload includes:

1. **Pipeline** — billed as **DLT Serverless** for the selected SDP edition (default **Advanced**)
2. **Gateway** (optional) — billed as **DLT Classic Advanced** plus a single-driver VM, for database connectors that require a gateway

The estimate-level cloud, region, and Databricks tier determine which choices and rates Lakemeter loads. Gateway is typically relevant for Premium/Enterprise scenarios where Connect is available.

## Form inputs

### Pipeline Edition

Select the SDP edition that matches the planned Connect pipeline. Lakemeter uses this edition context when resolving the DLT Serverless SKU for the pipeline component. Prefer **Advanced** unless your scenario intentionally uses another edition.

### Gateway (optional)

Enable **Include database connector gateway** when the scenario uses a Connect database gateway.

When enabled, choose a **Gateway Instance** (or leave the cloud default). Lakemeter models the gateway as always-on classic DLT Advanced compute with a separate VM charge for that instance.

### Monthly usage

Lakemeter offers two usage input methods for the **pipeline** component.

#### Run-Based

Enter:

- **Runs/Day**
- **Avg Runtime (min)**
- **Days/Month**

Lakemeter converts the entries to monthly pipeline compute hours:

```text
Hours per month
  = Runs per day
  × (Average runtime in minutes ÷ 60)
  × Days per month
```

#### Direct Hours

Enter **Hours/Month** when total pipeline active time is known directly.

Gateway hours are modeled separately as always-on (730 hours/month) when the gateway is enabled; they are not driven by the pipeline run schedule.

## How the estimate is calculated

### Pipeline (DLT Serverless)

Lakemeter estimates pipeline DBU consumption using a DLT Serverless sizing proxy (default instance shape and worker count for the cloud), multiplied by pipeline hours and the regional serverless DLT rate. Photon is treated as built-in for serverless.

```text
Pipeline monthly cost
  ≈ Pipeline DBUs
  × Regional DLT Serverless price per DBU
```

No separate pipeline VM charge is added.

### Gateway (optional)

When the gateway is enabled:

```text
Gateway DBU cost
  ≈ Gateway instance DBU rate
  × Photon multiplier
  × Gateway hours (default 730)

Gateway VM cost
  ≈ Gateway instance $/hour
  × Gateway hours

Gateway monthly cost
  = Gateway DBU cost + Gateway VM cost
```

Total Lakeflow Connect cost is the sum of pipeline and gateway components.

## What to review before saving

- Does this scenario need a database gateway, or is pipeline-only sufficient?
- Are pipeline hours based on expected Connect update duration, not wall-clock calendar time alone?
- Is the selected edition intentional for the commercial scenario?
- Does the estimate use the intended cloud, region, and pricing tier?
- Have list rates and negotiated terms been checked before external use?

## Excel export

Each Lakeflow Connect workload is exported as one row. The configuration notes whether a gateway is included. Cost fields include pipeline DBU consumption and, when enabled, gateway DBU and VM components.

## Related

- [Lakeflow Spark Declarative Pipelines](./dlt-pipelines)
- [Calculation Reference](./calculation-reference)
- [Workload Sizing Guides](./workloads)
- [Exporting to Excel](./exporting)
