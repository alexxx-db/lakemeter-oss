"""Opt-in anonymous usage telemetry.

**Disabled by default.** Telemetry activates only when BOTH
``TELEMETRY_ENABLED=true`` and ``TELEMETRY_ENDPOINT`` are set. When
active, it emits coarse product-usage events (e.g. "app started",
"excel exported") to the configured endpoint — never user data,
estimate names/contents, node types, regions, or costs.

Design guarantees:
- ``track_event`` never raises and never blocks the request path
  (fire-and-forget on a daemon thread, 2s timeout)
- the install identifier is a one-way SHA-256 hash of the workspace
  host, not the host itself
- event properties are sanitized to scalar values only
"""
import hashlib
import logging
import os
import threading
import time
from pathlib import Path

logger = logging.getLogger("lakemeter.telemetry")

_TRUE_VALUES = {"1", "true", "yes", "on"}


def telemetry_enabled() -> bool:
    """True only when explicitly opted in AND an endpoint is configured."""
    return (
        os.getenv("TELEMETRY_ENABLED", "").strip().lower() in _TRUE_VALUES
        and bool(os.getenv("TELEMETRY_ENDPOINT", "").strip())
    )


def install_id() -> str:
    """Pseudonymous install identifier: SHA-256 of the workspace host."""
    host = os.getenv("DATABRICKS_HOST", "") or "local"
    return hashlib.sha256(host.strip().lower().encode()).hexdigest()[:16]


def app_version() -> str:
    """App version from the repo VERSION file, else 'unknown'."""
    version_file = Path(__file__).resolve().parents[2] / "VERSION"
    try:
        version = version_file.read_text().strip()
        if version:
            return version
    except OSError:
        pass
    return "unknown"


def _sanitize_properties(properties):
    """Keep only scalar (str/int/float/bool/None) property values."""
    if not properties:
        return {}
    clean = {}
    for key, value in properties.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            clean[str(key)] = value
    return clean


def _post(payload):
    """POST the event; every failure is logged and swallowed."""
    try:
        import httpx
        httpx.post(
            os.getenv("TELEMETRY_ENDPOINT", "").strip(),
            json=payload,
            timeout=2.0,
        )
    except Exception as e:  # noqa: BLE001 — telemetry must never break the app
        logger.debug("telemetry post failed: %s", e)


def track_event(event: str, properties: dict | None = None) -> None:
    """Emit a usage event. No-op unless telemetry is opted in."""
    if not telemetry_enabled():
        return
    payload = {
        "event": event,
        "properties": _sanitize_properties(properties),
        "install_id": install_id(),
        "app_version": app_version(),
        "timestamp": int(time.time()),
    }
    threading.Thread(target=_post, args=(payload,), daemon=True).start()
