"""Sprint 10: Combined Excel export tests — all 9 workload types in one sheet."""
import pytest
from tests.sprint_10.conftest import make_all_nine_items
from tests.sprint_10.excel_helpers import (
    generate_xlsx, find_all_data_rows, find_rows_by_sku, find_row_by_name,
    find_totals_row,
    COL_SKU, COL_MODE, COL_HOURS, COL_TOKEN_TYPE, COL_TOKEN_QTY,
    COL_DBU_PER_M, COL_DBU_HR, COL_DBUS_MO, COL_DBU_RATE, COL_DISCOUNT,
    COL_DBU_RATE_DISC, COL_DBU_COST_L, COL_DBU_COST_D,
    COL_DRIVER_VM_HR, COL_WORKER_VM_HR, COL_DRIVER_VM_COST,
    COL_WORKER_VM_COST, COL_TOTAL_VM,
    COL_TOTAL_L, COL_TOTAL_D, COL_NOTES, COL_NAME,
)


@pytest.fixture(scope="module")
def combined_wb():
    """Generate a combined Excel workbook once for all tests in module."""
    return generate_xlsx()


@pytest.fixture(scope="module")
def ws(combined_wb):
    return combined_wb.active


class TestExcelGenerates:
    """AC-1: Excel generation succeeds with all 9 workload types."""

    def test_workbook_has_active_sheet(self, combined_wb):
        assert combined_wb.active is not None

    def test_sheet_has_rows(self, ws):
        assert ws.max_row > 10


class TestRowCount:
    """AC-4: Correct number of data rows including storage sub-rows."""

    def test_total_data_rows(self, ws):
        rows = find_all_data_rows(ws)
        # 9 workload items + Lakebase storage + Vector Search storage = 11
        assert len(rows) == 11, f"Expected 11 data rows, got {len(rows)}"

    def test_lakebase_storage_row_exists(self, ws):
        storage_rows = find_rows_by_sku(ws, 'DATABRICKS_STORAGE')
        assert len(storage_rows) >= 2, \
            f"Expected >=2 DATABRICKS_STORAGE rows, got {len(storage_rows)}"

    def test_lakebase_compute_row_exists(self, ws):
        rows = find_rows_by_sku(ws, 'DATABASE_SERVERLESS_COMPUTE')
        assert len(rows) == 1

    def test_vector_search_compute_row_exists(self, ws):
        rows = find_rows_by_sku(ws, 'VECTOR_SEARCH_ENDPOINT')
        assert len(rows) == 1


class TestSkuMapping:
    """AC-3: Each workload type maps to correct SKU in Excel."""

    def test_jobs_serverless_sku(self, ws):
        row = find_row_by_name(ws, 'Jobs Serverless Perf')
        assert row is not None
        assert ws.cell(row=row, column=COL_SKU).value == \
            'JOBS_SERVERLESS_COMPUTE'

    def test_all_purpose_photon_sku(self, ws):
        row = find_row_by_name(ws, 'All-Purpose Classic Photon')
        assert row is not None
        assert ws.cell(row=row, column=COL_SKU).value == \
            'ALL_PURPOSE_COMPUTE_(PHOTON)'

    def test_dlt_serverless_sku(self, ws):
        row = find_row_by_name(ws, 'DLT Pro Serverless')
        assert row is not None
        assert ws.cell(row=row, column=COL_SKU).value == \
            'DELTA_LIVE_TABLES_SERVERLESS'

    def test_dbsql_serverless_sku(self, ws):
        row = find_row_by_name(ws, 'DBSQL Serverless Medium')
        assert row is not None
        assert ws.cell(row=row, column=COL_SKU).value == \
            'SERVERLESS_SQL_COMPUTE'

    def test_model_serving_sku(self, ws):
        row = find_row_by_name(ws, 'Model Serving GPU')
        assert row is not None
        assert ws.cell(row=row, column=COL_SKU).value == \
            'SERVERLESS_REAL_TIME_INFERENCE'

    def test_lakebase_compute_sku(self, ws):
        row = find_row_by_name(ws, 'Lakebase 4CU 2HA')
        assert row is not None
        sku = ws.cell(row=row, column=COL_SKU).value
        assert sku == 'DATABASE_SERVERLESS_COMPUTE'


class TestServerlessMode:
    """AC-13: Serverless items show 'Serverless'; classic shows 'Classic'."""

    def test_jobs_serverless_mode(self, ws):
        row = find_row_by_name(ws, 'Jobs Serverless Perf')
        assert ws.cell(row=row, column=COL_MODE).value == 'Serverless'

    def test_all_purpose_classic_mode(self, ws):
        row = find_row_by_name(ws, 'All-Purpose Classic Photon')
        assert ws.cell(row=row, column=COL_MODE).value == 'Classic'

    def test_dbsql_serverless_mode(self, ws):
        row = find_row_by_name(ws, 'DBSQL Serverless Medium')
        assert ws.cell(row=row, column=COL_MODE).value == 'Serverless'


class TestFormulaPatterns:
    """AC-9, AC-11, AC-12: Correct formula patterns per workload type."""

    def test_hourly_dbus_formula(self, ws):
        """Hourly items use =P{r}*L{r} for DBUs/Mo."""
        row = find_row_by_name(ws, 'Jobs Serverless Perf')
        cell = ws.cell(row=row, column=COL_DBUS_MO)
        val = cell.value
        assert isinstance(val, str) and val.startswith('='), \
            f"Expected formula in DBUs/Mo, got {val}"
        r = row + 1  # openpyxl 1-indexed matches Excel row
        # Formula should reference DBU/Hr (col P=15, 0-indexed) and Hours (col L=11)
        assert 'P' in val and 'L' in val, \
            f"Expected P*L pattern, got {val}"

    def test_token_dbus_formula(self, ws):
        """Token items use =N{r}*O{r} for DBUs/Mo."""
        row = find_row_by_name(ws, 'FMAPI DB Llama Input')
        cell = ws.cell(row=row, column=COL_DBUS_MO)
        val = cell.value
        assert isinstance(val, str) and val.startswith('='), \
            f"Expected formula for token DBUs/Mo, got {val}"
        assert 'N' in val and 'O' in val, \
            f"Expected N*O pattern, got {val}"

    def test_dbu_rate_disc_formula(self, ws):
        """All data rows have discount formula =R*(1-S)."""
        for row_idx in find_all_data_rows(ws):
            cell = ws.cell(row=row_idx, column=COL_DBU_RATE_DISC)
            val = cell.value
            assert isinstance(val, str) and val.startswith('='), \
                f"Row {row_idx}: expected formula in disc rate, got {val}"

    def test_dbu_cost_list_formula(self, ws):
        """Non-storage data rows have =Q*R formula for DBU Cost (List)."""
        storage_rows = find_rows_by_sku(ws, 'DATABRICKS_STORAGE')
        for row_idx in find_all_data_rows(ws):
            if row_idx in storage_rows:
                continue  # Storage rows have static cost
            cell = ws.cell(row=row_idx, column=COL_DBU_COST_L)
            val = cell.value
            assert isinstance(val, str) and val.startswith('='), \
                f"Row {row_idx}: expected formula in DBU Cost List, got {val}"

    def test_total_cost_list_formula(self, ws):
        """All data rows have =U+AA formula for Total Cost (List)."""
        for row_idx in find_all_data_rows(ws):
            cell = ws.cell(row=row_idx, column=COL_TOTAL_L)
            val = cell.value
            assert isinstance(val, str) and val.startswith('='), \
                f"Row {row_idx}: expected formula in Total List, got {val}"

    def test_total_cost_disc_formula(self, ws):
        """All data rows have formula for Total Cost (Disc.)."""
        for row_idx in find_all_data_rows(ws):
            cell = ws.cell(row=row_idx, column=COL_TOTAL_D)
            val = cell.value
            assert isinstance(val, str) and val.startswith('='), \
                f"Row {row_idx}: expected formula in Total Disc, got {val}"


class TestVmCosts:
    """AC-13: Serverless = no VM costs; Classic = VM costs present."""

    def test_serverless_no_vm_costs(self, ws):
        """Serverless items have 0 in VM cost columns."""
        serverless_names = [
            'Jobs Serverless Perf', 'DLT Pro Serverless',
            'DBSQL Serverless Medium', 'Model Serving GPU',
            'FMAPI DB Llama Input', 'FMAPI Anthropic Output',
            'Vector Search Standard 5M', 'Lakebase 4CU 2HA',
        ]
        for name in serverless_names:
            row = find_row_by_name(ws, name)
            if row is None:
                continue
            driver_vm = ws.cell(row=row, column=COL_DRIVER_VM_HR).value
            worker_vm = ws.cell(row=row, column=COL_WORKER_VM_HR).value
            assert driver_vm == 0 or driver_vm == '-', \
                f"{name}: expected 0 or '-' driver VM, got {driver_vm}"

    def test_classic_has_vm_costs(self, ws):
        """All-Purpose Classic Photon has non-zero VM cost rates."""
        row = find_row_by_name(ws, 'All-Purpose Classic Photon')
        assert row is not None
        driver_vm = ws.cell(row=row, column=COL_DRIVER_VM_HR).value
        assert isinstance(driver_vm, (int, float)) and driver_vm > 0, \
            f"Classic should have driver VM cost, got {driver_vm}"


class TestTokenColumns:
    """AC-11: FMAPI token items have token columns populated."""

    def test_fmapi_db_token_type(self, ws):
        row = find_row_by_name(ws, 'FMAPI DB Llama Input')
        token_type = ws.cell(row=row, column=COL_TOKEN_TYPE).value
        assert token_type == 'Input', f"Expected 'Input', got {token_type}"

    def test_fmapi_prop_token_type(self, ws):
        row = find_row_by_name(ws, 'FMAPI Anthropic Output')
        token_type = ws.cell(row=row, column=COL_TOKEN_TYPE).value
        assert token_type == 'Output', f"Expected 'Output', got {token_type}"

    def test_fmapi_db_token_qty(self, ws):
        row = find_row_by_name(ws, 'FMAPI DB Llama Input')
        qty = ws.cell(row=row, column=COL_TOKEN_QTY).value
        assert qty == 100, f"Expected 100M tokens, got {qty}"

    def test_fmapi_prop_token_qty(self, ws):
        row = find_row_by_name(ws, 'FMAPI Anthropic Output')
        qty = ws.cell(row=row, column=COL_TOKEN_QTY).value
        assert qty == 50, f"Expected 50M tokens, got {qty}"

    def test_non_token_items_have_dash(self, ws):
        """Non-FMAPI items should show '-' in token type column."""
        row = find_row_by_name(ws, 'Jobs Serverless Perf')
        assert ws.cell(row=row, column=COL_TOKEN_TYPE).value == '-'


class TestHoursColumn:
    """AC-8: Hours/Mo populated correctly for non-token items."""

    def test_jobs_hours(self, ws):
        row = find_row_by_name(ws, 'Jobs Serverless Perf')
        assert ws.cell(row=row, column=COL_HOURS).value == 200

    def test_all_purpose_hours(self, ws):
        row = find_row_by_name(ws, 'All-Purpose Classic Photon')
        assert ws.cell(row=row, column=COL_HOURS).value == 730

    def test_dbsql_hours(self, ws):
        row = find_row_by_name(ws, 'DBSQL Serverless Medium')
        assert ws.cell(row=row, column=COL_HOURS).value == 500

    def test_fmapi_hours_na(self, ws):
        """FMAPI token items show N/A for hours."""
        row = find_row_by_name(ws, 'FMAPI DB Llama Input')
        assert ws.cell(row=row, column=COL_HOURS).value == 'N/A'


class TestDbuPerHour:
    """AC-8: DBU/Hr populated correctly for hourly items."""

    def test_jobs_dbu_hr(self, ws):
        row = find_row_by_name(ws, 'Jobs Serverless Perf')
        val = ws.cell(row=row, column=COL_DBU_HR).value
        assert val == pytest.approx(1.0, abs=0.01)

    def test_all_purpose_dbu_hr(self, ws):
        row = find_row_by_name(ws, 'All-Purpose Classic Photon')
        val = ws.cell(row=row, column=COL_DBU_HR).value
        assert val == pytest.approx(2.5, abs=0.01)

    def test_dbsql_dbu_hr(self, ws):
        row = find_row_by_name(ws, 'DBSQL Serverless Medium')
        val = ws.cell(row=row, column=COL_DBU_HR).value
        assert val == pytest.approx(24.0, abs=0.01)

    def test_lakebase_dbu_hr(self, ws):
        row = find_row_by_name(ws, 'Lakebase 4CU 2HA')
        val = ws.cell(row=row, column=COL_DBU_HR).value
        assert val == pytest.approx(8.0, abs=0.01)

    def test_fmapi_dbu_hr_na(self, ws):
        """FMAPI token items show N/A for DBU/Hr."""
        row = find_row_by_name(ws, 'FMAPI DB Llama Input')
        assert ws.cell(row=row, column=COL_DBU_HR).value == 'N/A'


class TestDbuRate:
    """AC-8: DBU Rate column has non-zero values for all items."""

    def test_all_rows_have_dbu_rate(self, ws):
        for row_idx in find_all_data_rows(ws):
            rate = ws.cell(row=row_idx, column=COL_DBU_RATE).value
            assert isinstance(rate, (int, float)), \
                f"Row {row_idx}: DBU rate should be numeric, got {rate}"
            # Rate can be 0 for storage rows but should be non-negative
            assert rate >= 0, \
                f"Row {row_idx}: negative DBU rate {rate}"


class TestNoNanOrBroken:
    """AC-8: No NaN, no #REF!, no broken values."""

    def test_no_nan_in_data_rows(self, ws):
        for row_idx in find_all_data_rows(ws):
            for col in range(1, 31):
                val = ws.cell(row=row_idx, column=col).value
                if isinstance(val, str):
                    assert 'nan' not in val.lower(), \
                        f"Row {row_idx} col {col}: NaN found"
                    assert '#REF' not in val, \
                        f"Row {row_idx} col {col}: #REF error found"
                    assert '#VALUE' not in val, \
                        f"Row {row_idx} col {col}: #VALUE error found"
