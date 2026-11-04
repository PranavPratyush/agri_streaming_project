# AgriKafka-Agent Backend API Service

**Module:** `services/api`  
**Framework:** FastAPI (ASGI) + Pydantic V2  
**Implementation Stage:** Stage 17  
**Architecture Decisions:** `ADR-0007` (FastAPI + Asyncpg/Psycopg), `ADR-0010` (Multi-Agent State Machine Supervisor)

---

## 1. Architectural Scope & Invariants

The AgriKafka-Agent Backend API provides the public and operational boundary for the entire streaming, multi-agent investigation, and agronomic advisory platform. It serves the Farmer Progressive Web App (PWA) and Agronomist / Extension Workbenches without allowing clients to bypass the multi-agent supervisor, agent contracts, deterministic safety gates, or human approval.

### Core System Invariants
1. **Supervisor Exclusivity:** Investigations are strictly invoked through `MultiAgentSupervisor`, never by calling individual specialist agents directly.
2. **State Machine Integrity:** The API cannot bypass workflow states, manually alter agent outputs, or mark a Critic rejection as approved.
3. **Information Security:** No raw LLM prompts, private chain-of-thought, infrastructure secrets, internal file paths, or raw unstructured outputs are leaked in client responses.
4. **Zero Physical Actuation:** Human approval (`APPROVE`, `REJECT`) records decision provenance and updates advisory status only. It never triggers automated physical control or actuation commands to irrigation hardware.
5. **Role-Based Isolation (RBAC):** Farmers are strictly quarantined to parcels they own. Regional agronomists and admins have authorized regional oversight.

---

## 2. Authentication & Scoped Authorization

Identity is established via standard HTTP request headers:
- `X-User-Role`: Client role (`farmer`, `agronomist`, `admin`). Defaults to `farmer`.
- `X-User-ID`: Unique user identifier (e.g., `farmer-kolar-01`, `agronomist-kvk-01`).
- `X-Farmer-ID`: Farmer parcel ID (e.g., `field-kolar-001`). Used to enforce field ownership boundaries.
- `X-API-Key`: Required for administrative / operations debug routes (`AGRI_ADMIN_API_KEY`).

| Role | Field Ownership Enforcement | Operations Status (`/operations/status`) | Advisory Human Actions | Debug State (`/admin/debug/state`) |
| :--- | :--- | :--- | :--- | :--- |
| **Farmer** | Access strictly confined to own registered field parcels | Denied (`403 Forbidden`) | View advisories & submit execution feedback | Denied (`403 Forbidden`) |
| **Agronomist** | Full regional access to all field parcels | Allowed (`200 OK`) | Approve / Reject / Request Inspection | Denied (`403 Forbidden`) |
| **Admin** | Full system-wide access | Allowed (`200 OK`) | Full administrative oversight | Allowed with valid API key |

---

## 3. Endpoints Directory

All versioned endpoints are prefixed with `/api/v1`.

### Operations & Diagnostics (Root & `/api/v1`)
- `GET /healthz` — Service liveness probe.
- `GET /readyz` — Service readiness probe (checks database and vector store connectivity).
- `GET /metrics` — Prometheus metrics scrape endpoint.
- `GET /api/v1/operations/status` — Comprehensive operational state (investigation counters, KRaft broker status, TimescaleDB pool state, ChromaDB version). Requires agronomist or admin role.
- `GET /api/v1/admin/debug/state` — Low-level administrative debug state. Requires admin role and API key.

### Fields & Parcels (`/api/v1/fields`)
- `GET /api/v1/fields` — List registered field parcels (paginated, filtered by role boundary).
- `POST /api/v1/fields` — Register a new field parcel (Agronomist/Admin only).
- `GET /api/v1/fields/{id}` — Retrieve field parcel profile and soil properties.
- `PATCH /api/v1/fields/{id}` & `PUT /api/v1/fields/{id}` — Update field metadata (e.g., current growth stage, irrigation type).
- `GET /api/v1/fields/{id}/status` — Real-time operational status, composite stress index, risk category, and data freshness.

### Telemetry & Sensor Health (`/api/v1`)
- `GET /api/v1/fields/{id}/observations` — Time-series physical observations with quality flags and provenance.
- `GET /api/v1/fields/{id}/trends` — 24h temporal trends and statistical summaries (soil moisture, temperature).
- `GET /api/v1/fields/{id}/sensor-health` — Historical sensor health classifications and reason codes.
- `GET /api/v1/sensors/freshness` — Fleet-wide sensor latency, telemetry freshness, and connectivity state.

### Alerts & Evidence (`/api/v1/alerts`)
- `GET /api/v1/alerts` — Query candidate risk alerts (filter by field, status, severity, limit).
- `GET /api/v1/alerts/{id}` — Query specific alert details.
- `GET /api/v1/alerts/{id}/evidence` — Retrieve corroborated sensor evidence and deterministic threshold metrics.

### Multi-Agent Investigations (`/api/v1/investigations`)
- `POST /api/v1/investigations` — Trigger multi-agent investigation on a candidate alert via `MultiAgentSupervisor`.
- `GET /api/v1/investigations/{id}` — Retrieve sanitized investigation summary and decisions.
- `GET /api/v1/investigations/{id}/timeline` — Chronological state machine transition timeline.
- `GET /api/v1/investigations/{id}/messages` — Auditable agent handoff summaries (without raw prompts or hidden chain-of-thought).
- `GET /api/v1/investigations/{id}/citations` — Accredited knowledge base citations supporting the investigation.
- `POST /api/v1/investigations/{id}/human-decision` — Submit human approval (`APPROVE`, `REJECT`) with idempotency token.

### Advisories & Farmer Feedback (`/api/v1`)
- `GET /api/v1/advisories` — List proposed or resolved farmer advisories.
- `GET /api/v1/advisories/{id}` — Retrieve specific advisory proposal.
- `POST /api/v1/advisories/{id}/action` — Agronomist approval, rejection, or inspection request.
- `GET /api/v1/feedback` — List recorded farmer feedback.
- `POST /api/v1/feedback` — Farmer execution outcome feedback and utility rating (1-5).

---

## 4. Local Development & Running

### Starting the Server
```bash
# Launch development ASGI server with hot reloading on port 8000
python -m uvicorn agri_api.main:app --host 127.0.0.1 --port 8000 --reload
```

### Interactive Documentation
- **Swagger UI:** `http://127.0.0.1:8000/docs`
- **ReDoc:** `http://127.0.0.1:8000/redoc`
- **OpenAPI JSON:** `http://127.0.0.1:8000/openapi.json`

### Running the Test Suite
```bash
pytest tests/unit/test_api_endpoints.py tests/unit/test_api_auth_boundaries.py -v
```
