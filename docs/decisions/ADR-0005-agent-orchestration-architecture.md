# ADR-0005: Agent Orchestration Architecture

- **Status:** Proposed (Pending User Approval)
- **Date:** 2026-11-01
- **Deciders:** Lead Engineer, Team (Aanish Khan, Daksh Chauhan, Pranav Pratyush)
- **Technical Domain:** Agentic AI, Tool Calling, Workflow Orchestration

---

## 1. Context & Problem Statement
The alert investigator must examine candidate alerts flagged by PySpark stream detection. It must sequence read-only tools conditionally (e.g. check sensor health first; if healthy, check history, weather, and agronomy RAG; if faulty, halt and classify as sensor error), enforce token budgets, validate citations, and fallback on failure.

We need to choose between:
1. Direct Python Bounded Tool-Calling State Machine.
2. LangGraph state graph framework.

---

## 2. Options Considered

### Option 1: Direct Python Bounded Tool-Calling State Machine (Recommended)
- **Architecture:** Pure Python class (`BoundedAlertInvestigator`) implementing an explicit, deterministic state graph.
- **Pros:**
  - Zero heavy framework dependencies (eliminates `langchain`, `langgraph`, and associated version thrash).
  - Extremely fast execution (< 2ms framework overhead).
  - 100% auditable: every tool call, input, output, and decision branch is recorded as an immutable step log in the event envelope.
  - Trivial to mock and unit test with `pytest`.
  - Deterministic guardrails (citation check, dosage filter) execute naturally in native Python.
- **Cons:**
  - Lacks built-in LangGraph Studio UI visualization (mitigated by logging state transitions to TimescaleDB/Grafana).

### Option 2: LangGraph Framework
- **Architecture:** Formal `StateGraph` with nodes and conditional edges.
- **Pros:**
  - Industry-standard abstraction for cyclic agent workflows.
  - Built-in state checkpointing.
- **Cons:**
  - Heavy dependency footprint with frequent breaking updates.
  - Adds unnecessary cognitive and debugging overhead for a bounded, read-only 6-step tool investigation.

---

## 3. Decision
Adopt **Option 1 (Direct Python Bounded State Machine)**:
1. Build the investigator in `services/alert-investigator/` using a clean state pattern with an explicit `InvestigationState` dataclass.
2. Enforce hard limits: maximum 6 tool calls, 8-second LLM timeout, and 15-second total budget.
3. Keep the interface clean and node-based so that wrapping with LangGraph remains a non-breaking future option if external visualization is needed.

---

## 4. Consequences

### Positive
- Robust, transparent, and ultra-fast reasoning loop.
- Easy debugging and testing; zero dependency hell.
- Complete adherence to the project invariant: deterministic guardrails and bounded agent actions.

### Negative
- Custom state graph code must be maintained within the project rather than relying on an external library.
