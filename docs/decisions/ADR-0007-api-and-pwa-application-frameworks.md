# ADR-0007: Backend API & Farmer PWA Application Frameworks

- **Status:** Proposed (Pending User Approval)
- **Date:** 2026-11-01
- **Deciders:** Lead Engineer, Team (Aanish Khan, Daksh Chauhan, Pranav Pratyush)
- **Technical Domain:** Application Layer, Web Framework, Frontend PWA, Authentication

---

## 1. Context & Problem Statement
AgriKafka-Agent requires:
1. A backend API in `services/api/` to serve field profiles, streaming telemetry summaries, alert queues, and record farmer approval actions.
2. A farmer-facing mobile-first Progressive Web App (PWA) in `apps/farmer-pwa/` with offline capability, plain explanations, and bilingual (English/Kannada) support.
3. An authentication and approval authorization mechanism appropriate for a local research prototype.

---

## 2. Options Considered

### Backend API Framework
- **FastAPI (Recommended):** Modern, asynchronous ASGI, native Pydantic v2 support, automatic OpenAPI/Swagger documentation, lightweight, broad community adoption.
- **Litestar:** High performance, but less ubiquitous than FastAPI.
- **Flask:** Synchronous WSGI by default; lacks native async streaming and automatic OpenAPI generation.

### Farmer PWA Frontend Framework
- **React 18 + Vite PWA (`vite-plugin-pwa`) (Recommended):**
  - Ultra-fast HMR and bundle compilation.
  - Rich ecosystem for mobile-responsive components, accessible UI, and internationalization (i18next for Kannada/English).
  - Native service worker configuration for offline field caching.
- **Vanilla JavaScript PWA:**
  - Zero framework dependencies, but high boilerplate for state synchronization, multi-page routing, and bilingual localization.
- **Next.js:**
  - Full-stack SSR is overkill for a lightweight client and adds Node server hosting overhead.

### Authentication & Human Approval Authorization
- **Local Research Prototype Approach (Recommended):**
  - Lightweight, scoped API key or session token (`X-Farmer-ID: field-owner-1`) for PWA access.
  - Action verification: Each candidate recommendation carries a cryptographically signed HMAC or opaque one-time approval token (`approval_token: uuid`).
  - Clicking **Approve** or **Reject** in either the PWA or Telegram submits this token, ensuring idempotency and preventing duplicate replay actions.

---

## 3. Decision
1. **Backend Framework:** **FastAPI $\ge 0.115$** running under `uvicorn`.
2. **Frontend Framework:** **React 18 + TypeScript + Vite + `vite-plugin-pwa`** in `apps/farmer-pwa/`.
3. **Authentication Strategy:** Lightweight scoped headers (`X-Farmer-ID`) with UUIDv4 one-time action tokens for idempotent human approvals.

---

## 4. Consequences

### Positive
- Unified Pydantic models shared between Kafka contracts and FastAPI endpoints.
- Rapid frontend prototyping with hot module replacement and service-worker offline caching.
- Secure, idempotent action authorization without complex OAuth2 server infrastructure overhead during local evaluation.

### Negative
- Requires Node.js build step (`npm run build`) for production PWA bundling (Node 23.11.0 is already verified on host).
