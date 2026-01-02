"""Export API routes for Excel download."""
from uuid import UUID
from io import BytesIO
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import xlsxwriter

from app.database import get_db
from app.models import Estimate, LineItem, User
from app.models.sharing import Sharing
from app.auth import get_current_user

router = APIRouter(prefix="/export", tags=["export"])


def _check_estimate_access(estimate_id: UUID, user: User, db: Session) -> Estimate:
    """Check if user has access to an estimate."""
    estimate = db.query(Estimate).filter(
        Estimate.estimate_id == estimate_id,
        Estimate.is_deleted == False
    ).first()
    
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")
    
    is_owner = estimate.owner_user_id == user.user_id
    is_shared = db.query(Sharing).filter(
        Sharing.estimate_id == estimate_id,
        Sharing.shared_with_user_id == user.user_id
    ).first() is not None
    
    if not is_owner and not is_shared:
        raise HTTPException(status_code=404, detail="Estimate not found")
    
    return estimate


# DBU rates by product type (defaults - would come from pricing tables)
DBU_RATES = {
    'JOBS_COMPUTE': 0.15,
    'JOBS_COMPUTE_(PHOTON)': 0.29,
    'JOBS_SERVERLESS_COMPUTE': 0.39,
    'ALL_PURPOSE_COMPUTE': 0.55,
    'ALL_PURPOSE_COMPUTE_(PHOTON)': 0.55,
    'INTERACTIVE_SERVERLESS_COMPUTE': 0.83,
    'DLT_CORE_COMPUTE': 0.20,
    'DLT_PRO_COMPUTE': 0.25,
    'DLT_ADVANCED_COMPUTE': 0.36,
    'DELTA_LIVE_TABLES_SERVERLESS': 0.50,
    'SQL_COMPUTE': 0.22,
    'SQL_PRO_COMPUTE': 0.55,
    'SERVERLESS_SQL_COMPUTE': 0.70,
    'VECTOR_SEARCH_ENDPOINT': 0.088,
    'SERVERLESS_REAL_TIME_INFERENCE': 0.088,
    'FOUNDATION_MODEL_TRAINING': 0.20,
    'DATABASE_SERVERLESS_COMPUTE': 0.40,
}

# Default VM hourly costs by pricing tier
VM_HOURLY_COSTS = {
    'on_demand': 0.05,  # Default per-core hour
    'spot': 0.02,
    'reserved_1y': 0.035,
    'reserved_3y': 0.025,
}


def _get_workload_display_name(workload_type: str) -> str:
    """Get friendly display name for workload type."""
    names = {
        'JOBS': 'Job Compute',
        'ALL_PURPOSE': 'All-Purpose Compute',
        'DLT': 'Delta Live Tables',
        'DBSQL': 'Databricks SQL',
        'VECTOR_SEARCH': 'Vector Search',
        'MODEL_SERVING': 'Model Serving',
        'FMAPI_DATABRICKS': 'Foundation Models (Databricks)',
        'FMAPI_PROPRIETARY': 'Foundation Models (Proprietary)',
        'LAKEBASE': 'Lakebase',
    }
    return names.get(workload_type, workload_type)


def _get_workload_config_details(item) -> str:
    """Get workload-specific configuration details for display."""
    wt = item.workload_type or ''
    details = []
    
    if wt == 'DBSQL':
        if item.dbsql_warehouse_type:
            details.append(f"Type: {item.dbsql_warehouse_type}")
        if item.dbsql_warehouse_size:
            details.append(f"Size: {item.dbsql_warehouse_size}")
        if item.dbsql_num_clusters and item.dbsql_num_clusters > 1:
            details.append(f"Clusters: {item.dbsql_num_clusters}")
    
    elif wt == 'VECTOR_SEARCH':
        mode = item.vector_search_mode or 'standard'
        mode_display = 'Storage Optimized' if mode == 'storage_optimized' else 'Standard'
        details.append(f"Mode: {mode_display}")
        if item.vector_capacity_millions:
            details.append(f"Capacity: {item.vector_capacity_millions}M vectors")
    
    elif wt == 'MODEL_SERVING':
        if item.model_serving_gpu_type:
            gpu_names = {
                'cpu': 'CPU',
                'gpu_small_t4': 'Small (T4)',
                'gpu_medium_a10g_1x': 'Medium (A10G 1x)',
                'gpu_large_a10g_4x': 'Large (A10G 4x)',
                'gpu_medium_a100_1x': 'Medium (A100 1x)',
                'gpu_large_a100_2x': 'Large (A100 2x)',
                'gpu_xlarge_a100_80gb_8x': 'XLarge (A100 80GB 8x)',
            }
            details.append(f"Type: {gpu_names.get(item.model_serving_gpu_type, item.model_serving_gpu_type)}")
    
    elif wt in ('FMAPI_DATABRICKS', 'FMAPI_PROPRIETARY'):
        if item.fmapi_model:
            details.append(f"Model: {item.fmapi_model}")
        if item.fmapi_rate_type:
            rate_type_display = {
                'input_token': 'Input Tokens',
                'output_token': 'Output Tokens',
                'provisioned_scaling': 'Provisioned Scaling',
                'provisioned_entry': 'Provisioned Entry',
            }
            details.append(f"Rate: {rate_type_display.get(item.fmapi_rate_type, item.fmapi_rate_type)}")
        if item.fmapi_quantity:
            # Format quantity based on rate type
            if item.fmapi_rate_type in ('input_token', 'output_token'):
                qty = float(item.fmapi_quantity)
                if qty >= 1_000_000:
                    details.append(f"Tokens: {qty/1_000_000:.1f}M")
                elif qty >= 1_000:
                    details.append(f"Tokens: {qty/1_000:.1f}K")
                else:
                    details.append(f"Tokens: {int(qty)}")
            else:
                details.append(f"Hours: {item.fmapi_quantity}")
    
    elif wt == 'LAKEBASE':
        if item.lakebase_cu:
            details.append(f"CU: {item.lakebase_cu}")
        if item.lakebase_ha_nodes:
            details.append(f"Nodes: {item.lakebase_ha_nodes}")
    
    elif wt == 'DLT':
        if item.dlt_edition:
            details.append(f"Edition: {item.dlt_edition.upper()}")
    
    return ' | '.join(details) if details else '-'


def _get_sku_type(item) -> str:
    """Determine the SKU/product type for a line item."""
    wt = item.workload_type or ''
    
    if wt == 'JOBS':
        if item.serverless_enabled:
            return 'JOBS_SERVERLESS_COMPUTE'
        elif item.photon_enabled:
            return 'JOBS_COMPUTE_(PHOTON)'
        return 'JOBS_COMPUTE'
    
    elif wt == 'ALL_PURPOSE':
        if item.serverless_enabled:
            return 'INTERACTIVE_SERVERLESS_COMPUTE'
        elif item.photon_enabled:
            return 'ALL_PURPOSE_COMPUTE_(PHOTON)'
        return 'ALL_PURPOSE_COMPUTE'
    
    elif wt == 'DLT':
        if item.serverless_enabled:
            return 'DELTA_LIVE_TABLES_SERVERLESS'
        edition = (item.dlt_edition or 'CORE').upper()
        return f'DLT_{edition}_COMPUTE'
    
    elif wt == 'DBSQL':
        warehouse_type = (item.dbsql_warehouse_type or 'SERVERLESS').upper()
        if warehouse_type == 'SERVERLESS':
            return 'SERVERLESS_SQL_COMPUTE'
        elif warehouse_type == 'PRO':
            return 'SQL_PRO_COMPUTE'
        return 'SQL_COMPUTE'
    
    elif wt == 'VECTOR_SEARCH':
        return 'VECTOR_SEARCH_ENDPOINT'
    
    elif wt == 'MODEL_SERVING':
        return 'SERVERLESS_REAL_TIME_INFERENCE'
    
    elif wt in ('FMAPI_DATABRICKS', 'FMAPI_PROPRIETARY'):
        return 'FOUNDATION_MODEL_TRAINING'
    
    elif wt == 'LAKEBASE':
        return 'DATABASE_SERVERLESS_COMPUTE'
    
    return 'JOBS_COMPUTE'


def _calculate_hours_per_month(item) -> float:
    """Calculate hours per month from usage config."""
    if item.hours_per_month:
        return float(item.hours_per_month)
    
    runs = item.runs_per_day or 1
    runtime = item.avg_runtime_minutes or 30
    days = item.days_per_month or 22
    
    return (runs * runtime / 60) * days


def _calculate_dbu_per_hour(item) -> float:
    """Calculate DBU per hour for a workload."""
    wt = item.workload_type or ''
    
    # For compute workloads
    if wt in ('JOBS', 'ALL_PURPOSE', 'DLT'):
        num_workers = item.num_workers or 1
        base_dbu = 0.25 + (0.5 * num_workers)
        
        if item.photon_enabled:
            base_dbu *= 2
        
        if item.serverless_enabled:
            mode_multiplier = 2 if item.serverless_mode == 'performance' else 1
            return base_dbu * mode_multiplier
        
        return base_dbu
    
    elif wt == 'DBSQL':
        size_dbu = {
            '2X-Small': 4, 'X-Small': 6, 'Small': 12, 'Medium': 24,
            'Large': 40, 'X-Large': 80, '2X-Large': 144, '3X-Large': 272, '4X-Large': 528
        }
        return size_dbu.get(item.dbsql_warehouse_size or 'Small', 12) * (item.dbsql_num_clusters or 1)
    
    elif wt == 'VECTOR_SEARCH':
        capacity = float(item.vector_capacity_millions or 1)
        if item.vector_search_mode == 'storage_optimized':
            return capacity * 18.29
        return capacity * 4.0
    
    elif wt == 'MODEL_SERVING':
        gpu_dbu = {
            'cpu': 1.0, 'gpu_small_t4': 10.48, 'gpu_medium_a10g_1x': 20.0,
            'gpu_large_a10g_4x': 80.0, 'gpu_medium_a100_1x': 40.0, 'gpu_large_a100_2x': 80.0
        }
        return gpu_dbu.get(item.model_serving_gpu_type or 'cpu', 1.0)
    
    elif wt in ('FMAPI_DATABRICKS', 'FMAPI_PROPRIETARY'):
        return 0
    
    elif wt == 'LAKEBASE':
        cu = item.lakebase_cu or 1
        nodes = item.lakebase_ha_nodes or 1
        return cu * nodes * 2
    
    return 0


def _is_serverless_workload(item) -> bool:
    """Check if workload is serverless (no VM costs)."""
    wt = item.workload_type or ''
    
    # These are always serverless
    if wt in ('VECTOR_SEARCH', 'MODEL_SERVING', 'FMAPI_DATABRICKS', 'FMAPI_PROPRIETARY', 'LAKEBASE'):
        return True
    
    # Compute workloads with serverless enabled
    if wt in ('JOBS', 'ALL_PURPOSE', 'DLT') and item.serverless_enabled:
        return True
    
    # DBSQL Serverless
    if wt == 'DBSQL' and (item.dbsql_warehouse_type or '').upper() == 'SERVERLESS':
        return True
    
    return False


def _get_pricing_tier_display(tier: str) -> str:
    """Get display name for pricing tier."""
    displays = {
        'on_demand': 'On-Demand',
        'spot': 'Spot',
        'reserved_1y': '1-Year Reserved',
        'reserved_3y': '3-Year Reserved',
    }
    return displays.get(tier, tier or '-')


@router.get("/estimate/{estimate_id}/excel")
def export_estimate_to_excel(
    estimate_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export an estimate to Excel format with professional RFP-ready layout."""
    estimate = _check_estimate_access(estimate_id, current_user, db)
    line_items = sorted(estimate.line_items, key=lambda x: x.display_order or 0)
    
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    
    # ========== DEFINE FORMATS ==========
    title_format = workbook.add_format({
        'bold': True, 'font_size': 18, 'font_color': '#1e293b',
        'bottom': 2, 'bottom_color': '#f97316'
    })
    subtitle_format = workbook.add_format({
        'font_size': 11, 'font_color': '#64748b', 'italic': True
    })
    
    section_header_format = workbook.add_format({
        'bold': True, 'font_size': 12, 'font_color': 'white',
        'bg_color': '#1e293b', 'border': 1, 'align': 'left', 'valign': 'vcenter'
    })
    
    # Table header groups
    header_main_format = workbook.add_format({
        'bold': True, 'font_size': 10, 'font_color': 'white',
        'bg_color': '#f97316', 'border': 1, 'align': 'center',
        'valign': 'vcenter', 'text_wrap': True
    })
    header_dbu_format = workbook.add_format({
        'bold': True, 'font_size': 10, 'font_color': 'white',
        'bg_color': '#3b82f6', 'border': 1, 'align': 'center',
        'valign': 'vcenter', 'text_wrap': True
    })
    header_vm_format = workbook.add_format({
        'bold': True, 'font_size': 10, 'font_color': 'white',
        'bg_color': '#10b981', 'border': 1, 'align': 'center',
        'valign': 'vcenter', 'text_wrap': True
    })
    header_total_format = workbook.add_format({
        'bold': True, 'font_size': 10, 'font_color': 'white',
        'bg_color': '#8b5cf6', 'border': 1, 'align': 'center',
        'valign': 'vcenter', 'text_wrap': True
    })
    
    # Data cells
    cell_format = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'text_wrap': True
    })
    cell_center = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'align': 'center'
    })
    cell_mono = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'font_name': 'Consolas', 'font_size': 9
    })
    
    # Number formats
    number_format = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'num_format': '#,##0', 'align': 'right'
    })
    decimal_format = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'num_format': '#,##0.00', 'align': 'right'
    })
    currency_format = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'num_format': '$#,##0.00', 'align': 'right'
    })
    
    # Colored currency for cost columns
    dbu_currency_format = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'num_format': '$#,##0.00', 'align': 'right',
        'bg_color': '#eff6ff'  # Light blue
    })
    vm_currency_format = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'num_format': '$#,##0.00', 'align': 'right',
        'bg_color': '#ecfdf5'  # Light green
    })
    total_currency_format = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'num_format': '$#,##0.00', 'align': 'right',
        'bg_color': '#f5f3ff', 'bold': True  # Light purple
    })
    
    # Summary/Total formats
    total_label_format = workbook.add_format({
        'bold': True, 'border': 1, 'bg_color': '#f1f5f9', 'align': 'right'
    })
    total_dbu_value = workbook.add_format({
        'bold': True, 'border': 1, 'bg_color': '#dbeafe',
        'num_format': '$#,##0.00', 'align': 'right'
    })
    total_vm_value = workbook.add_format({
        'bold': True, 'border': 1, 'bg_color': '#d1fae5',
        'num_format': '$#,##0.00', 'align': 'right'
    })
    total_grand_value = workbook.add_format({
        'bold': True, 'border': 1, 'bg_color': '#ede9fe',
        'num_format': '$#,##0.00', 'align': 'right'
    })
    total_dbu_num = workbook.add_format({
        'bold': True, 'border': 1, 'bg_color': '#f1f5f9',
        'num_format': '#,##0', 'align': 'right'
    })
    
    # Info/metadata format
    label_format = workbook.add_format({
        'bold': True, 'font_color': '#64748b', 'align': 'right'
    })
    value_format = workbook.add_format({
        'font_color': '#1e293b'
    })
    
    # Notes format
    notes_format = workbook.add_format({
        'font_size': 9, 'font_color': '#64748b', 'italic': True, 'text_wrap': True
    })
    
    # Serverless indicator
    serverless_format = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'align': 'center',
        'font_color': '#059669', 'italic': True
    })
    
    def get_val(obj, key, default=''):
        val = getattr(obj, key, default)
        return val if val is not None else default
    
    # ========== CREATE WORKSHEET ==========
    sheet = workbook.add_worksheet('Databricks Estimate')
    
    # Set column widths (A=0, B=1, etc.)
    # Columns: #, Name, Type, Mode, Config, Driver Node, Worker Node, #Workers, Driver Tier, Worker Tier,
    #          Hours/Mo, DBU/Hr, DBUs/Mo, DBU Rate, DBU Cost, Driver VM $/Hr, Worker VM $/Hr, Driver VM Cost, Worker VM Cost, Total VM Cost, Total Cost, Notes
    widths = [4, 22, 18, 12, 30, 18, 18, 8, 12, 12, 10, 10, 12, 10, 12, 12, 12, 12, 12, 12, 14, 25]
    for i, w in enumerate(widths):
        sheet.set_column(i, i, w)
    
    row = 0
    max_col = 21  # Total columns (0-indexed: 22 columns)
    
    # ========== HEADER SECTION ==========
    estimate_name = get_val(estimate, 'estimate_name', 'Untitled Estimate')
    customer_name = get_val(estimate, 'customer_name', '')
    
    sheet.write(row, 0, 'Databricks Pricing Estimate', title_format)
    sheet.merge_range(row, 0, row, max_col, 'Databricks Pricing Estimate', title_format)
    row += 1
    
    subtitle = f"{estimate_name}"
    if customer_name:
        subtitle += f" - {customer_name}"
    sheet.write(row, 0, subtitle, subtitle_format)
    sheet.merge_range(row, 0, row, max_col, subtitle, subtitle_format)
    row += 2
    
    # ========== ESTIMATE DETAILS SECTION ==========
    sheet.write(row, 0, 'ESTIMATE DETAILS', section_header_format)
    sheet.merge_range(row, 0, row, max_col, 'ESTIMATE DETAILS', section_header_format)
    row += 1
    
    cloud = get_val(estimate, 'cloud', '-').upper()
    region = get_val(estimate, 'region', '-')
    tier = get_val(estimate, 'tier', '-').upper()
    status = get_val(estimate, 'status', 'draft').capitalize()
    version = get_val(estimate, 'version', 1)
    created_at = get_val(estimate, 'created_at', datetime.utcnow())
    updated_at = get_val(estimate, 'updated_at', datetime.utcnow())
    
    if isinstance(created_at, datetime):
        created_at = created_at.strftime('%Y-%m-%d')
    if isinstance(updated_at, datetime):
        updated_at = updated_at.strftime('%Y-%m-%d')
    
    info_data = [
        [('Cloud:', cloud), ('Region:', region), ('Tier:', tier), ('Status:', status)],
        [('Customer:', customer_name or '-'), ('Version:', str(version)), ('Created:', created_at), ('Updated:', updated_at)],
    ]
    
    for info_row in info_data:
        col = 0
        for label, value in info_row:
            sheet.write(row, col, label, label_format)
            sheet.write(row, col + 1, value, value_format)
            col += 4
        row += 1
    
    row += 1
    
    # ========== WORKLOADS TABLE ==========
    sheet.write(row, 0, 'WORKLOADS & COST BREAKDOWN', section_header_format)
    sheet.merge_range(row, 0, row, max_col, 'WORKLOADS & COST BREAKDOWN', section_header_format)
    row += 1
    
    # Table headers - organized by category
    # Basic Info (Orange): #, Name, Type, Mode, Configuration
    # VM Config (Green): Driver Node, Worker Node, #Workers, Driver Tier, Worker Tier
    # DBU Costs (Blue): Hours/Mo, DBU/Hr, DBUs/Mo, DBU Rate, DBU Cost
    # VM Costs (Green): Driver VM $/Hr, Worker VM $/Hr, Driver VM Cost, Worker VM Cost, Total VM Cost
    # Total (Purple): Total Cost
    # Notes
    
    headers = [
        ('#', header_main_format),
        ('Workload Name', header_main_format),
        ('Type', header_main_format),
        ('Mode', header_main_format),
        ('Configuration', header_main_format),
        ('Driver Node', header_vm_format),
        ('Worker Node', header_vm_format),
        ('Workers', header_vm_format),
        ('Driver Tier', header_vm_format),
        ('Worker Tier', header_vm_format),
        ('Hours/Mo', header_dbu_format),
        ('DBU/Hr', header_dbu_format),
        ('DBUs/Mo', header_dbu_format),
        ('DBU Rate', header_dbu_format),
        ('DBU Cost', header_dbu_format),
        ('Driver VM $/Hr', header_vm_format),
        ('Worker VM $/Hr', header_vm_format),
        ('Driver VM Cost', header_vm_format),
        ('Worker VM Cost', header_vm_format),
        ('Total VM Cost', header_vm_format),
        ('Total Cost', header_total_format),
        ('Notes', header_main_format),
    ]
    
    for col, (header, fmt) in enumerate(headers):
        sheet.write(row, col, header, fmt)
    
    header_row = row
    row += 1
    data_start_row = row
    
    # Write line items
    for idx, item in enumerate(line_items):
        wt = item.workload_type or 'JOBS'
        sku = _get_sku_type(item)
        dbu_rate = DBU_RATES.get(sku, 0.15)
        hours_per_month = _calculate_hours_per_month(item)
        dbu_per_hour = _calculate_dbu_per_hour(item)
        is_serverless = _is_serverless_workload(item)
        
        # Handle FMAPI token-based workloads
        if wt in ('FMAPI_DATABRICKS', 'FMAPI_PROPRIETARY'):
            is_provisioned = item.fmapi_rate_type in ('provisioned_scaling', 'provisioned_entry')
            if is_provisioned:
                hours_per_month = float(item.fmapi_quantity or 0)
                dbu_per_hour = 200 if item.fmapi_rate_type == 'provisioned_scaling' else 50
            else:
                token_rate = 3.0 if item.fmapi_rate_type == 'output_token' else 1.0
                hours_per_month = 1
                dbu_per_hour = float(item.fmapi_quantity or 0) * token_rate
        
        # Calculate VM cost per hour (for non-serverless compute)
        driver_vm_cost_per_hour = 0
        worker_vm_cost_per_hour = 0
        num_workers = item.num_workers or 1
        if not is_serverless and wt in ('JOBS', 'ALL_PURPOSE', 'DLT'):
            driver_tier = item.driver_pricing_tier or 'on_demand'
            worker_tier = item.worker_pricing_tier or 'spot'
            driver_vm_rate = VM_HOURLY_COSTS.get(driver_tier, 0.05)
            worker_vm_rate = VM_HOURLY_COSTS.get(worker_tier, 0.02)
            # Assume ~4 cores per node average
            driver_vm_cost_per_hour = driver_vm_rate * 4  # Per driver node
            worker_vm_cost_per_hour = worker_vm_rate * 4  # Per worker node
        
        # Write row
        sheet.write(row, 0, idx + 1, cell_center)  # #
        sheet.write(row, 1, get_val(item, 'workload_name', f'Workload {idx + 1}'), cell_format)  # Name
        sheet.write(row, 2, _get_workload_display_name(wt), cell_format)  # Type
        
        # Mode (Serverless/Classic/etc)
        if is_serverless:
            if wt in ('JOBS', 'ALL_PURPOSE', 'DLT'):
                mode = f"Serverless ({(item.serverless_mode or 'standard').capitalize()})"
            else:
                mode = "Serverless"
            sheet.write(row, 3, mode, serverless_format)
        else:
            sheet.write(row, 3, "Classic", cell_center)
        
        # Configuration column (4) - workload-specific details
        config_details = _get_workload_config_details(item)
        sheet.write(row, 4, config_details, cell_format)
        
        # VM Config columns (5-9)
        if is_serverless:
            sheet.write(row, 5, '-', serverless_format)  # Driver
            sheet.write(row, 6, '-', serverless_format)  # Worker
            sheet.write(row, 7, '-', serverless_format)  # #Workers
            sheet.write(row, 8, '-', serverless_format)  # Driver Tier
            sheet.write(row, 9, '-', serverless_format)  # Worker Tier
        else:
            sheet.write(row, 5, get_val(item, 'driver_node_type', '-') or '-', cell_mono)  # Driver
            sheet.write(row, 6, get_val(item, 'worker_node_type', '-') or '-', cell_mono)  # Worker
            sheet.write(row, 7, item.num_workers or 1, number_format)  # #Workers
            sheet.write(row, 8, _get_pricing_tier_display(item.driver_pricing_tier), cell_center)  # Driver Tier
            sheet.write(row, 9, _get_pricing_tier_display(item.worker_pricing_tier), cell_center)  # Worker Tier
        
        # DBU columns (10-14)
        sheet.write(row, 10, hours_per_month, decimal_format)  # Hours/Mo
        sheet.write(row, 11, dbu_per_hour, decimal_format)  # DBU/Hr
        sheet.write_formula(row, 12, f'=K{row+1}*L{row+1}', number_format)  # DBUs/Mo
        sheet.write(row, 13, dbu_rate, currency_format)  # DBU Rate
        sheet.write_formula(row, 14, f'=M{row+1}*N{row+1}', dbu_currency_format)  # DBU Cost
        
        # VM columns (15-19): Driver VM $/Hr, Worker VM $/Hr, Driver VM Cost, Worker VM Cost, Total VM Cost
        if is_serverless:
            sheet.write(row, 15, 0, vm_currency_format)  # Driver VM $/Hr
            sheet.write(row, 16, 0, vm_currency_format)  # Worker VM $/Hr
            sheet.write(row, 17, 0, vm_currency_format)  # Driver VM Cost
            sheet.write(row, 18, 0, vm_currency_format)  # Worker VM Cost
            sheet.write(row, 19, 0, vm_currency_format)  # Total VM Cost
        else:
            sheet.write(row, 15, driver_vm_cost_per_hour, currency_format)  # Driver VM $/Hr
            sheet.write(row, 16, worker_vm_cost_per_hour, currency_format)  # Worker VM $/Hr (per worker)
            sheet.write_formula(row, 17, f'=K{row+1}*P{row+1}', vm_currency_format)  # Driver VM Cost = Hours * Driver $/Hr
            sheet.write_formula(row, 18, f'=K{row+1}*Q{row+1}*H{row+1}', vm_currency_format)  # Worker VM Cost = Hours * Worker $/Hr * #Workers
            sheet.write_formula(row, 19, f'=R{row+1}+S{row+1}', vm_currency_format)  # Total VM Cost
        
        # Total Cost (20)
        sheet.write_formula(row, 20, f'=O{row+1}+T{row+1}', total_currency_format)  # Total = DBU Cost + Total VM Cost
        
        # Notes (21)
        sheet.write(row, 21, get_val(item, 'notes', ''), cell_format)
        
        row += 1
    
    data_end_row = row - 1
    
    # ========== TOTALS ROW ==========
    row += 1
    sheet.write(row, 13, 'TOTALS:', total_label_format)
    sheet.merge_range(row, 0, row, 13, 'TOTALS:', total_label_format)
    
    if data_end_row >= data_start_row:
        sheet.write_formula(row, 14, f'=SUM(O{data_start_row+1}:O{data_end_row+1})', total_dbu_value)  # DBU Cost Total
        sheet.write(row, 15, '', total_label_format)  # Driver VM $/Hr (empty for totals)
        sheet.write(row, 16, '', total_label_format)  # Worker VM $/Hr (empty for totals)
        sheet.write_formula(row, 17, f'=SUM(R{data_start_row+1}:R{data_end_row+1})', total_vm_value)  # Driver VM Cost Total
        sheet.write_formula(row, 18, f'=SUM(S{data_start_row+1}:S{data_end_row+1})', total_vm_value)  # Worker VM Cost Total
        sheet.write_formula(row, 19, f'=SUM(T{data_start_row+1}:T{data_end_row+1})', total_vm_value)  # Total VM Cost
        sheet.write_formula(row, 20, f'=SUM(U{data_start_row+1}:U{data_end_row+1})', total_grand_value)  # Grand Total
        sheet.write(row, 21, '', total_label_format)  # Notes (empty for totals)
    else:
        sheet.write(row, 14, 0, total_dbu_value)
        sheet.write(row, 15, '', total_label_format)
        sheet.write(row, 16, '', total_label_format)
        sheet.write(row, 17, 0, total_vm_value)
        sheet.write(row, 18, 0, total_vm_value)
        sheet.write(row, 19, 0, total_vm_value)
        sheet.write(row, 20, 0, total_grand_value)
        sheet.write(row, 21, '', total_label_format)
    
    totals_row = row
    row += 2
    
    # ========== COST SUMMARY SECTION ==========
    sheet.write(row, 0, 'COST SUMMARY', section_header_format)
    sheet.merge_range(row, 0, row, 7, 'COST SUMMARY', section_header_format)
    row += 1
    
    # Summary table with Monthly and Annual - now includes Driver/Worker VM breakdown
    summary_headers = ['', 'DBU Cost', 'Driver VM', 'Worker VM', 'Total VM', 'Total Cost']
    for col, h in enumerate(summary_headers):
        if col == 0:
            fmt = header_main_format
        elif col == 1:
            fmt = header_dbu_format
        elif col in (2, 3, 4):
            fmt = header_vm_format
        else:
            fmt = header_total_format
        sheet.write(row, col, h, fmt)
    row += 1
    
    # Monthly row - O=DBU Cost, R=Driver VM Cost, S=Worker VM Cost, T=Total VM Cost, U=Total Cost
    sheet.write(row, 0, 'Monthly', cell_format)
    sheet.write_formula(row, 1, f'=O{totals_row+1}', dbu_currency_format)  # DBU Cost
    sheet.write_formula(row, 2, f'=R{totals_row+1}', vm_currency_format)   # Driver VM Cost
    sheet.write_formula(row, 3, f'=S{totals_row+1}', vm_currency_format)   # Worker VM Cost
    sheet.write_formula(row, 4, f'=T{totals_row+1}', vm_currency_format)   # Total VM Cost
    sheet.write_formula(row, 5, f'=U{totals_row+1}', total_currency_format)  # Total Cost
    monthly_row = row
    row += 1
    
    # Annual row
    sheet.write(row, 0, 'Annual', cell_format)
    sheet.write_formula(row, 1, f'=B{monthly_row+1}*12', dbu_currency_format)
    sheet.write_formula(row, 2, f'=C{monthly_row+1}*12', vm_currency_format)
    sheet.write_formula(row, 3, f'=D{monthly_row+1}*12', vm_currency_format)
    sheet.write_formula(row, 4, f'=E{monthly_row+1}*12', vm_currency_format)
    sheet.write_formula(row, 5, f'=F{monthly_row+1}*12', total_currency_format)
    row += 2
    
    # DBU Summary
    sheet.write(row, 0, 'Total DBUs/Month:', label_format)
    sheet.merge_range(row, 0, row, 1, 'Total DBUs/Month:', label_format)
    if data_end_row >= data_start_row:
        sheet.write_formula(row, 2, f'=SUM(M{data_start_row+1}:M{data_end_row+1})', total_dbu_num)
    else:
        sheet.write(row, 2, 0, total_dbu_num)
    row += 2
    
    # ========== LEGEND ==========
    sheet.write(row, 0, 'LEGEND', section_header_format)
    sheet.merge_range(row, 0, row, 7, 'LEGEND', section_header_format)
    row += 1
    
    legend_items = [
        ('Blue columns', 'DBU-related costs (Databricks compute units)'),
        ('Green columns', 'VM infrastructure costs (cloud provider)'),
        ('Purple column', 'Total cost (DBU + VM)'),
        ('Serverless', 'No VM costs - compute is fully managed by Databricks'),
    ]
    
    for label, desc in legend_items:
        sheet.write(row, 0, f'• {label}:', label_format)
        sheet.write(row, 1, desc, value_format)
        sheet.merge_range(row, 1, row, 7, desc, value_format)
        row += 1
    
    row += 1
    
    # ========== ASSUMPTIONS & NOTES ==========
    sheet.write(row, 0, 'ASSUMPTIONS & NOTES', section_header_format)
    sheet.merge_range(row, 0, row, max_col, 'ASSUMPTIONS & NOTES', section_header_format)
    row += 1
    
    assumptions = [
        "• This estimate is based on list pricing. Actual costs may vary based on negotiated discounts.",
        "• DBU rates are based on the selected cloud provider, region, and tier.",
        "• VM costs are estimated based on typical instance sizes. Actual costs depend on specific instance types.",
        "• Usage hours calculated as: Runs/Day × Avg Runtime (min) ÷ 60 × Days/Month",
        "• Serverless workloads have no VM costs - compute is included in the DBU rate.",
        "• For accurate pricing, please consult your Databricks account team.",
        f"• Estimate exported: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}",
    ]
    
    for assumption in assumptions:
        sheet.write(row, 0, assumption, notes_format)
        sheet.merge_range(row, 0, row, max_col, assumption, notes_format)
        row += 1
    
    # Footer
    row += 1
    footer_format = workbook.add_format({
        'font_size': 9, 'font_color': '#94a3b8', 'align': 'center'
    })
    sheet.write(row, 0, f'Generated by Lakemeter • Databricks Pricing Calculator • {datetime.now().year}', footer_format)
    sheet.merge_range(row, 0, row, max_col, f'Generated by Lakemeter • Databricks Pricing Calculator • {datetime.now().year}', footer_format)
    
    # Freeze panes
    sheet.freeze_panes(header_row + 1, 2)
    
    # Print settings
    sheet.set_landscape()
    sheet.fit_to_pages(1, 0)
    sheet.set_margins(left=0.25, right=0.25, top=0.5, bottom=0.5)
    
    workbook.close()
    output.seek(0)
    
    safe_name = estimate_name.replace(' ', '_').replace('/', '-')[:50]
    filename = f"Databricks_Estimate_{safe_name}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/estimates/excel")
def export_all_estimates_to_excel(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export all estimates summary to Excel."""
    from sqlalchemy import or_
    
    shared_estimate_ids = db.query(Sharing.estimate_id).filter(
        Sharing.shared_with_user_id == current_user.user_id
    ).subquery()
    
    estimates = db.query(Estimate).filter(
        Estimate.is_deleted == False,
        or_(
            Estimate.owner_user_id == current_user.user_id,
            Estimate.estimate_id.in_(shared_estimate_ids)
        )
    ).order_by(Estimate.updated_at.desc()).all()
    
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    
    header_format = workbook.add_format({
        'bold': True, 'bg_color': '#f97316', 'font_color': 'white', 'border': 1
    })
    cell_format = workbook.add_format({'border': 1})
    
    sheet = workbook.add_worksheet('All Estimates')
    
    headers = ['Estimate Name', 'Customer', 'Cloud', 'Region', 'Tier', 'Status', 'Version', 'Created', 'Updated']
    widths = [40, 30, 15, 20, 15, 15, 10, 20, 20]
    
    for i, width in enumerate(widths):
        sheet.set_column(i, i, width)
    
    for col, header in enumerate(headers):
        sheet.write(0, col, header, header_format)
    
    def get_val(obj, key, default=''):
        return getattr(obj, key, default) or default
    
    for row, est in enumerate(estimates, start=1):
        created = get_val(est, 'created_at', '')
        updated = get_val(est, 'updated_at', '')
        if isinstance(created, datetime):
            created = created.strftime('%Y-%m-%d %H:%M')
        if isinstance(updated, datetime):
            updated = updated.strftime('%Y-%m-%d %H:%M')
        
        sheet.write(row, 0, get_val(est, 'estimate_name', ''), cell_format)
        sheet.write(row, 1, get_val(est, 'customer_name', ''), cell_format)
        sheet.write(row, 2, get_val(est, 'cloud', ''), cell_format)
        sheet.write(row, 3, get_val(est, 'region', ''), cell_format)
        sheet.write(row, 4, get_val(est, 'tier', ''), cell_format)
        sheet.write(row, 5, get_val(est, 'status', ''), cell_format)
        sheet.write(row, 6, get_val(est, 'version', 1), cell_format)
        sheet.write(row, 7, created, cell_format)
        sheet.write(row, 8, updated, cell_format)
    
    workbook.close()
    output.seek(0)
    
    filename = f"Databricks_Estimates_Export_{datetime.now().strftime('%Y%m%d')}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
