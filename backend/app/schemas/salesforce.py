"""Pydantic schemas for Salesforce data."""
from typing import Optional
from pydantic import BaseModel


class SalesforceAccountResponse(BaseModel):
    """Response schema for Salesforce Account."""
    salesforce_account_id: str
    salesforce_account_name: Optional[str] = None
    dim_salesforce_account_region: Optional[str] = None
    
    class Config:
        from_attributes = True


class SalesforceOpportunityResponse(BaseModel):
    """Response schema for Salesforce Opportunity."""
    id: str
    name: Optional[str] = None
    accountid: Optional[str] = None
    
    class Config:
        from_attributes = True


class SalesforceUseCaseResponse(BaseModel):
    """Response schema for Salesforce Use Case."""
    salesforce_use_case_id: str
    salesforce_use_case_name: Optional[str] = None
    customer_id: Optional[str] = None
    dim_canonical_customer_name: Optional[str] = None
    dim_business_unit_latest: Optional[str] = None
    
    class Config:
        from_attributes = True

