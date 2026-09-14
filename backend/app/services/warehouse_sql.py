"""SQL warehouse Statement Execution helper for UC reads (Live FinOps).

Uses the app Service Principal via WorkspaceClient. Does not touch Lakebase.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Optional

from databricks.sdk import WorkspaceClient

logger = logging.getLogger(__name__)

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class WarehouseSQLError(RuntimeError):
    """Raised when warehouse SQL cannot be executed or returns FAILED."""


def validate_uc_identifier(name: str, *, kind: str = "identifier") -> str:
    """Reject anything that is not a simple UC catalog/schema/table name."""
    value = (name or "").strip()
    if not _IDENT.match(value):
        raise ValueError(f"Invalid UC {kind}: {name!r}")
    return value


def get_workspace_client() -> WorkspaceClient:
    """App SP in Databricks Apps; CLI/env auth locally."""
    return WorkspaceClient()


def resolve_warehouse_id(
    client: WorkspaceClient,
    configured_id: Optional[str] = None,
) -> str:
    """Prefer explicit warehouse id; otherwise first usable warehouse."""
    if configured_id and configured_id.strip():
        return configured_id.strip()

    warehouses = list(client.warehouses.list())
    for wh in warehouses:
        state = wh.state.value if hasattr(wh.state, "value") else str(wh.state)
        if state in ("RUNNING", "STOPPED", "STARTING"):
            return wh.id
    if warehouses:
        return warehouses[0].id
    raise WarehouseSQLError(
        "No SQL warehouse found. Set FINOPS_WAREHOUSE_ID or create a warehouse."
    )


def execute_sql(
    statement: str,
    *,
    warehouse_id: Optional[str] = None,
    wait_timeout: str = "50s",
    client: Optional[WorkspaceClient] = None,
) -> list[dict[str, Any]]:
    """Run SQL and return rows as list of dicts (column name → value)."""
    from databricks.sdk.service.sql import Disposition, Format

    w = client or get_workspace_client()
    wh_id = resolve_warehouse_id(w, warehouse_id)

    resp = w.statement_execution.execute_statement(
        warehouse_id=wh_id,
        statement=statement,
        disposition=Disposition.INLINE,
        format=Format.JSON_ARRAY,
        wait_timeout=wait_timeout,
    )

    state = getattr(resp.status, "state", None)
    state_val = state.value if hasattr(state, "value") else str(state)
    if state_val == "FAILED":
        err = getattr(resp.status, "error", None)
        raise WarehouseSQLError(f"SQL failed: {err}")

    columns: list[str] = []
    if resp.manifest and resp.manifest.schema and resp.manifest.schema.columns:
        columns = [c.name for c in resp.manifest.schema.columns]

    raw_rows: list[list[Any]] = []
    if resp.result and resp.result.data_array:
        raw_rows.extend(resp.result.data_array)

    if resp.result and resp.result.next_chunk_index is not None:
        chunk_idx = resp.result.next_chunk_index
        while chunk_idx is not None:
            chunk = w.statement_execution.get_statement_result_chunk_n(
                resp.statement_id, chunk_idx
            )
            if chunk.data_array:
                raw_rows.extend(chunk.data_array)
            chunk_idx = chunk.next_chunk_index

    if not columns and raw_rows:
        columns = [f"c{i}" for i in range(len(raw_rows[0]))]

    return [dict(zip(columns, row)) for row in raw_rows]
