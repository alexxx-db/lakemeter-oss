"""AuthZ tests for user routes and chat conversation ownership."""
import os
import sys

# Ensure engine init does not attempt live Lakebase/secrets auth.
os.environ.setdefault("DATABASE_URL", "postgresql://u:p@localhost:5432/db")
os.environ.setdefault("ENVIRONMENT", "local")

BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, BACKEND_DIR)

from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.database import get_db
from app.main import app
from app.routes import chat as chat_routes


class _NoopSession:
    def query(self, *args, **kwargs):
        raise AssertionError("DB should be mocked via dependency overrides")


def _user(email: str, role: str = "user"):
    now = datetime.utcnow()
    return SimpleNamespace(
        user_id=uuid4(),
        email=email,
        full_name=email.split("@")[0].title(),
        role=role,
        is_active=True,
        last_login_at=now,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def owner():
    return _user("owner@databricks.com")


@pytest.fixture
def other():
    return _user("other@databricks.com")


@pytest.fixture
def client(owner):
    def _override_user():
        return owner

    def _db():
        yield _NoopSession()

    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[get_db] = _db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()
    chat_routes._conversation_agents.clear()
    chat_routes._conversation_owners.clear()


class TestUsersAuthZ:
    def test_user_and_chat_routes_require_get_current_user(self):
        """Route callables must declare Depends(get_current_user)."""
        protected = []
        for route in app.routes:
            path = getattr(route, "path", "")
            endpoint = getattr(route, "endpoint", None)
            if not endpoint:
                continue
            if path.startswith("/api/v1/users") or path.startswith("/api/v1/chat"):
                deps = getattr(route, "dependant", None)
                dep_names = []
                if deps is not None:
                    dep_names = [d.call.__name__ for d in deps.dependencies if getattr(d, "call", None)]
                protected.append((path, dep_names))

        assert protected, "Expected user/chat routes to be registered"
        for path, dep_names in protected:
            assert "get_current_user" in dep_names, f"{path} missing get_current_user (have {dep_names})"

    def test_me_returns_current_user(self, client, owner):
        resp = client.get("/api/v1/users/me")
        assert resp.status_code == 200
        assert resp.json()["email"] == owner.email

    def test_get_other_user_forbidden(self, client, other):
        resp = client.get(f"/api/v1/users/{other.user_id}")
        assert resp.status_code == 403

    def test_update_other_user_forbidden(self, client, other):
        resp = client.put(
            f"/api/v1/users/{other.user_id}",
            json={"full_name": "Hacked"},
        )
        assert resp.status_code == 403

    def test_create_user_removed(self, client):
        resp = client.post(
            "/api/v1/users/",
            json={"email": "new@databricks.com", "full_name": "New"},
        )
        assert resp.status_code in (404, 405)


class TestChatOwnership:
    def test_state_requires_owner(self, client, owner, other):
        cid = str(uuid4())
        agent = SimpleNamespace(
            current_estimate={},
            current_workloads=[],
            proposed_workloads=[],
            conversation_history=[],
            reset=lambda: None,
        )
        chat_routes._conversation_agents[cid] = agent
        chat_routes._conversation_owners[cid] = owner.email

        resp = client.get(f"/api/v1/chat/{cid}/state")
        assert resp.status_code == 200

        app.dependency_overrides[get_current_user] = lambda: other
        resp = client.get(f"/api/v1/chat/{cid}/state")
        assert resp.status_code == 403

    def test_delete_requires_owner(self, client, owner, other):
        cid = str(uuid4())
        agent = SimpleNamespace(
            current_estimate={},
            current_workloads=[],
            proposed_workloads=[],
            conversation_history=[],
            reset=lambda: None,
        )
        chat_routes._conversation_agents[cid] = agent
        chat_routes._conversation_owners[cid] = owner.email

        app.dependency_overrides[get_current_user] = lambda: other
        resp = client.delete(f"/api/v1/chat/{cid}")
        assert resp.status_code == 403
        assert cid in chat_routes._conversation_agents

        app.dependency_overrides[get_current_user] = lambda: owner
        resp = client.delete(f"/api/v1/chat/{cid}")
        assert resp.status_code == 200
        assert cid not in chat_routes._conversation_agents
        assert cid not in chat_routes._conversation_owners
