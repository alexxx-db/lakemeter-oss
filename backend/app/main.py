"""FastAPI main application entry point."""
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings, setup_logging, log_info
from app.routes import (
    estimates_router,
    line_items_router,
    workload_types_router,
    users_router,
    export_router,
    vm_pricing_router,
    calculate_router,
    reference_router
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
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    redirect_slashes=False
)

# Log startup info
log_info(f"Starting Lakemeter API (environment: {settings.environment})")

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


@app.get("/api")
def api_root():
    """API root endpoint."""
    return {
        "name": "Lakemeter API",
        "version": "1.0.0",
        "description": "Databricks Pricing Calculator API"
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


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
        app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")
    
    # Mount static pricing data (for instant local calculations)
    PRICING_DIR = STATIC_DIR / "pricing"
    if PRICING_DIR.exists():
        app.mount("/static/pricing", StaticFiles(directory=PRICING_DIR), name="pricing")
        log_info(f"Pricing bundle found at {PRICING_DIR}")

    # Mount documentation site (Docusaurus build)
    DOCS_DIR = STATIC_DIR / "docs"
    if DOCS_DIR.exists():
        app.mount("/docs", StaticFiles(directory=DOCS_DIR, html=True), name="docs")
        log_info(f"Documentation site mounted at /docs/")
    
    # Serve static files at root (favicon, etc.)
    @app.get("/favicon.ico")
    async def favicon():
        favicon_path = STATIC_DIR / "favicon.ico"
        if favicon_path.exists():
            return FileResponse(favicon_path)
        return FileResponse(STATIC_DIR / "databricks-icon.svg")
    
    @app.get("/databricks-icon.svg")
    async def databricks_icon():
        return FileResponse(STATIC_DIR / "databricks-icon.svg")
    
    # Serve index.html at root
    @app.get("/")
    async def serve_root():
        """Serve React SPA at root."""
        return FileResponse(STATIC_DIR / "index.html")
    
    # SPA catch-all handler - serve index.html for non-API routes
    # This must be the LAST route defined
    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        """Serve React SPA for all non-API routes."""
        # Don't intercept API routes
        if full_path.startswith("api/"):
            return {"error": "Not found"}, 404
        
        # Serve index.html for client-side routing
        return FileResponse(STATIC_DIR / "index.html")

else:
    log_info("Static files not found - running in API-only mode (local development)")
    
    # In local dev mode, serve API info at root
    @app.get("/")
    def root():
        """Root endpoint (local dev only)."""
        return {
            "name": "Lakemeter API",
            "version": "1.0.0",
            "description": "Databricks Pricing Calculator API",
            "mode": "API-only (frontend served separately)"
        }
