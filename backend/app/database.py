"""
Database connection and session management.

Supports automatic OAuth token refresh for Lakebase using Service Principal M2M flow.
Reference: https://docs.databricks.com/aws/en/oltp/instances/authentication
"""
from urllib.parse import quote_plus
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


# Base class for models (defined early so models can import it)
Base = declarative_base()


def _get_database_url() -> str:
    """Build database URL from token manager."""
    from app.auth.token_manager import token_manager
    
    if not token_manager:
        raise Exception("Token manager not initialized. Check DATABRICKS_HOST and DATABRICKS_SECRETS_SCOPE.")
    
    params = token_manager.get_connection_params()
    
    if not params["password"]:
        raise Exception("No valid OAuth token available. Run 'databricks auth login' to authenticate.")
    
    # URL-encode credentials
    encoded_user = quote_plus(params["user"])
    encoded_password = quote_plus(params["password"])
    
    return (
        f"postgresql://{encoded_user}:{encoded_password}"
        f"@{params['host']}:{params['port']}/{params['dbname']}"
        f"?sslmode={params['sslmode']}"
    )


def _create_engine_with_token_refresh():
    """Create SQLAlchemy engine with automatic token refresh."""
    try:
        database_url = _get_database_url()
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise
    
    try:
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            pool_recycle=1800,
            connect_args={"sslmode": "require"}
        )
        
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        print(f"✓ Database engine created for Lakebase")
        
        session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return engine, session_local
        
    except Exception as e:
        print(f"❌ Could not create database engine: {e}")
        raise


# Initialize engine and session factory
engine, SessionLocal = _create_engine_with_token_refresh()


def refresh_engine():
    """Refresh the database engine with a new token."""
    global engine, SessionLocal
    
    from app.auth.token_manager import token_manager
    
    if token_manager:
        token_manager._token = None
        token_manager._expires_at = None
    
    engine, SessionLocal = _create_engine_with_token_refresh()
    return engine is not None


def get_db():
    """Dependency to get database session."""
    if SessionLocal is None:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
