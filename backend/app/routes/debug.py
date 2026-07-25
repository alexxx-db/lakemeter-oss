"""Debug and diagnostic endpoints.

These endpoints expose environment variables, database host/user details, and
token status. They are intended for LOCAL DEVELOPMENT AND STAGING ONLY and are
NOT registered when ENVIRONMENT=production (see app.main). In production, use
`databricks apps logs` and workspace monitoring instead.
"""
from fastapi import APIRouter, Request

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/headers")
def debug_headers(request: Request):
    """Debug endpoint to see what headers Databricks Apps sends."""
    from app.auth.databricks_auth import debug_headers as get_debug_headers
    return get_debug_headers(request)




@router.get("/database")
def debug_database():
    """Debug endpoint to check database connection status."""
    import os
    import uuid
    from app.auth.token_manager import token_manager
    
    result = {
        "environment_vars": {
            "DATABRICKS_HOST": os.getenv("DATABRICKS_HOST", "NOT SET"),
            "DATABRICKS_SECRETS_SCOPE": os.getenv("DATABRICKS_SECRETS_SCOPE", "NOT SET"),
            "LAKEBASE_INSTANCE_NAME": os.getenv("LAKEBASE_INSTANCE_NAME", "NOT SET"),
            "DB_HOST": os.getenv("DB_HOST", "NOT SET"),
            "DB_USER": os.getenv("DB_USER", "NOT SET"),
            "DB_NAME": os.getenv("DB_NAME", "NOT SET"),
        },
        "token_manager_status": "NOT INITIALIZED",
        "workspace_client_status": "NOT INITIALIZED",
        "sp_credentials_status": "NOT FETCHED",
        "token_status": "NO TOKEN",
        "token_error": None,
        "database_status": "NOT CONNECTED",
    }
    
    if token_manager:
        result["token_manager_status"] = "INITIALIZED"
        
        if token_manager._workspace_client:
            result["workspace_client_status"] = "INITIALIZED"
        
        # Try to generate token using the workspace client
        try:
            token = token_manager.get_token()
            if token:
                result["token_status"] = f"GENERATED (length: {len(token)})"
                result["db_user"] = token_manager.db_user
            else:
                result["token_status"] = "NO TOKEN"
        except Exception as e:
            result["token_status"] = "GENERATION FAILED"
            result["token_error"] = str(e)
        
        # Try to test database connection
        try:
            from app.database import engine, refresh_engine
            
            # If engine is None, try to refresh it now that we have a token
            if engine is None:
                result["database_status"] = "ENGINE IS NONE - attempting refresh..."
                try:
                    refresh_engine()
                    from app.database import engine as new_engine
                    if new_engine:
                        from sqlalchemy import text
                        with new_engine.connect() as conn:
                            conn.execute(text("SELECT 1"))
                        result["database_status"] = "CONNECTED (after refresh)"
                except Exception as refresh_err:
                    result["database_status"] = f"REFRESH FAILED: {str(refresh_err)}"
            else:
                from sqlalchemy import text
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                result["database_status"] = "CONNECTED"
        except Exception as e:
            result["database_status"] = f"ERROR: {str(e)}"
    
    return result


@router.post("/database/refresh")
def debug_database_refresh():
    """Force refresh the database token and reconnect."""
    from app.database import refresh_engine
    from app.auth.token_manager import token_manager
    
    result = {
        "action": "refresh",
        "token_refresh": "NOT ATTEMPTED",
        "engine_refresh": "NOT ATTEMPTED",
        "status": "UNKNOWN"
    }
    
    # Step 1: Force token refresh
    if token_manager:
        try:
            # Clear existing token to force refresh
            token_manager._token = None
            token_manager._expires_at = None
            
            # Get new token
            new_token = token_manager.get_token()
            if new_token:
                result["token_refresh"] = f"SUCCESS (length: {len(new_token)})"
            else:
                result["token_refresh"] = "FAILED - no token returned"
        except Exception as e:
            result["token_refresh"] = f"FAILED: {str(e)}"
    else:
        result["token_refresh"] = "SKIPPED - token_manager not initialized"
    
    # Step 2: Show connection params before attempting
    if token_manager:
        try:
            params = token_manager.get_connection_params()
            result["connection_params"] = {
                "host": params.get("host", "?"),
                "port": params.get("port", "?"),
                "user": params.get("user", "?"),
                "dbname": params.get("dbname", "?"),
                "sslmode": params.get("sslmode", "?"),
                "password_length": len(params.get("password", "") or ""),
            }
        except Exception as e:
            result["connection_params"] = f"ERROR: {str(e)}"

    # Step 3: Refresh database engine
    try:
        success = refresh_engine()
        if success:
            result["engine_refresh"] = "SUCCESS"
            result["status"] = "CONNECTED"
        else:
            result["engine_refresh"] = "FAILED"
            result["status"] = "DISCONNECTED"
    except Exception as e:
        result["engine_refresh"] = f"ERROR: {str(e)}"
        result["status"] = "ERROR"
    
    return result
