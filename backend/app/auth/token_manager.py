"""
Lakebase OAuth Token Manager

Uses Databricks Service Principal OAuth (M2M) to generate and refresh
database credentials for Lakebase authentication.

Supports fetching SP credentials from Databricks secrets for enhanced security.

Reference: https://docs.databricks.com/aws/en/oltp/instances/authentication
"""
import os
import uuid
import threading
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import logging helpers (defined inline to avoid circular import)
def _log_info(msg: str):
    """Log info - only in local/dev mode."""
    if os.getenv("ENVIRONMENT", "local").lower() != "production":
        print(f"[TokenManager] {msg}")

def _log_warning(msg: str):
    """Log warning - always."""
    print(f"[TokenManager] WARNING: {msg}")

def _log_error(msg: str):
    """Log error - always."""
    print(f"[TokenManager] ERROR: {msg}")


class LakebaseTokenManager:
    """
    Manages OAuth tokens for Lakebase database authentication.
    
    Authentication flow:
    1. First, authenticate to Databricks using CLI auth (browser OAuth)
    2. Fetch SP credentials from Databricks secrets
    3. Use SP credentials to generate Lakebase database tokens
    4. Auto-refresh tokens before expiration (1 hour lifetime)
    
    This approach keeps SP credentials secure in Databricks secrets.
    """
    
    def __init__(self):
        self._token: Optional[str] = None
        self._expires_at: Optional[datetime] = None
        self._lock = threading.Lock()
        
        # Load settings from environment variables
        self.databricks_host = os.getenv("DATABRICKS_HOST")
        self.databricks_config_profile = os.getenv("DATABRICKS_CONFIG_PROFILE")
        self.lakebase_instance_name = os.getenv("LAKEBASE_INSTANCE_NAME")
        self.db_user = os.getenv("DB_USER")
        self.db_name = os.getenv("DB_NAME")
        self.db_host = os.getenv("DB_HOST")
        self.db_port = int(os.getenv("DB_PORT", "5432"))
        self.db_sslmode = os.getenv("DB_SSLMODE", "require")

        self.secrets_scope = os.getenv("DATABRICKS_SECRETS_SCOPE")
        self.sp_client_id_key = os.getenv("SP_CLIENT_ID_KEY")
        self.sp_secret_key = os.getenv("SP_SECRET_KEY")
        
        self._workspace_client: Optional[WorkspaceClient] = None
        self._sp_client_id: Optional[str] = None
        self._sp_client_secret: Optional[str] = None
        
        self._init_workspace_client()
        self._fetch_sp_credentials()
        self.get_token() # Initial token fetch
        
        _log_info("LakebaseTokenManager initialized")
        _log_info(f"Workspace: {self.databricks_host}")
        _log_info(f"Instance: {self.lakebase_instance_name}")
        _log_info(f"Secrets scope: {self.secrets_scope}")
    
    def _init_workspace_client(self):
        """Initialize Databricks WorkspaceClient using CLI auth."""
        try:
            config = Config(
                host=self.databricks_host,
                profile=self.databricks_config_profile
            )
            self._workspace_client = WorkspaceClient(config=config)
            # Test CLI auth by getting current user
            current_user = self._workspace_client.current_user.me()
            _log_info(f"CLI auth: {current_user.user_name}")
        except Exception as e:
            _log_warning(f"CLI auth failed: {e}")
            self._workspace_client = None
    
    def _fetch_sp_credentials(self):
        """Fetch Service Principal credentials from Databricks secrets."""
        if not self._workspace_client:
            _log_warning("Cannot fetch SP credentials: WorkspaceClient not initialized.")
            return
        
        if not all([self.secrets_scope, self.sp_client_id_key, self.sp_secret_key]):
            _log_warning("Missing secrets configuration (scope/keys). Cannot fetch SP credentials.")
            return

        _log_info("Fetching SP credentials from secrets...")
        try:
            self._sp_client_id = self._workspace_client.secrets.get_secret(
                scope=self.secrets_scope, key=self.sp_client_id_key
            ).value
            self._sp_client_secret = self._workspace_client.secrets.get_secret(
                scope=self.secrets_scope, key=self.sp_secret_key
            ).value
            _log_info("SP credentials fetched from secrets.")
        except Exception as e:
            _log_warning(f"Failed to fetch secrets: {e}")
            self._sp_client_id = None
            self._sp_client_secret = None
    
    def _refresh_token(self):
        """Generate a new OAuth token using Service Principal."""
        if not self._sp_client_id or not self._sp_client_secret:
            _log_warning("Cannot refresh token: Service Principal credentials not available.")
            self._token = None
            self._expires_at = None
            return

        if not self.lakebase_instance_name:
            _log_warning("Cannot refresh token: LAKEBASE_INSTANCE_NAME not set.")
            self._token = None
            self._expires_at = None
            return
        
        _log_info("Refreshing Lakebase OAuth token...")
        try:
            # Initialize a new WorkspaceClient for the Service Principal
            sp_client = WorkspaceClient(
                host=self.databricks_host,
                client_id=self._sp_client_id,
                client_secret=self._sp_client_secret
            )
            
            credential = sp_client.database.generate_database_credential(
                request_id=str(uuid.uuid4()),
                instance_names=[self.lakebase_instance_name]
            )
            
            self._token = credential.token
            # Set expiration 5 minutes before actual expiry for proactive refresh
            self._expires_at = datetime.fromisoformat(credential.expiration_time.replace('Z', '+00:00')) - timedelta(minutes=5)
            _log_info(f"Token refreshed. Expires at: {self._expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        except Exception as e:
            _log_error(f"Failed to refresh token: {e}")
            self._token = None
            self._expires_at = None
    
    def get_token(self) -> Optional[str]:
        """
        Returns the current valid OAuth token, refreshing it if it's expired or near expiration.
        Thread-safe.
        """
        with self._lock:
            now = datetime.now(timezone.utc)
            if not self._token or (self._expires_at and now >= self._expires_at):
                self._refresh_token()
            return self._token
    
    def get_connection_params(self) -> Dict[str, Any]:
        """Returns database connection parameters, including the current token as password."""
        return {
            "host": self.db_host,
            "port": self.db_port,
            "user": self.db_user,
            "password": self.get_token(), # Use the dynamically refreshed token
            "dbname": self.db_name,
            "sslmode": self.db_sslmode
        }


# Initialize token manager (will be None if not configured)
token_manager: Optional[LakebaseTokenManager] = None

def init_token_manager():
    """Initialize the token manager if OAuth is configured."""
    global token_manager
    
    # Check if OAuth is configured
    databricks_host = os.getenv("DATABRICKS_HOST")
    secrets_scope = os.getenv("DATABRICKS_SECRETS_SCOPE")
    
    if not databricks_host:
        raise Exception("DATABRICKS_HOST environment variable not set")
    if not secrets_scope:
        raise Exception("DATABRICKS_SECRETS_SCOPE environment variable not set")
    
    token_manager = LakebaseTokenManager()


# Initialize on module load
init_token_manager()

