"""FastAPI main application entry point."""
from pathlib import Path
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import text

from app.config import settings, setup_logging, log_info
from app.database import get_db
from app.version import APP_VERSION
from app.routes import (
    estimates_router,
    line_items_router,
    workload_types_router,
    users_router,
    export_router,
    vm_pricing_router,
    calculate_router,
    reference_router,
    health_router
)
from app.routes.chat import router as chat_router

# Initialize logging based on environment
setup_logging()

# Create FastAPI application
# redirect_slashes=False prevents automatic redirects that break CORS
# Disable docs in production for cleaner deployment
app = FastAPI(
    title="Lakemeter API",
    description="Databricks Pricing Calculator API - Estimate and manage Databricks workload costs",
    version=APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    redirect_slashes=False
)

# Log startup info
log_info(f"Starting Lakemeter API (environment: {settings.environment})")

# Opt-in anonymous telemetry (no-op unless TELEMETRY_ENABLED=true and
# TELEMETRY_ENDPOINT are set — see app/telemetry.py for guarantees).
from app import telemetry
telemetry.track_event("app_started", {"environment": settings.environment})

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(estimates_router, prefix="/api/v1")
app.include_router(line_items_router, prefix="/api/v1")
app.include_router(workload_types_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(export_router, prefix="/api/v1")
app.include_router(vm_pricing_router, prefix="/api/v1")
app.include_router(calculate_router, prefix="/api/v1")
app.include_router(reference_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
# Readiness and diagnostics carry their own full paths (/health/ready,
# /api/v1/diagnostics) — no prefix.
app.include_router(health_router)


@app.get("/api")
def api_root():
    """API root endpoint."""
    return {
        "name": "Lakemeter API",
        "version": APP_VERSION,
        "description": "Databricks Pricing Calculator API"
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": APP_VERSION}


@app.get("/api/v1/system/version")
def system_version():
    """Return machine-readable version and upgrade policy metadata."""
    return {
        "app_version": APP_VERSION,
        "upgrade_policy": {
            "patch": "code_only",
            "minor": "data_update",
            "major": "schema_migration",
        },
    }


@app.get("/api/v1/system/health")
def system_health(db=Depends(get_db)):
    """Verify both the running application and its database connection."""
    db.execute(text("SELECT 1"))
    return {
        "status": "healthy",
        "app_version": APP_VERSION,
        "database": "connected",
    }


# Debug/diagnostic endpoints are registered ONLY outside production.
# They expose environment variables and database details; in production use
# `databricks apps logs` and workspace monitoring instead.
if not settings.is_production:
    from app.routes.debug import router as debug_router
    app.include_router(debug_router, prefix="/api/v1")
    log_info("Debug endpoints enabled at /api/v1/debug/* (non-production environment)")




# =============================================================================
# Static File Serving for Combined Frontend + Backend Deployment
# Must be AFTER all API routes
# =============================================================================

# Path to static files (React build)
STATIC_DIR = Path(__file__).parent.parent / "static"

# Check if static directory exists (production deployment)
if STATIC_DIR.exists() and (STATIC_DIR / "index.html").exists():
    log_info(f"Static files found at {STATIC_DIR}, enabling SPA serving")

    # Mount static assets (JS, CSS, images)
    if (STATIC_DIR / "assets").exists():
        app.mount(
            "/assets",
            StaticFiles(directory=STATIC_DIR / "assets"),
            name="assets",
        )

    # Mount static pricing data (for instant local calculations)
    PRICING_DIR = STATIC_DIR / "pricing"
    if PRICING_DIR.exists():
        app.mount(
            "/static/pricing",
            StaticFiles(directory=PRICING_DIR),
            name="pricing",
        )
        log_info(f"Pricing bundle found at {PRICING_DIR}")

    # Mount documentation site (Docusaurus build)
    DOCS_DIR = STATIC_DIR / "docs"
    if DOCS_DIR.exists():
        app.mount(
            "/docs",
            StaticFiles(directory=DOCS_DIR, html=True),
            name="docs",
        )
        log_info("Documentation site mounted at /docs/")

    # Serve favicon
    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        favicon_path = STATIC_DIR / "favicon.ico"
        fallback_path = STATIC_DIR / "databricks-icon.svg"

        if favicon_path.exists():
            return FileResponse(favicon_path)

        if fallback_path.exists():
            return FileResponse(fallback_path)

        raise HTTPException(status_code=404, detail="Favicon not found")

    # Serve Databricks icon
    @app.get("/databricks-icon.svg", include_in_schema=False)
    async def databricks_icon():
        icon_path = STATIC_DIR / "databricks-icon.svg"

        if not icon_path.exists():
            raise HTTPException(
                status_code=404,
                detail="Databricks icon not found",
            )

        return FileResponse(icon_path)

    # Serve index.html at root
    @app.get("/", include_in_schema=False)
    async def serve_root():
        """Serve the React SPA at the application root."""
        return FileResponse(STATIC_DIR / "index.html")

    # SPA catch-all handler.
    # This must remain the final route defined in the application.
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(request: Request, full_path: str):
        """Serve the React SPA for non-API client-side routes."""

        # Do not allow the SPA handler to mask missing API endpoints.
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API route not found")

        return FileResponse(STATIC_DIR / "index.html")

else:
    log_info(
        "Static files not found - running in API-only mode "
        "(local development)"
    )

    # In local development, serve API information at root.
    @app.get("/")
    def root():
        """Return API information when the frontend is served separately."""
        return {
            "name": "Lakemeter API",
            "version": APP_VERSION,
            "description": "Databricks Pricing Calculator API",
            "mode": "API-only (frontend served separately)",
        }
