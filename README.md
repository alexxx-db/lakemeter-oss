# Lakemeter - Databricks Pricing Calculator

A full-stack application for creating, managing, and exporting Databricks pricing estimates. Built with React + Tailwind CSS frontend and FastAPI backend, connected to a Databricks Lakebase database.

## Features

### Workload Types (from Lakebase)
The workload types are dynamically loaded from the `lakemeter.ref_workload_types` table:

| Workload Type | Display Name | SKU (Standard) | SKU (Photon) | SKU (Serverless) |
|---------------|--------------|----------------|--------------|------------------|
| JOBS | Jobs Compute | JOBS_COMPUTE | JOBS_COMPUTE_(PHOTON) | JOBS_SERVERLESS_COMPUTE |
| ALL_PURPOSE | All-Purpose Compute | ALL_PURPOSE_COMPUTE | ALL_PURPOSE_COMPUTE_(PHOTON) | INTERACTIVE_SERVERLESS_COMPUTE |
| DLT | Delta Live Tables | DLT_CORE_COMPUTE | DLT_CORE_COMPUTE_(PHOTON) | DELTA_LIVE_TABLES_SERVERLESS |
| DBSQL | Databricks SQL | SQL_COMPUTE | SQL_PRO_COMPUTE | SERVERLESS_SQL_COMPUTE |
| VECTOR_SEARCH | Vector Search | - | - | VECTOR_SEARCH_ENDPOINT |
| MODEL_SERVING | Model Serving | - | - | SERVERLESS_REAL_TIME_INFERENCE |
| FMAPI_DATABRICKS | Foundation Models (Databricks) | - | - | SERVERLESS_REAL_TIME_INFERENCE |
| FMAPI_PROPRIETARY | Foundation Models (Proprietary) | - | - | - |
| LAKEBASE | Lakebase | - | - | DATABASE_SERVERLESS_COMPUTE |

### Key Features
- **Dynamic SKU Selection**: SKUs automatically update based on workload configuration
- **Serverless Toggle**: Switch between classic and serverless compute
- **Photon Acceleration**: Enable/disable Photon for compatible workloads
- **Export to Excel**: Download estimates with detailed worksheets
- **Estimate Management**: Create, duplicate, and delete estimates

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  React + Vite   │────▶│    FastAPI      │────▶│   Lakebase      │
│  Tailwind CSS   │     │    Python       │     │   PostgreSQL    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
     Frontend               Backend                Database
```

## Quick Start

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set database connection
export DATABASE_URL="postgresql://user:pass@host:5432/lakemeter"

# Run server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173`

## Database Schema

### Reference Table: `lakemeter.ref_workload_types`

```sql
CREATE TABLE lakemeter.ref_workload_types (
    workload_type VARCHAR(50) PRIMARY KEY,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    show_compute_config BOOLEAN DEFAULT FALSE,
    show_serverless_toggle BOOLEAN DEFAULT FALSE,
    show_serverless_performance_mode BOOLEAN DEFAULT FALSE,
    show_photon_toggle BOOLEAN DEFAULT FALSE,
    show_dlt_config BOOLEAN DEFAULT FALSE,
    show_dbsql_config BOOLEAN DEFAULT FALSE,
    show_serverless_product BOOLEAN DEFAULT FALSE,
    show_fmapi_config BOOLEAN DEFAULT FALSE,
    show_lakebase_config BOOLEAN DEFAULT FALSE,
    show_vector_search_mode BOOLEAN DEFAULT FALSE,
    show_vm_pricing BOOLEAN DEFAULT FALSE,
    show_usage_hours BOOLEAN DEFAULT FALSE,
    show_usage_runs BOOLEAN DEFAULT FALSE,
    show_usage_tokens BOOLEAN DEFAULT FALSE,
    sku_product_type_standard VARCHAR(100),
    sku_product_type_photon VARCHAR(100),
    sku_product_type_serverless VARCHAR(100),
    display_order INTEGER DEFAULT 0
);
```

### Insert Reference Data

```sql
INSERT INTO lakemeter.ref_workload_types VALUES
('JOBS', 'Jobs Compute', 'Scheduled batch jobs (Classic or Serverless)', true, true, true, true, false, false, false, false, false, false, true, false, true, false, 'JOBS_COMPUTE', 'JOBS_COMPUTE_(PHOTON)', 'JOBS_SERVERLESS_COMPUTE', 1),
('ALL_PURPOSE', 'All-Purpose Compute', 'Interactive clusters for notebooks (Classic or Serverless)', true, true, false, true, false, false, false, false, false, false, true, true, false, false, 'ALL_PURPOSE_COMPUTE', 'ALL_PURPOSE_COMPUTE_(PHOTON)', 'INTERACTIVE_SERVERLESS_COMPUTE', 2),
('DLT', 'Delta Live Tables', 'Declarative ETL pipelines (Classic or Serverless)', true, true, true, true, true, false, false, false, false, false, true, true, false, false, 'DLT_CORE_COMPUTE', 'DLT_CORE_COMPUTE_(PHOTON)', 'DELTA_LIVE_TABLES_SERVERLESS', 3),
('DBSQL', 'Databricks SQL', 'SQL analytics warehouse (Classic/Pro/Serverless)', false, false, false, false, false, true, false, false, false, false, false, true, false, false, 'SQL_COMPUTE', 'SQL_PRO_COMPUTE', 'SERVERLESS_SQL_COMPUTE', 4),
('VECTOR_SEARCH', 'Vector Search', 'Vector search endpoints for RAG', false, false, false, false, false, false, true, false, false, true, false, true, false, false, NULL, NULL, 'VECTOR_SEARCH_ENDPOINT', 5),
('MODEL_SERVING', 'Model Serving', 'Real-time model inference endpoints', false, false, false, false, false, false, true, false, false, false, false, true, false, false, NULL, NULL, 'SERVERLESS_REAL_TIME_INFERENCE', 6),
('FMAPI_DATABRICKS', 'Foundation Models (Databricks)', 'Databricks-hosted LLMs (Llama, DBRX)', false, false, false, false, false, false, false, true, false, false, false, false, false, true, NULL, NULL, 'SERVERLESS_REAL_TIME_INFERENCE', 7),
('FMAPI_PROPRIETARY', 'Foundation Models (Proprietary)', 'OpenAI, Anthropic, Google models served by Databricks', false, false, false, false, false, false, false, true, false, false, false, false, false, true, NULL, NULL, NULL, 8),
('LAKEBASE', 'Lakebase', 'Managed PostgreSQL database for operational workloads', false, false, false, false, false, false, false, false, true, false, false, true, true, false, NULL, NULL, 'DATABASE_SERVERLESS_COMPUTE', 9);
```

## API Endpoints

### Workload Types
- `GET /api/v1/workload-types` - List all workload types from database

### Estimates
- `GET /api/v1/estimates` - List all estimates
- `POST /api/v1/estimates` - Create estimate
- `GET /api/v1/estimates/{id}` - Get estimate
- `PUT /api/v1/estimates/{id}` - Update estimate
- `DELETE /api/v1/estimates/{id}` - Delete estimate
- `POST /api/v1/estimates/{id}/duplicate` - Duplicate estimate

### Line Items
- `GET /api/v1/line-items/estimate/{id}` - List line items
- `POST /api/v1/line-items` - Create line item
- `PUT /api/v1/line-items/{id}` - Update line item
- `DELETE /api/v1/line-items/{id}` - Delete line item

### Export
- `GET /api/v1/export/estimate/{id}/excel` - Export to Excel

### Reference Data
- `GET /api/v1/reference/clouds` - Cloud providers and regions
- `GET /api/v1/reference/instance-types/{cloud}` - Instance types
- `GET /api/v1/reference/dbsql-sizes` - SQL Warehouse sizes
- `GET /api/v1/reference/dlt-editions` - DLT editions
- `GET /api/v1/reference/fmapi-models` - Foundation models

## Tech Stack

**Frontend**
- React 18 + TypeScript
- Tailwind CSS
- Vite
- Zustand (state management)
- Framer Motion (animations)
- React Hot Toast (notifications)

**Backend**
- FastAPI
- SQLAlchemy
- PostgreSQL (Lakebase)
- XlsxWriter (Excel export)

## License

MIT
