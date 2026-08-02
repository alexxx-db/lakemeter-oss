"""VM cost lookup tests: DB-first regional pricing with documented fallbacks.

Covers the fix for hardcoded/static-first VM pricing in the Excel export:
- lakemeter.sync_pricing_vm_costs is authoritative (region/tier/payment-option
  aware) and wins over the static DEFAULT_VM_PRICING reference map
- static defaults are a documented fallback (noted in the export)
- unknown instances produce a not-found note instead of silent $0
- reserved tiers normalize a missing payment option to 'no_upfront'
"""
import os
import sys
import pytest

BACKEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, BACKEND_DIR)

from app.routes.export.excel_builder import (
    _resolve_vm_price, _query_vm_cost_from_db, _lookup_dbsql_vm_costs,
)
from app.routes.vm_pricing import DEFAULT_VM_PRICING


class FakeRow:
    def __init__(self, cost):
        self.cost_per_hour = cost


class FakeResult:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class FakeDB:
    """Fake db session returning a fixed price and recording queries."""
    def __init__(self, price=0.45):
        self.price = price
        self.queries = []

    def execute(self, stmt, params):
        self.queries.append((str(stmt), params))
        row = FakeRow(self.price) if self.price is not None else None
        return FakeResult(row)


def test_db_price_wins_over_static_default():
    """Authoritative Lakebase price takes precedence over the static map."""
    db = FakeDB(price=0.45)
    notes = []
    price = _resolve_vm_price('aws', 'eu-west-1', 'i3.xlarge', 'on_demand',
                              None, db, notes, 'Driver')
    assert price == 0.45  # static default would be 0.312 (us-east-1)
    assert notes == []  # authoritative hit needs no fallback note


def test_db_query_is_region_tier_and_option_aware():
    db = FakeDB(price=0.1)
    _resolve_vm_price('aws', 'eu-west-1', 'i3.xlarge', 'on_demand',
                      None, db, [], 'Driver')
    _, params = db.queries[0]
    assert params['region'] == 'eu-west-1'
    assert params['pricing_tier'] == 'on_demand'
    assert params['payment_option'] == 'NA'
    assert params['instance_type'] == 'i3.xlarge'


def test_static_default_fallback_is_noted():
    """Without a DB, the static reference price is used and disclosed."""
    notes = []
    price = _resolve_vm_price('aws', 'us-east-1', 'i3.xlarge', 'on_demand',
                              None, None, notes, 'Driver')
    expected = DEFAULT_VM_PRICING['aws']['i3.xlarge']['on_demand']
    assert price == expected
    assert any('default reference price' in n for n in notes)


def test_unknown_instance_produces_not_found_note():
    notes = []
    price = _resolve_vm_price('aws', 'us-east-1', 'nonexistent.42xlarge',
                              'on_demand', None, None, notes, 'Worker')
    assert price == 0.0
    assert any('not found' in n and 'nonexistent.42xlarge' in n for n in notes)


def test_db_miss_falls_through_to_static_default():
    db = FakeDB(price=None)  # DB reachable, instance missing
    notes = []
    price = _resolve_vm_price('aws', 'us-east-1', 'i3.xlarge', 'on_demand',
                              None, db, notes, 'Driver')
    assert price == DEFAULT_VM_PRICING['aws']['i3.xlarge']['on_demand']
    assert any('default reference price' in n for n in notes)


def test_reserved_tier_normalizes_payment_option():
    """reserved_1y with no explicit option queries 'no_upfront' rows."""
    db = FakeDB(price=0.22)
    price = _resolve_vm_price('aws', 'us-east-1', 'i3.xlarge', 'reserved_1y',
                              None, db, [], 'Driver')
    assert price == 0.22
    _, params = db.queries[0]
    assert params['pricing_tier'] == 'reserved_1y'
    assert params['payment_option'] == 'no_upfront'


def test_reserved_tier_skips_static_defaults_without_db():
    """Static map has no reserved prices; without a DB this is a noted miss."""
    notes = []
    price = _resolve_vm_price('aws', 'us-east-1', 'i3.xlarge', 'reserved_1y',
                              'all_upfront', None, notes, 'Driver')
    assert price == 0.0
    assert any('not found' in n for n in notes)


class _FakeItem:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


def test_dbsql_vm_costs_use_db_prices():
    """DBSQL warehouse VM costs come from sync data, not the static map."""
    from app.routes.export import pricing as export_pricing
    key = 'aws:classic:Small'
    if key not in export_pricing.DBSQL_WAREHOUSE_CONFIG:
        pytest.skip('warehouse config not in static data')
    cfg = export_pricing.DBSQL_WAREHOUSE_CONFIG[key]
    item = _FakeItem(dbsql_warehouse_type='CLASSIC', dbsql_warehouse_size='Small',
                     dbsql_vm_pricing_tier='on_demand', dbsql_vm_payment_option=None)
    db = FakeDB(price=0.99)
    d, w, n = _lookup_dbsql_vm_costs(item, 'aws', 'us-east-1', {}, db, [])
    assert d == 0.99 and w == 0.99
    assert n == (cfg['worker_count'] if isinstance(cfg, dict) else cfg.worker_count)
    # both driver and worker queried with their own instance types
    insts = [p['instance_type'] for _, p in db.queries]
    if isinstance(cfg, dict):
        assert cfg['driver_instance_type'] in insts
        assert cfg['worker_instance_type'] in insts
