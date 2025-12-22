"""Salesforce API routes for accounts, opportunities, and use cases."""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.salesforce import SalesforceAccount, SalesforceOpportunity, SalesforceUseCase
from app.schemas.salesforce import (
    SalesforceAccountResponse,
    SalesforceOpportunityResponse,
    SalesforceUseCaseResponse
)
from app.config import log_warning

router = APIRouter(prefix="/salesforce", tags=["salesforce"])


@router.get("/accounts", response_model=List[SalesforceAccountResponse])
def list_salesforce_accounts(
    search: Optional[str] = Query(None, description="Search by account name"),
    limit: int = Query(500, ge=1, le=10000),
    db: Session = Depends(get_db)
):
    """
    List Salesforce accounts with optional search.
    Returns accounts sorted by name.
    """
    try:
        query = db.query(SalesforceAccount)
        
        if search:
            query = query.filter(
                SalesforceAccount.salesforce_account_name.ilike(f"%{search}%")
            )
        
        accounts = query.order_by(SalesforceAccount.salesforce_account_name).limit(limit).all()
        return accounts
        
    except Exception as e:
        log_warning(f"Could not fetch Salesforce accounts: {e}")
        return []


@router.get("/accounts/{account_id}", response_model=SalesforceAccountResponse)
def get_salesforce_account(
    account_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific Salesforce account by ID."""
    try:
        account = db.query(SalesforceAccount).filter(
            SalesforceAccount.salesforce_account_id == account_id
        ).first()
        
        if account:
            return account
    except Exception as e:
        log_warning(f"Could not fetch Salesforce account: {e}")
    
    return None


@router.get("/opportunities", response_model=List[SalesforceOpportunityResponse])
def list_salesforce_opportunities(
    account_id: Optional[str] = Query(None, description="Filter by account ID"),
    search: Optional[str] = Query(None, description="Search by opportunity name"),
    limit: int = Query(500, ge=1, le=10000),
    db: Session = Depends(get_db)
):
    """
    List Salesforce opportunities with optional filters.
    Can filter by account ID and/or search by name.
    """
    try:
        query = db.query(SalesforceOpportunity)
        
        if account_id:
            query = query.filter(SalesforceOpportunity.accountid == account_id)
        
        if search:
            query = query.filter(
                SalesforceOpportunity.name.ilike(f"%{search}%")
            )
        
        opportunities = query.order_by(SalesforceOpportunity.name).limit(limit).all()
        return opportunities
        
    except Exception as e:
        log_warning(f"Could not fetch Salesforce opportunities: {e}")
        return []


@router.get("/opportunities/{opportunity_id}", response_model=SalesforceOpportunityResponse)
def get_salesforce_opportunity(
    opportunity_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific Salesforce opportunity by ID."""
    try:
        opportunity = db.query(SalesforceOpportunity).filter(
            SalesforceOpportunity.id == opportunity_id
        ).first()
        
        if opportunity:
            return opportunity
    except Exception as e:
        log_warning(f"Could not fetch Salesforce opportunity: {e}")
    
    return None


@router.get("/use-cases", response_model=List[SalesforceUseCaseResponse])
def list_salesforce_use_cases(
    account_id: Optional[str] = Query(None, description="Filter by customer/account ID"),
    search: Optional[str] = Query(None, description="Search by use case name"),
    limit: int = Query(500, ge=1, le=10000),
    db: Session = Depends(get_db)
):
    """
    List Salesforce use cases with optional filters.
    Can filter by customer/account ID and/or search by name.
    """
    try:
        query = db.query(SalesforceUseCase)
        
        if account_id:
            query = query.filter(SalesforceUseCase.customer_id == account_id)
        
        if search:
            query = query.filter(
                SalesforceUseCase.salesforce_use_case_name.ilike(f"%{search}%")
            )
        
        use_cases = query.order_by(SalesforceUseCase.salesforce_use_case_name).limit(limit).all()
        return use_cases
        
    except Exception as e:
        log_warning(f"Could not fetch Salesforce use cases: {e}")
        return []


@router.get("/use-cases/{use_case_id}", response_model=SalesforceUseCaseResponse)
def get_salesforce_use_case(
    use_case_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific Salesforce use case by ID."""
    try:
        use_case = db.query(SalesforceUseCase).filter(
            SalesforceUseCase.salesforce_use_case_id == use_case_id
        ).first()
        
        if use_case:
            return use_case
    except Exception as e:
        log_warning(f"Could not fetch Salesforce use case: {e}")
    
    return None

