# AgriKafka-Agent Farmer Progressive Web App (PWA)

**Module:** `apps/farmer-pwa`  
**Framework:** React 18 + Vite + TypeScript  
**Implementation Stage:** Stage 18  
**Architecture Decisions:** `ADR-0007` (React 18 + Vite PWA), `ADR-0010` (Multi-Agent State Machine Supervisor)

---

## 1. Overview & Capabilities

The AgriKafka Farmer PWA is an accessible, mobile-first progressive web application tailored for smallholder dryland farmers (specifically finger millet growers in Kolar, Karnataka) and extension agronomists.

### Core Capabilities
- **Bilingual Interface:** Instantaneous toggle between English and Kannada (ಕನ್ನಡ).
- **Real-Time Telemetry:** Ground capacitive soil moisture ($m^3/m^3$) and regional meteorological telemetry.
- **Sensor Reliability Notice:** Plain-language explanations of sensor health, data freshness, and transmission status.
- **Deterministic Alert Inbox:** Contextual explanations of observed moisture depletion and why it impacts flowering yield.
- **Multi-Agent Transparency:** 5-milestone progression tracking sensor reliability, crop context, risk severity, agronomic knowledge retrieval, and safety review.
- **Human Decision Controls:** One-tap action buttons (`Approve`, `Reject`, `Request Inspection`) with zero autonomous valve actuation.
- **Farmer Feedback Outcome Loop:** 1–5 star rating and post-irrigation recovery logging.
- **PWA & Offline Capability:** Service worker precaching (`sw.js`) and web app manifest (`manifest.json`).

---

## 2. Directory Structure

```
apps/farmer-pwa/
├── public/
│   ├── favicon.svg             # Application SVG icon
│   ├── manifest.json           # PWA standalone manifest
│   └── sw.js                   # Service Worker offline caching script
├── src/
│   ├── components/
│   │   ├── common/
│   │   │   ├── Badge.tsx               # Status & provenance badges
│   │   │   ├── Header.tsx              # Brand header & language toggle
│   │   │   ├── Icons.tsx               # Lightweight accessible inline SVGs
│   │   │   ├── MultiAgentProgress.tsx  # 5-milestone investigation tracker
│   │   │   └── Navbar.tsx              # Bottom navigation bar
│   │   └── screens/
│   │       ├── AdvisoriesScreen.tsx    # Recommendations & action controls
│   │       ├── AlertsScreen.tsx        # Alerts inbox & physical evidence
│   │       ├── FieldsScreen.tsx        # Parcel list & profile setup/edit
│   │       ├── HistoryScreen.tsx       # Chronological audit log
│   │       ├── OnboardingScreen.tsx    # Field sign-in & onboarding guide
│   │       ├── OverviewScreen.tsx      # Real-time telemetry cards & status
│   │       └── TrendsScreen.tsx        # 24h/7d depletion trend visualization
│   ├── i18n/
│   │   └── translations.ts     # Complete English & Kannada dictionary
│   ├── services/
│   │   └── api.ts              # Exclusive backend API integration client
│   ├── test/
│   │   ├── accessibility.test.tsx  # WCAG & landmark tests
│   │   ├── api_service.test.ts     # API client contract tests
│   │   ├── components.test.tsx     # Screen rendering & workflow tests
│   │   └── setup.ts                # Test runner setup
│   ├── types/
│   │   └── api.ts              # TypeScript API contract models
│   ├── App.tsx                 # Root application state & router
│   ├── index.css               # Mobile-first accessible stylesheet
│   └── main.tsx                # React DOM mount & SW registration
├── index.html                  # HTML entrypoint with PWA meta tags
├── package.json                # Dependencies and scripts
├── tsconfig.json               # TypeScript configuration
└── vite.config.ts              # Vite & Vitest configuration
```

---

## 3. Local Development & Testing

### Running the Development Server
```bash
cd apps/farmer-pwa
npm run dev
```
Open `http://127.0.0.1:5173` in your browser.

### Running Automated Tests
```bash
cd apps/farmer-pwa
npm test
```
All 13 unit, component, and accessibility tests execute in Vitest.

### Production Build & Preview
```bash
cd apps/farmer-pwa
npm run build
npm run preview
```
Production bundle is compiled into `dist/` (gzip size: ~64 kB).
