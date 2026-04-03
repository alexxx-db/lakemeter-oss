---
sidebar_position: 4
---

# Quick Reference

A concise reference for all 9 workload types in Lakemeter. Use this page to quickly identify which workload type to use and what configuration options are available.

## Workload types at a glance

| Workload | What it is | When to use it | Min. Tier |
|----------|-----------|----------------|-----------|
| **Jobs** | Batch compute for ETL, ML training, data processing | Scheduled or triggered pipelines that run and terminate | Standard |
| **All-Purpose** | Interactive compute for notebooks and development | Ad-hoc analysis, prototyping, development clusters | Standard |
| **DLT** | Delta Live Tables declarative data pipelines | Managed ETL with built-in data quality and monitoring | Standard |
| **DBSQL** | SQL analytics warehouses | BI dashboards, SQL queries, analyst workloads | Standard (Classic/Pro), Premium (Serverless) |
| **Model Serving** | Real-time ML model inference endpoints | Deploying custom ML models for online predictions | Premium |
| **Vector Search** | Managed vector database | Similarity search, RAG applications, embeddings | Premium |
| **FMAPI (Databricks)** | Foundation Model API for open-source models | Llama, DBRX, Mixtral via Databricks-hosted endpoints | Premium |
| **FMAPI (Proprietary)** | Foundation Model API for third-party models | GPT-4, Claude, Gemini via Databricks gateway | Premium |
| **Lakebase** | Managed PostgreSQL-compatible database | Transactional workloads, application backends | Premium |

## Key terms

| Term | Meaning |
|------|---------|
| **DBU** | Databricks Unit -- the billing unit for Databricks services. Different workload types have different $/DBU rates. |
| **SKU** | Stock Keeping Unit -- identifies the specific product being priced (e.g., `JOBS_COMPUTE`, `SERVERLESS_SQL_COMPUTE`). |
| **Photon** | Hardware-accelerated query engine. Doubles the DBU rate but often halves runtime for compatible workloads. |
| **Serverless** | Databricks-managed infrastructure. No VM configuration needed; infrastructure cost is included in the DBU price. |
| **Classic** | Customer-managed infrastructure. You choose instance types and pay DBU + VM costs separately. |

## Configuration by workload type

### Compute workloads (Jobs, All-Purpose, DLT)

These workloads share a common configuration pattern:

| Field | Description | Default |
|-------|-------------|---------|
| **Serverless** | Toggle on for Databricks-managed compute, off for classic | Off |
| **Serverless Mode** | Standard or Performance (Performance uses 2x DBU rate) | Standard |
| **Photon** | Hardware-accelerated engine (classic mode only) | Off |
| **Driver Node Type** | VM instance for the driver (classic only) | -- |
| **Worker Node Type** | VM instance for workers (classic only) | -- |
| **Number of Workers** | Worker node count (classic only) | 1 |
| **Driver Pricing** | On-demand, 1-year reserved, 3-year reserved | On-demand |
| **Worker Pricing** | Spot, On-demand, 1-year reserved, 3-year reserved | On-demand |
| **Payment Option** | No upfront, partial upfront, all upfront (reserved only) | No upfront |

**DLT-specific:**

| Field | Description | Options |
|-------|-------------|---------|
| **DLT Edition** | Feature tier for the pipeline | Core, Pro, Advanced |

**Usage fields (Jobs):**

| Field | Description | Default |
|-------|-------------|---------|
| **Runs Per Day** | Number of job executions daily | -- |
| **Avg Runtime (minutes)** | Average duration of each run | -- |
| **Days Per Month** | Active days per month | 30 |

**Usage fields (All-Purpose, DLT):**

| Field | Description | Default |
|-------|-------------|---------|
| **Hours Per Month** | Total compute hours | -- |

### DBSQL

| Field | Description | Options |
|-------|-------------|---------|
| **Warehouse Type** | Classic, Pro, or Serverless | Classic, Pro, Serverless |
| **Warehouse Size** | Determines DBU/hr consumption | 2X-Small (4 DBU/hr) through 4X-Large |
| **Number of Clusters** | Concurrent cluster count for scaling | 1+ |
| **Hours Per Month** | Warehouse uptime | -- |

**DBSQL warehouse sizes and DBU rates:**

| Size | DBU/hr |
|------|--------|
| 2X-Small | 4 |
| X-Small | 8 |
| Small | 12 |
| Medium | 24 |
| Large | 40 |
| X-Large | 64 |
| 2X-Large | 128 |
| 3X-Large | 256 |
| 4X-Large | 512 |

### Model Serving

| Field | Description | Options |
|-------|-------------|---------|
| **GPU Type** | Compute tier for the endpoint | CPU, GPU Small (T4), GPU Medium (A10G 1x), GPU Large (A10G 4x), etc. |
| **Hours Per Month** | Endpoint uptime | Default: 730 (24/7) |

### Vector Search

| Field | Description | Options |
|-------|-------------|---------|
| **Mode** | Standard or Storage Optimized | Standard, Storage Optimized |
| **Vector Capacity (millions)** | Number of vectors the index can hold | -- |
| **Storage (GB)** | Storage capacity | -- |
| **Hours Per Month** | Service uptime | Default: 730 (24/7) |

### FMAPI (Databricks models)

| Field | Description |
|-------|-------------|
| **Model** | Databricks-hosted model (e.g., Llama, DBRX, Mixtral) |
| **Rate Type** | Input tokens, output tokens, provisioned scaling, provisioned entry |
| **Quantity (millions)** | Volume of tokens or provisioned units |

### FMAPI (Proprietary models)

| Field | Description |
|-------|-------------|
| **Provider** | OpenAI, Anthropic, or Google |
| **Model** | Specific model (GPT-4, Claude, Gemini, etc.) |
| **Endpoint Type** | Global or In-Geo |
| **Context Length** | All, Short, or Long (affects pricing for some models) |
| **Rate Type** | Input tokens, output tokens, cache read, cache write |
| **Quantity (millions)** | Token volume |

### Lakebase

| Field | Description | Default |
|-------|-------------|---------|
| **CU Size** | Compute units (0.5, 1-32 autoscaling, 36-112 fixed) | -- |
| **Number of Nodes** | 1 = primary only, 2-3 = primary + read replicas | 1 |
| **Storage (GB)** | Database storage capacity (0-8192 GB) | -- |
| **Hours Per Month** | Instance uptime | Default: 730 (24/7) |

## Cost formula summary

| Workload type | Cost formula |
|--------------|-------------|
| **Classic compute** (Jobs, All-Purpose, DLT) | (DBU/hr x hours/month x $/DBU) + (VM $/hr x hours/month) |
| **Serverless compute** (Jobs, All-Purpose, DLT, DBSQL) | DBU/hr x hours/month x $/DBU (VM cost included) |
| **DBSQL Classic/Pro** | (Warehouse DBU/hr x clusters x hours/month x $/DBU) + VM costs |
| **Model Serving** | GPU DBU/hr x hours/month x $/DBU |
| **Vector Search** | Endpoint units x DBU/unit x hours/month x $/DBU |
| **FMAPI** | Token quantity (M) x DBU per M tokens x $/DBU |
| **Lakebase** | (CU x nodes x hours/month x $/DBU) + storage costs |
