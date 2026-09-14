"""Live FinOps queries against UC gold (ADR-012).

Reads `{catalog}.{schema}.cost_daily` / `cost_by_product_daily` /
`finops_run_metadata` via SQL warehouse. Never queries system.billing.*
from the app request path.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Optional

from app.config import settings
from app.services.warehouse_sql import (
    WarehouseSQLError,
    execute_sql,
    validate_uc_identifier,
)

logger = logging.getLogger(__name__)

# Tag keys — keep in sync with etl/finops/TAGGING.md and frontend/src/lib/finopsTags.ts
TAG_ESTIMATE_ID = "lakemeter_estimate_id"
TAG_WORKLOAD_TYPE = "lakemeter_workload_type"
TAG_LINE_ITEM_ID = "lakemeter_line_item_id"


@dataclass(frozen=True)
class FinOpsConfig:
    warehouse_id: str
    catalog: str
    schema: str
    enabled: bool

    @property
    def fqn_prefix(self) -> str:
        return f"{self.catalog}.{self.schema}"


def get_finops_config() -> FinOpsConfig:
    catalog = validate_uc_identifier(settings.finops_catalog, kind="catalog")
    schema = validate_uc_identifier(settings.finops_schema, kind="schema")
    warehouse_id = (settings.finops_warehouse_id or "").strip()
    # Enabled when warehouse is set, or when auto-discover is allowed (empty = try).
    # Prefer explicit warehouse in production; empty still attempts discover so
    # local/dev can work. UI treats query failures as "unavailable".
    enabled = bool(warehouse_id) or settings.finops_auto_warehouse
    return FinOpsConfig(
        warehouse_id=warehouse_id,
        catalog=catalog,
        schema=schema,
        enabled=enabled,
    )


def _as_float(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _as_int(value: Any) -> int:
    if value is None:
        return 0
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def fetch_metadata(cfg: Optional[FinOpsConfig] = None) -> dict[str, Any]:
    cfg = cfg or get_finops_config()
    if not cfg.enabled:
        return {
            "available": False,
            "configured": False,
            "message": (
                "FinOps warehouse is not configured. Set FINOPS_WAREHOUSE_ID "
                "and deploy gold via etl/finops (ADR-012)."
            ),
        }

    sql = f"""
    SELECT
      built_at,
      catalog_name,
      schema_name,
      lookback_days,
      cost_daily_rows,
      cost_by_product_daily_rows,
      cost_by_estimate_daily_rows,
      unpriced_positive_usage_rows,
      total_list_cost_usd,
      attributed_list_cost_usd,
      attributed_pct,
      cost_basis,
      build_version
    FROM {cfg.fqn_prefix}.finops_run_metadata
    LIMIT 1
    """
    try:
        rows = execute_sql(sql, warehouse_id=cfg.warehouse_id or None)
    except Exception as exc:
        logger.warning("FinOps metadata query failed: %s", exc)
        return {
            "available": False,
            "configured": True,
            "catalog": cfg.catalog,
            "schema": cfg.schema,
            "message": str(exc),
        }

    if not rows:
        return {
            "available": False,
            "configured": True,
            "catalog": cfg.catalog,
            "schema": cfg.schema,
            "message": (
                f"No finops_run_metadata in {cfg.fqn_prefix}. "
                "Run job lakemeter_finops_gold."
            ),
        }

    row = rows[0]
    return {
        "available": True,
        "configured": True,
        "built_at": row.get("built_at"),
        "catalog": row.get("catalog_name") or cfg.catalog,
        "schema": row.get("schema_name") or cfg.schema,
        "lookback_days": _as_int(row.get("lookback_days")),
        "cost_daily_rows": _as_int(row.get("cost_daily_rows")),
        "cost_by_product_daily_rows": _as_int(row.get("cost_by_product_daily_rows")),
        "cost_by_estimate_daily_rows": _as_int(row.get("cost_by_estimate_daily_rows")),
        "unpriced_positive_usage_rows": _as_int(row.get("unpriced_positive_usage_rows")),
        "total_list_cost_usd": _as_float(row.get("total_list_cost_usd")),
        "attributed_list_cost_usd": _as_float(row.get("attributed_list_cost_usd")),
        "attributed_pct": _as_float(row.get("attributed_pct")),
        "cost_basis": row.get("cost_basis") or "list",
        "build_version": row.get("build_version"),
        "message": None,
    }


def fetch_summary(
    *,
    days: int = 30,
    workspace_id: Optional[str] = None,
    cfg: Optional[FinOpsConfig] = None,
) -> dict[str, Any]:
    """Totals, daily trend, and product mix over the lookback window."""
    cfg = cfg or get_finops_config()
    days = max(1, min(int(days), 730))

    if not cfg.enabled:
        return {
            "available": False,
            "configured": False,
            "days": days,
            "cost_basis": "list",
            "total_list_cost_usd": 0.0,
            "daily": [],
            "by_product": [],
            "message": (
                "FinOps warehouse is not configured. Set FINOPS_WAREHOUSE_ID "
                "and deploy gold via etl/finops (ADR-012)."
            ),
        }

    ws_filter = ""
    if workspace_id and workspace_id.strip():
        # Bind-like escaping for string literal
        safe_ws = workspace_id.strip().replace("'", "''")
        ws_filter = f" AND workspace_id = '{safe_ws}'"

    daily_sql = f"""
    SELECT
      usage_date,
      SUM(list_cost_usd) AS list_cost_usd,
      SUM(usage_quantity) AS usage_quantity
    FROM {cfg.fqn_prefix}.cost_by_product_daily
    WHERE usage_date >= date_sub(current_date(), {days})
    {ws_filter}
    GROUP BY usage_date
    ORDER BY usage_date
    """

    product_sql = f"""
    SELECT
      billing_origin_product,
      SUM(list_cost_usd) AS list_cost_usd,
      SUM(usage_quantity) AS usage_quantity,
      SUM(usage_record_count) AS usage_record_count
    FROM {cfg.fqn_prefix}.cost_by_product_daily
    WHERE usage_date >= date_sub(current_date(), {days})
    {ws_filter}
    GROUP BY billing_origin_product
    ORDER BY list_cost_usd DESC
    """

    try:
        daily_rows = execute_sql(daily_sql, warehouse_id=cfg.warehouse_id or None)
        product_rows = execute_sql(product_sql, warehouse_id=cfg.warehouse_id or None)
    except WarehouseSQLError as exc:
        logger.warning("FinOps summary query failed: %s", exc)
        return {
            "available": False,
            "configured": True,
            "days": days,
            "cost_basis": "list",
            "total_list_cost_usd": 0.0,
            "daily": [],
            "by_product": [],
            "message": str(exc),
        }
    except Exception as exc:
        logger.warning("FinOps summary unexpected error: %s", exc)
        return {
            "available": False,
            "configured": True,
            "days": days,
            "cost_basis": "list",
            "total_list_cost_usd": 0.0,
            "daily": [],
            "by_product": [],
            "message": str(exc),
        }

    daily = [
        {
            "usage_date": str(r.get("usage_date")),
            "list_cost_usd": _as_float(r.get("list_cost_usd")),
            "usage_quantity": _as_float(r.get("usage_quantity")),
        }
        for r in daily_rows
    ]
    by_product = [
        {
            "billing_origin_product": r.get("billing_origin_product") or "UNKNOWN",
            "list_cost_usd": _as_float(r.get("list_cost_usd")),
            "usage_quantity": _as_float(r.get("usage_quantity")),
            "usage_record_count": _as_int(r.get("usage_record_count")),
        }
        for r in product_rows
    ]
    total = sum(d["list_cost_usd"] for d in daily)

    return {
        "available": True,
        "configured": True,
        "days": days,
        "workspace_id": workspace_id.strip() if workspace_id else None,
        "cost_basis": "list",
        "total_list_cost_usd": total,
        "daily": daily,
        "by_product": by_product,
        "message": None,
    }


def fetch_top_skus(
    *,
    days: int = 30,
    limit: int = 25,
    workspace_id: Optional[str] = None,
    cfg: Optional[FinOpsConfig] = None,
) -> dict[str, Any]:
    cfg = cfg or get_finops_config()
    days = max(1, min(int(days), 730))
    limit = max(1, min(int(limit), 100))

    if not cfg.enabled:
        return {
            "available": False,
            "configured": False,
            "days": days,
            "cost_basis": "list",
            "skus": [],
            "message": "FinOps warehouse is not configured.",
        }

    ws_filter = ""
    if workspace_id and workspace_id.strip():
        safe_ws = workspace_id.strip().replace("'", "''")
        ws_filter = f" AND workspace_id = '{safe_ws}'"

    sql = f"""
    SELECT
      sku_name,
      billing_origin_product,
      cloud,
      usage_unit,
      SUM(usage_quantity) AS usage_quantity,
      SUM(list_cost_usd) AS list_cost_usd,
      SUM(usage_record_count) AS usage_record_count
    FROM {cfg.fqn_prefix}.cost_daily
    WHERE usage_date >= date_sub(current_date(), {days})
    {ws_filter}
    GROUP BY sku_name, billing_origin_product, cloud, usage_unit
    ORDER BY list_cost_usd DESC
    LIMIT {limit}
    """
    try:
        rows = execute_sql(sql, warehouse_id=cfg.warehouse_id or None)
    except Exception as exc:
        logger.warning("FinOps top SKUs query failed: %s", exc)
        return {
            "available": False,
            "configured": True,
            "days": days,
            "cost_basis": "list",
            "skus": [],
            "message": str(exc),
        }

    skus = [
        {
            "sku_name": r.get("sku_name"),
            "billing_origin_product": r.get("billing_origin_product"),
            "cloud": r.get("cloud"),
            "usage_unit": r.get("usage_unit"),
            "usage_quantity": _as_float(r.get("usage_quantity")),
            "list_cost_usd": _as_float(r.get("list_cost_usd")),
            "usage_record_count": _as_int(r.get("usage_record_count")),
        }
        for r in rows
    ]
    return {
        "available": True,
        "configured": True,
        "days": days,
        "cost_basis": "list",
        "skus": skus,
        "message": None,
    }


_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def build_tag_pack(
    estimate_id: str,
    line_items: list[Any],
) -> dict[str, Any]:
    """Suggested custom_tags for jobs/clusters/serverless policies."""
    eid = str(estimate_id).strip()
    estimate = {TAG_ESTIMATE_ID: eid}
    items = []
    for li in line_items:
        lid = str(getattr(li, "line_item_id", "") or "")
        wtype = getattr(li, "workload_type", None)
        wname = getattr(li, "workload_name", None)
        tags = {TAG_ESTIMATE_ID: eid}
        if wtype:
            tags[TAG_WORKLOAD_TYPE] = str(wtype).upper()
        if lid:
            tags[TAG_LINE_ITEM_ID] = lid
        items.append(
            {
                "line_item_id": lid,
                "workload_name": wname,
                "workload_type": wtype,
                "tags": tags,
            }
        )
    return {
        "estimate": estimate,
        "line_items": items,
        "tag_keys": {
            "estimate_id": TAG_ESTIMATE_ID,
            "workload_type": TAG_WORKLOAD_TYPE,
            "line_item_id": TAG_LINE_ITEM_ID,
        },
        "notes": (
            "Apply tags on compute resources or serverless usage policies. "
            "See etl/finops/TAGGING.md."
        ),
    }


def planned_monthly_from_response(cost_calculation_response: Any) -> float:
    """Extract monthly plan $ from a stored calculator response JSON."""
    if not cost_calculation_response or not isinstance(cost_calculation_response, dict):
        return 0.0
    candidates = [cost_calculation_response]
    data = cost_calculation_response.get("data")
    if isinstance(data, dict):
        candidates.append(data)
    for blob in candidates:
        tc = blob.get("total_cost")
        if isinstance(tc, dict):
            val = tc.get("cost_per_month")
            if val is not None:
                return _as_float(val)
        if isinstance(tc, (int, float)):
            return float(tc)
        if blob.get("cost_per_month") is not None:
            return _as_float(blob.get("cost_per_month"))
    return 0.0


def fetch_estimate_actuals(
    estimate_id: str,
    *,
    days: int = 30,
    cfg: Optional[FinOpsConfig] = None,
) -> dict[str, Any]:
    """Tagged list-cost actuals for one estimate id from cost_by_estimate_daily."""
    cfg = cfg or get_finops_config()
    days = max(1, min(int(days), 730))
    eid = (estimate_id or "").strip()
    if not _UUID_RE.match(eid):
        return {
            "available": False,
            "configured": cfg.enabled,
            "estimate_id": eid,
            "days": days,
            "actual_list_cost_usd": 0.0,
            "by_product": [],
            "daily": [],
            "message": "estimate_id must be a UUID",
        }

    if not cfg.enabled:
        return {
            "available": False,
            "configured": False,
            "estimate_id": eid,
            "days": days,
            "actual_list_cost_usd": 0.0,
            "by_product": [],
            "daily": [],
            "message": "FinOps warehouse is not configured.",
        }

    safe_id = eid.replace("'", "''")
    daily_sql = f"""
    SELECT
      usage_date,
      SUM(list_cost_usd) AS list_cost_usd
    FROM {cfg.fqn_prefix}.cost_by_estimate_daily
    WHERE lakemeter_estimate_id = '{safe_id}'
      AND usage_date >= date_sub(current_date(), {days})
    GROUP BY usage_date
    ORDER BY usage_date
    """
    product_sql = f"""
    SELECT
      COALESCE(lakemeter_workload_type, billing_origin_product, 'UNKNOWN') AS product_key,
      billing_origin_product,
      lakemeter_workload_type,
      SUM(list_cost_usd) AS list_cost_usd,
      SUM(usage_quantity) AS usage_quantity
    FROM {cfg.fqn_prefix}.cost_by_estimate_daily
    WHERE lakemeter_estimate_id = '{safe_id}'
      AND usage_date >= date_sub(current_date(), {days})
    GROUP BY
      COALESCE(lakemeter_workload_type, billing_origin_product, 'UNKNOWN'),
      billing_origin_product,
      lakemeter_workload_type
    ORDER BY list_cost_usd DESC
    """
    try:
        daily_rows = execute_sql(daily_sql, warehouse_id=cfg.warehouse_id or None)
        product_rows = execute_sql(product_sql, warehouse_id=cfg.warehouse_id or None)
    except Exception as exc:
        logger.warning("FinOps estimate actuals failed: %s", exc)
        return {
            "available": False,
            "configured": True,
            "estimate_id": eid,
            "days": days,
            "actual_list_cost_usd": 0.0,
            "by_product": [],
            "daily": [],
            "message": str(exc),
        }

    daily = [
        {
            "usage_date": str(r.get("usage_date")),
            "list_cost_usd": _as_float(r.get("list_cost_usd")),
        }
        for r in daily_rows
    ]
    by_product = [
        {
            "product_key": r.get("product_key"),
            "billing_origin_product": r.get("billing_origin_product"),
            "lakemeter_workload_type": r.get("lakemeter_workload_type"),
            "list_cost_usd": _as_float(r.get("list_cost_usd")),
            "usage_quantity": _as_float(r.get("usage_quantity")),
        }
        for r in product_rows
    ]
    actual = sum(d["list_cost_usd"] for d in daily)
    return {
        "available": True,
        "configured": True,
        "estimate_id": eid,
        "days": days,
        "actual_list_cost_usd": actual,
        "by_product": by_product,
        "daily": daily,
        "cost_basis": "list",
        "message": None,
    }


def build_variance(
    *,
    estimate_id: str,
    estimate_name: str,
    planned_monthly_usd: float,
    days: int,
    actuals: dict[str, Any],
) -> dict[str, Any]:
    """Combine Lakebase plan with gold actuals into a variance payload."""
    days = max(1, min(int(days), 730))
    plan_period = _as_float(planned_monthly_usd) * (days / 30.0)
    actual = _as_float(actuals.get("actual_list_cost_usd"))
    variance_usd = actual - plan_period
    variance_pct = (variance_usd / plan_period * 100.0) if plan_period > 0 else None
    return {
        "available": bool(actuals.get("available")),
        "configured": bool(actuals.get("configured")),
        "estimate_id": estimate_id,
        "estimate_name": estimate_name,
        "days": days,
        "cost_basis": "list",
        "plan_monthly_usd": _as_float(planned_monthly_usd),
        "plan_period_usd": plan_period,
        "actual_list_cost_usd": actual,
        "variance_usd": variance_usd,
        "variance_pct": variance_pct,
        "by_product": actuals.get("by_product") or [],
        "daily": actuals.get("daily") or [],
        "message": actuals.get("message"),
        "notes": (
            "Plan prorated as monthly × (days/30). Actuals are tagged list cost only. "
            "See etl/finops/TAGGING.md."
        ),
    }
