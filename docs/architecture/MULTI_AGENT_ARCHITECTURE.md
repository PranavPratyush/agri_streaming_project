# Multi-Agent Investigation Architecture Specification

- **Module:** `services/alert-investigator` (`src/agri_investigator`)
- **Status:** IMPLEMENTED AND VERIFIED
- **Date:** 2026-11-04
- **Author:** AgriKafka Engineering Team
- **Governing Decision:** [ADR-0008: Multi-Agent Investigation Architecture](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/docs/decisions/ADR-0008-multi-agent-investigation-architecture.md)

---

## 1. System Overview & Core Philosophy

The **AgriKafka-Agent Multi-Agent Investigation Architecture** replaces the monolithic investigator with a coordinated topology featuring **one Supervisor/Coordinator and six separately invocable specialist agents**.

```mermaid
flowchart TD
    CandidateAlert[Candidate Alert from PySpark Risk Engine] --> Supervisor[Multi-Agent Supervisor]

    subgraph FanOut["Phase 1: Dual Diagnostic Ingestion (Parallel)"]
        Supervisor -->|TASK_REQUEST| SRA[Sensor Reliability Agent]
        Supervisor -->|TASK_REQUEST| FCA[Field Context Agent]
        SRA -->|SensorReliabilityOutput| Supervisor
        FCA -->|FieldContextOutput| Supervisor
    end

    subgraph Evaluation["Phase 2: Risk Analysis & Grounded Evidence Retrieval"]
        Supervisor -->|Reliability + Context + Alert| CRA[Crop Risk Analyst Agent]
        CRA -->|AgronomyEvidenceRequest| Supervisor
        Supervisor -->|EvidenceRequest| AKA[Agronomy Knowledge Agent]
        AKA -->|Queries Stage 15 Chroma RAG| Stage15RAG[(Chroma Vector DB: 21 Chunks)]
        AKA -->|EvidenceBundle| Supervisor
    end

    subgraph AdvisoryAndCritic["Phase 3: Advisory Synthesis & Critic Audit Loop"]
        Supervisor -->|Risk + Context + Evidence| AAA[Agricultural Advisory Agent]
        AAA -->|AdvisoryProposalOutput| Supervisor
        Supervisor -->|Advisory + Evidence + Context| CSA[Critic / Safety Agent]
        CSA -->|REVISION_REQUIRED| Supervisor
        Supervisor -.->|Bounded Revision (max=2)| AAA
        CSA -->|APPROVED_FOR_HUMAN_REVIEW| Supervisor
    end

    subgraph SafetyGate["Phase 4: Deterministic Policy Gating (External)"]
        Supervisor --> DSG{Deterministic Safety Gate}
        DSG -->|Citations / Chemical Regex / Sensor Health| GatePassed{Passed?}
        GatePassed -->|Yes| HumanQueue[State: awaiting_human_review]
        GatePassed -->|No| AbstainQueue[State: abstained]
    end

    subgraph HumanAction["Phase 5: Human Decision Lifecycle"]
        HumanQueue --> FarmerReview{Farmer / Agronomist Decision}
        FarmerReview -->|Approve| CompletedApproved[State: approved_by_human -> completed]
        FarmerReview -->|Reject| CompletedRejected[State: rejected_by_human -> completed]
    end
```

---

## 2. Specialist Agent Catalog & Functional Invariants

Every specialist is an isolated Python class inheriting from `BaseSpecialistAgent` with separate input/output schemas, distinct prompt versions, and dedicated metrics.

| Agent Symbol | Class Location | Input Schema | Output Schema | Key Functional Responsibilities | Core Invariants & Safety Constraints |
|---|---|---|---|---|---|
| `sensor_reliability_agent` | `agri_investigator.agents.sensor_reliability` | `SensorReliabilityInput` | `SensorReliabilityOutput` | Evaluates sensor health results from Stage 11; differentiates natural flatlines from sensor faults; determines if telemetry is safe for crop advice. | Interprets Stage 11 forensics; must NEVER override or recalculate deterministic sensor-health classifications. |
| `field_context_agent` | `agri_investigator.agents.field_context` | `FieldContextInput` | `FieldContextOutput` | Retrieves parcel profiles, cultivar parameters (Ragi GPU-28), soil hydraulics, and regional weather context. | NEVER invent missing field, crop, or soil parameters. Regional context is NOT treated as parcel in-situ telemetry. |
| `crop_risk_analyst_agent` | `agri_investigator.agents.crop_risk_analyst` | `CropRiskAnalystInput` | `CropRiskAnalystOutput` | Synthesizes telemetry reliability, field metadata, and deterministic CSI/water balance; drafts risk hypothesis; formulates focused evidence request. | NEVER recalculate deterministic CSI or modify threshold values; index is not described as damage probability. |
| `agronomy_knowledge_agent` | `agri_investigator.agents.agronomy_knowledge` | `AgronomyKnowledgeInput` | `AgronomyKnowledgeOutput` | Queries Stage 15 RAG service (`retrieve_agronomy_guidance`); selects accredited chunks; validates citation IDs. | Must ONLY return evidence actually retrieved by Stage 15 RAG. Emits explicit `EVIDENCE_INSUFFICIENT` if no chunks meet threshold. |
| `agricultural_advisory_agent` | `agri_investigator.agents.agricultural_advisory` | `AgriculturalAdvisoryInput` | `AdvisoryProposalOutput` | Formulates cautious, field-contextual advisory proposals citing verified evidence chunks; specifies when to seek agronomist inspection. | Zero unsupported diagnosis; zero chemical pesticide/fertilizer dosages; zero autonomous actuation; abstains on untrusted telemetry. |
| `critic_safety_agent` | `agri_investigator.agents.critic_safety` | `CriticSafetyInput` | `CriticReviewOutput` | Independently audits cross-agent consistency, citation backing, absence of chemical dosages, and uncertainty acknowledgment. | Critic approval is not the final authority; deterministic policy and safety gates execute externally outside all LLM agents. |

---

## 3. Supervisor Coordination Dynamics

The **`MultiAgentSupervisor`** (`agri_investigator.supervisor.py`) operates as a deterministic workflow controller:
1. **No Direct Agent-to-Agent Mesh:** Specialist agents never invoke each other directly. All interactions are mediated via the Supervisor using `AgentMessage` envelopes.
2. **Deterministic Gating:** If `sensor_reliability.proceed_to_agronomy` is `False`, the Supervisor halts the run immediately, setting state to `ABSTAINED` (`ABSTAINED_SENSOR_FAULT`), preventing crop advice on faulty sensor readings.
3. **Bounded Revision Protocol:** When Critic issues `REVISION_REQUIRED`, Supervisor routes instructions to the designated upstream agent. Revisions are hard-capped by `max_revisions = 2`. If exceeded, the run terminates as `ABSTAINED_MAX_REVISIONS_EXCEEDED` to eliminate infinite reasoning loops.
4. **External Deterministic Safety Gating:** All proposed advisories pass through `DeterministicSafetyGate` before reaching the human review queue.
5. **Human Review Isolation:** Transitioning to `approved_by_human` or `rejected_by_human` requires explicit invocation of `submit_human_decision()`. No automated process can approve on behalf of the farmer.

