"""Export API routes for Excel download."""
from uuid import UUID
from io import BytesIO
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import xlsxwriter

from app.database import get_db
from app.models import Estimate, LineItem
from app.routes.estimates import get_demo_estimates
from app.routes.line_items import get_demo_line_items

router = APIRouter(prefix="/export", tags=["export"])


def _check_demo_mode(db: Session) -> bool:
    """Check if we should use demo mode."""
    try:
        db.execute("SELECT 1")
        return False
    except Exception:
        return True


@router.get("/estimate/{estimate_id}/excel")
def export_estimate_to_excel(
    estimate_id: UUID,
    db: Session = Depends(get_db)
):
    """Export an estimate to Excel format."""
    str_id = str(estimate_id)
    
    if _check_demo_mode(db):
        demo_estimates = get_demo_estimates()
        demo_line_items = get_demo_line_items()
        
        if str_id not in demo_estimates:
            raise HTTPException(status_code=404, detail="Estimate not found")
        
        estimate = demo_estimates[str_id]
        line_items = [item for item in demo_line_items.values() if item.get("estimate_id") == str_id]
    else:
        estimate = db.query(Estimate).filter(
            Estimate.estimate_id == estimate_id,
            Estimate.is_deleted == False
        ).first()
        
        if not estimate:
            raise HTTPException(status_code=404, detail="Estimate not found")
        
        line_items = estimate.line_items
    
    # Create Excel file in memory
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    
    # Define formats
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#f97316',
        'font_color': 'white',
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'text_wrap': True
    })
    
    section_format = workbook.add_format({
        'bold': True,
        'bg_color': '#1e293b',
        'font_color': 'white',
        'border': 1
    })
    
    cell_format = workbook.add_format({
        'border': 1,
        'valign': 'vcenter'
    })
    
    number_format = workbook.add_format({
        'border': 1,
        'num_format': '#,##0',
        'valign': 'vcenter'
    })
    
    # Helper to get value from dict or object
    def get_val(obj, key, default=''):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)
    
    # Summary sheet
    summary_sheet = workbook.add_worksheet('Summary')
    summary_sheet.set_column('A:A', 25)
    summary_sheet.set_column('B:B', 40)
    
    estimate_name = get_val(estimate, 'estimate_name', 'Untitled')
    customer_name = get_val(estimate, 'customer_name', '')
    cloud = get_val(estimate, 'cloud', '')
    region = get_val(estimate, 'region', '')
    tier = get_val(estimate, 'tier', '')
    status = get_val(estimate, 'status', 'draft')
    version = get_val(estimate, 'version', 1)
    created_at = get_val(estimate, 'created_at', datetime.utcnow())
    updated_at = get_val(estimate, 'updated_at', datetime.utcnow())
    
    if isinstance(created_at, datetime):
        created_at = created_at.strftime('%Y-%m-%d %H:%M')
    if isinstance(updated_at, datetime):
        updated_at = updated_at.strftime('%Y-%m-%d %H:%M')
    
    summary_data = [
        ['Estimate Name', estimate_name],
        ['Customer Name', customer_name or ''],
        ['Cloud Provider', cloud or ''],
        ['Region', region or ''],
        ['Tier', tier or ''],
        ['Status', status or ''],
        ['Version', version],
        ['Created', created_at],
        ['Last Updated', updated_at],
        ['Line Items', len(line_items)]
    ]
    
    summary_sheet.write(0, 0, 'Databricks Pricing Estimate', header_format)
    summary_sheet.merge_range(0, 0, 0, 1, 'Databricks Pricing Estimate', header_format)
    
    for i, (label, value) in enumerate(summary_data, start=2):
        summary_sheet.write(i, 0, label, section_format)
        summary_sheet.write(i, 1, value, cell_format)
    
    # Line Items sheet
    items_sheet = workbook.add_worksheet('Workloads')
    
    column_widths = [5, 30, 20, 12, 25, 12, 10, 12, 15, 12, 30]
    for i, width in enumerate(column_widths):
        items_sheet.set_column(i, i, width)
    
    headers = [
        '#', 'Workload Name', 'Type', 'Serverless', 'Worker Node',
        'Workers', 'Photon', 'Hours/Day', 'Days/Month', 'SKU', 'Notes'
    ]
    
    for col, header in enumerate(headers):
        items_sheet.write(0, col, header, header_format)
    
    for row, item in enumerate(line_items, start=1):
        items_sheet.write(row, 0, get_val(item, 'display_order', row) + 1, cell_format)
        items_sheet.write(row, 1, get_val(item, 'workload_name', ''), cell_format)
        items_sheet.write(row, 2, get_val(item, 'workload_type', ''), cell_format)
        items_sheet.write(row, 3, 'Yes' if get_val(item, 'is_serverless') else 'No', cell_format)
        items_sheet.write(row, 4, get_val(item, 'worker_node_type', ''), cell_format)
        items_sheet.write(row, 5, get_val(item, 'num_workers', 0) or 0, number_format)
        items_sheet.write(row, 6, 'Yes' if get_val(item, 'photon_enabled') else 'No', cell_format)
        items_sheet.write(row, 7, float(get_val(item, 'hours_per_day', 0) or 0), number_format)
        items_sheet.write(row, 8, get_val(item, 'days_per_month', 0) or 0, number_format)
        items_sheet.write(row, 9, get_val(item, 'selected_sku', ''), cell_format)
        items_sheet.write(row, 10, get_val(item, 'notes', ''), cell_format)
    
    workbook.close()
    
    output.seek(0)
    
    filename = f"databricks_estimate_{estimate_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.get("/estimates/excel")
def export_all_estimates_to_excel(
    db: Session = Depends(get_db)
):
    """Export all estimates summary to Excel."""
    if _check_demo_mode(db):
        demo_estimates = get_demo_estimates()
        demo_line_items = get_demo_line_items()
        estimates = list(demo_estimates.values())
    else:
        estimates = db.query(Estimate).filter(
            Estimate.is_deleted == False
        ).order_by(Estimate.updated_at.desc()).all()
    
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#f97316',
        'font_color': 'white',
        'border': 1
    })
    
    cell_format = workbook.add_format({
        'border': 1
    })
    
    sheet = workbook.add_worksheet('All Estimates')
    
    headers = [
        'Estimate Name', 'Customer', 'Cloud', 'Region', 'Tier',
        'Status', 'Version', 'Created', 'Updated'
    ]
    
    widths = [40, 30, 15, 20, 15, 15, 10, 20, 20]
    for i, width in enumerate(widths):
        sheet.set_column(i, i, width)
    
    for col, header in enumerate(headers):
        sheet.write(0, col, header, header_format)
    
    def get_val(obj, key, default=''):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)
    
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
    
    filename = f"databricks_estimates_export_{datetime.now().strftime('%Y%m%d')}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
