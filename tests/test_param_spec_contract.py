"""Contract test: LINE_ITEM_COST_PARAM_SPECS vs the SQL function signature.

Pins the backend's single source of truth
(``LINE_ITEM_COST_PARAM_SPECS`` in ``app.services.lakebase_queries``)
against the authoritative PostgreSQL signature of
``lakemeter.calculate_line_item_costs`` in
``etl/lakebase_setup/functions/09_Main_Orchestrator.py`` (and its
``scripts/functions`` copy), so the two can never drift silently.

This is the regression guard for the wrong-slot class of bug, e.g. a
calculator passing the DLT edition into the ``p_dbsql_warehouse_type``
slot — which silently priced DLT gateway compute as CORE instead of
ADVANCED because the DLT branch reads ``p_dlt_edition``.
"""
import ast
import os
import re
import sys

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
BACKEND_DIR = os.path.join(REPO_ROOT, 'backend')
sys.path.insert(0, BACKEND_DIR)

ORCHESTRATOR_PATHS = [
    os.path.join(REPO_ROOT, 'etl', 'lakebase_setup', 'functions',
                 '09_Main_Orchestrator.py'),
    os.path.join(REPO_ROOT, 'scripts', 'functions', '09_Main_Orchestrator.py'),
]

from app.services.lakebase_queries import (  # noqa: E402
    LINE_ITEM_COST_PARAM_SPECS, _LINE_ITEM_COST_SQL,
)


def _load_build_cost_params():
    """Import build_cost_params directly from helpers.py.

    Loaded by file path so the heavy app.routes package __init__ (FastAPI
    routers and their dependency chain) is not required for this contract
    test.
    """
    import importlib.util
    path = os.path.join(BACKEND_DIR, 'app', 'routes', 'calculate', 'helpers.py')
    spec = importlib.util.spec_from_file_location('calculate_helpers', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_cost_params


build_cost_params = _load_build_cost_params()

VALID_WORKLOAD_TYPES = {
    'JOBS', 'ALL_PURPOSE', 'DLT', 'DBSQL', 'VECTOR_SEARCH',
    'MODEL_SERVING', 'FMAPI_DATABRICKS', 'FMAPI_PROPRIETARY', 'LAKEBASE',
}

_SIGNATURE_RE = re.compile(
    r"CREATE OR REPLACE FUNCTION lakemeter\.calculate_line_item_costs\((.*?)\)\s*RETURNS",
    re.S,
)
_PARAM_RE = re.compile(
    r"(p_[a-z0-9_]+)\s+(VARCHAR|INT|BIGINT|BOOLEAN|DECIMAL)(?:\(\s*\d+(?:\s*,\s*\d+)?\s*\))?",
)


def _sql_signature(path):
    """Extract the ordered (param_name, pg_type) signature from the SQL DDL."""
    with open(path) as f:
        src = f.read()
    m = _SIGNATURE_RE.search(src)
    assert m, f"calculate_line_item_costs DDL not found in {path}"
    return _PARAM_RE.findall(m.group(1))


def _calculate_route_files():
    calc_dir = os.path.join(BACKEND_DIR, 'app', 'routes', 'calculate')
    for name in sorted(os.listdir(calc_dir)):
        if name.endswith('.py') and name != '__init__.py':
            yield os.path.join(calc_dir, name)


def _build_cost_params_calls(path):
    """Yield (lineno, call) AST nodes for every build_cost_params call."""
    with open(path) as f:
        tree = ast.parse(f.read(), filename=path)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else (
                func.attr if isinstance(func, ast.Attribute) else None)
            if name == 'build_cost_params':
                yield node.lineno, node


class TestSignatureContract:
    """The param spec table must mirror the SQL function exactly."""

    @pytest.mark.parametrize("path", ORCHESTRATOR_PATHS)
    def test_param_specs_match_orchestrator_signature(self, path):
        sql_sig = _sql_signature(path)
        spec_sig = [(sql_name, pg_type)
                    for _, sql_name, pg_type in LINE_ITEM_COST_PARAM_SPECS]
        assert len(spec_sig) == 35, (
            f"expected 35 param specs, found {len(spec_sig)}")
        assert spec_sig == sql_sig, (
            f"LINE_ITEM_COST_PARAM_SPECS is out of sync with {path}:\n"
            f"specs: {spec_sig}\n"
            f"sql:   {sql_sig}")

    def test_orchestrator_copies_have_identical_signatures(self):
        sigs = [_sql_signature(p) for p in ORCHESTRATOR_PATHS]
        assert sigs[0] == sigs[1], (
            "etl/ and scripts/ copies of 09_Main_Orchestrator.py declare "
            "different calculate_line_item_costs signatures")


class TestGeneratedSQL:
    """The generated query must bind every parameter by name."""

    def test_every_param_bound_by_name_with_matching_type(self):
        sql = str(_LINE_ITEM_COST_SQL)
        for semantic, sql_name, pg_type in LINE_ITEM_COST_PARAM_SPECS:
            expected = f"{sql_name} => CAST(:{semantic} AS {pg_type})"
            assert expected in sql, (
                f"generated SQL missing named binding: {expected}")

    def test_no_positional_p_n_bindings_remain(self):
        """Positional :p1..:p35 binds are the fragile pattern we replaced."""
        assert not re.search(r":p\d+\b", str(_LINE_ITEM_COST_SQL)), (
            "generated SQL still uses positional :pN binds")


class TestBuilderAndCallSites:
    """build_cost_params and its callers must stay on the semantic contract."""

    def test_build_cost_params_keys_match_specs(self):
        params = build_cost_params(
            workload_type='JOBS', cloud='aws', region='us-east-1', tier='premium')
        spec_keys = [semantic for semantic, _, _ in LINE_ITEM_COST_PARAM_SPECS]
        assert list(params.keys()) == spec_keys

    def test_call_sites_use_only_known_kwargs(self):
        spec_keys = {semantic for semantic, _, _ in LINE_ITEM_COST_PARAM_SPECS}
        errors = []
        for path in _calculate_route_files():
            for lineno, call in _build_cost_params_calls(path):
                if call.args:
                    errors.append(
                        f"{os.path.basename(path)}:{lineno}: positional args "
                        f"passed to keyword-only build_cost_params")
                for kw in call.keywords:
                    if kw.arg is None:
                        errors.append(
                            f"{os.path.basename(path)}:{lineno}: **kwargs "
                            f"unpacking hides param names from the contract")
                    elif kw.arg not in spec_keys:
                        errors.append(
                            f"{os.path.basename(path)}:{lineno}: unknown "
                            f"kwarg '{kw.arg}' (not in "
                            f"LINE_ITEM_COST_PARAM_SPECS)")
        assert not errors, "\n".join(errors)

    def test_call_site_workload_type_literals_are_valid(self):
        errors = []
        for path in _calculate_route_files():
            for lineno, call in _build_cost_params_calls(path):
                for kw in call.keywords:
                    if kw.arg == 'workload_type' and isinstance(
                            kw.value, ast.Constant):
                        if kw.value.value not in VALID_WORKLOAD_TYPES:
                            errors.append(
                                f"{os.path.basename(path)}:{lineno}: invalid "
                                f"workload_type literal {kw.value.value!r}")
        assert not errors, "\n".join(errors)
