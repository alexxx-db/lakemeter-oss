"""Unit tests for durable AI conversation serialization."""
import os
import sys
from types import SimpleNamespace
from uuid import uuid4

os.environ.setdefault("DATABASE_URL", "postgresql://u:p@localhost:5432/db")
os.environ.setdefault("ENVIRONMENT", "local")

BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, BACKEND_DIR)

from app.services.conversation_store import hydrate_agent, serialize_agent
from app.services.ai_agent import EstimateAgent


class _DummyClient:
    def set_token(self, token):
        self.token = token


def _make_agent():
    agent = EstimateAgent.__new__(EstimateAgent)
    agent.client = _DummyClient()
    agent.mode = "estimate"
    agent.conversation_history = [{"role": "user", "content": "hello"}]
    agent.current_estimate = {"cloud": "AWS", "region": "us-east-1"}
    agent.current_workloads = [{"workload_name": "Jobs"}]
    agent.proposed_workloads = [{"proposal_id": str(uuid4()), "workload_type": "JOBS"}]
    agent.conversation_summary = "summary"
    agent._executed_tool_ids = {"tool-1"}
    return agent


def test_serialize_and_hydrate_round_trip():
    original = _make_agent()
    payload = serialize_agent(original)
    assert payload["mode"] == "estimate"
    assert payload["conversation_history"][0]["content"] == "hello"
    assert "tool-1" in payload["executed_tool_ids"]

    restored = EstimateAgent.__new__(EstimateAgent)
    restored.client = _DummyClient()
    restored.mode = "home"
    restored.conversation_history = []
    restored.current_estimate = None
    restored.current_workloads = []
    restored.proposed_workloads = []
    restored.conversation_summary = ""
    restored._executed_tool_ids = set()

    hydrate_agent(restored, payload)
    assert restored.mode == "estimate"
    assert restored.current_estimate["cloud"] == "AWS"
    assert restored.proposed_workloads[0]["workload_type"] == "JOBS"
    assert restored._executed_tool_ids == {"tool-1"}


def test_ai_conversations_table_created_by_installer():
    from pathlib import Path

    text = Path("scripts/notebooks/02_create_database.py").read_text()
    assert "ai_conversations" in text
    assert "owner_user_id" in text


def test_grants_include_ai_conversations():
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
    from lakebase_grants import APP_WRITE_TABLES

    assert "ai_conversations" in APP_WRITE_TABLES
