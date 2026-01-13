"""AI Model Testing Routes - Compare Claude Sonnet 4.5 vs Opus 4.5."""
import time
import json
import asyncio
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx
import traceback

from app.services.ai_agent import EstimateAgent, SYSTEM_PROMPT, TOOLS
from app.services.ai_client import ClaudeAIClient

router = APIRouter(tags=["AI Testing"])

# Model configurations based on Databricks FMAPI limits
# https://docs.databricks.com/aws/en/machine-learning/foundation-model-apis/limits
MODEL_CONFIGS = {
    "databricks-claude-sonnet-4-5": {
        "name": "Claude Sonnet 4.5",
        "model_id": "databricks-claude-sonnet-4-5",
        "itpm_limit": 50_000,  # Input tokens per minute
        "otpm_limit": 5_000,   # Output tokens per minute
        "description": "Latest Sonnet version - balanced performance and cost"
    },
    "databricks-claude-opus-4-5": {
        "name": "Claude Opus 4.5", 
        "model_id": "databricks-claude-opus-4-5",
        "itpm_limit": 200_000,  # Input tokens per minute
        "otpm_limit": 20_000,   # Output tokens per minute
        "description": "Latest Opus version - highest capability"
    }
}

# Test prompts for different scenarios
TEST_PROMPTS = {
    "short_simple": {
        "name": "Short Simple",
        "description": "Quick response test",
        "prompt": "What is 2 + 2? Answer in one word.",
        "expected_max_tokens": 10
    },
    "medium_analysis": {
        "name": "Medium Analysis",
        "description": "Moderate complexity analysis",
        "prompt": """Analyze the following Databricks pricing scenario and provide recommendations:

A company has:
- 10 data engineers using interactive clusters 8 hours/day
- 3 ETL jobs running 4 hours each daily
- 1 DBSQL warehouse for 20 analysts

What pricing tier and configurations would you recommend? Be concise.""",
        "expected_max_tokens": 500
    },
    "long_complex": {
        "name": "Long Complex",
        "description": "Complex multi-step reasoning",
        "prompt": """You are a Databricks pricing expert. Create a detailed cost optimization plan for:

Company Profile:
- Cloud: AWS, Region: us-east-1
- Current spend: $50,000/month on Databricks
- Workloads: 
  * 50 interactive notebooks (data science team)
  * 100 scheduled ETL jobs
  * 5 ML training pipelines
  * 1 real-time streaming pipeline
  * 3 DBSQL warehouses (BI team)

Requirements:
1. Analyze each workload type
2. Identify optimization opportunities
3. Calculate potential savings
4. Provide implementation timeline
5. List risks and mitigations

Provide a comprehensive response with specific recommendations.""",
        "expected_max_tokens": 2000
    },
    "token_stress": {
        "name": "Token Stress Test",
        "description": "Test maximum token generation",
        "prompt": """Write an extremely detailed technical guide about implementing a data lakehouse architecture on Databricks. 
        
Cover ALL of the following topics in depth:
1. Delta Lake fundamentals and ACID transactions
2. Unity Catalog setup and governance
3. Medallion architecture (bronze, silver, gold)
4. Performance optimization techniques
5. Cost management strategies
6. Security best practices
7. CI/CD pipelines for data engineering
8. Monitoring and observability
9. Disaster recovery planning
10. Migration strategies from legacy systems

For each topic, provide:
- Detailed explanation
- Code examples where applicable
- Best practices
- Common pitfalls to avoid
- Real-world use cases

Make this as comprehensive as possible.""",
        "expected_max_tokens": 4000
    }
}


class TestRequest(BaseModel):
    model_id: str
    test_type: str
    max_tokens: Optional[int] = None
    temperature: float = 0.7


class CompareRequest(BaseModel):
    test_type: str
    max_tokens: Optional[int] = None
    temperature: float = 0.7


@router.get("/models")
async def get_available_models():
    """Get available models and their configurations."""
    return {
        "models": MODEL_CONFIGS,
        "test_prompts": {k: {**v, "prompt": v["prompt"][:200] + "..." if len(v["prompt"]) > 200 else v["prompt"]} 
                        for k, v in TEST_PROMPTS.items()}
    }


@router.get("/test-prompts")
async def get_test_prompts():
    """Get all available test prompts."""
    return {"test_prompts": TEST_PROMPTS}


@router.post("/test-single")
async def test_single_model(request: Request, test_request: TestRequest):
    """Test a single model with a specific prompt."""
    from app.auth.token_manager import TokenManager
    
    if test_request.model_id not in MODEL_CONFIGS:
        raise HTTPException(status_code=400, detail=f"Unknown model: {test_request.model_id}")
    
    if test_request.test_type not in TEST_PROMPTS:
        raise HTTPException(status_code=400, detail=f"Unknown test type: {test_request.test_type}")
    
    model_config = MODEL_CONFIGS[test_request.model_id]
    test_config = TEST_PROMPTS[test_request.test_type]
    
    # Get token
    token_manager = TokenManager()
    token = token_manager.get_token()
    
    if not token:
        raise HTTPException(status_code=401, detail="Failed to get authentication token")
    
    # Determine max_tokens
    max_tokens = test_request.max_tokens or min(test_config["expected_max_tokens"], model_config["otpm_limit"])
    
    # Build request
    endpoint = f"https://fe-vm-lakemeter.cloud.databricks.com/serving-endpoints/{test_request.model_id}/invocations"
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Be concise and accurate."},
        {"role": "user", "content": test_config["prompt"]}
    ]
    
    payload = {
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": test_request.temperature
    }
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Execute request and measure performance
    start_time = time.time()
    first_token_time = None
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(endpoint, json=payload, headers=headers)
            end_time = time.time()
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "model": model_config["name"],
                    "error": f"API error {response.status_code}: {response.text[:500]}",
                    "latency_ms": (end_time - start_time) * 1000
                }
            
            result = response.json()
            
            # Extract usage info
            usage = result.get("usage", {})
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            return {
                "success": True,
                "model": model_config["name"],
                "model_id": test_request.model_id,
                "test_type": test_request.test_type,
                "test_name": test_config["name"],
                "content": content,
                "content_length": len(content),
                "metrics": {
                    "total_latency_ms": round((end_time - start_time) * 1000, 2),
                    "input_tokens": usage.get("prompt_tokens", 0),
                    "output_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                    "tokens_per_second": round(usage.get("completion_tokens", 0) / (end_time - start_time), 2) if (end_time - start_time) > 0 else 0
                },
                "limits": {
                    "itpm_limit": model_config["itpm_limit"],
                    "otpm_limit": model_config["otpm_limit"],
                    "max_tokens_used": max_tokens
                }
            }
            
        except httpx.TimeoutException:
            return {
                "success": False,
                "model": model_config["name"],
                "error": "Request timed out after 120 seconds",
                "latency_ms": 120000
            }
        except Exception as e:
            return {
                "success": False,
                "model": model_config["name"],
                "error": str(e),
                "latency_ms": (time.time() - start_time) * 1000
            }


@router.post("/compare")
async def compare_models(request: Request, compare_request: CompareRequest):
    """Compare both models on the same prompt."""
    from app.auth.token_manager import TokenManager
    
    if compare_request.test_type not in TEST_PROMPTS:
        raise HTTPException(status_code=400, detail=f"Unknown test type: {compare_request.test_type}")
    
    test_config = TEST_PROMPTS[compare_request.test_type]
    
    # Get token
    token_manager = TokenManager()
    token = token_manager.get_token()
    
    if not token:
        raise HTTPException(status_code=401, detail="Failed to get authentication token")
    
    results = {}
    
    for model_id, model_config in MODEL_CONFIGS.items():
        max_tokens = compare_request.max_tokens or min(test_config["expected_max_tokens"], model_config["otpm_limit"])
        
        endpoint = f"https://fe-vm-lakemeter.cloud.databricks.com/serving-endpoints/{model_id}/invocations"
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant. Be concise and accurate."},
            {"role": "user", "content": test_config["prompt"]}
        ]
        
        payload = {
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": compare_request.temperature
        }
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(endpoint, json=payload, headers=headers)
                end_time = time.time()
                
                if response.status_code != 200:
                    results[model_id] = {
                        "success": False,
                        "model": model_config["name"],
                        "error": f"API error {response.status_code}: {response.text[:200]}",
                        "latency_ms": (end_time - start_time) * 1000
                    }
                    continue
                
                result = response.json()
                usage = result.get("usage", {})
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                results[model_id] = {
                    "success": True,
                    "model": model_config["name"],
                    "content": content,
                    "content_length": len(content),
                    "metrics": {
                        "total_latency_ms": round((end_time - start_time) * 1000, 2),
                        "input_tokens": usage.get("prompt_tokens", 0),
                        "output_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0),
                        "tokens_per_second": round(usage.get("completion_tokens", 0) / (end_time - start_time), 2) if (end_time - start_time) > 0 else 0
                    },
                    "limits": {
                        "itpm_limit": model_config["itpm_limit"],
                        "otpm_limit": model_config["otpm_limit"],
                        "max_tokens_used": max_tokens
                    }
                }
                
            except httpx.TimeoutException:
                results[model_id] = {
                    "success": False,
                    "model": model_config["name"],
                    "error": "Request timed out",
                    "latency_ms": 120000
                }
            except Exception as e:
                results[model_id] = {
                    "success": False,
                    "model": model_config["name"],
                    "error": str(e),
                    "latency_ms": (time.time() - start_time) * 1000
                }
    
    # Calculate comparison metrics
    comparison = {}
    if all(r.get("success") for r in results.values()):
        sonnet = results.get("databricks-claude-sonnet-4-5", {})
        opus = results.get("databricks-claude-opus-4-5", {})
        
        sonnet_latency = sonnet.get("metrics", {}).get("total_latency_ms", 0)
        opus_latency = opus.get("metrics", {}).get("total_latency_ms", 0)
        
        comparison = {
            "faster_model": "Sonnet 4.5" if sonnet_latency < opus_latency else "Opus 4.5",
            "latency_difference_ms": abs(sonnet_latency - opus_latency),
            "latency_ratio": round(opus_latency / sonnet_latency, 2) if sonnet_latency > 0 else 0,
            "sonnet_tokens_per_sec": sonnet.get("metrics", {}).get("tokens_per_second", 0),
            "opus_tokens_per_sec": opus.get("metrics", {}).get("tokens_per_second", 0),
            "output_length_difference": abs(
                sonnet.get("content_length", 0) - opus.get("content_length", 0)
            )
        }
    
    return {
        "test_type": compare_request.test_type,
        "test_name": test_config["name"],
        "prompt_preview": test_config["prompt"][:200] + "...",
        "results": results,
        "comparison": comparison
    }


@router.post("/stress-test")
async def stress_test_tokens(request: Request, model_id: str, target_output_tokens: int = 4000):
    """Stress test a model's token generation capacity."""
    from app.auth.token_manager import TokenManager
    
    if model_id not in MODEL_CONFIGS:
        raise HTTPException(status_code=400, detail=f"Unknown model: {model_id}")
    
    model_config = MODEL_CONFIGS[model_id]
    
    # Validate against OTPM limit
    if target_output_tokens > model_config["otpm_limit"]:
        return {
            "warning": f"Target tokens ({target_output_tokens}) exceeds OTPM limit ({model_config['otpm_limit']})",
            "adjusted_target": model_config["otpm_limit"]
        }
    
    token_manager = TokenManager()
    token = token_manager.get_token()
    
    if not token:
        raise HTTPException(status_code=401, detail="Failed to get authentication token")
    
    # Use stress test prompt
    test_config = TEST_PROMPTS["token_stress"]
    
    endpoint = f"https://fe-vm-lakemeter.cloud.databricks.com/serving-endpoints/{model_id}/invocations"
    
    messages = [
        {"role": "system", "content": "You are a technical documentation expert. Provide extremely detailed and comprehensive responses."},
        {"role": "user", "content": test_config["prompt"]}
    ]
    
    payload = {
        "messages": messages,
        "max_tokens": min(target_output_tokens, model_config["otpm_limit"]),
        "temperature": 0.7
    }
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    start_time = time.time()
    
    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            response = await client.post(endpoint, json=payload, headers=headers)
            end_time = time.time()
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "model": model_config["name"],
                    "error": f"API error {response.status_code}: {response.text[:500]}",
                    "latency_ms": (end_time - start_time) * 1000
                }
            
            result = response.json()
            usage = result.get("usage", {})
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            finish_reason = result.get("choices", [{}])[0].get("finish_reason", "unknown")
            
            return {
                "success": True,
                "model": model_config["name"],
                "model_id": model_id,
                "target_output_tokens": target_output_tokens,
                "actual_output_tokens": usage.get("completion_tokens", 0),
                "finish_reason": finish_reason,
                "content_preview": content[:500] + "..." if len(content) > 500 else content,
                "content_length": len(content),
                "metrics": {
                    "total_latency_ms": round((end_time - start_time) * 1000, 2),
                    "total_latency_seconds": round(end_time - start_time, 2),
                    "input_tokens": usage.get("prompt_tokens", 0),
                    "output_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                    "tokens_per_second": round(usage.get("completion_tokens", 0) / (end_time - start_time), 2) if (end_time - start_time) > 0 else 0,
                    "output_token_utilization": round(usage.get("completion_tokens", 0) / target_output_tokens * 100, 1) if target_output_tokens > 0 else 0
                },
                "limits": {
                    "model_itpm_limit": model_config["itpm_limit"],
                    "model_otpm_limit": model_config["otpm_limit"],
                    "tokens_requested": min(target_output_tokens, model_config["otpm_limit"])
                }
            }
            
        except httpx.TimeoutException:
            return {
                "success": False,
                "model": model_config["name"],
                "error": "Request timed out after 180 seconds",
                "latency_ms": 180000
            }
        except Exception as e:
            return {
                "success": False,
                "model": model_config["name"],
                "error": str(e),
                "latency_ms": (time.time() - start_time) * 1000
            }


# ============================================
# AI ASSISTANT TESTING (with full tools/prompts)
# ============================================

# Sample estimate context for testing
SAMPLE_ESTIMATE_CONTEXT = {
    "estimate_id": "test-estimate-001",
    "estimate_name": "AI Test Estimate",
    "cloud": "AWS",
    "region": "us-east-1",
    "tier": "PREMIUM"
}

SAMPLE_WORKLOADS = [
    {
        "line_item_id": "test-workload-001",
        "workload_name": "ETL Pipeline",
        "workload_type": "JOBS",
        "serverless_enabled": False,
        "photon_enabled": True,
        "driver_node_type": "m5.xlarge",
        "worker_node_type": "m5.xlarge",
        "num_workers": 4,
        "hours_per_month": 200,
        "total_cost": 1500.00
    },
    {
        "line_item_id": "test-workload-002",
        "workload_name": "Analytics Warehouse",
        "workload_type": "DBSQL",
        "dbsql_warehouse_type": "PRO",
        "dbsql_warehouse_size": "Medium",
        "hours_per_month": 400,
        "total_cost": 2800.00
    },
    {
        "line_item_id": "test-workload-003",
        "workload_name": "Dev Cluster",
        "workload_type": "ALL_PURPOSE",
        "serverless_enabled": False,
        "photon_enabled": False,
        "driver_node_type": "m5.large",
        "worker_node_type": "m5.large",
        "num_workers": 2,
        "hours_per_month": 160,
        "total_cost": 800.00
    }
]

# AI Assistant test prompts
AI_ASSISTANT_TEST_PROMPTS = {
    "analyze_costs": {
        "name": "Analyze Costs",
        "description": "Ask AI to analyze current workloads and suggest optimizations",
        "prompt": "Analyze my workloads and suggest specific optimizations to reduce costs."
    },
    "get_summary": {
        "name": "Get Summary",
        "description": "Ask AI to provide estimate summary",
        "prompt": "Give me a summary of my current estimate."
    },
    "add_workload": {
        "name": "Add Workload",
        "description": "Ask AI to propose a new workload",
        "prompt": "I need to add a new ETL job that processes 100GB of data daily. It runs once per day during business hours and takes about 2 hours."
    },
    "pricing_question": {
        "name": "Pricing Question",
        "description": "Ask a question about Databricks pricing",
        "prompt": "What's the difference between serverless and classic compute for jobs? Which is more cost effective?"
    },
    "complex_scenario": {
        "name": "Complex Scenario",
        "description": "Complex multi-part request",
        "prompt": """I have 3 requirements:
1. I need a DBSQL warehouse for 20 analysts doing ad-hoc queries on 500GB of data
2. An ML training pipeline that runs weekly for model retraining
3. A real-time streaming job that needs to run 24/7

What configurations would you recommend for each? Consider cost optimization."""
    }
}


class AIAssistantTestRequest(BaseModel):
    model_id: str
    test_type: str
    custom_prompt: Optional[str] = None
    include_sample_context: bool = True


class AIAssistantCompareRequest(BaseModel):
    test_type: str
    custom_prompt: Optional[str] = None


@router.get("/assistant/prompts")
async def get_assistant_test_prompts():
    """Get available AI Assistant test prompts."""
    return {
        "prompts": AI_ASSISTANT_TEST_PROMPTS,
        "sample_context": {
            "estimate": SAMPLE_ESTIMATE_CONTEXT,
            "workloads_count": len(SAMPLE_WORKLOADS),
            "total_cost": sum(w.get("total_cost", 0) for w in SAMPLE_WORKLOADS)
        },
        "system_prompt_preview": SYSTEM_PROMPT[:500] + "...",
        "tools_count": len(TOOLS)
    }


@router.post("/assistant/test")
async def test_ai_assistant(request: Request, test_request: AIAssistantTestRequest):
    """Test the AI Assistant with full tools and system prompt."""
    from app.auth.token_manager import TokenManager
    
    if test_request.model_id not in MODEL_CONFIGS:
        raise HTTPException(status_code=400, detail=f"Unknown model: {test_request.model_id}")
    
    model_config = MODEL_CONFIGS[test_request.model_id]
    
    # Get the prompt
    if test_request.custom_prompt:
        prompt = test_request.custom_prompt
        test_name = "Custom Prompt"
    elif test_request.test_type in AI_ASSISTANT_TEST_PROMPTS:
        prompt = AI_ASSISTANT_TEST_PROMPTS[test_request.test_type]["prompt"]
        test_name = AI_ASSISTANT_TEST_PROMPTS[test_request.test_type]["name"]
    else:
        raise HTTPException(status_code=400, detail=f"Unknown test type: {test_request.test_type}")
    
    # Get token
    token_manager = TokenManager()
    token = token_manager.get_token()
    
    if not token:
        raise HTTPException(status_code=401, detail="Failed to get authentication token")
    
    start_time = time.time()
    
    try:
        # Create AI client with specified model
        client = ClaudeAIClient(
            token=token,
            model=test_request.model_id
        )
        
        # Create agent
        agent = EstimateAgent(client)
        
        # Set context if requested
        if test_request.include_sample_context:
            agent.set_context(SAMPLE_ESTIMATE_CONTEXT, SAMPLE_WORKLOADS)
        
        # Get response (non-streaming for testing)
        result = await agent.chat(prompt)
        
        end_time = time.time()
        
        # Collect tool calls made
        tool_calls_made = []
        if agent.conversation_history:
            for msg in agent.conversation_history:
                if msg.get("role") == "assistant" and "[Actions:" in msg.get("content", ""):
                    content = msg.get("content", "")
                    if "[Actions:" in content:
                        actions_part = content.split("[Actions:")[1].split("]")[0]
                        tool_calls_made.append(actions_part.strip())
        
        return {
            "success": True,
            "model": model_config["name"],
            "model_id": test_request.model_id,
            "test_type": test_request.test_type,
            "test_name": test_name,
            "prompt": prompt,
            "response": result.get("content", ""),
            "response_length": len(result.get("content", "")),
            "tool_calls_made": tool_calls_made,
            "proposed_workloads": len(agent.proposed_workloads),
            "metrics": {
                "total_latency_ms": round((end_time - start_time) * 1000, 2),
                "total_latency_seconds": round(end_time - start_time, 2)
            },
            "context": {
                "estimate_loaded": agent.current_estimate is not None,
                "workloads_count": len(agent.current_workloads) if agent.current_workloads else 0,
                "conversation_length": len(agent.conversation_history)
            },
            "limits": {
                "model_itpm_limit": model_config["itpm_limit"],
                "model_otpm_limit": model_config["otpm_limit"]
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "model": model_config["name"],
            "error": str(e),
            "traceback": traceback.format_exc(),
            "latency_ms": (time.time() - start_time) * 1000
        }


@router.post("/assistant/compare")
async def compare_ai_assistant_models(request: Request, compare_request: AIAssistantCompareRequest):
    """Compare both models as AI Assistant backends."""
    from app.auth.token_manager import TokenManager
    
    try:
        # Get the prompt
        if compare_request.custom_prompt:
            prompt = compare_request.custom_prompt
            test_name = "Custom Prompt"
        elif compare_request.test_type in AI_ASSISTANT_TEST_PROMPTS:
            prompt = AI_ASSISTANT_TEST_PROMPTS[compare_request.test_type]["prompt"]
            test_name = AI_ASSISTANT_TEST_PROMPTS[compare_request.test_type]["name"]
        else:
            return {
                "error": f"Unknown test type: {compare_request.test_type}",
                "results": {},
                "comparison": {}
            }
        
        # Get token
        token_manager = TokenManager()
        token = token_manager.get_token()
        
        if not token:
            return {
                "error": "Failed to get authentication token",
                "results": {},
                "comparison": {}
            }
        
        results = {}
        
        for model_id, model_config in MODEL_CONFIGS.items():
            start_time = time.time()
            try:
                # Create AI client with specified model
                client = ClaudeAIClient(
                    token=token,
                    model=model_id
                )
                
                # Create agent
                agent = EstimateAgent(client)
                agent.set_context(SAMPLE_ESTIMATE_CONTEXT, SAMPLE_WORKLOADS)
                
                # Get response
                result = await agent.chat(prompt)
                
                end_time = time.time()
                
                # Collect tool calls
                tool_calls_made = []
                for msg in agent.conversation_history:
                    if msg.get("role") == "assistant" and "[Actions:" in msg.get("content", ""):
                        content = msg.get("content", "")
                        if "[Actions:" in content:
                            actions_part = content.split("[Actions:")[1].split("]")[0]
                            tool_calls_made.append(actions_part.strip())
                
                results[model_id] = {
                    "success": True,
                    "model": model_config["name"],
                    "response": result.get("content", ""),
                    "response_length": len(result.get("content", "")),
                    "tool_calls_made": tool_calls_made,
                    "proposed_workloads": len(agent.proposed_workloads),
                    "metrics": {
                        "total_latency_ms": round((end_time - start_time) * 1000, 2),
                        "total_latency_seconds": round(end_time - start_time, 2)
                    }
                }
                
            except Exception as e:
                results[model_id] = {
                    "success": False,
                    "model": model_config["name"],
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }
        
        # Calculate comparison
        comparison = {}
        if results and all(r.get("success") for r in results.values()):
            sonnet = results.get("databricks-claude-sonnet-4-5", {})
            opus = results.get("databricks-claude-opus-4-5", {})
            
            sonnet_latency = sonnet.get("metrics", {}).get("total_latency_ms", 0)
            opus_latency = opus.get("metrics", {}).get("total_latency_ms", 0)
            
            comparison = {
                "faster_model": "Sonnet 4.5" if sonnet_latency < opus_latency else "Opus 4.5",
                "latency_difference_ms": abs(sonnet_latency - opus_latency),
                "latency_ratio": round(opus_latency / sonnet_latency, 2) if sonnet_latency > 0 else 0,
                "sonnet_response_length": sonnet.get("response_length", 0),
                "opus_response_length": opus.get("response_length", 0),
                "sonnet_tools_used": len(sonnet.get("tool_calls_made", [])),
                "opus_tools_used": len(opus.get("tool_calls_made", []))
            }
        
        return {
            "test_type": compare_request.test_type,
            "test_name": test_name,
            "prompt": prompt,
            "results": results,
            "comparison": comparison,
            "sample_context": {
                "estimate": SAMPLE_ESTIMATE_CONTEXT,
                "workloads_count": len(SAMPLE_WORKLOADS)
            }
        }
    except Exception as e:
        return {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "results": {},
            "comparison": {}
        }


@router.get("/assistant/system-prompt")
async def get_system_prompt():
    """Get the full system prompt used by AI Assistant."""
    return {
        "system_prompt": SYSTEM_PROMPT,
        "system_prompt_length": len(SYSTEM_PROMPT),
        "tools": [{"name": t["name"], "description": t["description"], "parameters": t.get("input_schema", {})} for t in TOOLS],
        "tools_count": len(TOOLS)
    }
