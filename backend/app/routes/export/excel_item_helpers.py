"""Item-level calculation and storage sub-row helpers for Excel export."""
from .pricing import _get_dbu_price, _get_fmapi_dbu_per_million
from .calculations import _calculate_hours_per_month
from .excel_row_writer import write_data_row


# Token type display map for FMAPI token-based rate types
TOKEN_TYPE_DISPLAY = {
    'input_token': 'Input', 'input': 'Input',
    'output_token': 'Output', 'output': 'Output',
    'cache_read': 'Cache Read', 'cache_write': 'Cache Write',
}


def calc_item_values(item, is_fmapi_token, is_fmapi_provisioned,
                     dbu_per_hour, cloud, auto_notes):
    """Calculate hours, tokens, DBUs for a line item.

    Returns (hours, token_qty, dbu_per_m, total_dbus, token_type).
    """
    if is_fmapi_token:
        token_qty = float(item.fmapi_quantity or 0)
        dbu_per_m, found = _get_fmapi_dbu_per_million(item, cloud)
        if not found:
            auto_notes.append(
                f"FMAPI rate not found for {item.fmapi_model or 'unknown model'}")
        token_type = TOKEN_TYPE_DISPLAY.get(item.fmapi_rate_type, 'Input')
        return 0, token_qty, dbu_per_m, token_qty * dbu_per_m, token_type
    elif is_fmapi_provisioned:
        hours = float(item.fmapi_quantity or 0)
        dbu_hr, found = _get_fmapi_dbu_per_million(item, cloud)
        if not found:
            auto_notes.append(
                f"FMAPI rate not found for {item.fmapi_model or 'unknown model'}")
        return hours, 0, 0, dbu_hr * hours, ''
    else:
        hours = _calculate_hours_per_month(item)
        return hours, 0, 0, dbu_per_hour * hours, ''


def write_storage_subrow(sheet, fmt, row, item, idx, cloud, region, tier,
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
    approx = '~' if size_attr != 'lakebase_storage_gb' else ''
    precision = '1' if size_attr != 'lakebase_storage_gb' else '0'
    notes = f'${storage_rate}/GB/month × {approx}{storage_gb:.{precision}f} GB'

    name = getattr(item, 'workload_name', f'Workload {idx + 1}') or f'Workload {idx + 1}'
    storage_row = {
        'idx': '',
        'name': name,
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
