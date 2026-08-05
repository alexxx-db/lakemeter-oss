"""
Chat API Routes for AI Assistant

Provides endpoints for conversing with the AI assistant to create and manage estimates.
Conversations are owned by the authenticated SSO user and persisted in Lakebase,
with an in-process cache for hot agents.
"""
import json
import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.databricks_auth import get_current_user
from app.models import User
from app.external_api import get_model_serving_token
from app.services.ai_agent import create_agent, EstimateAgent
from app.services import conversation_store
from app.config import log_error


router = APIRouter(prefix="/chat", tags=["AI Assistant"])


class ChatMessage(BaseModel):
    """A single chat message."""
    role: str  # 'user' or 'assistant'
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None


class ChatRequest(BaseModel):
    """Request to send a message to the AI assistant."""
    message: str
    conversation_id: Optional[str] = None
    estimate_context: Optional[Dict[str, Any]] = None
    workloads_context: Optional[List[Dict[str, Any]]] = None
    mode: str = "estimate"  # 'estimate' for full features, 'home' for Q&A only
    stream: bool = True


class ChatResponse(BaseModel):
    """Response from the AI assistant."""
    content: str
    conversation_id: str
    tool_results: Optional[List[Dict[str, Any]]] = None
    estimate: Optional[Dict[str, Any]] = None
    workloads: Optional[List[Dict[str, Any]]] = None
    proposed_workload: Optional[Dict[str, Any]] = None


class ConfirmWorkloadRequest(BaseModel):
    """Request to confirm or reject a proposed workload."""
    proposal_id: str
    confirmed: bool = True


# Hot cache — durable source of truth is Lakebase ai_conversations
_conversation_agents: Dict[str, EstimateAgent] = {}
_conversation_owners: Dict[str, str] = {}  # conversation_id -> owner email


def _cleanup_old_conversations():
    """Trim the hot cache; durable rows remain in Lakebase."""
    if len(_conversation_agents) > 100:
        keys_to_remove = list(_conversation_agents.keys())[:50]
        for key in keys_to_remove:
            _conversation_agents.pop(key, None)
            _conversation_owners.pop(key, None)


def _cache_agent(conversation_id: str, user: User, agent: EstimateAgent) -> None:
    _conversation_agents[conversation_id] = agent
    _conversation_owners[conversation_id] = user.email


def _persist(db: Session, conversation_id: str, user: User, agent: EstimateAgent) -> None:
    try:
        conversation_store.upsert_conversation(
            db, conversation_id, user.user_id, agent
        )
    except PermissionError:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this conversation",
        )
    except Exception as exc:
        log_error(f"Failed to persist conversation {conversation_id}: {exc}")
        # Hot cache still works for this process; surface soft failure via log only.


def _get_owned_agent(
    db: Session,
    conversation_id: str,
    user: User,
    token: Optional[str] = None,
    mode: str = "estimate",
    create: bool = False,
) -> EstimateAgent:
    """Return an owned agent from cache or Lakebase; optionally create."""
    cached_owner = _conversation_owners.get(conversation_id)
    cached_agent = _conversation_agents.get(conversation_id)

    if cached_agent is not None:
        if cached_owner and cached_owner != user.email:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to access this conversation",
            )
        if token and getattr(cached_agent, "client", None) is not None:
            cached_agent.client.set_token(token)
        if hasattr(cached_agent, "set_mode"):
            cached_agent.set_mode(mode)
        _conversation_owners[conversation_id] = user.email
        return cached_agent

    # Durable lookup (falls back to memory-only when Lakebase is unavailable)
    existing = None
    try:
        existing = conversation_store.get_conversation_any_owner(db, conversation_id)
    except Exception as exc:
        log_error(f"Conversation DB lookup failed: {exc}")

    if existing is not None:
        if existing.owner_user_id != user.user_id:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to access this conversation",
            )
        agent = create_agent(token or "", mode=existing.mode or mode)
        conversation_store.hydrate_agent(agent, existing.state or {})
        if token:
            agent.client.set_token(token)
        agent.set_mode(mode or existing.mode or "estimate")
        _cache_agent(conversation_id, user, agent)
        return agent

    if not create:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required for AI assistant",
        )
    try:
        agent = conversation_store.load_or_create_agent(
            db, conversation_id, user.user_id, token, mode=mode
        )
    except Exception as exc:
        log_error(f"Conversation DB create failed, using memory-only: {exc}")
        agent = create_agent(token, mode=mode)
    _cache_agent(conversation_id, user, agent)
    return agent


def _delete_conversation(db: Session, conversation_id: str, user: User) -> None:
    _get_owned_agent(db, conversation_id, user, create=False)
    try:
        conversation_store.delete_conversation(db, conversation_id, user.user_id)
    except Exception as exc:
        log_error(f"Conversation DB delete failed: {exc}")
    agent = _conversation_agents.pop(conversation_id, None)
    _conversation_owners.pop(conversation_id, None)
    if agent is not None:
        agent.reset()


@router.post("", response_model=ChatResponse)
@router.post("/", response_model=ChatResponse)
async def chat(
    request: Request,
    chat_request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Send a message to the AI assistant and get a response."""
    token = get_model_serving_token(request)
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required for AI assistant",
        )

    conversation_id = chat_request.conversation_id or str(uuid.uuid4())
    _cleanup_old_conversations()
    agent = _get_owned_agent(
        db,
        conversation_id,
        current_user,
        token=token,
        mode=chat_request.mode,
        create=True,
    )

    if chat_request.mode == "estimate" and (
        chat_request.estimate_context or chat_request.workloads_context
    ):
        agent.set_context(
            chat_request.estimate_context or {},
            chat_request.workloads_context or [],
        )

    try:
        result = await agent.chat(chat_request.message)
        _persist(db, conversation_id, current_user, agent)
        return ChatResponse(
            content=result["content"],
            conversation_id=conversation_id,
            tool_results=result.get("tool_results"),
            estimate=result.get("estimate"),
            workloads=result.get("workloads"),
            proposed_workload=result.get("proposed_workload"),
        )
    except Exception as e:
        log_error(f"Chat error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"AI assistant error: {str(e)}",
        )


@router.post("/stream")
async def chat_stream(
    request: Request,
    chat_request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Send a message to the AI assistant and stream the response as SSE."""
    token = get_model_serving_token(request)
    if not token:
        async def error_generator():
            yield f"data: {json.dumps({'type': 'error', 'content': 'Authentication required'})}\n\n"
        return StreamingResponse(
            error_generator(),
            media_type="text/event-stream",
        )

    conversation_id = chat_request.conversation_id or str(uuid.uuid4())
    _cleanup_old_conversations()
    agent = _get_owned_agent(
        db,
        conversation_id,
        current_user,
        token=token,
        mode=chat_request.mode,
        create=True,
    )

    if chat_request.mode == "estimate" and (
        chat_request.estimate_context or chat_request.workloads_context
    ):
        agent.set_context(
            chat_request.estimate_context or {},
            chat_request.workloads_context or [],
        )

    async def generate():
        try:
            yield f"data: {json.dumps({'type': 'start', 'conversation_id': conversation_id})}\n\n"
            async for chunk in agent.chat_stream(chat_request.message):
                yield f"data: {json.dumps(chunk)}\n\n"
            _persist(db, conversation_id, current_user, agent)
        except Exception as e:
            log_error(f"Stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.delete("/{conversation_id}")
async def clear_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Clear a conversation's history and state."""
    _delete_conversation(db, conversation_id, current_user)
    return {"success": True, "message": "Conversation cleared"}


@router.post("/{conversation_id}/apply")
async def apply_estimate(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Apply the AI-generated estimate to create actual database records."""
    from app.models.estimate import Estimate
    from app.models.line_item import LineItem

    agent = _get_owned_agent(db, conversation_id, current_user, create=False)

    if not agent.current_estimate:
        raise HTTPException(status_code=400, detail="No estimate to apply")

    try:
        est_name = (
            agent.current_estimate.get("name")
            or agent.current_estimate.get("estimate_name", "AI Generated Estimate")
        )

        estimate = Estimate(
            estimate_name=est_name,
            cloud=agent.current_estimate.get("cloud", "aws"),
            region=agent.current_estimate.get("region", "us-east-1"),
            tier="PREMIUM",
            description=agent.current_estimate.get(
                "description", "Created by AI Assistant"
            ),
            owner_user_id=current_user.user_id,
        )
        db.add(estimate)
        db.flush()

        created_workloads = []
        workloads_to_create = agent.proposed_workloads if agent.proposed_workloads else []
        for workload in workloads_to_create:
            line_item = LineItem(
                estimate_id=estimate.estimate_id,
                workload_name=workload["workload_name"],
                workload_type=workload["workload_type"],
                serverless_enabled=workload.get("serverless_enabled", False),
                photon_enabled=workload.get("photon_enabled", False),
                driver_node_type=workload.get("driver_node_type"),
                worker_node_type=workload.get("worker_node_type"),
                num_workers=workload.get("num_workers"),
                hours_per_month=workload.get("hours_per_month", 730),
                runs_per_day=workload.get("runs_per_day"),
                avg_runtime_minutes=workload.get("avg_runtime_minutes"),
                days_per_month=workload.get("days_per_month", 22),
                driver_pricing_tier=workload.get("driver_pricing_tier", "on_demand"),
                worker_pricing_tier=workload.get("worker_pricing_tier", "spot"),
                dlt_edition=workload.get("dlt_edition"),
                dbsql_warehouse_type=workload.get("dbsql_warehouse_type"),
                dbsql_warehouse_size=workload.get("dbsql_warehouse_size"),
                dbsql_num_clusters=workload.get("dbsql_num_clusters"),
                lakebase_cu=workload.get("lakebase_cu"),
                lakebase_ha_nodes=workload.get("lakebase_ha_nodes"),
                notes="Created by AI Assistant",
            )
            db.add(line_item)
            created_workloads.append(workload["workload_name"])

        db.commit()
        agent.reset()
        _persist(db, conversation_id, current_user, agent)

        return {
            "success": True,
            "estimate_id": str(estimate.estimate_id),
            "estimate_name": estimate.estimate_name,
            "workloads_created": len(created_workloads),
            "message": (
                f"Created estimate '{estimate.estimate_name}' "
                f"with {len(created_workloads)} workloads"
            ),
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        log_error(f"Apply estimate error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create estimate: {str(e)}",
        )


@router.get("/{conversation_id}/state")
async def get_conversation_state(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the current state of a conversation (estimate and workloads)."""
    agent = _get_owned_agent(db, conversation_id, current_user, create=False)
    return {
        "conversation_id": conversation_id,
        "estimate": agent.current_estimate,
        "workloads": agent.current_workloads,
        "proposed_workloads": agent.proposed_workloads,
        "message_count": len(agent.conversation_history),
    }


@router.post("/{conversation_id}/confirm-workload")
async def confirm_workload(
    conversation_id: str,
    confirm_request: ConfirmWorkloadRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Confirm or reject a proposed workload."""
    agent = _get_owned_agent(db, conversation_id, current_user, create=False)

    if confirm_request.confirmed:
        workload = agent.confirm_workload(confirm_request.proposal_id)
        if not workload:
            raise HTTPException(status_code=404, detail="Proposal not found")

        _INTERNAL_FIELDS = {
            "proposal_id", "status", "reason", "cloud",
            "total_users", "concurrent_queries", "use_case_type",
            "query_selectivity", "query_complexity", "typical_data_volume",
            "model_serving_type", "model_serving_scale_to_zero",
            "vector_search_endpoint_type",
            "lakebase_expected_reads_per_sec", "lakebase_expected_bulk_writes_per_sec",
            "lakebase_expected_incremental_writes_per_sec", "lakebase_avg_row_size_kb",
            "lakebase_ha_enabled", "lakebase_num_read_replicas",
            "jobs_worker_min", "jobs_worker_max",
        }
        workload_config = {
            k: v for k, v in workload.items()
            if k not in _INTERNAL_FIELDS and v is not None
        }
        if not workload_config.get("notes"):
            workload_config["notes"] = (
                f"Created by AI Assistant: {workload.get('reason', '')}"
            )

        _persist(db, conversation_id, current_user, agent)
        return {
            "success": True,
            "action": "confirmed",
            "workload_config": workload_config,
            "message": (
                f"Workload '{workload['workload_name']}' confirmed. "
                "Use the returned config to create via "
                "/api/v1/estimates/{estimate_id}/line-items"
            ),
        }

    if agent.reject_workload(confirm_request.proposal_id):
        _persist(db, conversation_id, current_user, agent)
        return {
            "success": True,
            "action": "rejected",
            "message": "Workload proposal rejected",
        }
    raise HTTPException(status_code=404, detail="Proposal not found")
