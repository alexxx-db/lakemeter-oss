"""Salesforce sync models for accounts, opportunities, and use cases."""
from sqlalchemy import Column, String, Numeric, DateTime
from app.database import Base


class SalesforceAccount(Base):
    """Salesforce Account model matching lakemeter.sync_salesforce_account table."""
    
    __tablename__ = "sync_salesforce_account"
    __table_args__ = {"schema": "lakemeter"}
    
    salesforce_account_id = Column(String(18), primary_key=True)
    salesforce_account_name = Column(String(500))
    dim_salesforce_account_region = Column(String(100))
    ds = Column(String(20))


class SalesforceOpportunity(Base):
    """Salesforce Opportunity model matching lakemeter.sync_salesforce_opportunity table."""
    
    __tablename__ = "sync_salesforce_opportunity"
    __table_args__ = {"schema": "lakemeter"}
    
    id = Column(String(18), primary_key=True)
    name = Column(String(500))
    accountid = Column(String(18))


class SalesforceUseCase(Base):
    """Salesforce Use Case model matching lakemeter.sync_salesforce_usecase table."""
    
    __tablename__ = "sync_salesforce_usecase"
    __table_args__ = {"schema": "lakemeter"}
    
    salesforce_use_case_id = Column(String(18), primary_key=True)
    salesforce_use_case_name = Column(String(500))
    customer_id = Column(String(18))  # Links to account
    dim_canonical_customer_name = Column(String(500))
    dim_business_unit_latest = Column(String(255))
    estimated_quarterly_dollars = Column(Numeric(18, 2))
    ds = Column(String(20))
    ts = Column(String(50))
    uuid = Column(String(50))

