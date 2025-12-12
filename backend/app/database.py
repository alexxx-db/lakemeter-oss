"""Database connection and session management."""
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Get database URL
database_url = settings.get_database_url

# Create database engine with error handling
engine = None
SessionLocal = None

try:
    if "localhost/demo" not in database_url:
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            connect_args={
                "sslmode": "require"
            } if "sslmode" not in database_url else {}
        )
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        print(f"✓ Database engine created for Lakebase")
    else:
        print("⚠ No database password set - running in demo mode")
        print("  Set PGPASSWORD environment variable to connect to Lakebase")
except Exception as e:
    print(f"⚠ Could not create database engine: {e}")
    print("  Running in demo mode")
    engine = None
    SessionLocal = None

# Base class for models
Base = declarative_base()


class DemoSession:
    """Dummy session for demo mode when no database is available."""
    def execute(self, *args, **kwargs):
        raise Exception("Demo mode - no database")
    
    def query(self, *args, **kwargs):
        raise Exception("Demo mode - no database")
    
    def add(self, *args, **kwargs):
        pass
    
    def commit(self):
        pass
    
    def refresh(self, *args, **kwargs):
        pass
    
    def close(self):
        pass


def get_db():
    """Dependency to get database session."""
    if SessionLocal is None:
        db = DemoSession()
        try:
            yield db
        finally:
            db.close()
    else:
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
