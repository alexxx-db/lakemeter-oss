"""Tests: AI assistant proposes DLT (SDP) workloads from natural language.

Uses module-scoped fixtures to minimise expensive AI calls.
Three proposal variants: PRO serverless, CORE basic, ADVANCED with monitoring.
Plus negative test: non-DLT prompt must NOT produce DLT workload.
"""
import pytest

from tests.ai_assistant.conftest import send_chat_until_proposal
from tests.ai_assistant.sprint_3.prompts import (
    DLT_PRO_PRIMARY, DLT_PRO_FOLLOWUP, DLT_PRO_FINAL,
    DLT_CORE_PRIMARY, DLT_CORE_FOLLOWUP, DLT_CORE_FINAL,
    DLT_ADVANCED_PRIMARY, DLT_ADVANCED_FOLLOWUP, DLT_ADVANCED_FINAL,
    NON_DLT_PRIMARY, NON_DLT_FOLLOWUP, NON_DLT_FINAL,
)


# -- Module-scoped fixtures (one AI call per variant) --------------------------


@pytest.fixture(scope="module")
def dlt_pro_proposal(http_client, test_estimate):
    """Single AI call for DLT Pro serverless — shared by basic tests."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [DLT_PRO_PRIMARY, DLT_PRO_FOLLOWUP, DLT_PRO_FINAL],
        test_estimate,
    )
    return proposal


@pytest.fixture(scope="module")
def dlt_core_proposal(http_client, test_estimate):
    """Single AI call for DLT Core classic."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [DLT_CORE_PRIMARY, DLT_CORE_FOLLOWUP, DLT_CORE_FINAL],
        test_estimate,
    )
    return proposal


@pytest.fixture(scope="module")
def dlt_advanced_proposal(http_client, test_estimate):
    """Single AI call for DLT Advanced serverless."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [DLT_ADVANCED_PRIMARY, DLT_ADVANCED_FOLLOWUP, DLT_ADVANCED_FINAL],
        test_estimate,
    )
    return proposal


@pytest.fixture(scope="module")
def non_dlt_proposal(http_client, test_estimate):
    """AI call for an interactive compute request — should NOT be DLT."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [NON_DLT_PRIMARY, NON_DLT_FOLLOWUP, NON_DLT_FINAL],
        test_estimate,
    )
    return proposal


# -- DLT Pro Serverless (basic) tests -----------------------------------------


class TestDltProposalBasic:
    """AI proposes a DLT/SDP workload with Pro edition and correct fields."""

    def test_workload_type_is_dlt(self, dlt_pro_proposal):
        assert dlt_pro_proposal["workload_type"] == "DLT", (
            f"Expected DLT, got {dlt_pro_proposal['workload_type']}"
        )

    def test_workload_name_non_empty(self, dlt_pro_proposal):
        name = dlt_pro_proposal.get("workload_name", "")
        assert name and len(name) >= 3, (
            f"workload_name too short or missing: '{name}'"
        )

    def test_dlt_edition_is_pro(self, dlt_pro_proposal):
        edition = (dlt_pro_proposal.get("dlt_edition") or "").upper()
        assert "PRO" in edition, (
            f"dlt_edition should contain PRO, got '{dlt_pro_proposal.get('dlt_edition')}'"
        )

    def test_serverless_enabled(self, dlt_pro_proposal):
        assert dlt_pro_proposal.get("serverless_enabled") is True, (
            "serverless_enabled should be True for serverless DLT request"
        )

    def test_reason_populated(self, dlt_pro_proposal):
        reason = dlt_pro_proposal.get("reason", "")
        assert reason and len(reason) >= 10, (
            f"reason too short or missing: '{reason}'"
        )

    def test_notes_populated(self, dlt_pro_proposal):
        notes = dlt_pro_proposal.get("notes", "")
        assert notes and len(notes) >= 1, (
            f"notes should be populated: '{notes}'"
        )

    def test_proposal_id_present(self, dlt_pro_proposal):
        pid = dlt_pro_proposal.get("proposal_id", "")
        assert pid, "proposal_id must be present for confirm/reject flow"

    def test_scheduling_fields_present(self, dlt_pro_proposal):
        has_runs = dlt_pro_proposal.get("runs_per_day") is not None
        has_hours = dlt_pro_proposal.get("hours_per_month") is not None
        assert has_runs or has_hours, (
            "DLT proposal should have runs_per_day or hours_per_month"
        )

    def test_serverless_explicitly_set(self, dlt_pro_proposal):
        se = dlt_pro_proposal.get("serverless_enabled")
        assert se is not None, "serverless_enabled should be explicitly set"


# -- DLT Core edition tests ----------------------------------------------------


class TestDltCoreEdition:
    """AI proposes DLT with Core edition for basic ETL pipelines."""

    def test_workload_type_is_dlt(self, dlt_core_proposal):
        assert dlt_core_proposal["workload_type"] == "DLT", (
            f"Expected DLT, got {dlt_core_proposal['workload_type']}"
        )

    def test_dlt_edition_is_core(self, dlt_core_proposal):
        edition = (dlt_core_proposal.get("dlt_edition") or "").upper()
        assert "CORE" in edition, (
            f"dlt_edition should contain CORE for basic pipeline, "
            f"got '{dlt_core_proposal.get('dlt_edition')}'"
        )

    def test_workload_name_non_empty(self, dlt_core_proposal):
        name = dlt_core_proposal.get("workload_name", "")
        assert name and len(name) >= 3, (
            f"workload_name too short or missing: '{name}'"
        )

    def test_proposal_id_present(self, dlt_core_proposal):
        pid = dlt_core_proposal.get("proposal_id", "")
        assert pid, "proposal_id must be present"

    def test_reason_populated(self, dlt_core_proposal):
        reason = dlt_core_proposal.get("reason", "")
        assert reason and len(reason) >= 10, (
            f"reason too short or missing: '{reason}'"
        )

    def test_notes_populated(self, dlt_core_proposal):
        notes = dlt_core_proposal.get("notes", "")
        assert notes and len(notes) >= 1, (
            f"notes should be populated: '{notes}'"
        )

    def test_serverless_explicitly_set(self, dlt_core_proposal):
        se = dlt_core_proposal.get("serverless_enabled")
        assert se is not None, "serverless_enabled should be explicitly set"

    def test_classic_compute_fields(self, dlt_core_proposal):
        """Core classic should have node types and worker count."""
        if dlt_core_proposal.get("serverless_enabled"):
            pytest.skip("AI chose serverless — classic compute fields N/A")
        has_nodes = (
            dlt_core_proposal.get("driver_node_type")
            or dlt_core_proposal.get("worker_node_type")
        )
        assert has_nodes, "Classic DLT should have node types"
        nw = dlt_core_proposal.get("num_workers")
        assert nw is not None and nw >= 1, (
            f"Classic DLT should have num_workers >= 1, got {nw}"
        )

    def test_photon_set_for_classic(self, dlt_core_proposal):
        """If classic compute, photon_enabled should be set."""
        if dlt_core_proposal.get("serverless_enabled"):
            pytest.skip("AI chose serverless — photon check N/A")
        pe = dlt_core_proposal.get("photon_enabled")
        assert pe is not None, "photon_enabled should be set for classic"

    def test_scheduling_fields_present(self, dlt_core_proposal):
        has_runs = dlt_core_proposal.get("runs_per_day") is not None
        has_hours = dlt_core_proposal.get("hours_per_month") is not None
        assert has_runs or has_hours, (
            "DLT Core proposal should have runs_per_day or hours_per_month"
        )


# -- DLT Advanced edition tests ------------------------------------------------


class TestDltAdvancedEdition:
    """AI proposes DLT with Advanced edition for full monitoring."""

    def test_workload_type_is_dlt(self, dlt_advanced_proposal):
        assert dlt_advanced_proposal["workload_type"] == "DLT", (
            f"Expected DLT, got {dlt_advanced_proposal['workload_type']}"
        )

    def test_dlt_edition_is_advanced(self, dlt_advanced_proposal):
        edition = (dlt_advanced_proposal.get("dlt_edition") or "").upper()
        assert "ADVANCED" in edition, (
            f"dlt_edition should contain ADVANCED, "
            f"got '{dlt_advanced_proposal.get('dlt_edition')}'"
        )

    def test_workload_name_non_empty(self, dlt_advanced_proposal):
        name = dlt_advanced_proposal.get("workload_name", "")
        assert name and len(name) >= 3, (
            f"workload_name too short or missing: '{name}'"
        )

    def test_proposal_id_present(self, dlt_advanced_proposal):
        pid = dlt_advanced_proposal.get("proposal_id", "")
        assert pid, "proposal_id must be present"

    def test_reason_populated(self, dlt_advanced_proposal):
        reason = dlt_advanced_proposal.get("reason", "")
        assert reason and len(reason) >= 10, (
            f"reason too short or missing: '{reason}'"
        )

    def test_notes_populated(self, dlt_advanced_proposal):
        notes = dlt_advanced_proposal.get("notes", "")
        assert notes and len(notes) >= 1, (
            f"notes should be populated: '{notes}'"
        )

    def test_serverless_explicitly_set(self, dlt_advanced_proposal):
        se = dlt_advanced_proposal.get("serverless_enabled")
        assert se is not None, "serverless_enabled should be explicitly set"

    def test_scheduling_fields_present(self, dlt_advanced_proposal):
        has_runs = dlt_advanced_proposal.get("runs_per_day") is not None
        has_hours = dlt_advanced_proposal.get("hours_per_month") is not None
        assert has_runs or has_hours, (
            "DLT Advanced proposal should have scheduling fields"
        )


# -- Negative test: non-DLT prompt must NOT produce DLT -----------------------


class TestDltNegativeDiscrimination:
    """Non-DLT prompt (interactive compute) must NOT produce a DLT workload."""

    def test_non_dlt_prompt_does_not_produce_dlt(self, non_dlt_proposal):
        wt = non_dlt_proposal.get("workload_type", "")
        assert wt != "DLT", (
            f"Interactive compute prompt should NOT produce DLT, got {wt}"
        )

    def test_non_dlt_prompt_produces_all_purpose(self, non_dlt_proposal):
        wt = non_dlt_proposal.get("workload_type", "")
        assert wt == "ALL_PURPOSE", (
            f"Interactive compute prompt should produce ALL_PURPOSE, got {wt}"
        )
