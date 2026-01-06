"""
AI Agent Service for Lakemeter

Orchestrates conversations with Claude to help users create and analyze estimates.
Implements tool calling for estimate management operations.

The agent operates within the Estimate Detail page context, helping users:
1. Propose workload configurations based on requirements
2. Analyze existing estimates using calculated costs from context
3. Provide optimization recommendations and best practices

NOTE: This agent does NOT perform cost calculations - it uses costs provided by
the Lakemeter pricing engine after configurations are saved.
"""
import json
import uuid
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime

from app.services.ai_client import ClaudeAIClient, get_claude_client
from app.config import log_info, log_warning, log_error


# Base system prompt for the AI assistant
SYSTEM_PROMPT_BASE = """You are Lakemeter AI, an expert Databricks pricing assistant.

## Important: You Do NOT Calculate Costs
- You propose workload configurations based on user requirements
- Actual cost calculations are done by the Lakemeter pricing engine after configurations are saved
- When discussing costs, refer to the actual calculated costs provided in the context
- Do not make up or estimate cost numbers yourself

## Workload Types You Can Configure
- **JOBS (Lakeflow Jobs)**: Batch processing, ETL pipelines, scheduled tasks
- **ALL_PURPOSE**: Interactive development, notebooks, exploration
- **DLT (Lakeflow Spark Declarative Pipelines)**: Streaming pipelines, data quality
- **DBSQL (Databricks SQL)**: SQL analytics, BI dashboards, ad-hoc queries
- **MODEL_SERVING**: Real-time ML inference endpoints
- **VECTOR_SEARCH**: Vector similarity search for AI applications
- **FMAPI_DATABRICKS**: Foundation Model APIs (Databricks-hosted models like Llama, DBRX)
- **FMAPI_PROPRIETARY**: Foundation Model APIs (External models like GPT, Claude)
- **LAKEBASE**: PostgreSQL-compatible database

## Key Questions to Ask Users

### For ALL Workloads:
1. What is the primary use case? (ETL, analytics, ML, real-time, etc.)
2. What cloud provider? (AWS, Azure, GCP)
3. What region? (for compliance/latency requirements)

### For Compute Workloads (Jobs, All Purpose, DLT):
1. Is this a scheduled batch job or interactive/continuous?
2. For batch: How many runs per day? Average runtime per run?
3. For continuous: How many hours per month will it run?
4. How much data will be processed? (helps size the cluster)
5. Do you need fault tolerance? (determines spot vs on-demand)
6. Do you want serverless (simpler, pay-per-use) or classic (more control)?

### For DBSQL:
1. How many TOTAL users will access this warehouse?
2. How many of those users are PEAK CONCURRENT (querying at the same time)?
   - For reference: BI dashboards ~10-20% concurrent, Active analytics ~20-30%, Real-time monitoring ~40-60%
   - Example: 100 total users with BI dashboards = ~10-20 concurrent queries at peak
3. What's the typical compressed data size in the Delta table being queried? (1GB, 10GB, 100GB, 1TB, 10TB+)
4. What do users typically filter by? (helps assess query selectivity)
   - High selectivity: specific IDs, single day, individual records
   - Moderate selectivity: week/month ranges, departments, regions (~1-5%)
   - Low selectivity: quarters, large categories, broad date ranges (>5%)
5. What's the expected query frequency during peak? (rough queries per minute)
6. Is this for BI dashboards (periodic refresh) or ad-hoc queries (on-demand)?
7. Query complexity?
   - **Simple**: Single table with basic filters and aggregations (COUNT, SUM, AVG) - 2x faster than benchmark
   - **Medium**: 2-3 table joins with WHERE clauses and GROUP BY - baseline benchmark (TPC-DS medium)
   - **Complex**: 4+ table joins, subqueries, window functions, nested aggregations - 3x slower than benchmark
8. Warehouse type?
   - **Serverless**: Instant startup (<5s), Predictive I/O - best for variable/sporadic workloads
   - **Pro**: 3-4min startup, Predictive I/O, Unity Catalog - best for constant workloads
   - **Classic**: 3-4min startup, Unity Catalog, NO Predictive I/O - legacy, not recommended for new deployments
   (All types: auto-scaling, scale to zero, pay-per-use)

### For Model Serving:
1. What type of model? (LLM, custom ML, embeddings)
2. Expected queries per second?
3. Latency requirements?
4. GPU requirements?

### For FMAPI (Foundation Models):
1. Which model? (Llama, DBRX, GPT, Claude, etc.)
2. Expected token volume? (input + output tokens per month)
3. Rate type: pay-per-token or provisioned throughput?

### For Lakebase:
1. How many compute units (CU)? (1-128, based on workload)
2. Do you need HA? (adds 1 replica node for high availability)
3. Expected hours per month?

## Best Practices to Recommend
- **For Batch ETL**: Use Lakeflow Jobs with Photon enabled, spot instances for workers (up to 90% savings)
- **For Interactive**: All Purpose for development, DBSQL Serverless for production queries
- **For Streaming**: DLT with auto-scaling, consider Core vs Pro vs Advanced editions
- **For ML Inference**: Model Serving with appropriate GPU types
- **For Cost Savings**: Spot instances, Serverless (pay-per-use), Reserved capacity (1yr/3yr for predictable workloads)
- **For AWS Reserved**: Consider payment options (no_upfront, partial_upfront, all_upfront) for additional savings

## Common GenAI Use Cases & Recommended Workloads

### RAG Chatbot / Knowledge Assistant
A typical RAG (Retrieval-Augmented Generation) chatbot requires MULTIPLE workloads:
1. **Data Preparation (JOBS)**: Process and chunk documents for embeddings
   - Lakeflow Jobs, Photon enabled, spot workers for cost savings
   - Run frequency: daily or when new documents added
2. **Vector Search (VECTOR_SEARCH)**: Store and query document embeddings
   - Estimate based on number of vectors and query volume
3. **Foundation Model (FMAPI_PROPRIETARY or FMAPI_DATABRICKS)**: Generate responses
   - Input tokens: ~2000-4000 per query (context + question)
   - Output tokens: ~300-500 per response
   - Calculate monthly tokens based on expected conversations

### Document Processing / Summarization
1. **Data Ingestion (JOBS)**: Load and process documents
2. **Foundation Model (FMAPI)**: Summarize or extract information
   - Higher input tokens (full document), lower output tokens

### Customer Support Bot
1. **Vector Search**: FAQ and knowledge base retrieval
2. **Foundation Model**: Response generation
3. **Optional Model Serving**: Custom intent classification model

### Code Assistant
1. **Foundation Model**: Code generation/completion
   - Models: Claude Sonnet, GPT-4, or CodeLlama
   - Moderate input (code context), moderate output (completions)

When user mentions: "chatbot", "RAG", "knowledge base", "document Q&A", "assistant" - 
PROACTIVELY suggest the full architecture with multiple workloads!

## Notes Field Guidelines
When proposing workloads, ALWAYS include detailed notes explaining:
1. **Why this configuration**: Explain the reasoning for each choice
2. **Sizing rationale**: Why you chose this size/scale
3. **Cost considerations**: Any cost optimization choices made
4. **Assumptions**: What assumptions you made about usage
5. **Trade-offs**: Any trade-offs to be aware of

Format notes as multiple lines for readability:
"Configuration rationale:
- Chose X because Y
- Sized for Z concurrent users
- Using spot instances for 60-90% savings
- Assumption: 8 hours/day usage"

## Common Instance Types by Cloud
- **AWS**: m5.xlarge, i3.xlarge, r5.xlarge (memory), c5.xlarge (compute), p3.2xlarge (GPU)
- **Azure**: Standard_D4s_v3, Standard_E4s_v3 (memory), Standard_F4s_v2 (compute), Standard_NC6s_v3 (GPU)
- **GCP**: n1-standard-4, n1-highmem-4 (memory), n1-highcpu-4 (compute), n1-standard-4-nvidia-tesla-t4 (GPU)

**NOTE**: For Azure, use Standard_D series (D4s_v3, D8s_v3) - these are widely available across regions.

## Reference Data for Dropdown Options

### DBSQL Warehouse Sizes (DBU/hour, QPM for Pro/Serverless)
Performance based on TPC-DS 10GB benchmark (Pro/Serverless with Predictive I/O):
- 2X-Small: 4 DBU/hr, ~77 QPM - 1GB: <1s, 10GB: 5s, 100GB: 50s, 1TB: 8m, 10TB: 1h
- X-Small: 6 DBU/hr, ~131 QPM - 1GB: <1s, 10GB: 3s, 100GB: 29s, 1TB: 5m, 10TB: 49m
- Small: 12 DBU/hr, ~224 QPM - 1GB: <1s, 10GB: 2s, 100GB: 17s, 1TB: 3m, 10TB: 29m
- Medium: 24 DBU/hr, ~380 QPM - 1GB: <1s, 10GB: 1s, 100GB: 10s, 1TB: 2m, 10TB: 17m
- Large: 40 DBU/hr, ~646 QPM - 1GB: <1s, 10GB: <1s, 100GB: 6s, 1TB: 59s, 10TB: 10m
- X-Large: 80 DBU/hr, ~1,098 QPM - 1GB: <1s, 10GB: <1s, 100GB: 3s, 1TB: 35s, 10TB: 6m
- 2X-Large: 144 DBU/hr, ~1,867 QPM - 1GB: <1s, 10GB: <1s, 100GB: 2s, 1TB: 21s, 10TB: 3m
- 3X-Large: 272 DBU/hr, ~3,174 QPM - 1GB: <1s, 10GB: <1s, 100GB: 1s, 1TB: 12s, 10TB: 2m
- 4X-Large: 528 DBU/hr, ~5,395 QPM - 1GB: <1s, 10GB: <1s, 100GB: <1s, 1TB: 7s, 10TB: 1m

Note: QPM (queries per minute) based on TPC-DS **MEDIUM COMPLEXITY** queries on 10GB data.
Each cluster handles max 10 concurrent queries (not users - see concurrency conversion below).
Photon is always enabled for DBSQL warehouses.

### Query Complexity & Performance Impact
**CRITICAL**: Benchmark QPM assumes MEDIUM complexity queries. Adjust based on actual query patterns:

- **Simple Queries (2x faster, 2x more QPM)**:
  - Single table queries
  - Basic filters: WHERE col = value, WHERE col IN (...)
  - Basic aggregations: COUNT(*), SUM(col), AVG(col), MAX/MIN
  - Simple GROUP BY on 1-2 columns
  - Example: SELECT region, SUM(sales) FROM orders WHERE date = '2024-01-01' GROUP BY region

- **Medium Queries (Baseline, 1x performance)**:
  - 2-3 table joins (INNER JOIN, LEFT JOIN)
  - WHERE clauses with multiple conditions (AND/OR)
  - GROUP BY with HAVING clauses
  - Multiple aggregations in same query
  - TPC-DS benchmark queries (medium complexity)
  - Example: SELECT o.region, COUNT(DISTINCT c.customer_id), SUM(o.amount)
            FROM orders o JOIN customers c ON o.customer_id = c.id
            WHERE o.date >= '2024-01-01' GROUP BY o.region HAVING SUM(o.amount) > 1000

- **Complex Queries (3x slower, 1/3 QPM - need 3x more clusters)**:
  - 4+ table joins or self-joins
  - Subqueries or CTEs (WITH clauses)
  - Window functions: ROW_NUMBER(), RANK(), LAG/LEAD, PARTITION BY
  - Nested aggregations or aggregations of aggregations
  - UNION/UNION ALL/INTERSECT/EXCEPT operations
  - Recursive CTEs
  - Example: WITH ranked_sales AS (
              SELECT *, ROW_NUMBER() OVER (PARTITION BY region ORDER BY amount DESC) as rank
              FROM (SELECT region, customer_id, SUM(amount) as amount FROM orders GROUP BY region, customer_id)
            ) SELECT * FROM ranked_sales WHERE rank <= 10

**Sizing Impact Examples**:
- 1000 QPM needed with **Simple** queries (Large WH, 100GB):
  → Large WH (646 QPM base) × (10/100) = 64.6 QPM × 2 (simple) = **129 QPM/cluster**
  → 1000 ÷ 129 = **8 clusters needed**

- 1000 QPM needed with **Medium** queries (Large WH, 100GB):
  → Large WH (646 QPM base) × (10/100) = 64.6 QPM × 1 (medium) = **64.6 QPM/cluster**
  → 1000 ÷ 64.6 = **16 clusters needed**

- 1000 QPM needed with **Complex** queries (Large WH, 100GB):
  → Large WH (646 QPM base) × (10/100) = 64.6 QPM × 0.33 (complex) = **21.3 QPM/cluster**
  → 1000 ÷ 21.3 = **47 clusters needed**

### Query Selectivity & Predictive I/O Impact
Classic vs Pro/Serverless Performance:
- Datasets ≤10GB: Classic and Pro/Serverless have similar performance
- Datasets >10GB: Pro/Serverless can be 3-17x faster due to Predictive I/O (depends on selectivity)

Query Selectivity Categories (% of table returned as results):
- **High Selectivity (<1% of data)**: Up to 17x faster with Predictive I/O
  Examples: Filter to 1 specific user ID (1/10,000 users = 0.01%), 1 day in 3-year history (0.09%)
- **Moderate Selectivity (1-5% of data)**: 5-10x faster with Predictive I/O
  Examples: 1 week in a year (7/365 = 1.9%), 1 department out of 20 (5%), VIP customers (top 5%), 1 month in 2-year history (4.2%), 1 region out of 20 (5%)
- **Low Selectivity (>5% of data)**: Minimal benefit (1-3x)
  Examples: 1 quarter (25%), entire product category (20%), all US customers (40%)

### DLT Editions
- CORE: Basic pipelines, no CDC
- PRO: CDC, SCD Type 2, better monitoring
- ADVANCED: Expectations, enhanced monitoring, data quality

### Pricing Tiers
- on_demand: Pay as you go, most flexible
- spot: Up to 90% savings, for fault-tolerant batch jobs (workers only)
- 1yr_reserved: ~30% savings, 1-year commitment
- 3yr_reserved: ~40% savings, 3-year commitment

### AWS Reserved Payment Options (only for reserved tiers)
- no_upfront: No upfront payment, slightly higher hourly rate
- partial_upfront: ~50% upfront, balanced savings
- all_upfront: 100% upfront, maximum savings

### Serverless Modes
- standard: Cost-effective, good for most workloads
- performance: Faster provisioning, higher throughput, premium pricing

### Model Serving Types
- cpu: For small models, embeddings
- gpu_small: For medium models (7B-13B params)
- gpu_medium: For large models (30B-70B params)
- gpu_large: For very large models (70B+ params)

## Important Notes
- All costs shown are from the Lakemeter pricing engine
- Actual costs may vary based on usage patterns and negotiated discounts
- Always recommend reviewing configurations before finalizing
- Ask clarifying questions before proposing configurations - don't assume!
- ALWAYS use the estimate's cloud provider when suggesting instance types"""

SYSTEM_PROMPT = SYSTEM_PROMPT_BASE + """

## Your Role (Estimate Detail Page)
You are viewing a specific estimate with its workloads and calculated costs.

## CRITICAL: Check Estimate Configuration First
Before proposing ANY workload, verify the estimate has these REQUIRED fields set:
- **Cloud Provider**: Must be AWS, Azure, or GCP
- **Region**: Must have a valid region selected
- **Databricks Tier**: Should be set (usually Premium)

If any of these are missing, TELL THE USER to fill them in before adding workloads.
Example: "I see your estimate doesn't have a region selected yet. Please select a region in the estimate configuration before we add workloads, so I can suggest the right instance types."

## Your Capabilities Here
1. **Check Configuration**: Verify estimate has required fields before proposing workloads
2. **Ask Clarifying Questions**: ALWAYS ask questions first to understand requirements
3. **Propose Workloads**: Suggest workload configurations after gathering requirements
4. **Analyze Estimate**: Review current workloads and suggest optimizations using ACTUAL costs
5. **Provide Recommendations**: Share best practices and cost-saving tips
6. **Answer Questions**: Explain configurations, costs, and trade-offs

## CRITICAL: Ask Before You Propose
NEVER propose a workload without first asking clarifying questions.

**IMPORTANT**: When you say "let me ask questions", you MUST include the actual questions in the SAME response!
Don't just say you'll ask questions - actually list them with numbers so users can respond.

## Question Guidelines by Workload Type:

### For ETL/Pipeline Workloads:
1. What's the data volume? (GB/TB per run)
2. What's the latency requirement? (real-time, hourly, daily)
3. How long does processing typically take?
4. Is fault tolerance acceptable? (for spot instance decision)

### For Dashboarding/DBSQL:
1. How many total dashboard users?
2. What % are viewing dashboards simultaneously at peak? (typical BI: 10-20%)
   - This determines concurrent queries (not same as concurrent users)
   - Example: 100 users × 15% = 15 concurrent queries = 2 clusters needed
3. What's the typical compressed data size in the Delta table being queried?
4. Are dashboard filters selective? (e.g., filtering by date range, department, user ID)
5. Dashboard refresh frequency? (manual refresh, every minute, real-time)
6. Query complexity? (simple aggregations vs multi-table joins)
7. Usage pattern? (business hours 8-5, or 24/7 monitoring)

### For Interactive/All-Purpose:
1. How many data scientists/analysts using it?
2. What size datasets are they working with?
3. How many hours per day is it used?

### For GenAI/Chatbots:
1. What model preference? (Claude, GPT, Llama, etc.)
2. How many users and questions per day?
3. What's the knowledge base size? (number of documents)
4. How often is content updated? (for data prep sizing)

## Using Context
- The estimate details (name, cloud, region, tier) are provided in the context
- Use the ESTIMATE'S CLOUD PROVIDER to suggest appropriate instance types
- The workloads with their ACTUAL calculated costs are provided in the context
- Use these real costs when discussing the estimate, not made-up numbers
- When proposing new workloads, clearly state the configuration and that costs will be calculated after saving

## Conversation Flow for COMPLEX Requests (Multiple Workloads)
When user requests multiple workloads at once (like "I need ETL, dashboards, and a chatbot"):

1. **Acknowledge & Outline**: Briefly list what you'll help them configure
2. **Ask ALL Questions Together**: Group questions by workload type so user can answer once
3. **Wait for Answers**: Don't propose until you have the answers
4. **Propose Each Workload**: After getting answers, propose workloads one by one

**EXAMPLE of Good Response for Multi-Workload Request:**
```
I can help you set up all of these! To configure them optimally, I need a few details:

**For your ETL pipelines:**
1. What's the data volume per batch? (GB/TB)
2. How long do your batch jobs typically run?

**For dashboarding (20 users):**
3. Are all 20 users active at the same time, or spread throughout the day?
4. Simple dashboard queries or complex aggregations?

**For GenAI chatbot (10 users):**
5. What model do you prefer? (Claude, GPT, Llama)
6. How many documents in your knowledge base?

Once you answer these, I'll propose each workload with the right configuration!
```

## Configuration Tips
- For JOBS/DLT: Ask about runs_per_day + avg_runtime_minutes for batch, OR hours_per_month for continuous
- For DBSQL: Ask about total users, concurrency %, data volume, and query selectivity to size warehouse
- For serverless: No VM types needed, but ask about workload intensity for cost estimates
- For reserved pricing: Only recommend for predictable, long-running workloads
- For spot workers: Only for fault-tolerant batch jobs that can handle interruptions
- ALWAYS use instance types appropriate for the estimate's cloud provider!

## DBSQL Sizing Guidelines

### Concurrent Users to Queries Per Minute Calculation
Step 1: Calculate concurrent users from total users
- **BI Dashboards**: 10-20% concurrent (use 15% default)
- **Active Analytics**: 20-30% concurrent (use 25% default)
- **Real-time Monitoring**: 40-60% concurrent (use 50% default)

Step 2: Calculate queries per minute from concurrent users
- **BI Dashboard users**: Submit ~1 query/minute (mostly viewing, occasional interactions)
- **Analytics users**: Submit ~2 queries/minute (active exploration, filter changes)
- **Monitoring dashboards**: Usually automated refreshes (treat as queries/minute directly)

Example Calculations:
- **100 BI users**: 100 × 15% = 15 concurrent users × 1 query/min = 15 queries/min needed
- **100 Analytics users**: 100 × 25% = 25 concurrent users × 2 queries/min = 50 queries/min needed
- **2000 Analytics users**: 2000 × 25% = 500 concurrent users × 2 queries/min = 1000 queries/min needed

### Number of Clusters Calculation
IMPORTANT: This is based on QUERIES PER MINUTE throughput, not concurrent connections.

Step 1: Calculate queries per minute needed (from Step 2 above)
Step 2: Adjust warehouse QPM based on data volume
- QPM scales linearly with data volume: Larger data = proportionally lower QPM
- Formula: Adjusted QPM = Base QPM × (10GB / actual_data_volume_GB)
- Examples:
  - Large WH (646 QPM at 10GB): 100GB data → 646 × (10/100) = 64.6 QPM per cluster
  - Medium WH (380 QPM at 10GB): 1TB data → 380 × (10/1000) = 3.8 QPM per cluster

Step 3: Calculate clusters needed
- Formula: clusters = CEILING(queries_per_minute_needed / adjusted_QPM_per_cluster) - ALWAYS round UP
- Example: 1000 queries/min needed, Large WH with 100GB data:
  - Adjusted QPM = 646 × (10/100) = 64.6 QPM
  - Clusters = 1000 / 64.6 = 15.48 → **16 clusters** (rounded UP)
- Another example: 120 QPM needed, 64.6 QPM/cluster:
  - Clusters = 120 / 64.6 = 1.86 → **2 clusters** (rounded UP, NOT 1!)

### Warehouse Size Selection Process
Step 1: Assess Data Volume
- ≤10GB: Classic, Pro, Serverless perform similarly
- >10GB with selective queries: Pro/Serverless 3-17x faster (Predictive I/O benefit)

Step 2: Query Selectivity (for >10GB datasets)
- **High selectivity (<1% results)**: 10-17x faster with Pro/Serverless
  - "Show me user ID 12345's orders" (1 user out of 100K users)
  - "Show me yesterday's transactions" (1 day out of 3 years)
  - Speedup example: 1TB scan → Classic: 3min, Pro: 10-20s
- **Moderate selectivity (1-5% results)**: 5-10x faster with Pro/Serverless
  - "Show me last week's data" (1 week out of 1 year = ~2%)
  - "Show me Northeast region sales" (1 region out of 20 = 5%)
  - "Show me VIP tier customers" (top 5% of customer base)
  - Speedup example: 1TB scan → Classic: 3min, Pro: 20-40s
- **Low selectivity (>5% results)**: 1-3x faster
  - "Show me this quarter's data" (3 months out of 1 year = 25%)
  - "Show me all US customers" (40% of global base)

Step 3: Size by QPM & Query Time Requirements
- **Interactive dashboards**: Target <3s query time
  - 10GB data → Small (2s) or larger
  - 100GB data → Medium (10s) or larger
  - 1TB data → Large (59s) or larger
- **Analytical workloads**: 1-5min query times acceptable
  - 1TB data → Medium (2m) is sufficient
- **Heavy analytics**: Use QPM as guide
  - 200 queries/min → Small (224 QPM)
  - 400 queries/min → Medium (380 QPM)
  - 650 queries/min → Large (646 QPM)

### Warehouse Type Selection
- **SERVERLESS**: Instant startup (<5 seconds), scales to zero when idle, best for sporadic/variable workloads, includes Predictive I/O. Auto-scaling and pay-per-use.
- **PRO**: Slower startup (3-4 minutes), better for constant workloads where startup time matters, Unity Catalog support, includes Predictive I/O. Auto-scaling and pay-per-use.
- **CLASSIC**: Legacy (not recommended for new deployments), slower startup (3-4 minutes), Unity Catalog support, NO Predictive I/O. Auto-scaling, can scale to zero, and pay-per-use.
Note: All three types support Unity Catalog, auto-scaling, scale to zero, and pay-per-use. Main differences are startup time and Predictive I/O support (only Pro/Serverless have it).

**When in doubt:** If user mentions filtering by date ranges, user IDs, specific categories, or "drill-down" queries, assume moderate selectivity (5%) and recommend Pro/Serverless for datasets >10GB."""


# Tool definitions for the AI Assistant
TOOLS = [
    {
        "name": "propose_workload",
        "description": """Propose a new workload configuration for user confirmation. 
ASK CLARIFYING QUESTIONS FIRST before calling this tool to ensure you have the right configuration.
The user will review and confirm before it's added to the estimate.""",
        "parameters": {
            "type": "object",
            "properties": {
                # === Common Fields ===
                "workload_type": {
                    "type": "string",
                    "enum": ["JOBS", "ALL_PURPOSE", "DLT", "DBSQL", "MODEL_SERVING", "VECTOR_SEARCH", "FMAPI_DATABRICKS", "FMAPI_PROPRIETARY", "LAKEBASE"],
                    "description": "Type of Databricks workload"
                },
                "workload_name": {
                    "type": "string",
                    "description": "Descriptive name for this workload (e.g., 'Daily ETL Job', 'Analytics Warehouse')"
                },
                
                # === Compute Configuration (Jobs, All Purpose, DLT) ===
                "serverless_enabled": {
                    "type": "boolean",
                    "description": "Use serverless compute (simpler, pay-per-use, auto-scaling). Recommended for variable workloads."
                },
                "serverless_mode": {
                    "type": "string",
                    "enum": ["standard", "performance"],
                    "description": "For serverless: 'standard' (cost-effective) or 'performance' (faster, higher cost)"
                },
                "photon_enabled": {
                    "type": "boolean",
                    "description": "Enable Photon acceleration (recommended for SQL/Spark workloads, ~2x faster)"
                },
                "driver_node_type": {
                    "type": "string",
                    "description": "Instance type for driver node (e.g., 'i3.xlarge', 'm5.large', 'Standard_DS3_v2')"
                },
                "worker_node_type": {
                    "type": "string",
                    "description": "Instance type for worker nodes"
                },
                "num_workers": {
                    "type": "integer",
                    "description": "Number of worker nodes (typically 2-100 based on data volume)"
                },
                
                # === Usage Patterns ===
                "hours_per_month": {
                    "type": "number",
                    "description": "Direct hours of usage per month. Use for continuous workloads (730 = 24/7, 176 = 8h/day weekdays)"
                },
                "runs_per_day": {
                    "type": "integer",
                    "description": "For batch jobs: number of scheduled runs per day"
                },
                "avg_runtime_minutes": {
                    "type": "integer",
                    "description": "For batch jobs: average runtime in minutes per run"
                },
                "days_per_month": {
                    "type": "integer",
                    "description": "Days per month the workload runs (22 = weekdays only, 30 = daily)"
                },
                
                # === Pricing Tiers ===
                "driver_pricing_tier": {
                    "type": "string",
                    "enum": ["on_demand", "1yr_reserved", "3yr_reserved"],
                    "description": "Pricing tier for driver. Use reserved for predictable workloads (up to 40% savings)"
                },
                "worker_pricing_tier": {
                    "type": "string",
                    "enum": ["on_demand", "spot", "1yr_reserved", "3yr_reserved"],
                    "description": "Pricing tier for workers. Use 'spot' for fault-tolerant batch jobs (up to 90% savings)"
                },
                "driver_payment_option": {
                    "type": "string",
                    "enum": ["no_upfront", "partial_upfront", "all_upfront"],
                    "description": "AWS only: Payment option for reserved driver (all_upfront = most savings)"
                },
                "worker_payment_option": {
                    "type": "string",
                    "enum": ["no_upfront", "partial_upfront", "all_upfront"],
                    "description": "AWS only: Payment option for reserved workers"
                },
                
                # === DLT Specific ===
                "dlt_edition": {
                    "type": "string",
                    "enum": ["CORE", "PRO", "ADVANCED"],
                    "description": "DLT edition: CORE (basic), PRO (CDC, SCD), ADVANCED (expectations, monitoring)"
                },
                
                # === DBSQL Specific ===
                "dbsql_warehouse_type": {
                    "type": "string",
                    "enum": ["SERVERLESS", "PRO", "CLASSIC"],
                    "description": "DBSQL warehouse type: SERVERLESS (instant startup <5s, Predictive I/O), PRO (3-4min startup, Unity Catalog, Predictive I/O), CLASSIC (3-4min startup, Unity Catalog, NO Predictive I/O). All auto-scale and pay-per-use."
                },
                "dbsql_warehouse_size": {
                    "type": "string",
                    "enum": ["2X-Small", "X-Small", "Small", "Medium", "Large", "X-Large", "2X-Large", "3X-Large", "4X-Large"],
                    "description": "DBSQL warehouse size (2X-Small=4 DBU/hr, Small=12, Medium=24, Large=40, X-Large=80)"
                },
                "dbsql_num_clusters": {
                    "type": "integer",
                    "description": "Number of DBSQL clusters for scaling (1-100). 1 cluster = 10 concurrent queries."
                },
                "total_users": {
                    "type": "integer",
                    "description": "Total number of users who will access this warehouse"
                },
                "concurrent_queries": {
                    "type": "integer",
                    "description": "Peak concurrent queries (NOT users). If unknown, provide total_users and use_case_type instead."
                },
                "use_case_type": {
                    "type": "string",
                    "enum": ["bi_dashboard", "analytics", "monitoring"],
                    "description": "Type of use case - affects concurrency ratio: BI dashboards ~15%, Analytics ~25%, Monitoring ~50%"
                },
                "query_selectivity": {
                    "type": "string",
                    "enum": ["high", "moderate", "low", "unknown"],
                    "description": "Query selectivity (% of table data returned): high=<1% (specific IDs, single day), moderate=1-5% (week in year, one region), low=>5% (quarter, large categories). Affects Predictive I/O: high=10-17x, moderate=5-10x, low=1-3x faster vs Classic"
                },
                "query_complexity": {
                    "type": "string",
                    "enum": ["simple", "medium", "complex"],
                    "description": "Query complexity: simple (single table, basic filters/aggregations, 2x faster), medium (2-3 table joins, baseline benchmark), complex (4+ joins, subqueries, window functions, 3x slower)"
                },
                "typical_data_volume": {
                    "type": "string",
                    "enum": ["<1GB", "1-10GB", "10-100GB", "100GB-1TB", ">1TB"],
                    "description": "Typical compressed data size in Delta table being queried (affects query performance and QPM)"
                },
                
                # === Model Serving Specific ===
                "model_serving_type": {
                    "type": "string",
                    "enum": ["cpu", "gpu_small", "gpu_medium", "gpu_large"],
                    "description": "Model Serving compute type based on model requirements"
                },
                "model_serving_scale_to_zero": {
                    "type": "boolean",
                    "description": "Allow scaling to zero when idle (saves cost but adds cold start latency)"
                },
                
                # === Vector Search Specific ===
                "vector_search_index_type": {
                    "type": "string",
                    "enum": ["DIRECT_ACCESS", "DELTA_SYNC"],
                    "description": "Vector Search index type"
                },
                
                # === Foundation Model API Specific ===
                "fmapi_provider": {
                    "type": "string",
                    "enum": ["anthropic", "openai", "google", "meta", "databricks"],
                    "description": "FMAPI provider (for proprietary: anthropic/openai/google, for databricks: meta/databricks)"
                },
                "fmapi_model": {
                    "type": "string",
                    "description": "Model name (e.g., 'claude-sonnet-4', 'gpt-4', 'llama-3-3-70b', 'dbrx-instruct')"
                },
                "fmapi_endpoint_type": {
                    "type": "string",
                    "enum": ["global", "regional"],
                    "description": "Endpoint type: global (multi-region) or regional (single region)"
                },
                "fmapi_context_length": {
                    "type": "string",
                    "enum": ["all", "8k", "16k", "32k", "128k", "200k"],
                    "description": "Context length tier for the model"
                },
                "fmapi_rate_type": {
                    "type": "string",
                    "enum": ["input_token", "output_token", "cache_read", "cache_write"],
                    "description": "Token type for billing. Create separate workloads for input and output tokens."
                },
                "fmapi_quantity": {
                    "type": "number",
                    "description": "Token quantity in millions per month (e.g., 2.5 = 2.5M tokens/month)"
                },
                
                # === Lakebase Specific ===
                "lakebase_cu": {
                    "type": "integer",
                    "description": "Lakebase Compute Units (1-128). More CUs = more concurrent connections and faster queries"
                },
                "lakebase_ha_enabled": {
                    "type": "boolean",
                    "description": "Enable High Availability (adds 1 replica node for failover)"
                },
                
                # === Notes (DETAILED) ===
                "reason": {
                    "type": "string",
                    "description": "Brief one-line summary of why this configuration was chosen"
                },
                "notes": {
                    "type": "string",
                    "description": """OPTIONAL: You can leave this empty - comprehensive notes will be auto-generated.
If you want to add custom notes, they will be REPLACED by auto-generated detailed notes covering:
- Configuration rationale, sizing assumptions, cost considerations, usage assumptions, and trade-offs.
Recommendation: Leave empty and let the system generate comprehensive notes automatically."""
                }
            },
            "required": ["workload_type", "workload_name", "reason"]
        }
    },
    {
        "name": "ask_clarifying_questions",
        "description": "Use this tool to ask the user clarifying questions before proposing a workload. This ensures you have the right information for an accurate configuration.",
        "parameters": {
            "type": "object",
            "properties": {
                "questions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of questions to ask the user"
                },
                "context": {
                    "type": "string",
                    "description": "Brief context for why you need this information"
                }
            },
            "required": ["questions"]
        }
    },
    {
        "name": "get_estimate_summary",
        "description": "Get a summary of the current estimate including all workloads and their actual calculated costs from the context.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "analyze_estimate",
        "description": "Analyze the current estimate using actual costs and provide optimization recommendations. Use this when the user asks for cost-saving tips or improvements.",
        "parameters": {
            "type": "object",
            "properties": {
                "focus_area": {
                    "type": "string",
                    "enum": ["cost_optimization", "performance", "reliability", "all"],
                    "description": "Area to focus analysis on"
                }
            },
            "required": []
        }
    },
    {
        "name": "propose_genai_architecture",
        "description": """Propose a complete GenAI architecture with MULTIPLE workloads for common use cases.
Use this when user mentions: chatbot, RAG, knowledge base, document Q&A, assistant, AI agent, summarization.
This will propose all necessary workloads (data prep, vector search, foundation models) together.""",
        "parameters": {
            "type": "object",
            "properties": {
                "use_case": {
                    "type": "string",
                    "enum": ["rag_chatbot", "document_processing", "customer_support", "code_assistant", "custom"],
                    "description": "The GenAI use case pattern"
                },
                "use_case_name": {
                    "type": "string",
                    "description": "Descriptive name for this GenAI application (e.g., 'Customer Support Chatbot', 'Document Q&A System')"
                },
                "model_preference": {
                    "type": "string",
                    "enum": ["claude", "gpt", "llama", "dbrx", "no_preference"],
                    "description": "User's preferred foundation model family"
                },
                "expected_conversations_per_day": {
                    "type": "integer",
                    "description": "Expected number of conversations/queries per day"
                },
                "avg_context_tokens": {
                    "type": "integer",
                    "description": "Average context size in tokens (retrieved docs + question). Default 2000-4000 for RAG."
                },
                "avg_response_tokens": {
                    "type": "integer",
                    "description": "Average response size in tokens. Default 300-500."
                },
                "document_count": {
                    "type": "integer",
                    "description": "Approximate number of documents in knowledge base (for vector search sizing)"
                },
                "data_prep_frequency": {
                    "type": "string",
                    "enum": ["hourly", "daily", "weekly", "one_time"],
                    "description": "How often new documents are ingested"
                },
                "explanation": {
                    "type": "string",
                    "description": "Detailed explanation of why this architecture is recommended and how the components work together"
                }
            },
            "required": ["use_case", "use_case_name", "explanation"]
        }
    }
]


class EstimateAgent:
    """
    AI Agent that helps users create and manage Databricks pricing estimates.
    
    Operates within the Estimate Detail page context:
    - Proposes workload configurations based on user requirements
    - Analyzes estimates using actual calculated costs from context
    - Provides optimization recommendations and best practices
    
    Does NOT perform cost calculations - uses costs from the pricing engine.
    """
    
    def __init__(self, claude_client: ClaudeAIClient):
        self.client = claude_client
        self.conversation_history: List[Dict[str, Any]] = []
        self.current_estimate: Optional[Dict[str, Any]] = None
        self.current_workloads: List[Dict[str, Any]] = []  # Actual workloads with costs
        self.proposed_workloads: List[Dict[str, Any]] = []  # Pending workload confirmations
        self.proposed_estimate: Optional[Dict[str, Any]] = None  # Pending estimate confirmation
        self._conversation_summary: str = ""  # Summary of old conversation for context
    
    def reset(self):
        """Reset the agent state for a new conversation."""
        self.conversation_history = []
        self.current_estimate = None
        self.current_workloads = []
        self.proposed_workloads = []
        self.proposed_estimate = None
        self._conversation_summary = ""
    
    def _trim_conversation_history(self, max_messages: int = 20):
        """
        Trim conversation history to prevent it from growing too long.
        Properly handles tool_use/tool_result pairs to avoid API errors.
        
        Strategy:
        1. Find pairs of messages (assistant with tool_use + user with tool_result)
        2. Keep complete pairs, remove orphaned messages
        3. Keep at most max_messages but never break a pair
        """
        if len(self.conversation_history) <= max_messages:
            return
        
        # Find indices of messages that must stay together (tool_use and its tool_result)
        # A tool_use in assistant message must be followed by tool_result in next user message
        tool_use_indices = set()
        
        for i, msg in enumerate(self.conversation_history):
            # Check if this is an assistant message with tool_calls
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                tool_use_indices.add(i)
                # The next message should be the tool_result
                if i + 1 < len(self.conversation_history):
                    next_msg = self.conversation_history[i + 1]
                    if next_msg.get("role") == "user" and isinstance(next_msg.get("content"), list):
                        # This is a tool_result message - mark it as paired
                        tool_use_indices.add(i + 1)
        
        # Start from the end and find a safe cut point
        # We want at most max_messages, but we can't cut in the middle of a tool pair
        start_idx = len(self.conversation_history) - max_messages
        
        # Ensure we don't start in the middle of a tool pair
        # If start_idx lands on a tool_result (i.e., start_idx-1 is a tool_use), move forward
        while start_idx > 0 and start_idx < len(self.conversation_history):
            if start_idx in tool_use_indices:
                # Check if this is a tool_result that needs its tool_use before it
                prev_idx = start_idx - 1
                if prev_idx in tool_use_indices:
                    # We're cutting between tool_use and tool_result - bad!
                    # Move start forward to skip this broken pair
                    start_idx += 1
                    continue
            
            # Also check if start_idx-1 is a tool_use without its result being included
            if start_idx - 1 in tool_use_indices and start_idx not in tool_use_indices:
                # The message before is a tool_use but we're not including its result
                # Move forward to skip the orphaned tool_use
                start_idx += 1
                continue
            
            break
        
        # Apply the trim
        if start_idx > 0:
            self.conversation_history = self.conversation_history[start_idx:]
            log_info(f"Trimmed conversation history to {len(self.conversation_history)} messages (from {start_idx})")
    
    async def _summarize_conversation(self, messages_to_summarize: List[Dict[str, Any]]) -> str:
        """
        Summarize old conversation messages to preserve context while reducing tokens.
        
        Args:
            messages_to_summarize: List of messages to summarize
            
        Returns:
            A concise summary of the conversation
        """
        if not messages_to_summarize:
            return ""
        
        # Build a simple text representation of messages to summarize
        conversation_text = []
        for msg in messages_to_summarize:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            
            # Skip tool result messages (they're technical)
            if isinstance(content, list):
                continue
                
            if role == "user":
                conversation_text.append(f"User: {content}")
            elif role == "assistant":
                # Truncate long assistant responses
                if len(content) > 500:
                    content = content[:500] + "..."
                conversation_text.append(f"Assistant: {content}")
        
        if not conversation_text:
            return ""
        
        # Use Claude to summarize
        summary_prompt = f"""Summarize this conversation in 2-3 sentences, focusing on:
1. What the user asked for
2. What workloads were discussed or proposed
3. Any key decisions made

Conversation:
{chr(10).join(conversation_text)}

Summary (be concise):"""
        
        try:
            response = await self.client.chat(
                messages=[{"role": "user", "content": summary_prompt}],
                tools=[],
                system="You are a helpful assistant that summarizes conversations concisely.",
                max_tokens=200,
                temperature=0.3
            )
            return response.get("content", "").strip()
        except Exception as e:
            log_warning(f"Failed to summarize conversation: {e}")
            return ""
    
    async def _manage_conversation_history(self, max_recent: int = 10, summarize_threshold: int = 15):
        """
        Manage conversation history by summarizing old messages.
        
        Strategy:
        - If history > summarize_threshold messages, summarize older messages
        - Keep the last max_recent messages intact for context
        - Add summary as a system context note
        
        Args:
            max_recent: Number of recent messages to keep intact
            summarize_threshold: Trigger summarization when history exceeds this
        """
        if len(self.conversation_history) <= summarize_threshold:
            return
        
        # Separate messages to summarize vs keep
        messages_to_summarize = self.conversation_history[:-max_recent]
        messages_to_keep = self.conversation_history[-max_recent:]
        
        # Ensure we don't break tool_use/tool_result pairs in messages_to_keep
        # If the first message to keep is a tool_result, include its tool_use
        while messages_to_keep:
            first_msg = messages_to_keep[0]
            if (first_msg.get("role") == "user" and 
                isinstance(first_msg.get("content"), list)):
                # This is a tool_result - need the previous message (tool_use)
                if messages_to_summarize:
                    messages_to_keep.insert(0, messages_to_summarize.pop())
                else:
                    # No more messages to pull from - remove orphaned tool_result
                    messages_to_keep.pop(0)
            else:
                break
        
        # Summarize old messages
        summary = await self._summarize_conversation(messages_to_summarize)
        
        if summary:
            # Add summary as context for the agent (will be included in system prompt)
            self._conversation_summary = summary
            log_info(f"Summarized {len(messages_to_summarize)} messages, keeping {len(messages_to_keep)} recent")
        
        # Update history with just the recent messages
        self.conversation_history = messages_to_keep
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt, including any conversation summary."""
        prompt = SYSTEM_PROMPT
        
        # Add conversation summary if available
        if hasattr(self, '_conversation_summary') and self._conversation_summary:
            prompt += f"\n\n## Previous Conversation Summary\n{self._conversation_summary}"
        
        return prompt
    
    def _get_tools(self) -> List[Dict[str, Any]]:
        """Get the available tools."""
        return TOOLS
    
    def set_context(self, estimate: Dict[str, Any], workloads: List[Dict[str, Any]] = None):
        """
        Set the current estimate and workloads context.
        
        Args:
            estimate: Estimate details (name, cloud, region, etc.)
            workloads: List of workloads with their calculated costs
                       Each should include: workload_name, workload_type, 
                       total_cost, dbu_cost, vm_cost, configuration fields
        """
        self.current_estimate = estimate
        self.current_workloads = workloads or []
        
        # Filter out any proposals that have already been added to the estimate
        # (matching by workload_name to avoid duplicates showing in AI panel)
        if self.current_workloads and self.proposed_workloads:
            existing_names = {w.get('workload_name') for w in self.current_workloads}
            self.proposed_workloads = [
                p for p in self.proposed_workloads 
                if p.get('workload_name') not in existing_names
            ]
    
    async def chat(self, user_message: str) -> Dict[str, Any]:
        """
        Process a user message and return the assistant's response.
        
        Returns dict with:
        - content: Text response
        - tool_results: Any tool execution results
        - proposed_workload: Workload awaiting confirmation (if any)
        - estimate: Current estimate state
        """
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Build context for the system prompt
        context_info = self._build_context()
        system = self._get_system_prompt() + context_info
        tools = self._get_tools()
        
        # Get response from Claude
        response = await self.client.chat(
            messages=self.conversation_history,
            tools=tools,
            system=system,
            max_tokens=4096,
            temperature=0.7
        )
        
        # Process tool calls if any
        tool_results = []
        proposed_workload = None
        
        if response.get("tool_calls"):
            for tool_call in response["tool_calls"]:
                result = await self._execute_tool(
                    tool_call["name"],
                    tool_call["arguments"]
                )
                tool_results.append({
                    "tool": tool_call["name"],
                    "input": tool_call["arguments"],
                    "output": result
                })
                
                # Check if this is a workload proposal
                if tool_call["name"] == "propose_workload" and result.get("success"):
                    proposed_workload = result.get("proposed_workload")
            
            # Add assistant message with tool use to history
            self.conversation_history.append({
                "role": "assistant",
                "content": response.get("content", ""),
                "tool_calls": response["tool_calls"]
            })
            
            # Add tool results to history
            for i, tool_call in enumerate(response["tool_calls"]):
                self.conversation_history.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_call["id"],
                            "content": json.dumps(tool_results[i]["output"])
                        }
                    ]
                })
            
            # Get follow-up response after tool execution
            follow_up = await self.client.chat(
                messages=self.conversation_history,
                tools=tools,
                system=system,
                max_tokens=4096,
                temperature=0.7
            )
            
            final_content = follow_up.get("content", "")
            self.conversation_history.append({
                "role": "assistant",
                "content": final_content
            })
        else:
            # No tool calls, just text response
            final_content = response.get("content", "")
            self.conversation_history.append({
                "role": "assistant",
                "content": final_content
            })
            tool_results = None
        
        return {
            "content": final_content,
            "tool_results": tool_results,
            "proposed_workload": proposed_workload,
            "estimate": self.current_estimate,
            "workloads": self.current_workloads
        }
    
    async def chat_stream(self, user_message: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process a user message and stream the response.
        
        Yields chunks with type 'content', 'tool_start', 'tool_result', 'proposal', or 'done'.
        """
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Build context
        context_info = self._build_context()
        system = self._get_system_prompt() + context_info
        tools = self._get_tools()
        
        # Stream response
        full_content = ""
        tool_calls = []
        executed_tool_ids = set()  # Track tools that have already been executed
        current_tool = None
        tool_input_json = ""
        
        # Manage conversation history - summarize if too long, then trim if still needed
        await self._manage_conversation_history()
        self._trim_conversation_history()  # Fallback safety trim
        
        async for chunk in self.client.chat_stream(
            messages=self.conversation_history,
            tools=tools,
            system=system,
            max_tokens=4096,
            temperature=0.7
        ):
            chunk_type = chunk.get("type")
            
            if chunk_type == "content_delta":
                content = chunk.get("content", "")
                full_content += content
                yield {"type": "content", "content": content}
            
            elif chunk_type == "tool_use_start":
                current_tool = {
                    "id": chunk.get("id"),
                    "name": chunk.get("name"),
                    "arguments": {}
                }
                tool_input_json = ""
                yield {"type": "tool_start", "tool": chunk.get("name")}
            
            elif chunk_type == "tool_input_delta":
                tool_input_json += chunk.get("partial_json", "")
            
            elif chunk_type == "tool_call_complete":
                # Handle complete tool call from OpenAI format
                tool_id = chunk.get("id")
                current_tool = {
                    "id": tool_id,
                    "name": chunk.get("name"),
                    "arguments": chunk.get("arguments", {})
                }
                tool_calls.append(current_tool)
                
                # Execute tool and mark as executed
                result = await self._execute_tool(
                    current_tool["name"],
                    current_tool["arguments"]
                )
                executed_tool_ids.add(tool_id)
                
                # Store result with tool for later history update
                current_tool["_result"] = result
                
                yield {
                    "type": "tool_result",
                    "tool": current_tool["name"],
                    "result": result
                }
                
                # If it's a workload proposal, yield that separately
                if current_tool["name"] == "propose_workload" and result.get("success"):
                    yield {
                        "type": "proposal",
                        "workload": result.get("proposed_workload")
                    }
                
                # If it's a GenAI architecture proposal, yield each workload separately
                if current_tool["name"] == "propose_genai_architecture" and result.get("success"):
                    for w in result.get("workloads", []):
                        # Find the full workload from proposed_workloads
                        for proposed in self.proposed_workloads:
                            if proposed.get("proposal_id") == w.get("proposal_id"):
                                yield {
                                    "type": "proposal",
                                    "workload": proposed
                                }
                                break
                
                # If it's an estimate proposal, yield that separately
                if current_tool["name"] in ["propose_estimate", "create_estimate"] and result.get("success"):
                    yield {
                        "type": "estimate_proposal",
                        "estimate": result.get("proposed_estimate")
                    }
                
                current_tool = None
            
            elif chunk_type == "message_delta":
                if current_tool and tool_input_json:
                    try:
                        current_tool["arguments"] = json.loads(tool_input_json)
                    except json.JSONDecodeError:
                        current_tool["arguments"] = {}
                    tool_calls.append(current_tool)
                    current_tool = None
                    tool_input_json = ""
            
            elif chunk_type == "done":
                break
        
        # Process any tool calls that were accumulated
        if tool_calls:
            # Add assistant response to history (clean tool_calls without _result)
            clean_tool_calls = [{k: v for k, v in tc.items() if k != "_result"} for tc in tool_calls]
            self.conversation_history.append({
                "role": "assistant",
                "content": full_content,
                "tool_calls": clean_tool_calls
            })
            
            # Execute tools and add results to history
            for tool_call in tool_calls:
                tool_id = tool_call.get("id")
                
                # Check if already executed during streaming (has cached result)
                if tool_id in executed_tool_ids and "_result" in tool_call:
                    # Use cached result, just add to history
                    result = tool_call["_result"]
                    self.conversation_history.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_call["id"],
                                "content": json.dumps(result)
                            }
                        ]
                    })
                    continue
                
                # Execute tool (for Claude format streaming that doesn't hit tool_call_complete)
                result = await self._execute_tool(
                    tool_call["name"],
                    tool_call["arguments"]
                )
                
                yield {
                    "type": "tool_result",
                    "tool": tool_call["name"],
                    "result": result
                }
                
                # If it's a workload proposal, yield that separately
                if tool_call["name"] == "propose_workload" and result.get("success"):
                    yield {
                        "type": "proposal",
                        "workload": result.get("proposed_workload")
                    }
                
                # If it's a GenAI architecture proposal, yield each workload separately
                if tool_call["name"] == "propose_genai_architecture" and result.get("success"):
                    for w in result.get("workloads", []):
                        # Find the full workload from proposed_workloads
                        for proposed in self.proposed_workloads:
                            if proposed.get("proposal_id") == w.get("proposal_id"):
                                yield {
                                    "type": "proposal",
                                    "workload": proposed
                                }
                                break
                
                # If it's an estimate proposal, yield that separately
                if tool_call["name"] in ["propose_estimate", "create_estimate"] and result.get("success"):
                    yield {
                        "type": "estimate_proposal",
                        "estimate": result.get("proposed_estimate")
                    }
                
                self.conversation_history.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_call["id"],
                            "content": json.dumps(result)
                        }
                    ]
                })
            
            # Get follow-up response
            yield {"type": "content", "content": "\n\n"}
            
            follow_up_content = ""
            try:
                async for chunk in self.client.chat_stream(
                    messages=self.conversation_history,
                    tools=tools,
                    system=system,
                    max_tokens=4096,
                    temperature=0.7
                ):
                    chunk_type = chunk.get("type")
                    if chunk_type == "content_delta":
                        content = chunk.get("content", "")
                        follow_up_content += content
                        full_content += content
                        yield {"type": "content", "content": content}
                    elif chunk_type == "error":
                        log_error(f"Follow-up stream error: {chunk.get('content')}")
                        yield {"type": "content", "content": f"\n\n*Error getting response: {chunk.get('content')}*"}
                        break
                    elif chunk_type == "done":
                        break
                
                # If no follow-up content, provide a context-appropriate message
                if not follow_up_content.strip():
                    # Only mention proposed workloads if there actually are some
                    if self.proposed_workloads:
                        default_msg = "\n\nI've proposed the workloads above. Please review each one and click ✓ to confirm or ✗ to reject."
                    elif self.proposed_estimate:
                        default_msg = "\n\nI've proposed an estimate above. Please review and confirm or reject it."
                    else:
                        # Generic message when no proposals
                        default_msg = ""  # Don't add unnecessary text
                    
                    if default_msg:
                        yield {"type": "content", "content": default_msg}
                        full_content += default_msg
            except Exception as e:
                log_error(f"Follow-up response error: {e}")
                error_msg = f"\n\n*Error: {str(e)}*"
                yield {"type": "content", "content": error_msg}
                full_content += error_msg
        
        # Add final response to history
        self.conversation_history.append({
            "role": "assistant",
            "content": full_content
        })
        
        yield {
            "type": "done",
            "estimate": self.current_estimate,
            "workloads": self.current_workloads,
            "proposed_workloads": self.proposed_workloads,
            "proposed_estimate": self.proposed_estimate
        }
    
    def _build_context(self) -> str:
        """Build context string with current estimate state and actual costs."""
        context = "\n\n## Current Session Context"
        
        if self.current_estimate:
            est = self.current_estimate
            
            # Check required fields
            cloud = est.get('cloud')
            region = est.get('region')
            tier = est.get('tier')
            
            missing_fields = []
            if not cloud:
                missing_fields.append("Cloud Provider")
            if not region:
                missing_fields.append("Region")
            if not tier:
                missing_fields.append("Databricks Tier")
            
            context += f"""

### Estimate Details
- **Name**: {est.get('estimate_name') or est.get('name', 'Unnamed')}
- **Cloud**: {cloud.upper() if cloud else '⚠️ NOT SET - Required before adding workloads'}
- **Region**: {region if region else '⚠️ NOT SET - Required before adding workloads'}
- **Tier**: {tier if tier else '⚠️ NOT SET - Required before adding workloads'}
- **Status**: {est.get('status', 'draft')}"""
            
            if missing_fields:
                context += f"""

### ⚠️ MISSING REQUIRED FIELDS
The following fields MUST be set before workloads can be added:
{chr(10).join(f'- {field}' for field in missing_fields)}

**Tell the user to fill in these fields in the estimate configuration first!**"""
            
            if est.get('customer_name'):
                context += f"\n- **Customer**: {est.get('customer_name')}"
            if est.get('description'):
                context += f"\n- **Description**: {est.get('description')}"
            if est.get('sfdc_account_id'):
                context += f"\n- **Salesforce Account**: Linked"
        else:
            context += "\n\nNo estimate loaded. User may be creating a new one."
        
        if self.current_workloads:
            context += f"\n\n### Workloads ({len(self.current_workloads)} total)"
            
            total_cost = 0
            for w in self.current_workloads:
                # Get cost - could be in different formats depending on source
                cost = w.get('total_cost') or w.get('monthly_cost') or 0
                if isinstance(cost, dict):
                    cost = cost.get('total', 0)
                total_cost += float(cost) if cost else 0
                
                context += f"\n\n**{w.get('workload_name', 'Unnamed')}** ({w.get('workload_type', 'Unknown')})"
                context += f"\n- Monthly Cost: ${float(cost):.2f}" if cost else "\n- Monthly Cost: Calculating..."
                
                # Add relevant configuration details
                if w.get('serverless_enabled'):
                    context += "\n- Mode: Serverless"
                if w.get('photon_enabled'):
                    context += "\n- Photon: Enabled"
                if w.get('num_workers'):
                    context += f"\n- Workers: {w.get('num_workers')}"
                if w.get('driver_node_type'):
                    context += f"\n- Driver: {w.get('driver_node_type')}"
                if w.get('worker_node_type'):
                    context += f"\n- Worker Type: {w.get('worker_node_type')}"
                if w.get('worker_pricing_tier'):
                    context += f"\n- Worker Pricing: {w.get('worker_pricing_tier')}"
                if w.get('hours_per_month'):
                    context += f"\n- Hours/Month: {w.get('hours_per_month')}"
                if w.get('dbsql_warehouse_size'):
                    context += f"\n- Warehouse Size: {w.get('dbsql_warehouse_size')}"
                if w.get('dlt_edition'):
                    context += f"\n- DLT Edition: {w.get('dlt_edition')}"
            
            context += f"\n\n### Total Monthly Cost: ${total_cost:.2f}"
        else:
            context += "\n\n### Workloads: None yet"
        
        if self.proposed_workloads:
            context += f"\n\n### Pending Proposals ({len(self.proposed_workloads)})"
            for p in self.proposed_workloads:
                context += f"\n- {p.get('workload_name')} ({p.get('workload_type')}) - awaiting confirmation"
        
        return context
    
    async def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool and return the result."""
        log_info(f"Executing tool: {tool_name} with args: {arguments}")
        
        if tool_name == "create_estimate":
            # Legacy support - treat as proposal
            return self._propose_estimate(**arguments)
        elif tool_name == "propose_estimate":
            return self._propose_estimate(**arguments)
        elif tool_name == "propose_workload":
            return self._propose_workload(**arguments)
        elif tool_name == "add_workload":
            # Legacy support - treat as proposal
            return self._propose_workload(**arguments)
        elif tool_name == "get_estimate_summary":
            return self._get_estimate_summary()
        elif tool_name == "analyze_estimate":
            return self._analyze_estimate(**arguments)
        elif tool_name == "ask_clarifying_questions":
            return self._ask_clarifying_questions(**arguments)
        elif tool_name == "propose_genai_architecture":
            return self._propose_genai_architecture(**arguments)
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    
    def _propose_estimate(
        self,
        name: str,
        cloud: str,
        region: str,
        description: str = "",
        reason: str = ""
    ) -> Dict[str, Any]:
        """
        Propose an estimate configuration for user confirmation.
        Does NOT create the estimate - user must confirm first.
        """
        self.proposed_estimate = {
            "proposal_id": str(uuid.uuid4()),
            "name": name,
            "estimate_name": name,  # Support both formats
            "cloud": cloud.lower(),
            "region": region,
            "description": description,
            "reason": reason,
            "status": "pending_confirmation",
            "created_at": datetime.now().isoformat()
        }
        
        return {
            "success": True,
            "message": f"Proposed estimate '{name}' for {cloud.upper()} {region}",
            "proposed_estimate": self.proposed_estimate,
            "action_required": "User must confirm this estimate before it's created.",
            "note": "Once confirmed, you can click on the estimate to add workloads."
        }
    
    def confirm_estimate(self) -> Optional[Dict[str, Any]]:
        """
        Confirm the proposed estimate (called from API after user confirms).
        Returns the estimate configuration to be saved.
        """
        if self.proposed_estimate:
            estimate = self.proposed_estimate
            estimate["status"] = "confirmed"
            self.proposed_estimate = None
            return estimate
        return None
    
    def reject_estimate(self) -> bool:
        """Reject the proposed estimate."""
        if self.proposed_estimate:
            self.proposed_estimate = None
            return True
        return False
    
    def _ask_clarifying_questions(
        self,
        questions: List[str],
        context: str = ""
    ) -> Dict[str, Any]:
        """
        Format clarifying questions to ask the user.
        This is a "soft" tool - it just formats questions for the AI to present naturally.
        """
        formatted_questions = "\n".join([f"• {q}" for q in questions])
        
        return {
            "success": True,
            "action": "ask_questions",
            "questions": questions,
            "context": context,
            "message": f"I need a bit more information to create the right configuration:\n\n{formatted_questions}",
            "note": "Please answer these questions so I can propose an accurate workload configuration."
        }
    
    def _propose_genai_architecture(
        self,
        use_case: str,
        use_case_name: str,
        explanation: str,
        model_preference: str = "no_preference",
        expected_conversations_per_day: int = 100,
        avg_context_tokens: int = 3000,
        avg_response_tokens: int = 400,
        document_count: int = 1000,
        data_prep_frequency: str = "daily"
    ) -> Dict[str, Any]:
        """
        Propose a complete GenAI architecture with multiple workloads.
        Creates workload proposals for data prep, vector search, and foundation models.
        """
        # Check required estimate fields first
        if self.current_estimate:
            cloud = self.current_estimate.get('cloud')
            region = self.current_estimate.get('region')
            tier = self.current_estimate.get('tier')
            
            missing = []
            if not cloud:
                missing.append("Cloud Provider")
            if not region:
                missing.append("Region")
            if not tier:
                missing.append("Databricks Tier")
            
            if missing:
                return {
                    "success": False,
                    "error": "missing_required_fields",
                    "missing_fields": missing,
                    "message": f"Cannot propose architecture. Please fill in: {', '.join(missing)}"
                }
        else:
            return {
                "success": False,
                "error": "no_estimate",
                "message": "No estimate loaded."
            }
        
        cloud = self.current_estimate.get('cloud', 'aws').lower()
        workloads = []
        
        # Get existing proposal names to avoid duplicates
        existing_proposal_names = {p.get('workload_name') for p in self.proposed_workloads}
        existing_workload_names = {w.get('workload_name') for w in self.current_workloads} if self.current_workloads else set()
        all_existing_names = existing_proposal_names | existing_workload_names
        
        def add_workload_if_new(workload_config):
            """Only add workload if name doesn't already exist"""
            if workload_config['workload_name'] not in all_existing_names:
                workloads.append(workload_config)
                self.proposed_workloads.append(workload_config)
                return True
            return False
        
        # Calculate monthly token volumes
        days_per_month = 22  # Business days
        monthly_conversations = expected_conversations_per_day * days_per_month
        monthly_input_tokens = (monthly_conversations * avg_context_tokens) / 1_000_000  # In millions
        monthly_output_tokens = (monthly_conversations * avg_response_tokens) / 1_000_000  # In millions
        
        # Determine model based on preference
        if model_preference == "claude":
            provider = "anthropic"
            model = "claude-sonnet-4"
        elif model_preference == "gpt":
            provider = "openai"
            model = "gpt-4"
        elif model_preference == "llama":
            provider = "meta"
            model = "llama-3-3-70b"
        elif model_preference == "dbrx":
            provider = "databricks"
            model = "dbrx-instruct"
        else:
            provider = "anthropic"
            model = "claude-sonnet-4"
        
        # 1. Data Preparation Job (for RAG-like use cases)
        if use_case in ["rag_chatbot", "document_processing", "customer_support"]:
            # Determine job frequency
            if data_prep_frequency == "hourly":
                runs_per_day = 24
                runtime_mins = 15
            elif data_prep_frequency == "daily":
                runs_per_day = 1
                runtime_mins = 30
            elif data_prep_frequency == "weekly":
                runs_per_day = 1
                runtime_mins = 60
                days_per_month = 4
            else:  # one_time
                runs_per_day = 1
                runtime_mins = 60
                days_per_month = 1
            
            data_prep = {
                "proposal_id": str(uuid.uuid4()),
                "workload_type": "JOBS",
                "workload_name": f"{use_case_name} - Data Preparation",
                "cloud": cloud,
                "serverless_enabled": True,
                "serverless_mode": "standard",
                "photon_enabled": True,
                "runs_per_day": runs_per_day,
                "avg_runtime_minutes": runtime_mins,
                "days_per_month": days_per_month if data_prep_frequency != "weekly" else 4,
                "reason": "Document processing and chunking for embeddings",
                "notes": f"""Configuration Rationale:
• Purpose: Process and chunk documents for vector embeddings
• Serverless: Chosen for cost efficiency - only pay when running
• Photon enabled: 2-3x faster document processing
• Frequency: {data_prep_frequency} based on your content update needs
• Runtime: {runtime_mins} min estimated for ~{document_count} documents

Assumptions:
• Average document size: ~10KB
• Chunk size: ~500 tokens for optimal retrieval
• Using Delta Lake for document storage""",
                "status": "pending_confirmation"
            }
            add_workload_if_new(data_prep)
        
        # 2. Vector Search (for retrieval)
        if use_case in ["rag_chatbot", "customer_support", "document_processing"]:
            # Estimate vector dimensions and storage
            estimated_chunks = document_count * 5  # ~5 chunks per doc
            
            vector_search = {
                "proposal_id": str(uuid.uuid4()),
                "workload_type": "VECTOR_SEARCH",
                "workload_name": f"{use_case_name} - Vector Search",
                "cloud": cloud,
                "vector_search_index_type": "DELTA_SYNC",
                "hours_per_month": 730,  # 24/7 for production
                "reason": "Semantic search over document embeddings",
                "notes": f"""Configuration Rationale:
• Purpose: Store and query document embeddings for RAG retrieval
• Index Type: DELTA_SYNC for automatic updates when docs change
• 24/7 availability for production chatbot
• Estimated vectors: ~{estimated_chunks:,} (based on {document_count} docs)

Sizing:
• Vector dimensions: 1536 (OpenAI) or 768 (other models)
• Query latency: <100ms for top-k retrieval
• Automatically scales with query volume""",
                "status": "pending_confirmation"
            }
            add_workload_if_new(vector_search)
        
        # 3. Foundation Model - Input Tokens
        fm_input = {
            "proposal_id": str(uuid.uuid4()),
            "workload_type": "FMAPI_PROPRIETARY" if provider in ["anthropic", "openai", "google"] else "FMAPI_DATABRICKS",
            "workload_name": f"{use_case_name} - {model} (Input Tokens)",
            "cloud": cloud,
            "fmapi_provider": provider,
            "fmapi_model": model,
            "fmapi_endpoint_type": "global",
            "fmapi_context_length": "all",
            "fmapi_rate_type": "input_token",
            "fmapi_quantity": round(monthly_input_tokens, 2),
            "hours_per_month": 730,
            "reason": "Input tokens for context + questions",
            "notes": f"""Configuration Rationale:
• Model: {model} ({provider}) - good balance of quality and cost
• Input tokens: {monthly_input_tokens:.2f}M/month
• Calculation: {expected_conversations_per_day} conversations/day × {days_per_month} days × {avg_context_tokens} tokens/conversation

Token Breakdown:
• Retrieved context: ~{avg_context_tokens - 500} tokens
• User question: ~500 tokens
• System prompt: included in context

Tip: Add separate workload for output tokens to see full cost.""",
            "status": "pending_confirmation"
        }
        add_workload_if_new(fm_input)
        
        # 4. Foundation Model - Output Tokens
        fm_output = {
            "proposal_id": str(uuid.uuid4()),
            "workload_type": "FMAPI_PROPRIETARY" if provider in ["anthropic", "openai", "google"] else "FMAPI_DATABRICKS",
            "workload_name": f"{use_case_name} - {model} (Output Tokens)",
            "cloud": cloud,
            "fmapi_provider": provider,
            "fmapi_model": model,
            "fmapi_endpoint_type": "global",
            "fmapi_context_length": "all",
            "fmapi_rate_type": "output_token",
            "fmapi_quantity": round(monthly_output_tokens, 2),
            "hours_per_month": 730,
            "reason": "Output tokens for generated responses",
            "notes": f"""Configuration Rationale:
• Model: {model} ({provider})
• Output tokens: {monthly_output_tokens:.2f}M/month
• Calculation: {expected_conversations_per_day} conv/day × {days_per_month} days × {avg_response_tokens} tokens/response

Note: Output tokens are typically 3-5x more expensive than input tokens.
Consider caching common responses to reduce costs.""",
            "status": "pending_confirmation"
        }
        add_workload_if_new(fm_output)
        
        return {
            "success": True,
            "action": "genai_architecture_proposed",
            "use_case": use_case,
            "use_case_name": use_case_name,
            "workloads_proposed": len(workloads),
            "workloads": [
                {"name": w["workload_name"], "type": w["workload_type"], "proposal_id": w["proposal_id"]}
                for w in workloads
            ],
            "explanation": explanation,
            "message": f"""I've proposed a complete {use_case_name} architecture with {len(workloads)} workloads:

{chr(10).join(f"• {w['workload_name']} ({w['workload_type']})" for w in workloads)}

Each workload needs to be confirmed individually. Review the configurations and notes for each one.

**Monthly Usage Estimates:**
• Conversations: {monthly_conversations:,}
• Input tokens: {monthly_input_tokens:.2f}M
• Output tokens: {monthly_output_tokens:.2f}M
• Documents: {document_count:,}""",
            "note": "Confirm each workload individually after reviewing the configuration and notes."
        }
    
    def _propose_workload(
        self,
        workload_type: str,
        workload_name: str,
        reason: str = "",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Propose a workload configuration for user confirmation.
        Does NOT add to estimate - user must confirm first.
        
        Validates that required estimate fields are set before proposing.
        """
        # Check if estimate has required fields
        if self.current_estimate:
            cloud = self.current_estimate.get('cloud')
            region = self.current_estimate.get('region')
            tier = self.current_estimate.get('tier')
            
            missing = []
            if not cloud:
                missing.append("Cloud Provider")
            if not region:
                missing.append("Region")
            if not tier:
                missing.append("Databricks Tier")
            
            if missing:
                return {
                    "success": False,
                    "error": "missing_required_fields",
                    "missing_fields": missing,
                    "message": f"Cannot propose workload. The estimate is missing required fields: {', '.join(missing)}. Please ask the user to fill in these fields in the estimate configuration first.",
                    "user_message": f"Before I can add workloads, please fill in the missing fields in your estimate configuration: {', '.join(missing)}. You can set these in the Configuration section at the top of the page."
                }
        else:
            return {
                "success": False,
                "error": "no_estimate",
                "message": "No estimate loaded. Cannot propose workload.",
                "user_message": "Please select or create an estimate first before adding workloads."
            }
        
        # Check for duplicate proposals (same workload name)
        existing_names = {p.get('workload_name') for p in self.proposed_workloads}
        if workload_name in existing_names:
            # Find and return the existing proposal instead of creating a duplicate
            for p in self.proposed_workloads:
                if p.get('workload_name') == workload_name:
                    return {
                        "success": True,
                        "message": f"Workload '{workload_name}' already proposed",
                        "proposed_workload": p,
                        "action_required": "This workload is already pending confirmation.",
                        "note": "Review and confirm the existing proposal."
                    }
        
        # Build workload configuration with defaults
        workload = {
            "proposal_id": str(uuid.uuid4()),
            "workload_type": workload_type,
            "workload_name": workload_name,
            "cloud": self.current_estimate["cloud"] if self.current_estimate else "aws",
            "reason": reason,
            "status": "pending_confirmation",
            **kwargs
        }
        
        # Apply sensible defaults based on workload type
        workload = self._apply_defaults(workload)
        
        # Store as pending proposal
        self.proposed_workloads.append(workload)
        
        return {
            "success": True,
            "message": f"Proposed {workload_type} workload: '{workload_name}'",
            "proposed_workload": workload,
            "action_required": "User must confirm this configuration before it's added to the estimate.",
            "note": "Costs will be calculated after the workload is confirmed and saved."
        }
    
    def _apply_defaults(self, workload: Dict[str, Any]) -> Dict[str, Any]:
        """Apply sensible defaults based on workload type and generate explanatory notes."""
        wtype = workload["workload_type"]
        cloud = workload.get("cloud", "aws").lower()
        
        # Cloud-specific instance types for balanced cost/performance
        # Using widely available instance types across regions
        instance_types = {
            "aws": {
                "general": "i3.xlarge",    # NVMe SSD, good for Spark shuffle
                "memory": "r5.xlarge",      # Memory optimized
                "compute": "c5.xlarge",     # Compute optimized
            },
            "azure": {
                "general": "Standard_D4s_v3",      # General purpose, widely available
                "memory": "Standard_E4s_v3",       # Memory optimized
                "compute": "Standard_F4s_v2",      # Compute optimized
            },
            "gcp": {
                "general": "n1-standard-4",        # Balanced
                "memory": "n1-highmem-4",          # Memory optimized
                "compute": "n1-highcpu-4",         # Compute optimized
            }
        }
        
        default_instance = instance_types.get(cloud, instance_types["aws"])["general"]
        
        # Common defaults
        workload.setdefault("hours_per_month", 730)
        workload.setdefault("days_per_month", 22)
        
        notes_parts = []
        
        if wtype in ["JOBS", "ALL_PURPOSE", "DLT"]:
            # Set serverless default - prefer serverless for simplicity
            is_serverless = workload.setdefault("serverless_enabled", False)
            
            # Photon - enable by default for performance
            photon_enabled = workload.setdefault("photon_enabled", True)
            
            if not is_serverless:
                # Non-serverless: set instance types and worker pricing
                workload.setdefault("num_workers", 4)
                workload.setdefault("driver_node_type", default_instance)
                workload.setdefault("worker_node_type", default_instance)
                
                # DEFAULT TO SPOT WORKERS for cost savings
                workload.setdefault("worker_pricing_tier", "spot")
                workload.setdefault("driver_pricing_tier", "on_demand")
                
                # Comprehensive Job Configuration Notes
                notes_parts.append("=" * 60)
                notes_parts.append("**DATABRICKS JOBS (CLASSIC COMPUTE) CONFIGURATION**")
                notes_parts.append("=" * 60)
                notes_parts.append("")
                
                # Instance Selection
                notes_parts.append(f"**📦 Instance Type: {default_instance}**:")
                if cloud == "aws":
                    notes_parts.append("• **i3.xlarge**: 4 vCPUs, 30.5 GB RAM, 950 GB NVMe SSD")
                    notes_parts.append("• **Why chosen**: NVMe SSD storage optimal for Spark shuffle operations")
                    notes_parts.append("• **Use case**: ETL/batch jobs with high I/O requirements")
                    notes_parts.append("• **Alternative**: m5d.xlarge for memory-intensive workloads")
                elif cloud == "azure":
                    notes_parts.append("• **Standard_D4s_v3**: 4 vCPUs, 16 GB RAM, Premium SSD")
                    notes_parts.append("• **Why chosen**: Balanced CPU/memory with SSD storage")
                    notes_parts.append("• **Availability**: D-series widely available across ALL Azure regions")
                    notes_parts.append("• **Alternative**: E-series for memory-optimized workloads")
                else:  # GCP
                    notes_parts.append("• **n1-standard-4**: 4 vCPUs, 15 GB RAM")
                    notes_parts.append("• **Why chosen**: Balanced compute for general-purpose workloads")
                    notes_parts.append("• **Alternative**: n1-highmem-4 for memory-intensive jobs")
                
                # Pricing Strategy
                notes_parts.append("")
                notes_parts.append("**💰 Pricing Strategy: Spot Workers + On-Demand Driver**:")
                notes_parts.append("• **Worker nodes**: Spot instances (60-90% cost savings)")
                notes_parts.append("  → Suitable for fault-tolerant batch/ETL workloads")
                notes_parts.append("  → Databricks auto-replaces interrupted spot instances")
                notes_parts.append("  → NOT recommended for time-sensitive/SLA-critical jobs")
                notes_parts.append("• **Driver node**: On-demand (for stability)")
                notes_parts.append("  → Ensures job coordination remains stable")
                notes_parts.append("  → Stores critical DAG and task metadata")
                notes_parts.append("• **Cost impact**: ~70-80% reduction in VM costs vs all on-demand")
                notes_parts.append("• **Risk mitigation**: Driver stays up even if workers are interrupted")
                
                # Cluster Sizing
                worker_min = workload.get("jobs_worker_min", 1)
                worker_max = workload.get("jobs_worker_max", 2)
                notes_parts.append("")
                notes_parts.append(f"**🔧 Cluster Sizing: {worker_min}-{worker_max} Workers**:")
                if worker_min == worker_max:
                    notes_parts.append(f"• **Fixed cluster**: {worker_min} worker(s) - no autoscaling")
                    notes_parts.append("  → Predictable performance and cost")
                    notes_parts.append("  → Best for consistent workload patterns")
                else:
                    notes_parts.append(f"• **Autoscaling enabled**: {worker_min} min → {worker_max} max workers")
                    notes_parts.append(f"  → Scales based on pending Spark tasks")
                    notes_parts.append(f"  → Cost-efficient for variable workloads")
                    notes_parts.append(f"  → Recommended scaling ratio: 1:{worker_max/worker_min:.1f}x for balanced performance")
                notes_parts.append(f"• **Total cluster capacity**: 1 driver + {worker_max} workers = {worker_max+1} nodes max")
                
                # Photon
                if photon_enabled:
                    notes_parts.append("")
                    notes_parts.append("**⚡ Photon Acceleration: ENABLED**:")
                    notes_parts.append("• **Performance**: 2-3x faster for SQL/DataFrame operations")
                    notes_parts.append("• **How it works**: Native vectorized C++ engine (vs JVM)")
                    notes_parts.append("• **Best for**: SELECT, JOIN, aggregations, Parquet/Delta reads")
                    notes_parts.append("• **Cost consideration**: +2x DBU rate, but 2-3x faster = similar or lower total cost")
                    notes_parts.append("• **Example**: 1-hour job → 20-30 min with Photon, lower total DBU consumption")
                    notes_parts.append("• **When to disable**: Python UDFs, RDD operations (no Photon benefit)")
                else:
                    notes_parts.append("")
                    notes_parts.append("**🔧 Standard Spark Engine (Photon disabled)**:")
                    notes_parts.append("• Using JVM-based Spark execution")
                    notes_parts.append("• Consider enabling Photon for SQL-heavy workloads (2-3x speedup)")
                
                # Operational Guidance
                notes_parts.append("")
                notes_parts.append("**🎯 OPERATIONAL GUIDANCE:**:")
                notes_parts.append("• **Startup time**: 5-7 minutes for cluster initialization")
                notes_parts.append("  → Consider cluster pools for <1 min startup")
                notes_parts.append("• **Job scheduling**: Use Databricks Workflows for orchestration")
                notes_parts.append("• **Monitoring**: Track shuffle read/write, GC time, task duration")
                notes_parts.append("• **Cost optimization**: Use job clusters (terminate after run) vs all-purpose clusters")
                notes_parts.append("• **Spot best practices**: Enable retries, set max spot price limit")
                
            else:  # Serverless
                notes_parts.append("=" * 60)
                notes_parts.append("**DATABRICKS JOBS (SERVERLESS MODE) CONFIGURATION**")
                notes_parts.append("=" * 60)
                notes_parts.append("")
                notes_parts.append("**🚀 Serverless Compute**:")
                notes_parts.append("• **Zero infrastructure management**: No instance types, cluster sizing")
                notes_parts.append("• **Instant startup**: <1 minute (vs 5-7 min for classic clusters)")
                notes_parts.append("• **Auto-scaling**: Automatic based on Spark task parallelism")
                notes_parts.append("• **Pay-per-use**: Billed only for actual compute seconds used")
                notes_parts.append("• **Built-in optimization**: Photon always enabled, auto-tuned Spark configs")
                notes_parts.append("• **Use cases**: Ad-hoc jobs, inconsistent schedules, rapid development")
                notes_parts.append("• **Cost**: ~30% premium vs classic, but often cheaper due to instant termination")
                notes_parts.append("• **Limitations**: Limited Spark config customization, no cluster pools")
        
        if wtype == "DLT":
            edition = workload.setdefault("dlt_edition", "PRO")
            notes_parts.append("")
            notes_parts.append("=" * 60)
            notes_parts.append("**DELTA LIVE TABLES (DLT) CONFIGURATION**")
            notes_parts.append("=" * 60)
            notes_parts.append("")
            notes_parts.append(f"**📋 DLT Edition: {edition}**")
            notes_parts.append("")
            
            if edition == "CORE":
                notes_parts.append("**CORE Edition Features:**")
                notes_parts.append("• **Basic pipeline functionality**: Bronze → Silver → Gold transformations")
                notes_parts.append("• **Incremental processing**: Efficient updates with Delta Lake")
                notes_parts.append("• **Declarative Python/SQL**: Define tables, DLT handles orchestration")
                notes_parts.append("• **Automatic retries**: Built-in fault tolerance")
                notes_parts.append("• **Cost**: Lowest DBU rate (0.20x DBU multiplier)")
                notes_parts.append("")
                notes_parts.append("**Best For:**")
                notes_parts.append("• Simple ETL without CDC/SCD requirements")
                notes_parts.append("• Append-only data ingestion pipelines")
                notes_parts.append("• Cost-sensitive non-production workloads")
                notes_parts.append("")
                notes_parts.append("**Limitations:**")
                notes_parts.append("• ❌ No Change Data Capture (CDC)")
                notes_parts.append("• ❌ No SCD Type 2 (historical tracking)")
                notes_parts.append("• ❌ Limited data quality expectations")
                notes_parts.append("")
                notes_parts.append("**💡 Consider upgrading to PRO for:**")
                notes_parts.append("• Production pipelines requiring CDC")
                notes_parts.append("• Historical data tracking (SCD Type 2)")
                
            elif edition == "PRO":
                notes_parts.append("**PRO Edition Features:**")
                notes_parts.append("• **All CORE features**, PLUS:")
                notes_parts.append("• **Change Data Capture (CDC)**: Apply changes from databases (INSERT/UPDATE/DELETE)")
                notes_parts.append("• **SCD Type 2**: Automatically track historical changes with valid_from/valid_to")
                notes_parts.append("• **Enhanced monitoring**: Detailed pipeline metrics and lineage")
                notes_parts.append("• **Data quality expectations**: Basic validation rules (NOT NULL, ranges)")
                notes_parts.append("• **Cost**: Medium DBU rate (0.30x DBU multiplier, +50% vs CORE)")
                notes_parts.append("")
                notes_parts.append("**Best For:**")
                notes_parts.append("• Production ETL pipelines with CDC requirements")
                notes_parts.append("• Streaming data from databases (MySQL, Postgres, SQL Server)")
                notes_parts.append("• Maintaining historical snapshots of dimension tables")
                notes_parts.append("• Most enterprise data engineering workloads")
                notes_parts.append("")
                notes_parts.append("**Example Use Cases:**")
                notes_parts.append("• Replicate CRM database changes to Delta Lake")
                notes_parts.append("• Track customer attribute changes over time (SCD Type 2)")
                notes_parts.append("• Merge new/updated records from upstream sources")
                notes_parts.append("")
                notes_parts.append("**💡 Consider upgrading to ADVANCED for:**")
                notes_parts.append("• Mission-critical pipelines requiring strict data quality")
                notes_parts.append("• Complex expectations and custom validation logic")
                
            else:  # ADVANCED
                notes_parts.append("**ADVANCED Edition Features:**")
                notes_parts.append("• **All PRO features**, PLUS:")
                notes_parts.append("• **Advanced data quality expectations**: Custom validation with Python/SQL")
                notes_parts.append("  → Expectations can FAIL or WARN on violations")
                notes_parts.append("  → Track which records failed which expectations")
                notes_parts.append("  → Quarantine bad data to separate tables")
                notes_parts.append("• **Enhanced observability**: Detailed event logs, data quality metrics")
                notes_parts.append("• **Row-level lineage**: Track data flow at record level")
                notes_parts.append("• **Pipeline debugging**: Better error messages and troubleshooting")
                notes_parts.append("• **Cost**: Highest DBU rate (0.36x DBU multiplier, +80% vs CORE, +20% vs PRO)")
                notes_parts.append("")
                notes_parts.append("**Best For:**")
                notes_parts.append("• Production-critical pipelines with strict SLAs")
                notes_parts.append("• Regulated industries (finance, healthcare) requiring data quality audits")
                notes_parts.append("• Pipelines feeding downstream ML/BI with zero tolerance for bad data")
                notes_parts.append("• Complex validation logic (referential integrity, business rules)")
                notes_parts.append("")
                notes_parts.append("**Example Use Cases:**")
                notes_parts.append("• Financial transactions (must validate balances, detect anomalies)")
                notes_parts.append("• Healthcare data (HIPAA compliance, mandatory field validation)")
                notes_parts.append("• Customer 360 (enforce referential integrity across 10+ sources)")
                notes_parts.append("")
                notes_parts.append("**ROI Consideration:**")
                notes_parts.append("• +20% cost vs PRO, but prevents data quality issues saving 10x in debugging")
            
            notes_parts.append("")
            notes_parts.append("**🎯 DLT OPERATIONAL GUIDANCE:**")
            notes_parts.append("• **Pipeline mode**: Choose 'Continuous' (streaming) or 'Triggered' (batch)")
            notes_parts.append("• **Development**: Use 'Development' mode for faster iteration (no optimizations)")
            notes_parts.append("• **Production**: Use 'Production' mode (automatic optimizations, stable performance)")
            notes_parts.append("• **Monitoring**: Check DLT event log for pipeline metrics and data quality results")
            notes_parts.append("• **Cost optimization**: Use 'Enhanced Autoscaling' to minimize idle compute")
        
        if wtype == "DBSQL":
            warehouse_type = workload.setdefault("dbsql_warehouse_type", "SERVERLESS")
            size = workload.setdefault("dbsql_warehouse_size", "Small")
            
            # Calculate num_clusters based on queries per minute throughput
            total_users = workload.get("total_users", 0)
            use_case_type = workload.get("use_case_type", "bi_dashboard")
            typical_data_volume = workload.get("typical_data_volume", "1-10GB")
            query_complexity = workload.get("query_complexity", "medium")
            
            # Warehouse QPM at 10GB baseline (medium complexity queries)
            warehouse_qpm = {
                "2X-Small": 77,
                "X-Small": 131,
                "Small": 224,
                "Medium": 380,
                "Large": 646,
                "X-Large": 1098,
                "2X-Large": 1867,
                "3X-Large": 3174,
                "4X-Large": 5395,
            }
            base_qpm = warehouse_qpm.get(size, 224)  # Default to Small
            
            # Calculate queries per minute needed
            if total_users > 0:
                # Step 1: Calculate concurrent users
                concurrency_ratios = {
                    "bi_dashboard": 0.15,  # 15% average
                    "analytics": 0.25,     # 25% average
                    "monitoring": 0.50,    # 50% average
                }
                ratio = concurrency_ratios.get(use_case_type, 0.15)
                concurrent_users = int(total_users * ratio)
                
                # Step 2: Calculate queries per minute
                queries_per_user_per_minute = {
                    "bi_dashboard": 1,    # BI users: mostly viewing, occasional interactions
                    "analytics": 2,       # Analytics users: active exploration
                    "monitoring": 2,      # Monitoring: automated refreshes
                }
                qpm_per_user = queries_per_user_per_minute.get(use_case_type, 1)
                queries_per_minute_needed = concurrent_users * qpm_per_user
                
                # Step 3: Adjust QPM based on data volume (linear scaling)
                data_volume_gb_map = {
                    "<1GB": 0.5,
                    "1-10GB": 10,
                    "10-100GB": 50,
                    "100GB-1TB": 500,
                    ">1TB": 5000,
                }
                avg_data_gb = data_volume_gb_map.get(typical_data_volume, 10)
                adjusted_qpm_per_cluster = base_qpm * (10 / avg_data_gb)
                
                # Step 4: Adjust QPM based on query complexity
                # Baseline QPM is for medium complexity queries (TPC-DS benchmark)
                complexity_multipliers = {
                    "simple": 2.0,    # Simple queries are 2x faster
                    "medium": 1.0,    # Baseline
                    "complex": 0.33,  # Complex queries are 3x slower (1/3 throughput)
                }
                complexity_multiplier = complexity_multipliers.get(query_complexity, 1.0)
                adjusted_qpm_per_cluster = adjusted_qpm_per_cluster * complexity_multiplier
                
                # Step 5: Calculate clusters needed
                if adjusted_qpm_per_cluster > 0:
                    import math
                    num_clusters = max(1, math.ceil(queries_per_minute_needed / adjusted_qpm_per_cluster))  # Always round UP
                    workload.setdefault("dbsql_num_clusters", num_clusters)
                else:
                    workload.setdefault("dbsql_num_clusters", 1)
            else:
                workload.setdefault("dbsql_num_clusters", 1)
            
            notes_parts.append(f"**Warehouse Type ({warehouse_type})**:")
            if warehouse_type == "SERVERLESS":
                notes_parts.append("• Instant startup (<5 seconds)")
                notes_parts.append("• Auto-scaling, scales to zero when idle")
                notes_parts.append("• Pay-per-use, best for sporadic/variable workloads")
            elif warehouse_type == "PRO":
                notes_parts.append("• Slower startup (3-4 minutes)")
                notes_parts.append("• Auto-scaling, pay-per-use")
                notes_parts.append("• Better for constant workloads where startup time matters")
                notes_parts.append("• Unity Catalog support")
            else:  # CLASSIC
                notes_parts.append("• Legacy option (not recommended for new deployments)")
                notes_parts.append("• Slower startup (3-4 minutes)")
                notes_parts.append("• Unity Catalog support")
                notes_parts.append("• Auto-scaling, can scale to zero, pay-per-use")
                notes_parts.append("• NO Predictive I/O (slower for large datasets >10GB)")
            
            notes_parts.append("")
            notes_parts.append(f"**Warehouse Size ({size})**:")
            size_info = {
                "2X-Small": "4 DBU/hr, 77 QPM - Light usage: 1-5 users, 10GB: ~5s, suitable for small teams",
                "X-Small": "6 DBU/hr, 131 QPM - Small team: 5-10 users, 10GB: ~3s, 1TB: ~5min",
                "Small": "12 DBU/hr, 224 QPM - Standard BI: 10-20 users, 10GB: ~2s, 100GB: ~17s (default choice)",
                "Medium": "24 DBU/hr, 380 QPM - Active dashboards: 20-40 users, 10GB: <1s, 1TB: ~2min",
                "Large": "40 DBU/hr, 646 QPM - Heavy workloads: 40-80 users, 100GB: ~6s, 1TB: <1min",
                "X-Large": "80 DBU/hr, 1,098 QPM - High concurrency: 80-150 users, sub-second for 100GB",
                "2X-Large": "144 DBU/hr, 1,867 QPM - Enterprise scale: 150-250 users, 1TB: ~21s",
                "3X-Large": "272 DBU/hr, 3,174 QPM - Very large scale: 250-400 users, 10TB: ~2min",
                "4X-Large": "528 DBU/hr, 5,395 QPM - Maximum performance: 400+ users, 10TB: ~1min",
            }
            notes_parts.append(f"• {size_info.get(size, 'Sized based on expected query complexity')}")
            
            # Comprehensive sizing calculation with all inputs and assumptions
            notes_parts.append("")
            notes_parts.append("=" * 60)
            notes_parts.append("**DETAILED SIZING CALCULATION**")
            notes_parts.append("=" * 60)
            
            num_clusters = workload.get("dbsql_num_clusters", 1)
            total_users = workload.get("total_users", 0)
            use_case_type = workload.get("use_case_type", "bi_dashboard")
            typical_data_volume = workload.get("typical_data_volume", "1-10GB")
            query_complexity = workload.get("query_complexity", "medium")
            query_selectivity = workload.get("query_selectivity", "unknown")
            
            # Section 1: Inputs Collected
            notes_parts.append("")
            notes_parts.append("**📊 INPUTS COLLECTED:**")
            notes_parts.append(f"• Total Users: {total_users if total_users > 0 else 'Not specified'}")
            notes_parts.append(f"• Use Case Type: {use_case_type.replace('_', ' ').title()}")
            notes_parts.append(f"• Data Volume (compressed): {typical_data_volume}")
            notes_parts.append(f"• Query Complexity: {query_complexity.title()}")
            if query_complexity == "simple":
                notes_parts.append("  → Single table, basic filters/aggregations (COUNT, SUM, AVG)")
            elif query_complexity == "medium":
                notes_parts.append("  → 2-3 table joins with WHERE clauses and GROUP BY (TPC-DS baseline)")
            elif query_complexity == "complex":
                notes_parts.append("  → 4+ table joins, subqueries, window functions, nested aggregations")
            notes_parts.append(f"• Query Selectivity: {query_selectivity.title()}")
            notes_parts.append(f"• Selected Warehouse: {warehouse_type} {size}")
            
            # Section 2: Assumptions Made
            notes_parts.append("")
            notes_parts.append("**🎯 ASSUMPTIONS:**")
            concurrency_ratios = {"bi_dashboard": 0.15, "analytics": 0.25, "monitoring": 0.50}
            queries_per_user = {"bi_dashboard": 1, "analytics": 2, "monitoring": 2}
            ratio = concurrency_ratios.get(use_case_type, 0.15)
            qpm_per_user = queries_per_user.get(use_case_type, 1)
            
            if use_case_type == "bi_dashboard":
                notes_parts.append("• BI Dashboard Users:")
                notes_parts.append("  → Peak concurrency: ~15% of total users")
                notes_parts.append("  → Query frequency: 1 query/user/minute (mostly viewing, occasional filters)")
            elif use_case_type == "analytics":
                notes_parts.append("• Analytics Users:")
                notes_parts.append("  → Peak concurrency: ~25% of total users")
                notes_parts.append("  → Query frequency: 2 queries/user/minute (active exploration, filter changes)")
            elif use_case_type == "monitoring":
                notes_parts.append("• Monitoring Dashboard:")
                notes_parts.append("  → Peak concurrency: ~50% of total users")
                notes_parts.append("  → Query frequency: 2 queries/user/minute (automated refreshes)")
            
            notes_parts.append("• Benchmark: TPC-DS medium complexity queries on 10GB data")
            notes_parts.append("• Data volume scaling: Linear (100GB = 1/10th of 10GB QPM)")
            notes_parts.append("• Query complexity impact:")
            notes_parts.append("  → Simple queries: 2x faster than baseline")
            notes_parts.append("  → Medium queries: Baseline performance")
            notes_parts.append("  → Complex queries: 3x slower than baseline (1/3 throughput)")
            notes_parts.append("• Cluster rounding: ALWAYS round UP (e.g., 1.86 → 2 clusters, NOT 1)")
            notes_parts.append("  → Better to have extra capacity than insufficient throughput")
            
            # Section 3: Step-by-Step Calculation
            if total_users > 0:
                notes_parts.append("")
                notes_parts.append("**🔢 CALCULATION STEPS:**")
                
                # Step 1: Concurrent users
                concurrent_users = int(total_users * ratio)
                notes_parts.append(f"Step 1 - Calculate Concurrent Users:")
                notes_parts.append(f"  {total_users} total users × {int(ratio*100)}% = {concurrent_users} concurrent users")
                
                # Step 2: Queries per minute needed
                queries_per_minute_needed = concurrent_users * qpm_per_user
                notes_parts.append(f"Step 2 - Calculate Queries Per Minute Needed:")
                notes_parts.append(f"  {concurrent_users} users × {qpm_per_user} queries/user/min = {queries_per_minute_needed} QPM needed")
                
                # Step 3: Base QPM for warehouse size
                warehouse_qpm = {"2X-Small": 77, "X-Small": 131, "Small": 224, "Medium": 380, "Large": 646, "X-Large": 1098, "2X-Large": 1867, "3X-Large": 3174, "4X-Large": 5395}
                base_qpm = warehouse_qpm.get(size, 224)
                notes_parts.append(f"Step 3 - Base Warehouse QPM (10GB, Medium Complexity):")
                notes_parts.append(f"  {size} warehouse = {base_qpm} QPM per cluster")
                
                # Step 4: Adjust for data volume
                data_volume_gb_map = {"<1GB": 0.5, "1-10GB": 10, "10-100GB": 50, "100GB-1TB": 500, ">1TB": 5000}
                avg_data_gb = data_volume_gb_map.get(typical_data_volume, 10)
                qpm_after_volume = base_qpm * (10 / avg_data_gb)
                notes_parts.append(f"Step 4 - Adjust for Data Volume:")
                notes_parts.append(f"  {base_qpm} QPM × (10GB / {avg_data_gb}GB) = {qpm_after_volume:.1f} QPM")
                
                # Step 5: Adjust for query complexity
                complexity_multipliers = {"simple": 2.0, "medium": 1.0, "complex": 0.33}
                complexity_multiplier = complexity_multipliers.get(query_complexity, 1.0)
                final_qpm_per_cluster = qpm_after_volume * complexity_multiplier
                notes_parts.append(f"Step 5 - Adjust for Query Complexity:")
                notes_parts.append(f"  {qpm_after_volume:.1f} QPM × {complexity_multiplier} ({query_complexity}) = {final_qpm_per_cluster:.1f} QPM/cluster")
                
                # Step 6: Calculate clusters needed
                notes_parts.append(f"Step 6 - Calculate Clusters Needed:")
                notes_parts.append(f"  {queries_per_minute_needed} QPM needed ÷ {final_qpm_per_cluster:.1f} QPM/cluster = {queries_per_minute_needed / final_qpm_per_cluster:.2f}")
                notes_parts.append(f"  → Rounded UP to {num_clusters} cluster(s) (always round up for capacity)")
                
                # Section 4: Final Results
                notes_parts.append("")
                notes_parts.append("**✅ FINAL CONFIGURATION:**")
                total_capacity_qpm = num_clusters * final_qpm_per_cluster
                notes_parts.append(f"• Total Capacity: {num_clusters} clusters × {final_qpm_per_cluster:.1f} QPM = {total_capacity_qpm:.0f} QPM")
                notes_parts.append(f"• Required Throughput: {queries_per_minute_needed} QPM")
                headroom_pct = ((total_capacity_qpm - queries_per_minute_needed) / queries_per_minute_needed * 100) if queries_per_minute_needed > 0 else 0
                notes_parts.append(f"• Headroom: {headroom_pct:.0f}% above requirement")
                notes_parts.append(f"• Can support: ~{int(total_capacity_qpm / qpm_per_user / ratio)} total users at peak concurrency")
            else:
                notes_parts.append("")
                notes_parts.append(f"**Configuration:** {num_clusters} cluster(s) manually specified")
            
            notes_parts.append("")
            notes_parts.append("=" * 60)
            
            # Add performance information
            notes_parts.append("")
            notes_parts.append(f"**Query Performance ({size})**:")
            qpm_info = {
                "2X-Small": "77 QPM - 10GB: ~5s (Pro/Serverless with Predictive I/O)",
                "X-Small": "131 QPM - 10GB: ~3s, 1TB: ~5min",
                "Small": "224 QPM - 10GB: ~2s, 100GB: ~17s",
                "Medium": "380 QPM - 10GB: <1s, 1TB: ~2min",
                "Large": "646 QPM - 100GB: ~6s, 1TB: <1min",
                "X-Large": "1,098 QPM - 100GB: ~3s, 1TB: ~35s",
                "2X-Large": "1,867 QPM - 100GB: ~2s, 1TB: ~21s",
                "3X-Large": "3,174 QPM - 100GB: ~1s, 1TB: ~12s",
                "4X-Large": "5,395 QPM - 100GB: <1s, 1TB: ~7s",
            }
            notes_parts.append(f"• {qpm_info.get(size, 'Scales with warehouse size')}")
            notes_parts.append("• Photon acceleration always enabled for DBSQL")
            
            # Add Predictive I/O note for Pro/Serverless
            data_volume = workload.get("typical_data_volume", "unknown")
            selectivity = workload.get("query_selectivity", "unknown")
            
            if warehouse_type in ["SERVERLESS", "PRO"]:
                notes_parts.append("")
                notes_parts.append("**Predictive I/O Acceleration:**")
                notes_parts.append("• Enabled for Pro/Serverless warehouses")
                
                if data_volume in ["10-100GB", "100GB-1TB", ">1TB"]:
                    if selectivity == "high":
                        notes_parts.append("• High selectivity queries (<1%): up to 17x faster than Classic")
                        notes_parts.append("  Example: Filter to specific user ID, single day of data")
                    elif selectivity == "moderate":
                        notes_parts.append("• Moderate selectivity queries (1-5%): 5-10x faster than Classic")
                        notes_parts.append("  Example: Filter to 1 week in a year, 1 region out of 20, VIP customers")
                    elif selectivity == "low":
                        notes_parts.append("• Low selectivity queries (>5%): 1-3x faster than Classic")
                        notes_parts.append("  Example: Filter to 1 quarter, large categories")
                    else:
                        notes_parts.append("• For selective queries (<5% of data): 5-17x faster than Classic")
                        notes_parts.append("  Example: Filtering by date ranges, user IDs, specific categories")
                else:
                    notes_parts.append("• For datasets >10GB: significant speedup on selective queries")
                    
            elif warehouse_type == "CLASSIC":
                notes_parts.append("")
                notes_parts.append("**Performance Note:**")
                notes_parts.append("• Classic: Supports Unity Catalog, auto-scaling, scale to zero")
                notes_parts.append("• Classic: NO Predictive I/O (slower for large datasets)")
                if data_volume in ["10-100GB", "100GB-1TB", ">1TB"]:
                    notes_parts.append("• ⚠️ Consider Pro/Serverless for 5-17x faster performance on selective queries with Predictive I/O")
        
        if wtype == "LAKEBASE":
            cu = workload.setdefault("lakebase_cu", 2)
            ha_nodes = workload.setdefault("lakebase_ha_nodes", 1)
            
            notes_parts.append("")
            notes_parts.append("=" * 60)
            notes_parts.append("**LAKEBASE (POSTGRESQL) CONFIGURATION**")
            notes_parts.append("=" * 60)
            notes_parts.append("")
            notes_parts.append(f"**🗄️ Compute Units: {cu} CU**:")
            notes_parts.append(f"• Each CU = 1 vCPU + dedicated memory + storage IOPS")
            notes_parts.append(f"• **Your configuration**: {cu} CU = ~{cu*2}GB RAM, {cu*1000} IOPS baseline")
            notes_parts.append(f"• **Concurrent connections**: ~{cu*50} max recommended")
            notes_parts.append(f"• **Query throughput**: ~{cu*100} simple queries/second")
            notes_parts.append("")
            notes_parts.append("**Sizing Guidelines:**")
            notes_parts.append("• 1-2 CU: Development, <10 concurrent connections")
            notes_parts.append("• 2-4 CU: Small production, <50 concurrent connections")
            notes_parts.append("• 4-8 CU: Medium production, <200 concurrent connections")
            notes_parts.append("• 8+ CU: Large production, complex queries, high concurrency")
            notes_parts.append("")
            notes_parts.append(f"**High Availability: {ha_nodes} standby node(s)**:")
            if ha_nodes > 0:
                notes_parts.append("• ✅ HA enabled: Automatic failover to standby")
                notes_parts.append(f"• **Recovery time**: <60 seconds with {ha_nodes} standby")
                notes_parts.append("• **Cost**: +100% (each standby = full replica)")
                notes_parts.append("• **Best for**: Production systems requiring 99.95%+ uptime")
            else:
                notes_parts.append("• ⚠️ HA disabled: Single point of failure")
                notes_parts.append("• **Risk**: Downtime during maintenance or failures")
                notes_parts.append("• **Cost savings**: 50% (no standby replicas)")
                notes_parts.append("• **Best for**: Development/test environments")
            notes_parts.append("")
            notes_parts.append("**🎯 LAKEBASE OPERATIONAL GUIDANCE:**")
            notes_parts.append("• **Backups**: Automated daily backups with 7-day retention")
            notes_parts.append("• **Monitoring**: Track connection pool usage, query latency")
            notes_parts.append("• **Scaling**: Vertical (add CUs) for more power, horizontal (read replicas) for scale")
            notes_parts.append("• **Cost optimization**: Right-size CUs based on actual CPU/memory usage")
        
        # IGNORE any brief notes provided by LLM - we generate comprehensive ones
        # existing_notes = workload.get("notes", "")  # DON'T use LLM's brief notes
        
        # Add comprehensive header and footer if we have generated notes
        if notes_parts:
            # Add header
            header_parts = []
            header_parts.append("╔" + "=" * 58 + "╗")
            header_parts.append("║" + " " * 10 + "DATABRICKS WORKLOAD CONFIGURATION" + " " * 15 + "║")
            header_parts.append("║" + " " * 12 + f"Created by AI Assistant - {wtype}" + " " * (34 - len(wtype)) + "║")
            header_parts.append("╚" + "=" * 58 + "╝")
            header_parts.append("")
            header_parts.append("This configuration was generated based on your requirements.")
            header_parts.append("Review all sections carefully before deployment to production.")
            header_parts.append("")
            
            # Add footer with summary
            footer_parts = []
            footer_parts.append("")
            footer_parts.append("=" * 60)
            footer_parts.append("**📋 CONFIGURATION SUMMARY**")
            footer_parts.append("=" * 60)
            footer_parts.append(f"• **Workload Type**: {wtype}")
            footer_parts.append(f"• **Cloud**: {workload.get('cloud', 'Not specified').upper()}")
            footer_parts.append(f"• **Region**: {workload.get('region', 'Not specified')}")
            
            # Add workload-specific summary
            if wtype == "DBSQL":
                wh_type = workload.get("dbsql_warehouse_type", "SERVERLESS")
                wh_size = workload.get("dbsql_warehouse_size", "Small")
                wh_clusters = workload.get("dbsql_num_clusters", 1)
                footer_parts.append(f"• **Warehouse**: {wh_type} {wh_size} × {wh_clusters} cluster(s)")
                footer_parts.append(f"• **Expected Users**: {workload.get('total_users', 'Not specified')}")
            elif wtype == "JOBS":
                if workload.get("jobs_serverless"):
                    footer_parts.append("• **Compute**: Serverless (fully managed)")
                else:
                    instance = workload.get("jobs_instance_type", "Not specified")
                    workers = workload.get("jobs_worker_max", 2)
                    footer_parts.append(f"• **Compute**: Classic ({instance})")
                    footer_parts.append(f"• **Cluster size**: 1 driver + {workers} workers max")
            elif wtype == "DLT":
                edition = workload.get("dlt_edition", "PRO")
                footer_parts.append(f"• **Edition**: {edition}")
            elif wtype == "LAKEBASE":
                cu = workload.get("lakebase_cu", 2)
                ha = workload.get("lakebase_ha_nodes", 1)
                footer_parts.append(f"• **Compute Units**: {cu} CU")
                footer_parts.append(f"• **High Availability**: {'Enabled' if ha > 0 else 'Disabled'}")
            
            footer_parts.append("")
            footer_parts.append("**⚠️ IMPORTANT REMINDERS:**")
            footer_parts.append("• This is a PROPOSAL - review before confirming")
            footer_parts.append("• Costs shown are estimates - actual costs may vary")
            footer_parts.append("• Monitor actual usage and adjust sizing as needed")
            footer_parts.append("• Consider starting with smaller configuration and scaling up")
            footer_parts.append("• Set up budget alerts and cost monitoring")
            footer_parts.append("")
            footer_parts.append("**📊 NEXT STEPS:**")
            footer_parts.append("1. Review the detailed configuration above")
            footer_parts.append("2. Confirm this proposal to add to your estimate")
            footer_parts.append("3. Adjust sizing based on actual usage patterns")
            footer_parts.append("4. Set up monitoring and alerting")
            footer_parts.append("5. Document any custom configurations or requirements")
            footer_parts.append("")
            footer_parts.append("=" * 60)
            footer_parts.append("Need to modify this configuration? Just ask!")
            footer_parts.append("=" * 60)
            
            # Assemble the full notes
            full_header = "\n".join(header_parts)
            main_notes = "\n".join(notes_parts)
            full_footer = "\n".join(footer_parts)
            generated_notes = f"{full_header}\n{main_notes}\n{full_footer}"
        else:
            generated_notes = ""
        
        # Only use our comprehensive generated notes, not the LLM's brief summary
        if generated_notes:
            workload["notes"] = generated_notes
        else:
            # Fallback only if no notes were generated at all
            workload["notes"] = "Configuration proposal - details to be added."
        
        return workload
    
    def confirm_workload(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        """
        Confirm a proposed workload (called from API after user confirms).
        Returns the workload configuration to be saved.
        """
        for i, proposal in enumerate(self.proposed_workloads):
            if proposal.get("proposal_id") == proposal_id:
                workload = self.proposed_workloads.pop(i)
                workload["status"] = "confirmed"
                return workload
        return None
    
    def reject_workload(self, proposal_id: str) -> bool:
        """Reject a proposed workload."""
        for i, proposal in enumerate(self.proposed_workloads):
            if proposal.get("proposal_id") == proposal_id:
                self.proposed_workloads.pop(i)
                return True
        return False
    
    def _get_estimate_summary(self) -> Dict[str, Any]:
        """Get summary of current estimate using actual costs from context."""
        if not self.current_estimate:
            return {"error": "No estimate loaded"}
        
        total_cost = 0
        workload_summaries = []
        
        for w in self.current_workloads:
            cost = w.get('total_cost') or w.get('monthly_cost') or 0
            if isinstance(cost, dict):
                cost = cost.get('total', 0)
            cost = float(cost) if cost else 0
            total_cost += cost
            
            workload_summaries.append({
                "name": w.get("workload_name"),
                "type": w.get("workload_type"),
                "monthly_cost": f"${cost:.2f}"
            })
        
        return {
            "estimate": {
                "name": self.current_estimate.get("estimate_name") or self.current_estimate.get("name"),
                "cloud": self.current_estimate.get("cloud", "").upper(),
                "region": self.current_estimate.get("region")
            },
            "workload_count": len(self.current_workloads),
            "workloads": workload_summaries,
            "total_monthly_cost": f"${total_cost:.2f}",
            "total_annual_cost": f"${total_cost * 12:.2f}",
            "pending_proposals": len(self.proposed_workloads)
        }
    
    def _analyze_estimate(self, focus_area: str = "all") -> Dict[str, Any]:
        """Analyze estimate using actual costs and provide recommendations."""
        if not self.current_estimate:
            return {"error": "No estimate loaded"}
        
        if not self.current_workloads:
            return {
                "error": "No workloads to analyze",
                "suggestion": "Add some workloads first, then I can help optimize them."
            }
        
        recommendations = []
        total_cost = 0
        
        for workload in self.current_workloads:
            wtype = workload.get("workload_type", "")
            wname = workload.get("workload_name", "Unnamed")
            
            # Get actual cost
            cost = workload.get('total_cost') or workload.get('monthly_cost') or 0
            if isinstance(cost, dict):
                cost = cost.get('total', 0)
            cost = float(cost) if cost else 0
            total_cost += cost
            
            # Cost optimization recommendations
            if focus_area in ["cost_optimization", "all"]:
                if wtype == "JOBS" and workload.get("worker_pricing_tier") != "spot":
                    recommendations.append({
                        "workload": wname,
                        "type": "cost",
                        "current_cost": f"${cost:.2f}/month",
                        "suggestion": "Consider using spot instances for workers",
                        "potential_savings": "Up to 90% on worker costs",
                        "consideration": "Only for fault-tolerant batch jobs"
                    })
                
                if wtype in ["ALL_PURPOSE", "JOBS", "DLT"] and not workload.get("serverless_enabled"):
                    hours = workload.get("hours_per_month", 730)
                    if hours and hours < 200:
                        recommendations.append({
                            "workload": wname,
                            "type": "cost",
                            "current_cost": f"${cost:.2f}/month",
                            "suggestion": "Consider serverless for this low-utilization workload",
                            "current_hours": f"{hours} hours/month",
                            "potential_savings": "Pay only for actual usage"
                        })
                
                if wtype == "DBSQL" and workload.get("dbsql_warehouse_type") != "SERVERLESS":
                    recommendations.append({
                        "workload": wname,
                        "type": "cost",
                        "current_cost": f"${cost:.2f}/month",
                        "suggestion": "Consider DBSQL Serverless for automatic scaling",
                        "potential_savings": "Scales to zero when idle"
                    })
            
            # Performance recommendations
            if focus_area in ["performance", "all"]:
                if wtype in ["JOBS", "ALL_PURPOSE", "DLT"] and not workload.get("photon_enabled"):
                    recommendations.append({
                        "workload": wname,
                        "type": "performance",
                        "suggestion": "Enable Photon for faster processing",
                        "impact": "2-3x faster on compatible workloads",
                        "consideration": "Slightly higher DBU cost but often net cheaper due to faster completion"
                    })
        
        return {
            "total_monthly_cost": f"${total_cost:.2f}",
            "total_annual_cost": f"${total_cost * 12:.2f}",
            "workload_count": len(self.current_workloads),
            "recommendations": recommendations,
            "recommendation_count": len(recommendations),
            "focus_area": focus_area
        }


def create_agent(token: str) -> EstimateAgent:
    """Create a new agent instance with the given token."""
    client = get_claude_client(token)
    return EstimateAgent(client)