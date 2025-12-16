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
    db_name: str = "lakemeter_pricing"
    db_port: int = 5432
    db_sslmode: str = "require"
    
    # Databricks Service Principal OAuth (M2M) Configuration
    databricks_host: Optional[str] = None
    databricks_config_profile: Optional[str] = None
    
    # Databricks secrets configuration for Service Principal credentials
    databricks_secrets_scope: Optional[str] = None
    sp_client_id_key: str = "sp_clientid"
    sp_secret_key: str = "sp_secret"
    
    # Lakebase instance name (from Compute > Lakebase Postgres)
    lakebase_instance_name: Optional[str] = None
    
    # Override with full DATABASE_URL if provided
    database_url: Optional[str] = None
    
    # JWT Authentication
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    
    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    @property
    def use_oauth(self) -> bool:
        """Check if OAuth authentication is configured."""
        return bool(self.databricks_host and self.databricks_secrets_scope)
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


settings = Settings()
