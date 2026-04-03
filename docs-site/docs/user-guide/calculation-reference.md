---
sidebar_position: 9
---

# Calculation Reference

This page documents the exact cost calculation formulas Lakemeter uses for each workload type, along with fully worked examples using real pricing data.

## General Pattern

All Databricks workload costs follow a common structure:

```
Monthly Cost = DBU Cost + VM Cost (Classic only)
DBU Cost     = Monthly DBUs × $/DBU
VM Cost      = (Driver $/hr + Worker $/hr × Workers) × Hours/Month
```

Serverless workloads have **no VM cost** — the infrastructure is included in the DBU price.

## Hours Calculation

How Lakemeter determines monthly hours depends on the workload's usage mode:

| Usage Mode | Formula | Default |
|-----------|---------|---------|
| **Run-based** (Jobs, DLT) | Runs/Day × Avg Runtime (min) ÷ 60 × Days/Month | 22 business days |
| **Continuous** (DBSQL, Model Serving, etc.) | Hours/Month entered directly | 730 hrs (24/7) |

---

## Worked Example 1: Jobs Classic with Photon

**Scenario:** An ETL pipeline running 5 times per business day, 45 minutes per run, using 4 `i3.xlarge` workers on AWS us-east-1 (Premium tier) with Photon enabled.

### Step 1: Calculate monthly hours

```
Hours/Month = (Runs/Day × Avg Runtime Minutes ÷ 60) × Days/Month
            = (5 × 45 ÷ 60) × 22
            = 3.75 × 22
            = 82.5 hours
```

### Step 2: Calculate DBU/Hour

The `i3.xlarge` instance has a DBU rate of **1.0 DBU/hr** per instance.

```
DBU/Hour = (Driver DBU + Worker DBU × Num Workers) × Photon Multiplier
         = (1.0 + 1.0 × 4) × 2.0
         = 5.0 × 2.0
         = 10.0 DBU/hr
```

The Photon multiplier is **2.0** when Photon is enabled (1.0 otherwise).

### Step 3: Calculate monthly DBUs and DBU cost

The `JOBS_COMPUTE_(PHOTON)` SKU on AWS us-east-1 Premium costs **$0.15/DBU**.

```
Monthly DBUs = DBU/Hour × Hours/Month
             = 10.0 × 82.5
             = 825.0 DBUs

DBU Cost     = 825.0 × $0.15
             = $123.75/month
```

### Step 4: Calculate VM cost

The `i3.xlarge` on-demand rate is **$0.312/hr** per instance.

```
VM Cost = (Driver $/hr + Worker $/hr × Workers) × Hours/Month
        = ($0.312 + $0.312 × 4) × 82.5
        = $1.56 × 82.5
        = $128.70/month
```

### Step 5: Total cost

```
Monthly Cost = DBU Cost + VM Cost
             = $123.75 + $128.70
             = $252.45/month

Annual Cost  = $252.45 × 12 = $3,029.40/year
```

---

## Worked Example 2: DBSQL Serverless Warehouse

**Scenario:** A Medium Serverless SQL warehouse running 8 hours per business day (22 days/month) on AWS us-east-1 (Premium tier).

### Step 1: Calculate monthly hours

```
Hours/Month = 8 hours/day × 22 days
            = 176 hours
```

### Step 2: Look up DBU/Hour from size mapping

| Size | DBU/Hour |
|------|----------|
| 2X-Small | 4 |
| X-Small | 6 |
| Small | 12 |
| **Medium** | **24** |
| Large | 40 |
| X-Large | 80 |
| 2X-Large | 144 |
| 3X-Large | 272 |
| 4X-Large | 528 |

For a single cluster:

```
DBU/Hour = Size DBU × Number of Clusters
         = 24 × 1
         = 24 DBU/hr
```

### Step 3: Calculate cost

The `SERVERLESS_SQL_COMPUTE` SKU on AWS us-east-1 Premium costs **$0.70/DBU**.

```
Monthly DBUs = 24 × 176 = 4,224 DBUs
DBU Cost     = 4,224 × $0.70 = $2,956.80/month
VM Cost      = $0 (Serverless — no separate VM charges)

Monthly Cost = $2,956.80
Annual Cost  = $2,956.80 × 12 = $35,481.60/year
```

---

## Worked Example 3: FMAPI Token-Based Pricing

**Scenario:** Using Llama 3.1 8B on Databricks (AWS) with 50 million input tokens and 10 million output tokens per month.

### Step 1: Look up token rates

For Llama 3.1 8B on AWS:

| Rate Type | DBU per 1M Tokens |
|-----------|-------------------|
| Input tokens | 2.143 |
| Output tokens | 6.429 |

### Step 2: Calculate monthly DBUs for each rate type

```
Input DBUs  = 50M tokens × 2.143 DBU/1M = 107.15 DBUs
Output DBUs = 10M tokens × 6.429 DBU/1M =  64.29 DBUs
```

### Step 3: Calculate cost

The `SERVERLESS_REAL_TIME_INFERENCE` SKU on AWS us-east-1 Premium costs **$0.07/DBU**.

```
Input Cost   = 107.15 × $0.07 = $7.50/month
Output Cost  =  64.29 × $0.07 = $4.50/month

Monthly Cost = $7.50 + $4.50 = $12.00/month
Annual Cost  = $12.00 × 12 = $144.00/year
```

:::tip
Output tokens are typically more expensive than input tokens. For Llama 3.1 8B, output rates are 3x the input rate. Budget accordingly if your use case generates long responses.
:::

---

## Worked Example 4: Classic vs Serverless Comparison

**Scenario:** The same Jobs workload configured both ways — 4 `i3.xlarge` workers, 10 runs/day at 30 minutes each, on AWS us-east-1 Premium, Photon enabled.

### Common: Monthly hours

```
Hours/Month = (10 × 30 ÷ 60) × 22 = 110 hours
```

### Classic Calculation

```
DBU/Hour     = (1.0 + 1.0 × 4) × 2.0 = 10.0 DBU/hr
Monthly DBUs = 10.0 × 110 = 1,100 DBUs
DBU Cost     = 1,100 × $0.15 = $165.00
VM Cost      = ($0.312 + $0.312 × 4) × 110 = $171.60
Monthly Cost = $165.00 + $171.60 = $336.60
```

### Serverless Calculation

Jobs Serverless always applies Photon (2x) and a Serverless multiplier (1x Standard, 2x Performance). Using Standard:

```
DBU/Hour     = (1.0 + 1.0 × 4) × 2.0 × 1.0 = 10.0 DBU/hr
Monthly DBUs = 10.0 × 110 = 1,100 DBUs
DBU Cost     = 1,100 × $0.15 = $165.00
VM Cost      = $0 (Serverless)
Monthly Cost = $165.00
```

### Side-by-Side

| | Classic | Serverless (Standard) |
|--|---------|----------------------|
| DBU/Hour | 10.0 | 10.0 |
| Monthly DBUs | 1,100 | 1,100 |
| DBU Cost | $165.00 | $165.00 |
| VM Cost | $171.60 | $0.00 |
| **Monthly Total** | **$336.60** | **$165.00** |
| **Annual Total** | **$4,039.20** | **$1,980.00** |
| **Savings** | — | **51% less** |

:::note
This comparison uses the same instance types for both modes. In practice, Serverless may use different compute under the hood, but Lakemeter models it based on the equivalent instance configuration you select.
:::

---

## Formula Reference by Workload Type

### Jobs & All-Purpose (Classic)

```
DBU/Hour = (Driver DBU + Worker DBU × Workers) × Photon Multiplier
```

| Parameter | Value |
|-----------|-------|
| Photon Multiplier | 2.0 if Photon enabled, 1.0 otherwise |
| Driver/Worker DBU | From instance type lookup (e.g., `i3.xlarge` = 1.0) |
| Fallback DBU | 0.5 for unknown instance types |

**SKUs:** `JOBS_COMPUTE`, `JOBS_COMPUTE_(PHOTON)`, `ALL_PURPOSE_COMPUTE`, `ALL_PURPOSE_COMPUTE_(PHOTON)`

### Jobs & All-Purpose (Serverless)

```
DBU/Hour = (Driver DBU + Worker DBU × Workers) × Photon × Serverless Multiplier
```

| Parameter | Jobs | All-Purpose |
|-----------|------|-------------|
| Photon | Always 2x (built-in) | Always 2x |
| Serverless Standard | 1x | N/A |
| Serverless Performance | 2x | Always 2x |

**SKUs:** `JOBS_SERVERLESS_COMPUTE`, `ALL_PURPOSE_SERVERLESS_COMPUTE`

No VM costs for serverless workloads.

### Delta Live Tables (DLT)

DLT Classic uses the same formula as Jobs Classic. DLT Serverless uses Jobs Serverless pricing.

| Edition | Classic SKU | Photon SKU | Serverless SKU |
|---------|------------|------------|----------------|
| Core | `DLT_CORE_COMPUTE` | `DLT_CORE_COMPUTE_(PHOTON)` | `JOBS_SERVERLESS_COMPUTE` |
| Pro | `DLT_PRO_COMPUTE` | `DLT_PRO_COMPUTE_(PHOTON)` | `JOBS_SERVERLESS_COMPUTE` |
| Advanced | `DLT_ADVANCED_COMPUTE` | `DLT_ADVANCED_COMPUTE_(PHOTON)` | `JOBS_SERVERLESS_COMPUTE` |

All DLT Serverless editions use the same `JOBS_SERVERLESS_COMPUTE` SKU.

### Databricks SQL (DBSQL)

```
DBU/Hour = Size DBU Map[Warehouse Size] × Number of Clusters
```

| Type | SKU |
|------|-----|
| Classic | `SQL_COMPUTE` |
| Pro | `SQL_PRO_COMPUTE` |
| Serverless | `SERVERLESS_SQL_COMPUTE` |

Classic and Pro include VM costs. Serverless does not.

### Model Serving

```
DBU/Hour = GPU DBU Rate (from lookup by GPU type)
```

Each GPU type maps to a fixed DBU/hour rate. All Model Serving uses the `SERVERLESS_REAL_TIME_INFERENCE` SKU. No VM costs.

### Vector Search

```
Units = CEILING(Capacity in Millions ÷ Divisor)
DBU/Hour = Units × Mode DBU Rate
```

| Mode | Divisor | DBU Rate per Unit |
|------|---------|-------------------|
| Standard | 2,000,000 vectors | 4.0 DBU/hr |
| Storage Optimized | 64,000,000 vectors | 18.29 DBU/hr |

**SKU:** `SERVERLESS_REAL_TIME_INFERENCE`

May produce a second storage row in exports when storage GB > 0.

### FMAPI — Databricks Models

| Pricing Type | Formula |
|-------------|---------|
| Token-based (input/output) | Monthly DBUs = Quantity (Millions) × DBU per 1M Tokens |
| Provisioned (entry/scaling) | Monthly DBUs = Hours × DBU per Hour |

**SKU:** `SERVERLESS_REAL_TIME_INFERENCE`

### FMAPI — Proprietary Models

Same token-based formula as Databricks FMAPI. Rate types include `input`, `output`, `cache_read`, and `cache_write`.

| Provider | SKU |
|----------|-----|
| Anthropic | `ANTHROPIC_MODEL_SERVING` |
| OpenAI | `OPENAI_MODEL_SERVING` |
| Google | `GEMINI_MODEL_SERVING` |

### Lakebase

**Compute:**
```
DBU/Hour = CU Size × Number of Nodes
```
- CU Size: 0.5 to 112 compute units
- Nodes: 1 (primary only) or 2–3 (primary + read replicas)
- **SKU:** `DATABASE_SERVERLESS_COMPUTE`

**Storage:**
```
Storage Cost/Month = Storage GB × 15 DSU × $0.023/DSU
```
- Maximum storage: 8,192 GB
- **SKU:** `DATABRICKS_STORAGE`

Lakebase storage is a direct dollar cost (not DBU-based) and appears on a separate row in Excel exports.

---

## Excel Export Column Layout

The Excel export uses a 30-column layout. See the [Exporting guide](./exporting) for full details on sections and formatting.
