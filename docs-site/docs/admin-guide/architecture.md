---
sidebar_position: 5
---

# Architecture Notes

Lakemeter is a Databricks App with a FastAPI backend, React frontend, and Lakebase (Postgres) for OLTP storage of estimates, users, sharing, and AI conversations. Pricing snapshots live in Lakebase `sync_*` tables. Auth is Databricks Apps SSO (`X-Forwarded-*` headers).

## Why this stack

| Concern | Choice |
|---|---|
| Estimate CRUD, sharing, chat history | Lakebase OLTP |
| Pricing lookups | Lakebase sync tables (+ static pricing bundle for the UI) |
| Hosting | Databricks Apps (AWS/Azure workspaces) |
| AI assistant | Foundation Model API (Claude) via workspace endpoint |

The product is an **estimator**, not an analytics dashboard over Unity Catalog warehouses.

## Databricks AppKit — when to use (and when not to)

[Databricks AppKit](https://docs.databricks.com/) patterns (and related AppKit / AI/BI building blocks) are a strong fit when the primary UX is **UC analytics**: Lakeview-style dashboards, Genie natural-language SQL over warehouse tables, or IBCS KPI surfaces backed by SQL warehouses.

**Keep the current FastAPI + React + Lakebase architecture when:**

- The workload is **transactional** (create/edit estimates, line items, sharing ACLs, durable chat).
- Users need **low-latency form interaction** and Excel export with formula-driven discounts.
- Pricing and config are **snapshot OLTP data**, not warehouse fact tables.

**Consider AppKit (or Genie) only if you add a separate surface such as:**

- Usage analytics over exported estimate history landed in UC
- Natural-language Q&A over a curated estimate mart
- Executive dashboards that do not replace the OLTP estimator

Migrating the core estimator into AppKit would trade away Lakebase-centric CRUD, custom export, and the existing calculate API surface without a clear customer benefit for sizing workflows.

## Lakebase connectivity

The app uses Service Principal OAuth for Lakebase when available, with a secrets-based password fallback. Connections use `pool_pre_ping`, proactive engine refresh before token expiry, **atomic dispose** of replaced engines, and **bounded jittered retries** on cold-start / scale-to-zero transient errors before returning HTTP 503.

## Related

- [Pricing Data](./pricing-data)
- [Deployment](./deployment)
- [API Reference](./api-reference)
