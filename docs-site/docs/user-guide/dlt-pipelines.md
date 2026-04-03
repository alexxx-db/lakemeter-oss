---
sidebar_position: 10
---

# Delta Live Tables (DLT)

Delta Live Tables is Databricks' declarative ETL framework for building reliable, automated data pipelines. Lakemeter supports cost estimation for all three editions -- **Core**, **Pro**, and **Advanced** -- in both **Classic** and **Serverless** modes.

## When to use DLT

Use DLT when you need **managed, declarative data pipelines** with built-in data quality checks, automatic dependency management, and pipeline monitoring. If you just need simple batch jobs without the DLT framework, [Jobs](/user-guide/jobs-compute) is simpler and often cheaper.

## Real-world example

> **Scenario:** You are building a real-time streaming pipeline on AWS us-east-1 (Premium tier) that ingests change data from a source database using CDC. The pipeline runs continuously, 24/7. You need the **Pro** edition for CDC support and want a 3-worker cluster with Photon.

### Configuration

| Field | Value |
|-------|-------|
| Workload Type | DLT |
| Serverless | Off |
| SDP Edition | Pro |
| Driver Instance Type | m5d.xlarge |
| Worker Instance Type | m5d.xlarge |
| Number of Workers | 3 |
| Photon | On |
| Driver Pricing Tier | On-Demand |
| Worker Pricing Tier | On-Demand |
| Hours Per Month | 730 (24/7) |

### Step-by-step calculation

**1. DBU rate per hour**

```
DBU/Hour = (Driver DBU + Worker DBU x Workers) x Photon Multiplier
         = (1.0 + 1.0 x 3) x 2.9
         = 4.0 x 2.9
         = 11.6 DBU/hour
```

:::info Photon multiplier varies by cloud
The Photon multiplier for DLT is **2.9x on AWS** and **2.5x on Azure/GCP**. This example uses the AWS rate. Lakemeter loads the correct multiplier automatically from the pricing bundle.
:::

**2. Monthly DBUs and cost**

```
Monthly DBUs = 11.6 x 730 = 8,468 DBUs
DBU Cost     = 8,468 x $0.25/DBU (example DLT Pro Photon rate) = $2,117.00
```

**3. VM cost**

```
VM Cost = (Driver $/hr + Worker $/hr x Workers) x Hours/Month
        = ($0.192 + $0.192 x 3) x 730
        = $0.768/hr x 730
        = $560.64
```

**4. Total**

```
Total = $2,117.00 + $560.64 = $2,677.64/month
```

:::note
These are example rates for illustration. Actual $/DBU and VM prices depend on your cloud, region, and pricing tier. Lakemeter loads real rates from the Databricks pricing bundle.
:::

## Choosing an edition

DLT has three editions with progressively more features:

| Feature | Core | Pro | Advanced |
|---------|:----:|:---:|:--------:|
| Pipeline orchestration and auto-scaling | Yes | Yes | Yes |
| Change Data Capture (CDC) | No | Yes | Yes |
| Advanced monitoring | Basic | Enhanced | Full |
| Data quality expectations | No | No | Yes |
| Photon support | Yes | Yes | Yes |
| Serverless support | Yes | Yes | Yes |

**When to pick each:**

- **Core** -- Simple ETL that reads from files or tables, transforms, and writes. No CDC needed. Lowest cost.
- **Pro** -- You need CDC (tracking inserts, updates, deletes from a source), or you want enhanced monitoring for operational pipelines. Most common choice.
- **Advanced** -- Mission-critical pipelines where you need data quality expectations (assertions that fail the pipeline if data does not meet standards). Highest cost.

:::tip
The edition selector in the UI is labeled **"SDP Edition"** (Spark Declarative Pipelines). Core, Pro, and Advanced correspond to increasing levels of DLT features and pricing.
:::

## Configuration reference

### Compute mode

| Field | Description | Default |
|-------|-------------|---------|
| **Serverless** | Toggle between Classic and Serverless. Requires **Premium** tier or above. | Off |
| **Serverless Mode** | Standard (1x) or Performance (2x). Only shown when Serverless is on. | Standard |

### Classic mode fields

| Field | Description | Default |
|-------|-------------|---------|
| **SDP Edition** | Core, Pro, or Advanced. Determines the DLT pricing tier. Hidden when Serverless is on. | Pro |
| **Driver Instance Type** | VM size for the driver | -- (select from list) |
| **Worker Instance Type** | VM size for the workers | -- (select from list) |
| **Number of Workers** | Cluster size | 2 |
| **Photon** | Hardware-accelerated engine (2.9x DBU multiplier on AWS, 2.5x on Azure/GCP) | Off |
| **Driver Pricing Tier** | On-Demand, Spot, Reserved 1yr, or Reserved 3yr | On-Demand |
| **Worker Pricing Tier** | On-Demand, Spot, Reserved 1yr, or Reserved 3yr | Spot |

### Usage fields

DLT supports two input methods:

**Direct Hours (for continuous pipelines):**

| Field | Description | Default |
|-------|-------------|---------|
| **Hours Per Month** | Total pipeline uptime | 0 |

Common values: 730 (24/7 streaming), 176 (business hours), 44 (light usage).

**Run-Based (for scheduled pipelines):**

| Field | Description | Default |
|-------|-------------|---------|
| **Runs Per Day** | Pipeline executions per day | 1 |
| **Avg Runtime (minutes)** | Duration per run | 30 |
| **Days Per Month** | Active days | 22 |

## How costs are calculated

### Classic

```
DBU/Hour    = (Driver DBU Rate + Worker DBU Rate x Workers) x Photon Multiplier
DBU Cost    = DBU/Hour x Hours/Month x $/DBU
VM Cost     = (Driver $/hr + Worker $/hr x Workers) x Hours/Month
Total       = DBU Cost + VM Cost
```

The $/DBU rate depends on your edition (Core, Pro, or Advanced) and whether Photon is enabled. The Photon multiplier is cloud-specific: **2.9x** on AWS, **2.5x** on Azure/GCP.

### Serverless

```
DBU/Hour    = (Driver DBU Rate + Worker DBU Rate x Workers) x Photon Multiplier x Serverless Multiplier
DBU Cost    = DBU/Hour x Hours/Month x $/DBU
Total       = DBU Cost  (no VM costs)
```

- Photon is always applied for Serverless. The multiplier is cloud-specific: **2.9x** on AWS, **2.5x** on Azure/GCP.
- **Serverless Multiplier**: 1.0 for Standard, 2.0 for Performance

:::caution Important
DLT Serverless uses the **`JOBS_SERVERLESS_COMPUTE`** SKU regardless of which edition you selected in Classic mode. This means all DLT Serverless workloads are billed at the same $/DBU rate -- the edition distinction only affects Classic pricing.

When Serverless is enabled, the edition selector is hidden in the UI because the edition does not affect the Serverless price.
:::

### SKU mapping

| Edition | Classic SKU | Classic + Photon SKU | Serverless SKU |
|---------|------------|---------------------|----------------|
| Core | `DLT_CORE_COMPUTE` | `DLT_CORE_COMPUTE_(PHOTON)` | `JOBS_SERVERLESS_COMPUTE` |
| Pro | `DLT_PRO_COMPUTE` | `DLT_PRO_COMPUTE_(PHOTON)` | `JOBS_SERVERLESS_COMPUTE` |
| Advanced | `DLT_ADVANCED_COMPUTE` | `DLT_ADVANCED_COMPUTE_(PHOTON)` | `JOBS_SERVERLESS_COMPUTE` |

## Tips

- **DLT Serverless pricing is edition-independent**: If cost is your primary concern and you were choosing between Core and Pro Serverless, it does not matter -- the price is the same. Pick the edition based on features, not cost, when using Serverless.
- **Classic edition pricing varies significantly**: Core is the cheapest, Advanced is the most expensive. If you do not need CDC or data quality expectations, stick with Core Classic to save money.
- **Photon for DLT is almost always worth it**: DLT pipelines are inherently data-processing-heavy. Photon's higher DBU rate (2.9x on AWS, 2.5x on Azure/GCP) is usually offset by significantly faster execution, resulting in fewer total hours billed.
- **Continuous vs scheduled**: For pipelines that only need to process data a few times a day, use run-based scheduling (e.g., 4 runs/day x 15 min). Reserve continuous (730 hours) for true streaming use cases.

## Common mistakes

- **Choosing Advanced "just in case"**: Advanced edition costs significantly more than Core or Pro in Classic mode. Only choose it if you actually need data quality expectations. You can always upgrade later.
- **Assuming edition affects Serverless cost**: All DLT Serverless workloads use `JOBS_SERVERLESS_COMPUTE` pricing. Switching from Core to Pro Serverless changes nothing in the cost estimate.
- **Setting 730 hours for a batch pipeline**: If your pipeline runs 4 times a day for 15 minutes each, that is only 22 hours/month -- not 730. Use run-based input to calculate accurately.
- **Forgetting the Photon multiplier**: Like Jobs, Photon increases the DBU rate by 2.9x (AWS) or 2.5x (Azure/GCP). This is reflected in the cost but is offset by faster processing. Compare total cost with and without Photon, not just the DBU rate.

## Excel export

Each DLT workload appears as one row in the exported spreadsheet:

| Column | What it shows |
|--------|--------------|
| Hours/Month | Direct value or calculated from runs/runtime/days |
| DBU/Hour | Based on instance types, workers, and multipliers |
| Monthly DBUs | DBU/Hour x Hours/Month |
| SKU | Edition-specific Classic SKU or `JOBS_SERVERLESS_COMPUTE` |
| DBU Cost (List) | At list price |
| DBU Cost (Discounted) | At negotiated rate |
| VM Cost | Classic: driver + workers; Serverless: $0 |
| Total Cost | DBU Cost + VM Cost |
