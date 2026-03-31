"""Main Excel builder: assembles the estimate workbook."""
from io import BytesIO
from datetime import datetime
import xlsxwriter

from .excel_formats import create_formats
from .excel_row_writer import (
    NUM_COLS, COLUMN_WIDTHS, get_headers, write_data_row,
)
from .excel_sections import (
    write_totals, write_cost_summary, write_dbu_summary,
    write_legend, write_assumptions, write_footer,
)
from .pricing import (
    _get_dbu_price, _get_sku_type, _get_fmapi_dbu_per_million,
)
from .helpers import (
    _get_workload_display_name, _get_workload_config_details,
    _get_pricing_tier_display,
)
from .calculations import (
    _calculate_hours_per_month, _calculate_dbu_per_hour,
    _is_serverless_workload,
)


def build_estimate_excel(estimate, line_items, cloud, region, tier):
    """Build an Excel workbook for an estimate. Returns BytesIO output."""
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    fmt = create_formats(workbook)
    max_col = NUM_COLS - 1

    sheet = workbook.add_worksheet('Databricks Estimate')
    for i, w in enumerate(COLUMN_WIDTHS):
        sheet.set_column(i, i, w)

    row = _write_header_section(sheet, fmt, estimate, cloud, region, tier, max_col)
    row, header_row, data_start_row = _write_table_headers(sheet, fmt, row, max_col)
    row = _write_line_items(sheet, fmt, row, line_items, cloud, region, tier)
    data_end_row = row - 1
    row = write_totals(sheet, fmt, row, data_start_row, data_end_row)
    totals_row = row - 2
    row = write_cost_summary(sheet, fmt, row, totals_row)
    row = write_dbu_summary(sheet, fmt, row, data_start_row, data_end_row)
    row = write_legend(sheet, fmt, row)
    row = write_assumptions(sheet, fmt, row, max_col)
    write_footer(sheet, workbook, row, max_col)

    sheet.freeze_panes(header_row + 1, 2)
    sheet.set_landscape()
    sheet.fit_to_pages(1, 0)
    sheet.set_margins(left=0.25, right=0.25, top=0.5, bottom=0.5)

    workbook.close()
    output.seek(0)
    return output


def _get_val(obj, key, default=''):
    val = getattr(obj, key, default)
    return val if val is not None else default


def _write_header_section(sheet, fmt, estimate, cloud, region, tier, max_col):
    """Write title, subtitle, and estimate details."""
    row = 0
    estimate_name = _get_val(estimate, 'estimate_name', 'Untitled Estimate')
    sheet.merge_range(row, 0, row, max_col, 'Databricks Pricing Estimate', fmt['title'])
    row += 1
    sheet.merge_range(row, 0, row, max_col, estimate_name, fmt['subtitle'])
    row += 2

    sheet.merge_range(row, 0, row, max_col, 'ESTIMATE DETAILS', fmt['section_header'])
    row += 1

    status = _get_val(estimate, 'status', 'draft').capitalize()
    version = _get_val(estimate, 'version', 1)
    created_at = _get_val(estimate, 'created_at', datetime.utcnow())
    updated_at = _get_val(estimate, 'updated_at', datetime.utcnow())
    if isinstance(created_at, datetime):
        created_at = created_at.strftime('%Y-%m-%d')
    if isinstance(updated_at, datetime):
        updated_at = updated_at.strftime('%Y-%m-%d')

    info_data = [
        [('Cloud:', cloud.upper()), ('Region:', region), ('Tier:', tier.upper()),
         ('Status:', status)],
        [('Version:', str(version)), ('Created:', created_at), ('Updated:', updated_at)],
    ]
    for info_row in info_data:
        col = 0
        for label_text, value_text in info_row:
            sheet.write(row, col, label_text, fmt['label'])
            sheet.write(row, col + 1, value_text, fmt['value'])
            col += 4
        row += 1
    row += 1
    return row


def _write_table_headers(sheet, fmt, row, max_col):
    """Write the workloads table header row."""
    sheet.merge_range(row, 0, row, max_col, 'WORKLOADS & COST BREAKDOWN',
                      fmt['section_header'])
    row += 1
    headers = get_headers(fmt)
    for col, (header, header_fmt) in enumerate(headers):
        sheet.write(row, col, header, header_fmt)
    header_row = row
    row += 1
    data_start_row = row
    return row, header_row, data_start_row


def _write_line_items(sheet, fmt, row, line_items, cloud, region, tier):
    """Write all line item data rows including storage sub-rows."""
    for idx, item in enumerate(line_items):
        row = _write_single_item(sheet, fmt, row, idx, item, cloud, region, tier)
    return row


def _write_single_item(sheet, fmt, row, idx, item, cloud, region, tier):
    """Write one line item (and its storage sub-row if applicable)."""
    wt = item.workload_type or 'JOBS'
    sku = _get_sku_type(item, cloud)
    dbu_rate, dbu_rate_found = _get_dbu_price(cloud, region, tier, sku)
    dbu_per_hour, dbu_warnings = _calculate_dbu_per_hour(item, cloud)
    is_serverless = _is_serverless_workload(item)
    is_fmapi = wt in ('FMAPI_DATABRICKS', 'FMAPI_PROPRIETARY')
    is_fmapi_token = is_fmapi and item.fmapi_rate_type in (
        'input_token', 'output_token', 'input', 'output')
    is_fmapi_provisioned = is_fmapi and item.fmapi_rate_type in (
        'provisioned_scaling', 'provisioned_entry')

    auto_notes = list(dbu_warnings)
    if not dbu_rate_found:
        auto_notes.append(f"DBU rate not found for {sku}, using fallback ${dbu_rate:.2f}")

    hours, token_qty, dbu_per_m, total_dbus, token_type = _calc_item_values(
        item, is_fmapi_token, is_fmapi_provisioned, dbu_per_hour, cloud, auto_notes)

    num_workers = int(item.num_workers or 0)
    driver_vm_hr = 0.20 if (not is_serverless and wt in ('JOBS', 'ALL_PURPOSE', 'DLT')) else 0
    worker_vm_hr = 0.10 if (not is_serverless and wt in ('JOBS', 'ALL_PURPOSE', 'DLT')) else 0

    user_notes = _get_val(item, 'notes', '') or ''
    notes_parts = [user_notes] if user_notes else []
    if auto_notes:
        notes_parts.append(' | '.join(auto_notes))

    base_row = {
        'idx': idx + 1,
        'name': _get_val(item, 'workload_name', f'Workload {idx + 1}'),
        'type_display': _get_workload_display_name(wt),
        'config': _get_workload_config_details(item),
        'sku': sku,
        'driver_node': _get_val(item, 'driver_node_type', '-') or '-',
        'worker_node': _get_val(item, 'worker_node_type', '-') or '-',
        'num_workers': num_workers,
        'driver_tier': _get_pricing_tier_display(item.driver_pricing_tier)
        if hasattr(item, 'driver_pricing_tier') else '-',
        'worker_tier': _get_pricing_tier_display(item.worker_pricing_tier)
        if hasattr(item, 'worker_pricing_tier') else '-',
        'hours_per_month': hours,
        'token_type': token_type if is_fmapi_token else '',
        'token_quantity_millions': token_qty,
        'dbu_per_million': dbu_per_m,
        'dbu_per_hour': dbu_per_hour,
        'total_dbus_month': total_dbus,
        'dbu_rate': dbu_rate,
        'discount_pct': 0.0,
        'driver_vm_cost_per_hour': driver_vm_hr,
        'worker_vm_cost_per_hour': worker_vm_hr,
        'notes': ' — '.join(notes_parts) if notes_parts else '',
    }

    write_data_row(sheet, row, base_row, is_fmapi_token, is_serverless, fmt)
    row += 1

    if wt == 'LAKEBASE':
        row = _write_storage_subrow(sheet, fmt, row, item, idx, cloud, region, tier,
                                    'Lakebase (Storage)', 'lakebase_storage_gb')
    if wt == 'VECTOR_SEARCH':
        row = _write_storage_subrow(sheet, fmt, row, item, idx, cloud, region, tier,
                                    'Vector Search (Storage)', 'vector_capacity_millions')
    return row


def _calc_item_values(item, is_fmapi_token, is_fmapi_provisioned, dbu_per_hour,
                      cloud, auto_notes):
    """Calculate hours, tokens, DBUs for a line item."""
    if is_fmapi_token:
        token_qty = float(item.fmapi_quantity or 0)
        dbu_per_m, found = _get_fmapi_dbu_per_million(item, cloud)
        if not found:
            auto_notes.append(f"FMAPI rate not found for {item.fmapi_model or 'unknown model'}")
        token_type = 'Input' if item.fmapi_rate_type in ('input_token', 'input') else 'Output'
        return 0, token_qty, dbu_per_m, token_qty * dbu_per_m, token_type
    elif is_fmapi_provisioned:
        hours = float(item.fmapi_quantity or 0)
        dbu_hr, found = _get_fmapi_dbu_per_million(item, cloud)
        if not found:
            auto_notes.append(f"FMAPI rate not found for {item.fmapi_model or 'unknown model'}")
        return hours, 0, 0, dbu_hr * hours, ''
    else:
        hours = _calculate_hours_per_month(item)
        return hours, 0, 0, dbu_per_hour * hours, ''


def _write_storage_subrow(sheet, fmt, row, item, idx, cloud, region, tier,
                          type_display, size_attr):
    """Write a storage sub-row for Lakebase or Vector Search."""
    if size_attr == 'lakebase_storage_gb':
        storage_gb = float(item.lakebase_storage_gb or 0)
        config = f'Storage: {storage_gb:.0f} GB'
    else:
        capacity_m = float(item.vector_capacity_millions or 1)
        storage_gb = capacity_m
        config = f'Storage: ~{storage_gb:.1f} GB ({capacity_m:.0f}M vectors)'

    storage_rate, _ = _get_dbu_price(cloud, region, tier, 'DATABRICKS_STORAGE')
    storage_cost = storage_gb * storage_rate
    notes = f'${storage_rate}/GB/month × {"~" if size_attr != "lakebase_storage_gb" else ""}{storage_gb:.{"1" if size_attr != "lakebase_storage_gb" else "0"}f} GB'

    storage_row = {
        'idx': '',
        'name': _get_val(item, 'workload_name', f'Workload {idx + 1}'),
        'type_display': type_display,
        'config': config,
        'sku': 'DATABRICKS_STORAGE',
        'driver_node': '-', 'worker_node': '-',
        'num_workers': 0,
        'driver_tier': '-', 'worker_tier': '-',
        'hours_per_month': 0,
        'token_type': '', 'token_quantity_millions': 0,
        'dbu_per_million': 0, 'dbu_per_hour': 0,
        'total_dbus_month': 0,
        'dbu_rate': storage_rate,
        'discount_pct': 0.0,
        'driver_vm_cost_per_hour': 0, 'worker_vm_cost_per_hour': 0,
        'notes': notes,
        'storage_cost_monthly': storage_cost,
    }
    write_data_row(sheet, row, storage_row, False, True, fmt, is_storage_row=True)
    return row + 1
