# ADR-0008: Multi-Agent Investigation Architecture & Structured Specialist Handoffs

- **Status:** Approved (Incorporating Professor Feedback)
- **Date:** 2026-11-04
- **Deciders:** Lead Engineer, Team (Aanish Khan, Daksh Chauhan, Pranav Pratyush)
- **Technical Domain:** Agentic AI, Multi-Agent Coordination, Bounded State Machines, Deterministic Guardrails
- **Supersedes / Refines:** Refines ADR-0005 (evolves single bounded investigator into coordinated multi-agent supervisor with 6 specialist agents while strictly retaining pure Python state machine architecture)

---

## 1. Context & Problem Statement

In the initial architecture (ADR-0005), candidate agricultural alerts were triaged by a single-agent investigator equipped with 8 read-only inspection tools. Based on Stream Processing and Analytics (SPA) professor evaluation and feedback, a monolithic agent approach has key architectural vulnerabilities:
1. **Conflation of Diagnostic Roles:** A single agent attempting to evaluate raw electrical sensor anomalies while simultaneously interpreting biological crop water deficits suffers from role confusion and prompt dilution.
2. **Lack of Independent Peer Review (Self-Correction):** The entity drafting the agricultural recommendation was also the entity assessing its safety, lacking an independent critic auditor.
3. **Auditability of Handoffs:** Academic and operational rigor requires explicit, versioned message handoffs between distinct functional roles (telemetry reliability, parcel context, agronomic risk analysis, knowledge retrieval, advisory drafting, and safety criticism).

We must evolve the investigation architecture into a **Coordinated Multi-Agent System** without:
- Introducing heavy frameworks (e.g. LangGraph, CrewAI) that violate ADR-0005;
- Allowing uncontrolled recursive loops or broadcast storms;
- Permitting LLMs to override deterministic sensor forensics or fabricate citations;
- Allowing automated agents to approve advisories or actuate physical irrigation.

---

## 2. Options Considered

### Option 1: Monolithic Agent with 6 Specialized Tools (Rejected)
- One LLM call with a broad system prompt and 6 sub-tools.
- **Flaw:** High prompt dilution; reasoning steps are hidden in unvalidated tool calls; violates professor requirement.

### Option 2: Framework-Based Multi-Agent Graph (e.g. LangGraph / AutoGen) (Rejected)
- Multi-agent graph using LangGraph nodes.
- **Flaw:** Violates project invariant ADR-0005; introduces version instability and heavy runtime dependencies without adding reasoning rigor.

### Option 3: Pure-Python Supervisor with 6 Separately Invocable Specialist Agents (Selected)
- One central Supervisor/Coordinator orchestrating 6 distinct specialist agents via versioned `AgentMessage` contracts over a bounded 15-state deterministic state machine.
- Every specialist has an isolated class, distinct input/output schema, specific prompt version, and isolated latency/token metrics.
- Deterministic safety gates (citations, chemical dosage regex, sensor health veto) run externally in pure Python.

---

## 3. Decision

Adopt **Option 3 (Pure-Python Supervisor with 6 Separately Invocable Specialist Agents)**:

1. **The 6 Specialist Agents:**
   - `sensor_reliability_agent`: Interprets Stage 11 sensor forensics; differentiates natural flatlines from true faults; issues hard go/no-go recommendation for agronomic advice.
   - `field_context_agent`: Retrieves parcel metadata, cultivar parameters, and regional weather context; explicitly flags missing metadata.
   - `crop_risk_analyst_agent`: Integrates reliability + field context with deterministic CSI/water balance; formulates structured risk hypothesis and explicit evidence request.
   - `agronomy_knowledge_agent`: Queries Stage 15 RAG service; selects accredited chunks; validates citation IDs.
   - `agricultural_advisory_agent`: Formulates cautious, field-contextual advisory proposals citing verified evidence chunks; abstains on missing evidence.
   - `critic_safety_agent`: Independently audits cross-agent consistency, citation grounding, absence of chemical dosages, and uncertainty acknowledgment.

2. **Controlled Message Routing & Bounded Revisions:**
   - All agent communication must route through the `MultiAgentSupervisor`. Direct agent-to-agent recursive calling is strictly forbidden (`InvalidMessageError`).
   - Revision cycles requested by the Critic are bounded by `max_revisions = 2`. Exceeding this terminates the run safely as `ABSTAINED_MAX_REVISIONS_EXCEEDED`.

3. **External Deterministic Safety Boundary:**
   - Even if the Critic approves, the advisory must pass `DeterministicSafetyGate.audit_complete_investigation()` (zero hallucinated citations, zero chemical dosages per `agronomic-safety.md`, zero autonomous physical actuation).
   - The terminal output is `awaiting_human_review`. Human agronomist/farmer approval is a separate manual lifecycle state (`approved_by_human` / `rejected_by_human`).

---

## 4. Consequences

### Positive
- Fully fulfills SPA professor requirements with clear, auditable separation of concerns.
- 100% auditable message log (`agent_messages`) and transition history (`investigation_state_transitions`).
- Zero reliance on external heavy agent frameworks; lightweight, ultra-fast (<15ms framework overhead), and deterministic.
- Full offline testability using mocked responses or local ONNX RAG embeddings.

### Negative
- Requires maintaining separate input and output schemas and unit tests for 6 specialist agents.

