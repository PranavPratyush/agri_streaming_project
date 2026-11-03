# ADR-0006: LLM Provider & Offline Fallback Strategy

- **Status:** Proposed (Pending User Approval)
- **Date:** 2026-11-01
- **Deciders:** Lead Engineer, Team (Aanish Khan, Daksh Chauhan, Pranav Pratyush)
- **Technical Domain:** Artificial Intelligence, LLM Inference, Resilience Fallback

---

## 1. Context & Problem Statement
AgriKafka-Agent requires an LLM for selective candidate alert investigation, triage reasoning, and citation-grounded advisory drafting. We must balance reasoning quality, JSON schema compliance, latency, cost, and offline resilience without incurring paid cloud costs or downloading massive multi-gigabyte models without permission.

---

## 2. Options Evaluated

| Dimension | Hosted Free-Tier API (Gemini Flash) | Local Ollama (Llama 3.2 / Mistral) | Deterministic Rule Fallback |
|---|---|---|---|
| **Latency** | Fast (400–900 ms) | Moderate/Slow on CPU (4–15 s) | Instant (< 5 ms) |
| **Structured Output** | Native `response_schema` (100% valid JSON) | Supported via GBNF grammar, occasionally drifts | 100% deterministic template |
| **Cost** | Free tier (zero cost) | Free (zero token cost) | Free |
| **Offline Operation** | Requires Internet access | 100% Offline | 100% Offline |
| **Hardware Footprint** | Zero local RAM footprint | Requires 2–5 GB local RAM | 0 MB extra RAM |
| **Privacy** | Data leaves local machine (over TLS) | 100% Private | 100% Private |

---

## 3. Decision
Adopt a **Hierarchical Dual-Tier Architecture with Deterministic Fallback**:

1. **Primary Inference Tier:** **Google Gemini API (Free Tier, `gemini-1.5-flash`)**.
   - Leverages native JSON schema enforcement for guaranteed structured output.
   - Low latency preserves streaming responsiveness.
   - Zero financial cost on free quota.
2. **Resilience / Offline Fallback Tier:** **Deterministic Rule-Based Engine**.
   - If the external API times out (> 8s), returns an error, or the machine is offline, the investigator falls back **immediately** to the deterministic agronomic rule engine.
   - Formulates a standardized alert template with raw metrics and flags `investigation_status: FALLBACK_RULE_ENGINE`.
3. **Optional Local Ollama Runner:**
   - Architecture provides an adapter interface for local Ollama (`llama3.2:3b`).
   - *Constraint:* Ollama models will **NOT** be downloaded without explicit user authorization.

---

## 4. Consequences

### Positive
- Zero paid API expenses.
- 100% operational resilience: the streaming pipeline and demo continue without interruption even if internet access drops.
- High-fidelity structured JSON during normal execution.

### Negative
- Hosted API usage requires outbound HTTPS internet access.

### Neutral
- System logs fallback activation metrics to Prometheus for resilience evaluation.
