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
- **LAKEBASE**: PostgreSQL-compatible database

## Best Practices to Recommend
- **For Batch ETL**: Use Lakeflow Jobs with Photon enabled, spot instances for workers
- **For Interactive**: All Purpose for development, DBSQL Serverless for production queries
- **For Streaming**: DLT with auto-scaling, consider Core vs Pro vs Advanced editions
- **For ML Inference**: Model Serving with appropriate GPU types
- **For Cost Savings**: Spot instances (up to 90% savings), Serverless (pay-per-use), Reserved capacity

## Important Notes
- All costs shown are from the Lakemeter pricing engine
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
You are viewing a specific estimate with its workloads and calculated costs.

## Your Capabilities Here
1. **Propose Workloads**: Suggest workload configurations based on user requirements
2. **Analyze Estimate**: Review current workloads and suggest optimizations using ACTUAL costs
3. **Provide Recommendations**: Share best practices and cost-saving tips
4. **Answer Questions**: Explain configurations, costs, and trade-offs

## Using Context
- The estimate details and workloads with their ACTUAL calculated costs are provided in the context
- Use these real costs when discussing the estimate, not made-up numbers
- When proposing new workloads, clearly state the configuration and that costs will be calculated after saving

## Conversation Guidelines
1. Review the existing estimate context (name, cloud, region, workloads, costs)
2. Ask clarifying questions about new workload requirements
3. Use the propose_workload tool to suggest configurations
4. User must confirm before workloads are added
5. Use analyze_estimate to provide insights on current costs
6. Be specific about configurations and reference actual costs from context"""

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
        "description": "Propose a new workload configuration for user confirmation. The user will review and confirm before it's added to the estimate. Use this when you have enough information about what the user needs.",
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
                },
                "reason": {
                    "type": "string",
                    "description": "Brief explanation of why this configuration is recommended"
                }
            },
            "required": ["workload_type", "workload_name", "reason"]
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
        self.proposed_workloads = []  # Clear pending proposals on context change
    
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
            "workloads": self.current_workloads,
            "proposed_workloads": self.proposed_workloads,
            "proposed_estimate": self.proposed_estimate
        }
    
    def _build_context(self) -> str:
        """Build context string with current estimate state and actual costs."""
        context = "\n\n## Current Session Context"
        
        if self.current_estimate:
            est = self.current_estimate
            context += f"""

### Estimate Details
- **Name**: {est.get('estimate_name') or est.get('name', 'Unnamed')}
- **Cloud**: {(est.get('cloud') or 'aws').upper()}
- **Region**: {est.get('region', 'Not specified')}
- **Tier**: {est.get('tier', 'PREMIUM')}
- **Status**: {est.get('status', 'draft')}"""
            
            if est.get('customer_name'):
                context += f"\n- **Customer**: {est.get('customer_name')}"
            if est.get('description'):
                context += f"\n- **Description**: {est.get('description')}"
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
        """
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
        """Apply sensible defaults based on workload type."""
        wtype = workload["workload_type"]
        
        # Common defaults
        workload.setdefault("hours_per_month", 730)
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
