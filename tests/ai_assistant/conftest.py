"""Shared test infrastructure for AI assistant end-to-end tests.

Uses FastAPI TestClient against the local backend. The backend uses
Databricks CLI token for FMAPI calls (model-serving scope) and
service principal for Lakebase DB access.

Required env vars (set automatically if DATABRICKS_CONFIG_PROFILE=lakemeter):
  DATABRICKS_HOST, DATABRICKS_CONFIG_PROFILE, DATABRICKS_SECRETS_SCOPE,
  SP_CLIENT_ID_KEY, SP_SECRET_KEY, LAKEBASE_INSTANCE_NAME, DB_HOST,
  DB_USER, DB_NAME, DB_PORT, DB_SSLMODE
"""
import os
import sys
import uuid
from typing import Optional

import pytest

# Ensure backend is importable
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Set required env vars before importing the app
_ENV_DEFAULTS = {
    "DATABRICKS_HOST": "https://fe-vm-lakemeter.cloud.databricks.com",
    "DATABRICKS_CONFIG_PROFILE": "lakemeter",
    "DATABRICKS_SECRETS_SCOPE": "lakemeter-secrets",
    "SP_CLIENT_ID_KEY": "sp_clientid",
    "SP_SECRET_KEY": "sp_secret",
    "LAKEBASE_INSTANCE_NAME": "lakemeter-db",
    "DB_HOST": "instance-364041a4-0aae-44df-bbc6-37ac84169dfe.database.cloud.databricks.com",
    "DB_USER": "0a1a2461-5013-4110-94ff-f7157e7b8b8e",
    "DB_NAME": "lakemeter_pricing",
    "DB_PORT": "5432",
    "DB_SSLMODE": "require",
}
for key, default in _ENV_DEFAULTS.items():
    os.environ.setdefault(key, default)

AUTH_EMAIL = "test-harness@databricks.com"
AUTH_HEADERS = {"X-Forwarded-Email": AUTH_EMAIL}


@pytest.fixture(scope="session")
def http_client():
    """FastAPI TestClient wrapping the real backend (with Lakebase + FMAPI)."""
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture(scope="session")
def test_estimate(http_client):
    """Create a test estimate for the session, delete it afterwards."""
    payload = {
        "estimate_name": f"AI-Test-{uuid.uuid4().hex[:8]}",
        "cloud": "AWS",
        "region": "us-east-1",
        "tier": "PREMIUM",
    }
    resp = http_client.post(
        "/api/v1/estimates/", json=payload, headers=AUTH_HEADERS
    )
    assert resp.status_code == 201, f"Failed to create estimate: {resp.text}"
    estimate = resp.json()
    yield estimate
    http_client.delete(
        f"/api/v1/estimates/{estimate['estimate_id']}",
        headers=AUTH_HEADERS,
    )


# ── Chat helper utilities ──────────────────────────────────────────


def send_chat_message(
    http_client,
    message: str,
    estimate: dict,
    conversation_id: Optional[str] = None,
    workloads_context: Optional[list] = None,
    max_retries: int = 2,
) -> dict:
    """Send a non-streaming chat message and return the parsed response.

    Retries on 500 errors (rate-limit, transient Claude failures) with a
    30-second backoff between attempts.
    """
    import time

    cid = conversation_id or str(uuid.uuid4())
    payload = {
        "message": message,
        "conversation_id": cid,
        "estimate_context": {
            "estimate_id": estimate["estimate_id"],
            "estimate_name": estimate["estimate_name"],
            "cloud": estimate.get("cloud", "AWS"),
            "region": estimate.get("region", "us-east-1"),
            "tier": estimate.get("tier", "PREMIUM"),
        },
        "workloads_context": workloads_context or [],
        "mode": "estimate",
        "stream": False,
    }
    last_err = ""
    for attempt in range(1 + max_retries):
        resp = http_client.post(
            "/api/v1/chat", json=payload, headers=AUTH_HEADERS
        )
        if resp.status_code == 200:
            data = resp.json()
            data["_conversation_id"] = data.get("conversation_id", cid)
            return data
        last_err = resp.text[:300]
        if attempt < max_retries:
            time.sleep(30)  # back off for rate limits
    assert False, (
        f"Chat call failed after {1 + max_retries} attempts "
        f"({resp.status_code}): {last_err}"
    )


def extract_proposal(response: dict) -> Optional[dict]:
    """Extract proposed_workload from a chat response."""
    pw = response.get("proposed_workload")
    if pw:
        return pw
    for tr in response.get("tool_results") or []:
        if (
            tr.get("tool") == "propose_workload"
            and tr.get("result", {}).get("success")
        ):
            return tr["result"].get("workload")
    return None


def send_chat_until_proposal(
    http_client,
    messages: list[str],
    estimate: dict,
    conversation_id: Optional[str] = None,
) -> tuple[dict, dict]:
    """Send messages sequentially until we get a proposed_workload.

    Returns (proposal_dict, last_response_dict).
    Raises AssertionError if no proposal after all messages.
    """
    cid = conversation_id or str(uuid.uuid4())
    last_resp: dict = {}
    for msg in messages:
        last_resp = send_chat_message(
            http_client, msg, estimate, conversation_id=cid
        )
        proposal = extract_proposal(last_resp)
        if proposal:
            return proposal, last_resp
    raise AssertionError(
        f"No proposal after {len(messages)} messages. "
        f"Last response: {last_resp.get('content', '')[:300]}"
    )


def confirm_proposal(http_client, conversation_id: str, proposal_id: str) -> dict:
    """Confirm a proposed workload."""
    resp = http_client.post(
        f"/api/v1/chat/{conversation_id}/confirm-workload",
        json={"proposal_id": proposal_id, "confirmed": True},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200, f"Confirm failed: {resp.text[:200]}"
    return resp.json()


def reject_proposal(http_client, conversation_id: str, proposal_id: str) -> dict:
    """Reject a proposed workload."""
    resp = http_client.post(
        f"/api/v1/chat/{conversation_id}/confirm-workload",
        json={"proposal_id": proposal_id, "confirmed": False},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200, f"Reject failed: {resp.text[:200]}"
    return resp.json()


def get_conversation_state(http_client, conversation_id: str) -> dict:
    """Get conversation state (pending proposals, confirmed workloads)."""
    resp = http_client.get(
        f"/api/v1/chat/{conversation_id}/state",
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200, f"State fetch failed: {resp.text[:200]}"
    return resp.json()
