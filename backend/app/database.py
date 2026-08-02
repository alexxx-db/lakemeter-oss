"""
Database connection and session management.

Lakebase OAuth tokens expire after 1 hour, so credentials are minted per
connection via SQLAlchemy's `creator` hook: the pool calls the factory every
time it needs a new physical connection, and the token manager refreshes the
OAuth token transparently when it is near expiry. No engine rebuilds, no
stale-password window.

Reference: https://docs.databricks.com/aws/en/oltp/instances/authentication
"""
import threading

import psycopg2
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import log_info, log_warning, log_error


# Base class for models (defined early so models can import it)
Base = declarative_base()

_CONNECT_TIMEOUT = 10
# Recycle pooled connections well before the 1-hour server-side token lifetime.
_POOL_RECYCLE_SECONDS = 3300


def _params_from_url(url: str) -> dict:
    """Parse a DATABASE_URL into psycopg2 connect kwargs."""
    parsed = make_url(url)
    backend = parsed.get_backend_name()
    if backend == "sqlite":
        raise Exception(
            "SQLite is not supported. Lakemeter requires Lakebase/PostgreSQL. "
            "Set DATABASE_URL to a postgresql:// URL or configure OAuth."
        )
    if backend not in ("postgresql", "postgres"):
        raise Exception(f"Unsupported DATABASE_URL backend: {backend}")
    return {
        "host": parsed.host,
        "port": parsed.port or 5432,
        "dbname": parsed.database,
        "user": parsed.username,
        "password": parsed.password or "",
        "sslmode": parsed.query.get("sslmode", "require"),
    }


def _secrets_params() -> dict:
    """Static password auth via Databricks secrets (lakebase-password)."""
    import os
    import base64
    from databricks.sdk import WorkspaceClient

    w = WorkspaceClient()
    scope = os.getenv("DATABRICKS_SECRETS_SCOPE", "lakemeter-credentials")

    def _get_secret(key):
        raw = w.secrets.get_secret(scope=scope, key=key).value
        try:
            return base64.b64decode(raw).decode("utf-8")
        except Exception:
            return raw

    params = {
        "host": _get_secret("lakebase-host"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "dbname": _get_secret("lakebase-database"),
        "user": _get_secret("lakebase-user"),
        "password": _get_secret("lakebase-password"),
        "sslmode": "require",
    }
    log_info(f"Using password auth for user: {params['user']}")
    return params


def _static_factory(params: dict):
    """Connection factory for static credentials (DATABASE_URL / secrets)."""
    def connect():
        return psycopg2.connect(connect_timeout=_CONNECT_TIMEOUT, **params)
    return connect


def _build_connection_factory():
    """
    Decide the auth strategy once and return a psycopg2 connection factory.

    Order of precedence (mirrors the previous _get_database_url behavior):
    1. DATABASE_URL (local dev) — static params
    2. OAuth service principal via token manager — per-connection token minting
    3. Secrets-based password fallback — static params
    """
    import os

    direct_url = os.getenv("DATABASE_URL")
    if direct_url:
        # SQLite is not supported: the cost math lives in Lakebase SQL functions
        # and the engine is configured with PostgreSQL-specific pooling args.
        # Fail fast with a clear message instead of a cryptic pool error.
        if direct_url.strip().lower().startswith("sqlite"):
            raise Exception(
                "SQLite is not supported. Lakemeter requires Lakebase/PostgreSQL "
                "(the cost-calculation SQL functions run in the database). "
                "Point DATABASE_URL at a PostgreSQL instance, e.g. "
                "postgresql://user:pass@host:5432/dbname"
            )
        log_info("Using DATABASE_URL environment variable for database connection")
        return _static_factory(_params_from_url(direct_url))

    from app.auth.token_manager import token_manager

    if token_manager and token_manager.get_token():
        # Probe once: verify the SP can actually log in before committing to
        # per-connection OAuth (fast timeout to avoid blocking startup).
        try:
            probe = token_manager.get_connection_params()
            conn = psycopg2.connect(connect_timeout=5, **probe)
            conn.close()
            log_info(f"Using OAuth SP token for database connection (user: {probe['user']})")

            def oauth_connect():
                # get_connection_params() -> get_token() refreshes the OAuth
                # token under a lock when it is near expiry, so every pooled
                # connection is created with a valid credential.
                params = token_manager.get_connection_params()
                return psycopg2.connect(connect_timeout=_CONNECT_TIMEOUT, **params)

            return oauth_connect
        except Exception as e:
            log_warning(f"SP OAuth connection test failed: {e}")
            log_info("Falling back to password auth...")
    else:
        log_info("No SP OAuth credentials available, using password fallback...")

    log_info("Attempting password-based auth via Databricks secrets...")
    try:
        return _static_factory(_secrets_params())
    except Exception as e:
        log_error(f"Password fallback failed: {e}")

    raise Exception("No valid database credentials available. Check OAuth config or lakebase-password secret.")


def _create_engine():
    """Create the SQLAlchemy engine with per-connection credential minting."""
    factory = _build_connection_factory()
    try:
        engine = create_engine(
            "postgresql+psycopg2://",
            creator=factory,
            pool_pre_ping=True,
            pool_size=15,
            max_overflow=25,
            pool_timeout=15,
            pool_recycle=_POOL_RECYCLE_SECONDS,
        )
        # Startup smoke test (also warms the pool with one valid connection).
        with engine.connect() as conn:
            from sqlalchemy import text
            conn.execute(text("SELECT 1"))
        log_info("Database engine created for Lakebase")
        return engine
    except Exception as e:
        log_error(f"Could not create database engine: {e}")
        raise


def _new_session_factory(eng):
    return sessionmaker(autocommit=False, autoflush=False, bind=eng)


# Initialize engine and session factory (fault-tolerant — retries lazily on
# first request if startup fails, e.g. secrets not yet available).
try:
    engine = _create_engine()
    SessionLocal = _new_session_factory(engine)
except Exception as e:
    log_error(f"Database initialization failed (will retry on first request): {e}")
    engine = None
    SessionLocal = None


_init_lock = threading.Lock()


def _ensure_engine() -> bool:
    """Lazily (re)create the engine if startup failed. Thread-safe."""
    global engine, SessionLocal
    if engine is not None:
        return True
    with _init_lock:
        if engine is not None:
            return True
        log_info("Engine is None, attempting to create...")
        try:
            engine = _create_engine()
            SessionLocal = _new_session_factory(engine)
            return True
        except Exception as e:
            log_error(f"Failed to create engine: {e}")
            return False


def get_db():
    """
    Dependency to get database session.

    Auth freshness is handled by the connection factory (per-connection token
    minting) and pool_pre_ping, so no per-request engine checks are needed.
    """
    if not _ensure_engine():
        raise HTTPException(status_code=503, detail="Database not connected")

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
