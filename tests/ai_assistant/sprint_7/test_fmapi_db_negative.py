"""Tests: Non-FMAPI_DATABRICKS requests should NOT produce FMAPI_DATABRICKS type."""
import pytest


class TestFmapiDbNegativeClaude:
    """Claude (proprietary) request must NOT be FMAPI_DATABRICKS (AC-18)."""

    def test_not_fmapi_databricks(self, non_db_claude_proposal):
        wt = non_db_claude_proposal["workload_type"]
        assert wt != "FMAPI_DATABRICKS", (
            f"Claude request should NOT be FMAPI_DATABRICKS, got {wt}"
        )

    def test_is_fmapi_proprietary(self, non_db_claude_proposal):
        wt = non_db_claude_proposal["workload_type"]
        assert wt == "FMAPI_PROPRIETARY", (
            f"Claude should be FMAPI_PROPRIETARY, got {wt}"
        )


class TestFmapiDbNegativeGpu:
    """GPU model serving request must NOT be FMAPI_DATABRICKS (AC-19)."""

    def test_not_fmapi_databricks(self, non_db_gpu_proposal):
        wt = non_db_gpu_proposal["workload_type"]
        assert wt != "FMAPI_DATABRICKS", (
            f"GPU serving request should NOT be FMAPI_DATABRICKS, got {wt}"
        )

    def test_is_model_serving(self, non_db_gpu_proposal):
        wt = non_db_gpu_proposal["workload_type"]
        assert wt == "MODEL_SERVING", (
            f"GPU serving should be MODEL_SERVING, got {wt}"
        )
