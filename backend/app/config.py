"""Application configuration settings."""
import os
import json
import logging
import secrets
from urllib.parse import quote_plus
from pydantic import ConfigDict, model_validator
from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Environment: "local", "development", "production"
    environment: str = "local"
    
    # Log level: DEBUG, INFO, WARNING, ERROR
    log_level: str = "INFO"

    # Log format: "text" (default, human-readable) or "json" (structured,
    # one JSON object per line — recommended for production log aggregation)
    log_format: str = "text"
    
    # Lakebase Database Configuration
    db_host: str = ""
    db_user: str = ""
    db_name: str = "lakemeter_pricing"
    db_port: int = 5432
    db_sslmode: str = "require"
    
    # Databricks configuration
    # In Databricks Apps: DATABRICKS_HOST, DATABRICKS_CLIENT_ID, DATABRICKS_CLIENT_SECRET
    # are auto-injected. The app's built-in SP handles all authentication.
    databricks_host: Optional[str] = None
    databricks_config_profile: Optional[str] = None
    
    # Lakebase instance name (from Compute > Lakebase Postgres)
    lakebase_instance_name: Optional[str] = None
    
    # Override with full DATABASE_URL if provided
    database_url: Optional[str] = None
    
    # JWT Authentication
    # No default secret: in production the value MUST be provided via the
    # JWT_SECRET_KEY environment variable (sourced from a Databricks secret
    # scope, e.g. `valueFrom: lakemeter-jwt-secret` in app.yaml). A local-dev
    # fallback is generated per-process so nothing predictable is shipped.
    jwt_secret_key: Optional[str] = None
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://localhost:5175"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as list. Empty string means same-origin only."""
        if not self.cors_origins or self.cors_origins.strip() == "":
            return []
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
    
    @property
    def use_oauth(self) -> bool:
        """Check if OAuth authentication is configured (Databricks Apps auto-injects host)."""
        return bool(self.databricks_host)
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"
    
    @property
    def is_local(self) -> bool:
        """Check if running in local development."""
        return self.environment.lower() == "local"
    
    model_config = ConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    @model_validator(mode="after")
    def _resolve_jwt_secret(self) -> "Settings":
        """Require an explicit JWT secret in production; generate an ephemeral
        per-process secret for local development so no predictable value ships."""
        if self.jwt_secret_key:
            if self.is_production and self.jwt_secret_key == "your-secret-key-change-in-production":
                raise ValueError(
                    "JWT_SECRET_KEY is set to the old insecure placeholder. "
                    "Generate a real secret and store it in a Databricks secret scope."
                )
            return self
        if self.is_production:
            raise ValueError(
                "JWT_SECRET_KEY must be set when ENVIRONMENT=production. "
                "Store it in a Databricks secret scope and inject it via app.yaml, e.g.:\n"
                "  - name: JWT_SECRET_KEY\n"
                "    valueFrom: lakemeter-jwt-secret"
            )
        # Local/development: ephemeral per-process secret (tokens invalidate on restart).
        self.jwt_secret_key = secrets.token_urlsafe(32)
        return self


settings = Settings()


# =============================================================================
# Logging Setup
# =============================================================================

class JsonFormatter(logging.Formatter):
    """Structured JSON log formatter — one JSON object per line.

    Fields: timestamp (ISO 8601 UTC), level, logger, message, plus
    exception/stack info when present. No third-party dependencies.
    """

    def format(self, record: logging.LogRecord) -> str:
        from datetime import datetime, timezone
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)
        return json.dumps(payload, default=str)


def setup_logging():
    """Configure logging based on environment."""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    if settings.is_production:
        log_level = logging.WARNING
    else:
        # Local/Development: verbose logging
        log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    if settings.log_format.lower() == "json":
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        root = logging.getLogger()
        if not root.handlers:
            root.handlers.append(handler)
        else:
            root.handlers[0].setFormatter(JsonFormatter())
        root.setLevel(log_level)
    else:
        logging.basicConfig(level=log_level, format=log_format)

    # Suppress noisy third-party loggers in production
    if settings.is_production:
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with environment-aware settings."""
    return logging.getLogger(name)


# Helper for conditional logging (backwards compatible with print statements)
def log_debug(message: str, logger_name: str = "lakemeter"):
    """Log debug message (only in local/dev)."""
    if not settings.is_production:
        get_logger(logger_name).debug(message)


def log_info(message: str, logger_name: str = "lakemeter"):
    """Log info message (only in local/dev)."""
    if not settings.is_production:
        get_logger(logger_name).info(message)


def log_warning(message: str, logger_name: str = "lakemeter"):
    """Log warning message (always)."""
    get_logger(logger_name).warning(message)


def log_error(message: str, logger_name: str = "lakemeter"):
    """Log error message (always)."""
    get_logger(logger_name).error(message)
