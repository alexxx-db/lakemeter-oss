"""
AI Agent Service for Lakemeter

Orchestrates conversations with Claude to help users create and analyze estimates.
Implements tool calling for estimate management operations.

NOTE: This agent does NOT perform cost calculations. It:
1. Proposes workload configurations based on user requirements
2. Analyzes existing estimates using costs provided in context
3. Creates drafts that are then saved via the regular API flow
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
1. How many concurrent users/queries expected?
2. Is this for BI dashboards (continuous) or ad-hoc queries (sporadic)?
3. What query complexity? (determines warehouse size)
4. Serverless (auto-scaling, simpler) or Pro/Classic (fixed size)?

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

### DBSQL Warehouse Sizes (DBU/hour)
- 2X-Small: 4 DBU/hr
- X-Small: 6 DBU/hr  
- Small: 12 DBU/hr
- Medium: 24 DBU/hr
- Large: 40 DBU/hr
- X-Large: 80 DBU/hr
- 2X-Large: 144 DBU/hr
- 3X-Large: 272 DBU/hr
- 4X-Large: 528 DBU/hr

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

# System prompt for Estimates List page (create new estimates only)
SYSTEM_PROMPT_ESTIMATES_LIST = SYSTEM_PROMPT_BASE + """

## Your Role (Estimates List Page)
You are on the main estimates page. Here you can ONLY help users CREATE NEW ESTIMATES.
You cannot view, edit, or analyze existing estimates from this page.

## Your Capabilities Here
1. **Ask Questions**: Understand what the user wants to estimate
2. **Create New Estimates**: Propose new pricing estimates for confirmation

## CRITICAL: Ask Before You Create
NEVER create an estimate without asking at least these questions:
1. "What project or use case is this estimate for?" (for naming)
2. "Which cloud provider? (AWS, Azure, or GCP)"
3. "Any specific region requirements?" (for compliance/latency)

## Conversation Flow
1. **Greet**: "Hi! I can help you create a new Databricks pricing estimate."
2. **Ask Questions**: Get project name, cloud, and region
3. **Propose**: Use propose_estimate with the gathered info
4. **Guide Next Steps**: After confirmation, tell them to click the estimate to add workloads

## Example Conversation
User: "I need to estimate costs for a data pipeline"
You: "I'd be happy to help! A few quick questions:
1. What would you like to name this estimate? (e.g., 'Q1 Data Pipeline')
2. Which cloud provider are you using - AWS, Azure, or GCP?
3. Any preferred region for compliance or latency reasons?"

User: "Call it 'Marketing ETL', we use AWS in us-east-1"
You: [Use propose_estimate tool with those details]"""

# System prompt for Estimate Detail page (full functionality)
SYSTEM_PROMPT_ESTIMATE_DETAIL = SYSTEM_PROMPT_BASE + """

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
1. How many concurrent users at peak?
2. Query complexity? (simple lookups vs complex aggregations)
3. Usage pattern? (business hours only, or 24/7)

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
- For DBSQL: Ask about concurrent users and query patterns to size the warehouse
- For serverless: No VM types needed, but ask about workload intensity for cost estimates
- For reserved pricing: Only recommend for predictable, long-running workloads
- For spot workers: Only for fault-tolerant batch jobs that can handle interruptions
- ALWAYS use instance types appropriate for the estimate's cloud provider!"""

# For backwards compatibility
SYSTEM_PROMPT = SYSTEM_PROMPT_ESTIMATE_DETAIL


# Tool definitions for Estimates List page (create only)
TOOLS_ESTIMATES_LIST = [
    {
        "name": "propose_estimate",
        "description": "Propose a new estimate configuration for user confirmation. The user will review and confirm before the estimate is created.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name for the estimate (e.g., 'Q1 Data Pipeline', 'ML Platform Costs')"
                },
                "cloud": {
                    "type": "string",
                    "enum": ["aws", "azure", "gcp"],
                    "description": "Cloud provider"
                },
                "region": {
                    "type": "string",
                    "description": "Cloud region (e.g., 'us-east-1', 'eastus', 'us-central1')"
                },
                "description": {
                    "type": "string",
                    "description": "Optional description of the estimate purpose"
                },
                "reason": {
                    "type": "string",
                    "description": "Brief explanation of why this configuration is recommended"
                }
            },
            "required": ["name", "cloud", "region"]
        }
    }
]

# Tool definitions for Estimate Detail page (full functionality)
TOOLS_ESTIMATE_DETAIL = [
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
                    "description": "DBSQL warehouse type: SERVERLESS (auto-scaling), PRO (fixed, Unity Catalog), CLASSIC (fixed, legacy)"
                },
                "dbsql_warehouse_size": {
                    "type": "string",
                    "enum": ["2X-Small", "X-Small", "Small", "Medium", "Large", "X-Large", "2X-Large", "3X-Large", "4X-Large"],
                    "description": "DBSQL warehouse size (2X-Small=4 DBU/hr, Small=12, Medium=24, Large=40, X-Large=80)"
                },
                "dbsql_num_clusters": {
                    "type": "integer",
                    "description": "Number of DBSQL clusters for scaling (1-100)"
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
                    "description": """DETAILED multi-line notes explaining the configuration rationale. Include:
- Configuration rationale: Why each setting was chosen
- Sizing assumptions: How you arrived at the size/scale
- Cost considerations: Any cost optimization choices
- Usage assumptions: What usage patterns you assumed
- Trade-offs: Important trade-offs to be aware of
Use newlines to separate sections for readability."""
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

# For backwards compatibility
ESTIMATE_TOOLS = TOOLS_ESTIMATE_DETAIL


class EstimateAgent:
    """
    AI Agent that helps users create and manage estimates.
    
    Maintains conversation state and handles tool execution.
    Does NOT perform cost calculations - uses costs from context.
    
    Modes:
    - 'estimates_list': For main estimates page, only create new estimates
    - 'estimate_detail': For individual estimate view, full functionality
    """
    
    def __init__(self, claude_client: ClaudeAIClient, mode: str = "estimate_detail"):
        self.client = claude_client
        self.mode = mode
        self.conversation_history: List[Dict[str, Any]] = []
        self.current_estimate: Optional[Dict[str, Any]] = None
        self.current_workloads: List[Dict[str, Any]] = []  # Actual workloads with costs
        self.proposed_workloads: List[Dict[str, Any]] = []  # Pending workload confirmations
        self.proposed_estimate: Optional[Dict[str, Any]] = None  # Pending estimate confirmation
    
    def reset(self):
        """Reset the agent state for a new conversation."""
        self.conversation_history = []
        self.current_estimate = None
        self.current_workloads = []
        self.proposed_workloads = []
        self.proposed_estimate = None
    
    def _trim_conversation_history(self, max_messages: int = 20):
        """
        Trim conversation history to prevent it from growing too long.
        Keeps the most recent messages while preserving tool call/result pairs.
        """
        if len(self.conversation_history) <= max_messages:
            return
        
        # Keep only the most recent messages
        # But be careful not to break tool call/result pairs
        trimmed = self.conversation_history[-max_messages:]
        
        # If the first message is a tool result, we need to remove it
        # as it would reference a tool call that's no longer in history
        while trimmed and isinstance(trimmed[0].get("content"), list):
            # This is likely a tool result - remove it
            trimmed = trimmed[1:]
        
        self.conversation_history = trimmed
        log_info(f"Trimmed conversation history to {len(self.conversation_history)} messages")
    
    def set_mode(self, mode: str):
        """Set the agent mode (affects available tools and system prompt)."""
        self.mode = mode
    
    def _get_system_prompt(self) -> str:
        """Get the appropriate system prompt based on mode."""
        if self.mode == "estimates_list":
            return SYSTEM_PROMPT_ESTIMATES_LIST
        return SYSTEM_PROMPT_ESTIMATE_DETAIL
    
    def _get_tools(self) -> List[Dict[str, Any]]:
        """Get the appropriate tools based on mode."""
        if self.mode == "estimates_list":
            return TOOLS_ESTIMATES_LIST
        return TOOLS_ESTIMATE_DETAIL
    
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
        current_tool = None
        tool_input_json = ""
        
        # Trim conversation history to prevent 400 errors from too-long requests
        self._trim_conversation_history()
        
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
                current_tool = {
                    "id": chunk.get("id"),
                    "name": chunk.get("name"),
                    "arguments": chunk.get("arguments", {})
                }
                tool_calls.append(current_tool)
                
                # Execute tool
                result = await self._execute_tool(
                    current_tool["name"],
                    current_tool["arguments"]
                )
                
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
            # Add assistant response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": full_content,
                "tool_calls": tool_calls
            })
            
            # Execute tools and add results to history
            for tool_call in tool_calls:
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
                
                # Build explanatory notes
                notes_parts.append(f"**Instance Type ({default_instance})**:")
                if cloud == "aws":
                    notes_parts.append("• i3.xlarge chosen for NVMe SSD storage - optimal for Spark shuffle operations")
                elif cloud == "azure":
                    notes_parts.append("• Standard_D4s_v3 provides SSD storage with balanced CPU/memory")
                    notes_parts.append("• D-series VMs are widely available across Azure regions")
                else:
                    notes_parts.append("• n1-standard-4 provides balanced compute for general workloads")
                
                notes_parts.append("")
                notes_parts.append("**Worker Pricing (Spot)**:")
                notes_parts.append("• Spot instances provide 60-90% cost savings")
                notes_parts.append("• Suitable for batch/ETL workloads that can handle interruptions")
                notes_parts.append("• Driver uses on-demand for stability")
                
                if photon_enabled:
                    notes_parts.append("")
                    notes_parts.append("**Photon Enabled**:")
                    notes_parts.append("• 2-3x faster for SQL/DataFrame operations")
                    notes_parts.append("• Native vectorized engine reduces compute time")
                    notes_parts.append("• Often results in lower total cost despite higher DBU rate")
            else:
                notes_parts.append("**Serverless Mode**:")
                notes_parts.append("• No infrastructure management required")
                notes_parts.append("• Automatic scaling based on workload")
                notes_parts.append("• Pay only for actual compute time used")
        
        if wtype == "DLT":
            edition = workload.setdefault("dlt_edition", "PRO")
            notes_parts.append("")
            notes_parts.append(f"**DLT Edition ({edition})**:")
            if edition == "CORE":
                notes_parts.append("• Basic pipeline functionality")
                notes_parts.append("• Good for simple ETL without CDC requirements")
            elif edition == "PRO":
                notes_parts.append("• Includes Change Data Capture (CDC)")
                notes_parts.append("• SCD Type 2 support for historical tracking")
                notes_parts.append("• Enhanced monitoring and data quality")
            else:  # ADVANCED
                notes_parts.append("• Full data quality with expectations")
                notes_parts.append("• Advanced monitoring and observability")
                notes_parts.append("• Best for production-critical pipelines")
        
        if wtype == "DBSQL":
            warehouse_type = workload.setdefault("dbsql_warehouse_type", "SERVERLESS")
            size = workload.setdefault("dbsql_warehouse_size", "Small")
            workload.setdefault("dbsql_num_clusters", 1)
            
            notes_parts.append(f"**Warehouse Type ({warehouse_type})**:")
            if warehouse_type == "SERVERLESS":
                notes_parts.append("• Automatic scaling and instant startup")
                notes_parts.append("• Scales to zero when idle - no idle costs")
                notes_parts.append("• Best for variable query patterns")
            else:
                notes_parts.append("• Fixed capacity for predictable performance")
                notes_parts.append("• Better for constant, high-utilization workloads")
            
            notes_parts.append("")
            notes_parts.append(f"**Warehouse Size ({size})**:")
            size_info = {
                "2X-Small": "4 DBU/hr - Single user or light queries",
                "X-Small": "6 DBU/hr - Small team, simple queries",
                "Small": "12 DBU/hr - Standard BI dashboards",
                "Medium": "24 DBU/hr - Multiple concurrent users",
                "Large": "40 DBU/hr - Heavy analytics workloads",
            }
            notes_parts.append(f"• {size_info.get(size, 'Sized based on expected query complexity')}")
        
        if wtype == "LAKEBASE":
            cu = workload.setdefault("lakebase_cu", 2)
            workload.setdefault("lakebase_ha_nodes", 1)
            
            notes_parts.append(f"**Compute Units ({cu} CU)**:")
            notes_parts.append("• Each CU provides dedicated compute capacity")
            notes_parts.append("• Scale CUs based on concurrent connections and query complexity")
        
        # Combine existing notes with generated explanations
        existing_notes = workload.get("notes", "")
        generated_notes = "\n".join(notes_parts) if notes_parts else ""
        
        if existing_notes and generated_notes:
            workload["notes"] = f"{existing_notes}\n\n---\n\n{generated_notes}"
        elif generated_notes:
            workload["notes"] = f"Created by AI Assistant\n\n{generated_notes}"
        
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


def create_agent(token: str, mode: str = "estimate_detail") -> EstimateAgent:
    """Create a new agent instance with the given token and mode."""
    client = get_claude_client(token)
    return EstimateAgent(client, mode=mode)
