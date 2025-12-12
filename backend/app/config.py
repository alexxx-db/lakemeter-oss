"""Application configuration settings."""
import os
from urllib.parse import quote_plus
from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Lakebase Database Configuration
    db_host: str = "instance-364041a4-0aae-44df-bbc6-37ac84169dfe.database.cloud.databricks.com"
    db_user: str = "junyi.tiong@databricks.com"
    db_password: Optional[str] = None  # Set via PGPASSWORD or DB_PASSWORD env var
    db_name: str = "lakemeter_pricing"
    db_port: int = 5432
    db_sslmode: str = "require"
    
    # Override with full DATABASE_URL if provided
    database_url: Optional[str] = None
    
    @property
    def get_database_url(self) -> str:
        """Build database URL from components or use override."""
        if self.database_url:
            return self.database_url
        
        # Get password from environment
        password = self.db_password or os.environ.get("PGPASSWORD", "")
        
        if not password:
            # Return a dummy URL that will trigger demo mode
            return "postgresql://localhost/demo"
        
        # URL-encode the username (contains @)
        encoded_user = quote_plus(self.db_user)
        encoded_password = quote_plus(password)
        
        return f"postgresql://{encoded_user}:{encoded_password}@{self.db_host}:{self.db_port}/{self.db_name}?sslmode={self.db_sslmode}"
    
    # JWT Authentication
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    
    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra environment variables like PGPASSWORD


settings = Settings()
