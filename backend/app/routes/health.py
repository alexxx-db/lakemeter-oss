"""Health, readiness, and diagnostics endpoints.

Three tiers, cheapest first:

- ``GET /health`` (in main.py) — liveness: process is up. No I/O.
- ``GET /health/ready`` — readiness: the app can serve real traffic.
  Checks database connectivity and that pricing reference tables are
  populated. Returns 503 until ready, so load balancers / Databricks
  Apps health probes can gate traffic during cold start.
- ``GET /api/v1/diagnostics`` — support bundle: version, environment,
  uptime, redacted configuration, database status, and pricing table
  row counts. Secrets are always masked.
"""
import os
import platform
import re
import time
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import settings

router = APIRouter(tags=["health"])

_START_TIME = time.time()

# Pricing tables that must be populated for correct calculations.
_READINESS_TABLES = [
    "sync_pricing_dbu_rates",
    "sync_pricing_vm_costs",
]

# Tables reported in the diagnostics bundle.
_DIAGNOSTICS_TABLES = [
    "sync_pricing_dbu_rates",
    "sync_pricing_vm_costs",
    "sync_product_serverless_rates",
    "sync_product_dbsql_rates",
    "sync_product_fmapi_databricks",
    "sync_product_fmapi_proprietary",
    "sync_ref_instance_dbu_rates",
    "sync_ref_dbsql_warehouse_config",
]

_SENSITIVE_KEY_RE = re.compile(r"(?i)(password|secret|token|api[_-]?key|private[_-]?key)")


def _get_engine():
    """Return the current database engine, or None.

    Read lazily at request time so a late-initialized (or refreshed)
    engine is picked up without importing database internals.
    """
    try:
        from app import database as dbmod
    except Exception:
        return None
    return getattr(dbmod, "engine", None)


def _table_row_counts(conn, tables):
    """Return {table: row_count}; raises on the first unreadable table."""
    counts = {}
    for table in tables:
        counts[table] = conn.execute(
            text(f"SELECT COUNT(*) FROM lakemeter.{table}")).scalar()
    return counts


@router.get("/health/ready")
def readiness():
    """Readiness probe: 200 when the app can serve traffic, else 503."""
    checks = {}

    engine = _get_engine()
    if engine is None:
        checks["database"] = {"ok": False, "error": "engine not initialized"}
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "checks": checks})

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            try:
                counts = _table_row_counts(conn, _READINESS_TABLES)
                checks["database"] = {"ok": True}
                empty = [t for t, n in counts.items() if not n]
                checks["pricing_tables"] = {
                    "ok": not empty,
                    "rows": counts,
                    **({"empty": empty} if empty else {}),
                }
            except Exception as e:
                checks["database"] = {"ok": True}
                checks["pricing_tables"] = {"ok": False, "error": str(e)}
    except Exception as e:
        checks["database"] = {"ok": False, "error": str(e)}

    ready = all(c.get("ok") for c in checks.values())
    return JSONResponse(
        status_code=200 if ready else 503,
        content={"status": "ready" if ready else "not_ready", "checks": checks})


def _app_version():
    """Resolve the app version: repo VERSION file, then env, then 'unknown'."""
    version_file = Path(__file__).resolve().parents[3] / "VERSION"
    try:
        version = version_file.read_text().strip()
        if version:
            return version
    except OSError:
        pass
    return os.getenv("APP_VERSION", "unknown")


def _redacted_config():
    """Settings snapshot with every secret-bearing value masked."""
    try:
        raw = settings.model_dump()
    except AttributeError:  # pydantic v1 fallback
        raw = dict(settings.__dict__)
    config = {}
    for key, value in sorted(raw.items()):
        if _SENSITIVE_KEY_RE.search(key):
            config[key] = "***" if value else ""
        elif key == "database_url":
            config[key] = "***" if value else ""
        else:
            config[key] = value
    config["use_oauth"] = settings.use_oauth
    config["is_production"] = settings.is_production
    return config


def _database_diagnostics():
    """Database status for the diagnostics bundle."""
    result = {"connected": False, "error": None}
    engine = _get_engine()
    if engine is None:
        result["error"] = "engine not initialized"
        return result
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            result["connected"] = True
            try:
                result["pricing_table_rows"] = _table_row_counts(
                    conn, _DIAGNOSTICS_TABLES)
            except Exception as e:
                result["pricing_table_rows_error"] = str(e)
    except Exception as e:
        result["error"] = str(e)
        return result

    pool = getattr(engine, "pool", None)
    status = getattr(pool, "status", None)
    if callable(status):
        try:
            result["pool_status"] = status()
        except Exception:
            pass
    return result


@router.get("/api/v1/diagnostics")
def diagnostics():
    """Support diagnostics bundle. Safe to share: secrets are masked."""
    return {
        "app": {
            "name": "Lakemeter",
            "version": _app_version(),
            "environment": settings.environment,
        },
        "system": {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "uptime_seconds": int(time.time() - _START_TIME),
            "pid": os.getpid(),
        },
        "config": _redacted_config(),
        "database": _database_diagnostics(),
    }
