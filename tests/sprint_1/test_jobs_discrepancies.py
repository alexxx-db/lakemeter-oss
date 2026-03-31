"""
Sprint 1: Frontend vs Backend Discrepancy Documentation Tests

These tests document and verify known discrepancies between the frontend
(costCalculation.ts) and backend (export.py) calculation logic for Jobs.

Each test explicitly documents the discrepancy with expected values from both sides.
"""
import pytest
import os
import sys

BACKEND_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'backend')
sys.path.insert(0, BACKEND_DIR)

from app.routes.export import _calculate_dbu_per_hour, _get_sku_type
from tests.sprint_1.test_jobs_calculations import frontend_calc_jobs, backend_calc_jobs
from tests.sprint_1.conftest import make_line_item


class TestDiscrepancy01ServerlessPhoton:
    """
    DISCREPANCY #1: Serverless Photon Handling

    Frontend: Photon is ALWAYS enabled for serverless (built-in).
              costCalculation.ts lines 273-276: if serverless, photon_mult = 2.0
    Backend:  Photon only applied if photon_enabled=True flag is set.
              export.py lines 330-331: if item.photon_enabled: base_dbu *= 2

    Impact: For serverless Jobs with photon_enabled=False:
    - Frontend shows 2x higher DBU/hr than backend exports to Excel
    - This means Excel exports UNDERSTATE costs relative to what the user sees in the browser
    """

    def test_serverless_standard_no_photon_flag(self):
        """Frontend=6.0, Backend=3.0 — 2x discrepancy."""
        fe = frontend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
            photon_enabled=False, serverless_enabled=True,
            serverless_mode="standard", hours_per_month=100,
        )
        be = backend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
            photon_enabled=False, serverless_enabled=True,
            serverless_mode="standard", hours_per_month=100,
        )
        assert fe["dbu_per_hour"] == pytest.approx(6.0)
        assert be["dbu_per_hour"] == pytest.approx(3.0)
        discrepancy_ratio = fe["dbu_per_hour"] / be["dbu_per_hour"]
        assert discrepancy_ratio == pytest.approx(2.0), \
            f"Frontend is {discrepancy_ratio}x higher than backend"

    def test_serverless_performance_no_photon_flag(self):
        """Frontend=12.0, Backend=6.0 — 2x discrepancy."""
        fe = frontend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
            photon_enabled=False, serverless_enabled=True,
            serverless_mode="performance", hours_per_month=100,
        )
        be = backend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
            photon_enabled=False, serverless_enabled=True,
            serverless_mode="performance", hours_per_month=100,
        )
        assert fe["dbu_per_hour"] == pytest.approx(12.0)
        assert be["dbu_per_hour"] == pytest.approx(6.0)

    def test_no_discrepancy_when_photon_flag_set(self):
        """When photon_enabled=True, both agree."""
        fe = frontend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
            photon_enabled=True, serverless_enabled=True,
            serverless_mode="standard", hours_per_month=100,
        )
        be = backend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
            photon_enabled=True, serverless_enabled=True,
            serverless_mode="standard", hours_per_month=100,
        )
        assert fe["dbu_per_hour"] == pytest.approx(be["dbu_per_hour"])

    def test_backend_export_directly(self):
        """Verify the actual backend export function has this behavior."""
        item = make_line_item(
            workload_type="JOBS",
            driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge",
            num_workers=2,
            photon_enabled=False,
            serverless_enabled=True,
            serverless_mode="standard",
        )
        dbu_hr, _ = _calculate_dbu_per_hour(item, "aws")
        # Backend without photon flag: 1.0 + 1.0×2 = 3.0 (no photon)
        assert dbu_hr == pytest.approx(3.0)


class TestDiscrepancy02NumWorkersDefault:
    """
    DISCREPANCY #2: Default num_workers

    Frontend: num_workers defaults to 0 when falsy
              costCalculation.ts line 125: const numWorkers = item.num_workers || 0
    Backend:  num_workers defaults to 1 when falsy
              export.py line 327: num_workers = int(item.num_workers or 1)

    Impact: When num_workers is 0 or None:
    - Frontend: driver_dbu only (e.g., 1.0)
    - Backend: driver_dbu + 1×worker_dbu (e.g., 2.0)
    - Excel shows higher DBU/hr than browser for 0-worker configs
    """

    def test_zero_workers(self):
        """Frontend=1.0, Backend=2.0 when num_workers=0."""
        fe = frontend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=0,
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=100,
        )
        be = backend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=0,
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=100,
        )
        assert fe["dbu_per_hour"] == pytest.approx(1.0)
        assert be["dbu_per_hour"] == pytest.approx(2.0)

    def test_backend_export_directly_zero_workers(self):
        """Verify the actual backend export function defaults to 1."""
        item = make_line_item(
            workload_type="JOBS",
            driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge",
            num_workers=0,
            photon_enabled=False,
            serverless_enabled=False,
        )
        dbu_hr, _ = _calculate_dbu_per_hour(item, "aws")
        # Backend: int(0 or 1) = 1, so 1.0 + 1.0×1 = 2.0
        assert dbu_hr == pytest.approx(2.0)

    def test_nonzero_workers_no_discrepancy(self):
        """When num_workers > 0, both agree."""
        for n in [1, 2, 5, 10]:
            fe = frontend_calc_jobs(
                driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=n,
                photon_enabled=False, serverless_enabled=False,
                hours_per_month=100,
            )
            be = backend_calc_jobs(
                driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=n,
                photon_enabled=False, serverless_enabled=False,
                hours_per_month=100,
            )
            assert fe["dbu_per_hour"] == pytest.approx(be["dbu_per_hour"]), \
                f"Mismatch at num_workers={n}"


class TestDiscrepancy03BackendHoursFallback:
    """
    DISCREPANCY #3: Hours fallback when no usage config

    Frontend: Returns 0 hours (no fallback)
              costCalculation.ts: hoursPerMonth stays 0 if nothing set
    Backend:  Returns 11 hours as fallback
              export.py line 301: return (1 * 30 / 60) * 22

    Impact: If a line item has no usage config at all:
    - Frontend shows 0 DBUs and $0 cost
    - Backend Excel shows 11 hours worth of DBUs and cost
    """

    def test_no_usage_config(self):
        """Frontend=0 hours, Backend=11 hours when nothing set."""
        fe = frontend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
            photon_enabled=False, serverless_enabled=False,
        )
        be = backend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
            photon_enabled=False, serverless_enabled=False,
        )
        assert fe["hours_per_month"] == pytest.approx(0.0)
        assert be["hours_per_month"] == pytest.approx(11.0)
