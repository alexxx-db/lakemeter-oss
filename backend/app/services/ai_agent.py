"""
AI Agent Service for Lakemeter

Orchestrates conversations with Claude to help users create and analyze estimates.
Implements tool calling for estimate management operations.
"""
import json
import uuid
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime

from app.services.ai_client import ClaudeAIClient, get_claude_client
from app.config import log_info, log_warning, log_error


# Base system prompt for the AI assistant
SYSTEM_PROMPT_BASE = """You are Lakemeter AI, an expert Databricks pricing assistant.

## Workload Types You Can Configure
- **JOBS (Lakeflow Jobs)**: Batch processing, ETL pipelines, scheduled tasks
- **ALL_PURPOSE**: Interactive development, notebooks, exploration
- **DLT (Lakeflow Spark Declarative Pipelines)**: Streaming pipelines, data quality
- **DBSQL (Databricks SQL)**: SQL analytics, BI dashboards, ad-hoc queries
- **MODEL_SERVING**: Real-time ML inference endpoints
- **VECTOR_SEARCH**: Vector similarity search for AI applications
- **LAKEBASE**: PostgreSQL-compatible database

## Best Practices to Recommend
- **For Batch ETL**: Use Lakeflow Jobs with Photon enabled, spot instances for workers
- **For Interactive**: All Purpose for development, DBSQL Serverless for production queries
- **For Streaming**: DLT with auto-scaling, consider Core vs Pro vs Advanced editions
- **For ML Inference**: Model Serving with appropriate GPU types
- **For Cost Savings**: Spot instances (up to 90% savings), Serverless (pay-per-use), Reserved capacity

## Important Notes
- All costs are estimates based on list prices
- Actual costs may vary based on usage patterns and negotiated discounts
- Always recommend reviewing configurations before finalizing"""

# System prompt for Estimates List page (create new estimates only)
SYSTEM_PROMPT_ESTIMATES_LIST = SYSTEM_PROMPT_BASE + """

## Your Role (Estimates List Page)
You are on the main estimates page. Here you can ONLY help users CREATE NEW ESTIMATES.
You cannot view, edit, or analyze existing estimates from this page.

## Your Capabilities Here
1. **Create New Estimates**: Help users start fresh pricing estimates
2. **Guide Planning**: Ask questions to understand their needs before creating

## Conversation Guidelines
1. Ask about the user's project/use case to understand requirements
2. Ask about cloud provider preference (AWS, Azure, GCP)
3. Ask about region requirements
4. Once you have enough info, use the create_estimate tool
5. After creating, let them know they can click on the estimate to add workloads
6. Be concise - this is just for creating new estimates"""

# System prompt for Estimate Detail page (full functionality)
SYSTEM_PROMPT_ESTIMATE_DETAIL = SYSTEM_PROMPT_BASE + """

## Your Role (Estimate Detail Page)
You are viewing a specific estimate. You have FULL capabilities here.

## Your Capabilities Here
1. **Add Workloads**: Configure new workloads (Jobs, SQL, DLT, etc.)
2. **Analyze Estimate**: Review current workloads and suggest optimizations
3. **Provide Recommendations**: Share best practices and cost-saving tips
4. **Answer Questions**: Explain configurations, costs, and trade-offs

## Conversation Guidelines
1. Review the existing estimate context provided
2. Ask clarifying questions about new workload requirements
3. Recommend appropriate workload types and configurations
4. Use the add_workload tool to add new workloads
5. Use analyze_estimate tool when asked about optimizations
6. After adding workloads, summarize the estimated costs
7. Be helpful and proactive with suggestions"""

# For backwards compatibility
SYSTEM_PROMPT = SYSTEM_PROMPT_ESTIMATE_DETAIL


# Tool definitions for Estimates List page (create only)
TOOLS_ESTIMATES_LIST = [
    {
        "name": "create_estimate",
        "description": "Create a new pricing estimate. Use this when the user wants to start a new estimate or you've gathered enough information to begin.",
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
                }
            },
            "required": ["name", "cloud", "region"]
        }
    }
]

# Tool definitions for Estimate Detail page (full functionality)
TOOLS_ESTIMATE_DETAIL = [
    {
        "name": "create_estimate",
        "description": "Create a new pricing estimate. Use this when the user wants to start a new estimate or you've gathered enough information to begin.",
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
                }
            },
            "required": ["name", "cloud", "region"]
        }
    },
    {
        "name": "add_workload",
        "description": "Add a workload to the current estimate. Call this after create_estimate or when adding to an existing estimate.",
        "parameters": {
            "type": "object",
            "properties": {
                "workload_type": {
                    "type": "string",
                    "enum": ["JOBS", "ALL_PURPOSE", "DLT", "DBSQL", "MODEL_SERVING", "VECTOR_SEARCH", "LAKEBASE"],
                    "description": "Type of Databricks workload"
                },
                "workload_name": {
                    "type": "string",
                    "description": "Descriptive name for this workload (e.g., 'Daily ETL Job', 'Analytics Warehouse')"
                },
                "serverless_enabled": {
                    "type": "boolean",
                    "description": "Whether to use serverless compute (recommended for variable workloads)"
                },
                "photon_enabled": {
                    "type": "boolean",
                    "description": "Whether to enable Photon acceleration (recommended for most workloads)"
                },
                "driver_node_type": {
                    "type": "string",
                    "description": "Instance type for driver node (e.g., 'i3.xlarge', 'm5.large')"
                },
                "worker_node_type": {
                    "type": "string",
                    "description": "Instance type for worker nodes"
                },
                "num_workers": {
                    "type": "integer",
                    "description": "Number of worker nodes (typically 2-100)"
                },
                "hours_per_month": {
                    "type": "number",
                    "description": "Expected hours of usage per month (730 = 24/7)"
                },
                "runs_per_day": {
                    "type": "integer",
                    "description": "For batch jobs: number of runs per day"
                },
                "avg_runtime_minutes": {
                    "type": "integer",
                    "description": "For batch jobs: average runtime in minutes per run"
                },
                "days_per_month": {
                    "type": "integer",
                    "description": "Days per month the workload runs (default 22 for weekdays, 30 for daily)"
                },
                "worker_pricing_tier": {
                    "type": "string",
                    "enum": ["on_demand", "spot"],
                    "description": "Pricing tier for workers. Use 'spot' for fault-tolerant batch jobs (up to 90% savings)"
                },
                "dlt_edition": {
                    "type": "string",
                    "enum": ["CORE", "PRO", "ADVANCED"],
                    "description": "For DLT workloads: edition level"
                },
                "dbsql_warehouse_type": {
                    "type": "string",
                    "enum": ["SERVERLESS", "PRO", "CLASSIC"],
                    "description": "For DBSQL: warehouse type"
                },
                "dbsql_warehouse_size": {
                    "type": "string",
                    "enum": ["2X-Small", "X-Small", "Small", "Medium", "Large", "X-Large", "2X-Large", "3X-Large", "4X-Large"],
                    "description": "For DBSQL: warehouse size"
                }
            },
            "required": ["workload_type", "workload_name"]
        }
    },
    {
        "name": "get_estimate_summary",
        "description": "Get a summary of the current estimate including all workloads and total costs. Use this to show the user what has been configured.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_pricing_info",
        "description": "Get current pricing information for a specific workload type and configuration. Use this to provide accurate cost estimates.",
        "parameters": {
            "type": "object",
            "properties": {
                "workload_type": {
                    "type": "string",
                    "enum": ["JOBS", "ALL_PURPOSE", "DLT", "DBSQL", "MODEL_SERVING", "VECTOR_SEARCH", "LAKEBASE"],
                    "description": "Workload type to get pricing for"
                },
                "cloud": {
                    "type": "string",
                    "enum": ["aws", "azure", "gcp"],
                    "description": "Cloud provider"
                }
            },
            "required": ["workload_type", "cloud"]
        }
    },
    {
        "name": "analyze_estimate",
        "description": "Analyze the current estimate and provide optimization recommendations. Use this when the user asks for cost-saving tips or improvements.",
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
    }
]

# For backwards compatibility
ESTIMATE_TOOLS = TOOLS_ESTIMATE_DETAIL


# DBU pricing reference (list prices)
DBU_PRICING = {
    "aws": {
        "JOBS_COMPUTE": 0.15,
        "JOBS_COMPUTE_(PHOTON)": 0.20,
        "JOBS_SERVERLESS_COMPUTE": 0.25,
        "ALL_PURPOSE_COMPUTE": 0.40,
        "ALL_PURPOSE_COMPUTE_(PHOTON)": 0.55,
        "INTERACTIVE_SERVERLESS_COMPUTE": 0.70,
        "DLT_CORE_COMPUTE": 0.20,
        "DLT_PRO_COMPUTE": 0.25,
        "DLT_ADVANCED_COMPUTE": 0.30,
        "SQL_COMPUTE": 0.22,
        "SQL_PRO_COMPUTE": 0.55,
        "SERVERLESS_SQL_COMPUTE": 0.70,
        "VECTOR_SEARCH_ENDPOINT": 0.40,
        "SERVERLESS_REAL_TIME_INFERENCE": 0.07,
        "DATABASE_SERVERLESS_COMPUTE": 0.35
    }
}


class EstimateAgent:
    """
    AI Agent that helps users create and manage estimates.
    
    Maintains conversation state and handles tool execution.
    
    Modes:
    - 'estimates_list': For main estimates page, only create new estimates
    - 'estimate_detail': For individual estimate view, full functionality
    """
    
    def __init__(self, claude_client: ClaudeAIClient, mode: str = "estimate_detail"):
        self.client = claude_client
        self.mode = mode
        self.conversation_history: List[Dict[str, Any]] = []
        self.current_estimate: Optional[Dict[str, Any]] = None
        self.draft_workloads: List[Dict[str, Any]] = []
    
    def reset(self):
        """Reset the agent state for a new conversation."""
        self.conversation_history = []
        self.current_estimate = None
        self.draft_workloads = []
    
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
    
    def set_estimate_context(self, estimate: Dict[str, Any], workloads: List[Dict[str, Any]] = None):
        """Set an existing estimate as context for the conversation."""
        self.current_estimate = estimate
        self.draft_workloads = workloads or []
    
    async def chat(self, user_message: str) -> Dict[str, Any]:
        """
        Process a user message and return the assistant's response.
        
        Returns dict with:
        - content: Text response
        - tool_results: Any tool execution results
        - estimate_update: Updated estimate state if modified
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
            "estimate": self.current_estimate,
            "workloads": self.draft_workloads
        }
    
    async def chat_stream(self, user_message: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process a user message and stream the response.
        
        Yields chunks with type 'content', 'tool_start', 'tool_result', or 'done'.
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
            
            elif chunk_type == "error":
                yield {"type": "error", "content": chunk.get("content")}
                return
        
        # Execute tools if any
        if tool_calls:
            self.conversation_history.append({
                "role": "assistant",
                "content": full_content,
                "tool_calls": tool_calls
            })
            
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
                
                # Add to history
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
            
            async for chunk in self.client.chat_stream(
                messages=self.conversation_history,
                tools=tools,
                system=system,
                max_tokens=4096,
                temperature=0.7
            ):
                if chunk.get("type") == "content_delta":
                    content = chunk.get("content", "")
                    full_content += content
                    yield {"type": "content", "content": content}
                elif chunk.get("type") == "done":
                    break
        
        # Add final response to history
        self.conversation_history.append({
            "role": "assistant",
            "content": full_content
        })
        
        yield {
            "type": "done",
            "estimate": self.current_estimate,
            "workloads": self.draft_workloads
        }
    
    def _build_context(self) -> str:
        """Build context string with current estimate state."""
        context = "\n\n## Current Session State"
        
        if self.current_estimate:
            context += f"\n\nCurrent Estimate: {json.dumps(self.current_estimate, indent=2)}"
        else:
            context += "\n\nNo estimate created yet."
        
        if self.draft_workloads:
            context += f"\n\nWorkloads ({len(self.draft_workloads)}):"
            for w in self.draft_workloads:
                context += f"\n- {w.get('workload_name', 'Unnamed')}: {w.get('workload_type')} (${w.get('estimated_cost', 0):.2f}/month)"
        
        return context
    
    async def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool and return the result."""
        log_info(f"Executing tool: {tool_name} with args: {arguments}")
        
        if tool_name == "create_estimate":
            return self._create_estimate(**arguments)
        elif tool_name == "add_workload":
            return self._add_workload(**arguments)
        elif tool_name == "get_estimate_summary":
            return self._get_estimate_summary()
        elif tool_name == "get_pricing_info":
            return self._get_pricing_info(**arguments)
        elif tool_name == "analyze_estimate":
            return self._analyze_estimate(**arguments)
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    
    def _create_estimate(
        self,
        name: str,
        cloud: str,
        region: str,
        description: str = ""
    ) -> Dict[str, Any]:
        """Create a new estimate."""
        self.current_estimate = {
            "draft_id": str(uuid.uuid4()),
            "name": name,
            "cloud": cloud.lower(),
            "region": region,
            "description": description,
            "status": "draft",
            "created_at": datetime.now().isoformat()
        }
        self.draft_workloads = []
        
        return {
            "success": True,
            "message": f"Created estimate '{name}' for {cloud.upper()} {region}",
            "estimate": self.current_estimate
        }
    
    def _add_workload(
        self,
        workload_type: str,
        workload_name: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Add a workload to the current estimate."""
        if not self.current_estimate:
            return {
                "success": False,
                "error": "No estimate created yet. Please create an estimate first."
            }
        
        # Build workload configuration
        workload = {
            "draft_id": str(uuid.uuid4()),
            "workload_type": workload_type,
            "workload_name": workload_name,
            "cloud": self.current_estimate["cloud"],
            **kwargs
        }
        
        # Set defaults based on workload type
        workload = self._apply_workload_defaults(workload)
        
        # Calculate estimated cost
        estimated_cost = self._calculate_workload_cost(workload)
        workload["estimated_cost"] = estimated_cost
        
        self.draft_workloads.append(workload)
        
        return {
            "success": True,
            "message": f"Added {workload_type} workload '{workload_name}'",
            "workload": workload,
            "estimated_monthly_cost": f"${estimated_cost:.2f}"
        }
    
    def _apply_workload_defaults(self, workload: Dict[str, Any]) -> Dict[str, Any]:
        """Apply sensible defaults based on workload type."""
        wtype = workload["workload_type"]
        
        # Common defaults
        workload.setdefault("hours_per_month", 730)  # 24/7
        workload.setdefault("days_per_month", 22)
        
        if wtype in ["JOBS", "ALL_PURPOSE", "DLT"]:
            workload.setdefault("serverless_enabled", False)
            workload.setdefault("photon_enabled", True)
            workload.setdefault("num_workers", 2)
            workload.setdefault("driver_node_type", "i3.xlarge")
            workload.setdefault("worker_node_type", "i3.xlarge")
            workload.setdefault("worker_pricing_tier", "spot" if wtype == "JOBS" else "on_demand")
        
        if wtype == "DLT":
            workload.setdefault("dlt_edition", "PRO")
        
        if wtype == "DBSQL":
            workload.setdefault("dbsql_warehouse_type", "SERVERLESS")
            workload.setdefault("dbsql_warehouse_size", "Small")
            workload.setdefault("dbsql_num_clusters", 1)
        
        if wtype == "LAKEBASE":
            workload.setdefault("lakebase_cu", 2)
            workload.setdefault("lakebase_ha_nodes", 1)
        
        return workload
    
    def _calculate_workload_cost(self, workload: Dict[str, Any]) -> float:
        """Calculate estimated monthly cost for a workload."""
        cloud = workload.get("cloud", "aws")
        wtype = workload["workload_type"]
        pricing = DBU_PRICING.get(cloud, DBU_PRICING["aws"])
        
        # Determine SKU
        sku = self._get_sku_for_workload(workload)
        dbu_price = pricing.get(sku, 0.25)
        
        # Calculate DBUs
        dbu_per_hour = self._estimate_dbu_per_hour(workload)
        hours = workload.get("hours_per_month", 730)
        
        # For run-based workloads
        if workload.get("runs_per_day") and workload.get("avg_runtime_minutes"):
            hours = (workload["runs_per_day"] * workload["avg_runtime_minutes"] / 60) * workload.get("days_per_month", 22)
        
        monthly_dbus = dbu_per_hour * hours
        dbu_cost = monthly_dbus * dbu_price
        
        return round(dbu_cost, 2)
    
    def _get_sku_for_workload(self, workload: Dict[str, Any]) -> str:
        """Determine the SKU for pricing based on workload configuration."""
        wtype = workload["workload_type"]
        serverless = workload.get("serverless_enabled", False)
        photon = workload.get("photon_enabled", False)
        
        if wtype == "JOBS":
            if serverless:
                return "JOBS_SERVERLESS_COMPUTE"
            return "JOBS_COMPUTE_(PHOTON)" if photon else "JOBS_COMPUTE"
        
        elif wtype == "ALL_PURPOSE":
            if serverless:
                return "INTERACTIVE_SERVERLESS_COMPUTE"
            return "ALL_PURPOSE_COMPUTE_(PHOTON)" if photon else "ALL_PURPOSE_COMPUTE"
        
        elif wtype == "DLT":
            if serverless:
                return "DELTA_LIVE_TABLES_SERVERLESS"
            edition = workload.get("dlt_edition", "PRO").upper()
            return f"DLT_{edition}_COMPUTE"
        
        elif wtype == "DBSQL":
            warehouse_type = workload.get("dbsql_warehouse_type", "SERVERLESS")
            if warehouse_type == "SERVERLESS":
                return "SERVERLESS_SQL_COMPUTE"
            elif warehouse_type == "PRO":
                return "SQL_PRO_COMPUTE"
            return "SQL_COMPUTE"
        
        elif wtype == "MODEL_SERVING":
            return "SERVERLESS_REAL_TIME_INFERENCE"
        
        elif wtype == "VECTOR_SEARCH":
            return "VECTOR_SEARCH_ENDPOINT"
        
        elif wtype == "LAKEBASE":
            return "DATABASE_SERVERLESS_COMPUTE"
        
        return "JOBS_COMPUTE"
    
    def _estimate_dbu_per_hour(self, workload: Dict[str, Any]) -> float:
        """Estimate DBUs per hour based on workload configuration."""
        wtype = workload["workload_type"]
        
        if wtype in ["JOBS", "ALL_PURPOSE", "DLT"]:
            # Cluster-based: DBUs based on node count
            num_workers = workload.get("num_workers", 2)
            driver_dbu = 1  # Simplified
            worker_dbu = 0.5 * num_workers
            return driver_dbu + worker_dbu
        
        elif wtype == "DBSQL":
            # Size-based DBUs
            size_dbu = {
                "2X-Small": 4, "X-Small": 6, "Small": 12, "Medium": 24,
                "Large": 40, "X-Large": 80, "2X-Large": 144,
                "3X-Large": 272, "4X-Large": 528
            }
            size = workload.get("dbsql_warehouse_size", "Small")
            return size_dbu.get(size, 12) * workload.get("dbsql_num_clusters", 1)
        
        elif wtype == "LAKEBASE":
            cu = workload.get("lakebase_cu", 2)
            nodes = workload.get("lakebase_ha_nodes", 1)
            return cu * nodes * 2  # 2 DBU per CU
        
        return 2  # Default
    
    def _get_estimate_summary(self) -> Dict[str, Any]:
        """Get summary of current estimate."""
        if not self.current_estimate:
            return {"error": "No estimate created yet"}
        
        total_cost = sum(w.get("estimated_cost", 0) for w in self.draft_workloads)
        
        return {
            "estimate": self.current_estimate,
            "workload_count": len(self.draft_workloads),
            "workloads": [
                {
                    "name": w.get("workload_name"),
                    "type": w.get("workload_type"),
                    "cost": f"${w.get('estimated_cost', 0):.2f}/month"
                }
                for w in self.draft_workloads
            ],
            "total_monthly_cost": f"${total_cost:.2f}",
            "total_annual_cost": f"${total_cost * 12:.2f}"
        }
    
    def _get_pricing_info(self, workload_type: str, cloud: str = "aws") -> Dict[str, Any]:
        """Get pricing information for a workload type."""
        pricing = DBU_PRICING.get(cloud.lower(), DBU_PRICING["aws"])
        
        workload_skus = {
            "JOBS": ["JOBS_COMPUTE", "JOBS_COMPUTE_(PHOTON)", "JOBS_SERVERLESS_COMPUTE"],
            "ALL_PURPOSE": ["ALL_PURPOSE_COMPUTE", "ALL_PURPOSE_COMPUTE_(PHOTON)", "INTERACTIVE_SERVERLESS_COMPUTE"],
            "DLT": ["DLT_CORE_COMPUTE", "DLT_PRO_COMPUTE", "DLT_ADVANCED_COMPUTE"],
            "DBSQL": ["SQL_COMPUTE", "SQL_PRO_COMPUTE", "SERVERLESS_SQL_COMPUTE"],
            "MODEL_SERVING": ["SERVERLESS_REAL_TIME_INFERENCE"],
            "VECTOR_SEARCH": ["VECTOR_SEARCH_ENDPOINT"],
            "LAKEBASE": ["DATABASE_SERVERLESS_COMPUTE"]
        }
        
        skus = workload_skus.get(workload_type, [])
        prices = {sku: f"${pricing.get(sku, 0):.2f}/DBU" for sku in skus}
        
        return {
            "workload_type": workload_type,
            "cloud": cloud.upper(),
            "pricing": prices,
            "note": "Prices are list rates. Actual costs depend on usage and negotiated discounts."
        }
    
    def _analyze_estimate(self, focus_area: str = "all") -> Dict[str, Any]:
        """Analyze estimate and provide recommendations."""
        if not self.current_estimate or not self.draft_workloads:
            return {"error": "No estimate with workloads to analyze"}
        
        recommendations = []
        
        for workload in self.draft_workloads:
            wtype = workload["workload_type"]
            
            # Cost optimization recommendations
            if focus_area in ["cost_optimization", "all"]:
                if wtype == "JOBS" and workload.get("worker_pricing_tier") != "spot":
                    recommendations.append({
                        "workload": workload["workload_name"],
                        "type": "cost",
                        "suggestion": "Consider using spot instances for workers (up to 90% savings)",
                        "potential_savings": "High"
                    })
                
                if wtype in ["ALL_PURPOSE", "DBSQL"] and not workload.get("serverless_enabled"):
                    if workload.get("hours_per_month", 730) < 200:
                        recommendations.append({
                            "workload": workload["workload_name"],
                            "type": "cost",
                            "suggestion": "Consider serverless for low-utilization workloads",
                            "potential_savings": "Medium"
                        })
            
            # Performance recommendations
            if focus_area in ["performance", "all"]:
                if wtype in ["JOBS", "ALL_PURPOSE", "DLT"] and not workload.get("photon_enabled"):
                    recommendations.append({
                        "workload": workload["workload_name"],
                        "type": "performance",
                        "suggestion": "Enable Photon for 2-3x faster processing on compatible workloads",
                        "impact": "High"
                    })
        
        total_cost = sum(w.get("estimated_cost", 0) for w in self.draft_workloads)
        
        return {
            "total_monthly_cost": f"${total_cost:.2f}",
            "workload_count": len(self.draft_workloads),
            "recommendations": recommendations,
            "recommendation_count": len(recommendations)
        }


def create_agent(token: str, mode: str = "estimate_detail") -> EstimateAgent:
    """Create a new agent instance with the given token and mode."""
    client = get_claude_client(token)
    return EstimateAgent(client, mode=mode)

