"""Persist and hydrate AI conversation agents in Lakebase."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import log_warning
from app.models.ai_conversation import AIConversation
from app.services.ai_agent import EstimateAgent, create_agent

_TABLE_READY = False

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS lakemeter.ai_conversations (
    conversation_id UUID PRIMARY KEY,
    owner_user_id UUID NOT NULL REFERENCES lakemeter.users(user_id),
    mode VARCHAR(20) DEFAULT 'estimate',
    state JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ai_conversations_owner
    ON lakemeter.ai_conversations(owner_user_id);
"""


def ensure_ai_conversations_table(db: Session) -> None:
    """Create the ai_conversations table if missing (new installs + upgrades)."""
    global _TABLE_READY
    if _TABLE_READY:
        return
    try:
        for stmt in _CREATE_SQL.strip().split(";"):
            sql = stmt.strip()
            if sql:
                db.execute(text(sql))
        db.commit()
        _TABLE_READY = True
    except Exception as exc:
        db.rollback()
        log_warning(f"Could not ensure ai_conversations table: {exc}")


def serialize_agent(agent: EstimateAgent) -> dict[str, Any]:
    return {
        "mode": agent.mode,
        "conversation_history": agent.conversation_history,
        "current_estimate": agent.current_estimate,
        "current_workloads": agent.current_workloads,
        "proposed_workloads": agent.proposed_workloads,
        "conversation_summary": agent.conversation_summary,
        "executed_tool_ids": list(getattr(agent, "_executed_tool_ids", set()) or []),
    }


def hydrate_agent(agent: EstimateAgent, state: dict[str, Any]) -> EstimateAgent:
    agent.mode = state.get("mode") or agent.mode
    agent.conversation_history = list(state.get("conversation_history") or [])
    agent.current_estimate = state.get("current_estimate")
    agent.current_workloads = list(state.get("current_workloads") or [])
    agent.proposed_workloads = list(state.get("proposed_workloads") or [])
    agent.conversation_summary = state.get("conversation_summary") or ""
    agent._executed_tool_ids = set(state.get("executed_tool_ids") or [])
    return agent


def _as_uuid(conversation_id: str | UUID) -> UUID:
    return conversation_id if isinstance(conversation_id, UUID) else UUID(str(conversation_id))


def get_conversation(
    db: Session,
    conversation_id: str,
    owner_user_id: UUID,
) -> Optional[AIConversation]:
    ensure_ai_conversations_table(db)
    return (
        db.query(AIConversation)
        .filter(
            AIConversation.conversation_id == _as_uuid(conversation_id),
            AIConversation.owner_user_id == owner_user_id,
        )
        .first()
    )


def get_conversation_any_owner(
    db: Session,
    conversation_id: str,
) -> Optional[AIConversation]:
    ensure_ai_conversations_table(db)
    return (
        db.query(AIConversation)
        .filter(AIConversation.conversation_id == _as_uuid(conversation_id))
        .first()
    )


def upsert_conversation(
    db: Session,
    conversation_id: str,
    owner_user_id: UUID,
    agent: EstimateAgent,
) -> AIConversation:
    ensure_ai_conversations_table(db)
    cid = _as_uuid(conversation_id)
    row = (
        db.query(AIConversation)
        .filter(AIConversation.conversation_id == cid)
        .first()
    )
    payload = serialize_agent(agent)
    now = datetime.utcnow()
    if row is None:
        row = AIConversation(
            conversation_id=cid,
            owner_user_id=owner_user_id,
            mode=agent.mode,
            state=payload,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
    else:
        if row.owner_user_id != owner_user_id:
            raise PermissionError("Conversation owned by another user")
        row.mode = agent.mode
        row.state = payload
        row.updated_at = now
    db.commit()
    db.refresh(row)
    return row


def delete_conversation(db: Session, conversation_id: str, owner_user_id: UUID) -> bool:
    ensure_ai_conversations_table(db)
    row = get_conversation(db, conversation_id, owner_user_id)
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True


def load_or_create_agent(
    db: Session,
    conversation_id: str,
    owner_user_id: UUID,
    token: str,
    mode: str = "estimate",
) -> EstimateAgent:
    """Load agent state from DB or create a fresh agent (and persist an empty shell)."""
    row = get_conversation(db, conversation_id, owner_user_id)
    agent = create_agent(token, mode=mode)
    if row is not None:
        hydrate_agent(agent, row.state or {})
        agent.set_mode(mode or row.mode or "estimate")
        agent.client.set_token(token)
    else:
        # Claim the conversation id for this owner immediately.
        upsert_conversation(db, conversation_id, owner_user_id, agent)
    return agent
