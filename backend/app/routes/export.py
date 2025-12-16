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


@router.get("/estimate/{estimate_id}/excel")
def export_estimate_to_excel(
    estimate_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export an estimate to Excel format. User must have access to the estimate."""
    estimate = _check_estimate_access(estimate_id, current_user, db)
    
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
    
    # Helper to get value from object
    def get_val(obj, key, default=''):
        return getattr(obj, key, default) or default
    
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
        ['Customer Name', customer_name],
        ['Cloud Provider', cloud],
        ['Region', region],
        ['Tier', tier],
        ['Status', status],
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
        'Workers', 'Photon', 'Runs/Day', 'Days/Month', 'SKU', 'Notes'
    ]
    
    for col, header in enumerate(headers):
        items_sheet.write(0, col, header, header_format)
    
    for row, item in enumerate(line_items, start=1):
        items_sheet.write(row, 0, get_val(item, 'display_order', row) + 1, cell_format)
        items_sheet.write(row, 1, get_val(item, 'workload_name', ''), cell_format)
        items_sheet.write(row, 2, get_val(item, 'workload_type', ''), cell_format)
        items_sheet.write(row, 3, 'Yes' if get_val(item, 'serverless_enabled') else 'No', cell_format)
        items_sheet.write(row, 4, get_val(item, 'worker_node_type', ''), cell_format)
        items_sheet.write(row, 5, get_val(item, 'num_workers', 0) or 0, number_format)
        items_sheet.write(row, 6, 'Yes' if get_val(item, 'photon_enabled') else 'No', cell_format)
        items_sheet.write(row, 7, get_val(item, 'runs_per_day', 0) or 0, number_format)
        items_sheet.write(row, 8, get_val(item, 'days_per_month', 0) or 0, number_format)
        items_sheet.write(row, 9, get_val(item, 'workload_type', ''), cell_format)
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export all estimates summary to Excel (only user's estimates)."""
    from sqlalchemy import or_
    
    # Get estimates user has access to
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
    
    filename = f"databricks_estimates_export_{datetime.now().strftime('%Y%m%d')}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
