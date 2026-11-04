# Multi-Agent Investigation Architecture: Code Walkthrough & Traceability

- **Module:** `services/alert-investigator` (`src/agri_investigator`)
- **Status:** IMPLEMENTED AND VERIFIED
- **Date:** 2026-11-04
- **Verification Evidence:** `tests/unit/test_multi_agent_investigation.py` (13/13 passing in 6.14s)

---

## 1. Specialist Agent Classes & Invocation Functions

| Specialist Role | File Path | Class Symbol | Line Range | Input Schema | Output Schema | Proving Unit Test |
|---|---|---|---|---|---|---|
| **Base Agent** | [`services/alert-investigator/src/agri_investigator/agents/base.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/services/alert-investigator/src/agri_investigator/agents/base.py) | `BaseSpecialistAgent` | Lines 21–87 | Abstract (`BaseModel`) | Abstract (`BaseModel`) | `test_multi_agent_investigation.py::test_end_to_end_investigation_success_flow` |
| **Sensor Reliability** | [`services/alert-investigator/src/agri_investigator/agents/sensor_reliability.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/services/alert-investigator/src/agri_investigator/agents/sensor_reliability.py) | `SensorReliabilityAgent` | Lines 28–98 | `SensorReliabilityInput` (Lines 18–25) | `SensorReliabilityOutput` ([`models.py#L86-L97`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/services/alert-investigator/src/agri_investigator/models.py#L86-L97)) | `test_multi_agent_investigation.py::test_faulty_sensor_blocks_crop_advice` |
| **Field Context** | [`services/alert-investigator/src/agri_investigator/agents/field_context.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/services/alert-investigator/src/agri_investigator/agents/field_context.py) | `FieldContextAgent` | Lines 53–112 | `FieldContextInput` (Lines 44–50) | `FieldContextOutput` ([`models.py#L99-L112`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/services/alert-investigator/src/agri_investigator/models.py#L99-L112)) | `test_multi_agent_investigation.py::test_risk_analyst_consumes_reliability_and_field_context` |
| **Crop Risk Analyst** | [`services/alert-investigator/src/agri_investigator/agents/crop_risk_analyst.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/services/alert-investigator/src/agri_investigator/agents/crop_risk_analyst.py) | `CropRiskAnalystAgent` | Lines 35–98 | `CropRiskAnalystInput` (Lines 26–32) | `CropRiskAnalystOutput` ([`models.py#L125-L135`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/services/alert-investigator/src/agri_investigator/models.py#L125-L135)) | `test_multi_agent_investigation.py::test_risk_analyst_consumes_reliability_and_field_context` |
| **Agronomy Knowledge** | [`services/alert-investigator/src/agri_investigator/agents/agronomy_knowledge.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/services/alert-investigator/src/agri_investigator/agents/agronomy_knowledge.py) | `AgronomyKnowledgeAgent` | Lines 42–108 | `AgronomyKnowledgeInput` (Lines 21–27) | `AgronomyKnowledgeOutput` (Lines 30–39) | `test_multi_agent_investigation.py::test_knowledge_agent_retrieves_genuine_bundle` |
| **Agricultural Advisory** | [`services/alert-investigator/src/agri_investigator/agents/agricultural_advisory.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/services/alert-investigator/src/agri_investigator/agents/agricultural_advisory.py) | `AgriculturalAdvisoryAgent` | Lines 33–114 | `AgriculturalAdvisoryInput` (Lines 22–30) | `AdvisoryProposalOutput` ([`models.py#L137-L149`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/services/alert-investigator/src/agri_investigator/models.py#L137-L149)) | `test_multi_agent_investigation.py::test_end_to_end_investigation_success_flow` |
| **Critic & Safety** | [`services/alert-investigator/src/agri_investigator/agents/critic_safety.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/services/alert-investigator/src/agri_investigator/agents/critic_safety.py) | `CriticSafetyAgent` | Lines 34–106 | `CriticSafetyInput` (Lines 24–31) | `CriticReviewOutput` ([`models.py#L151-L159`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/services/alert-investigator/src/agri_investigator/models.py#L151-L159)) | `test_multi_agent_investigation.py::test_critic_revision_routing_and_recovery` |

---

## 2. Core Orchestration & Communication Components

### 2.1 Supervisor Dispatch & Pipeline Execution
- **File:** [`services/alert-investigator/src/agri_investigator/supervisor.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/services/alert-investigator/src/agri_investigator/supervisor.py)
- **Class / Symbol:** `MultiAgentSupervisor.investigate_alert()`
- **Line Range:** Lines 170–422
- **Key Variables:** `run_id`, `state`, `rel_task`, `ctx_task`, `risk_task`, `know_task`, `adv_task`, `critic_task`, `revision_instructions`.
- **Proving Test:** `test_multi_agent_investigation.py::test_end_to_end_investigation_success_flow`

### 2.2 Shared State Creation & Updates
- **File:** [`services/alert-investigator/src/agri_investigator/models.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/services/alert-investigator/src/agri_investigator/models.py)
- **Symbol:** `InvestigationState`
- **Line Range:** Lines 173–194
- **State Fields:** `run_id`, `alert_id`, `field_id`, `current_state`, `revision_count`, `sensor_reliability`, `field_context`, `risk_assessment`, `evidence_bundle`, `advisory_proposal`, `critic_review`, `safety_gate_result`, `audit_trail`, `messages`.
- **Proving Test:** `test_multi_agent_investigation.py::test_end_to_end_investigation_success_flow`

### 2.3 Agent Message Creation & Idempotent Routing
- **File:** [`services/alert-investigator/src/agri_investigator/protocol.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/services/alert-investigator/src/agri_investigator/protocol.py)
- **Symbols:** `create_agent_message()` (Lines 44–77), `generate_idempotency_key()` (Lines 29–41), `MessageRouter` (Lines 80–105).
- **Proving Tests:**
  - `test_multi_agent_investigation.py::test_duplicate_message_idempotency_collision`
  - `test_multi_agent_investigation.py::test_direct_agent_to_agent_message_rejected`

### 2.4 State Machine Transition Validation
- **File:** [`services/alert-investigator/src/agri_investigator/state.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/services/alert-investigator/src/agri_investigator/state.py)
- **Symbols:** `VALID_TRANSITIONS` (Lines 34–97), `validate_transition()` (Lines 100–104), `transition_state()` (Lines 107–130).
- **Proving Test:** `test_multi_agent_investigation.py::test_invalid_state_transition_raises_error`

### 2.5 Critic Revision Loop & Bounded Exhaustion
- **File:** [`services/alert-investigator/src/agri_investigator/supervisor.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/services/alert-investigator/src/agri_investigator/supervisor.py)
- **Loop Block:** Lines 291–380
- **Exhaustion Guard:** Lines 355–363 (`if state.revision_count > state.max_revisions: transition to ABSTAINED`)
- **Proving Tests:**
  - `test_multi_agent_investigation.py::test_critic_revision_routing_and_recovery`
  - `test_multi_agent_investigation.py::test_max_revisions_exceeded_terminates_abstained`

### 2.6 Deterministic Non-LLM Safety Gates
- **File:** [`services/alert-investigator/src/agri_investigator/safety.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/services/alert-investigator/src/agri_investigator/safety.py)
- **Symbol:** `DeterministicSafetyGate` (Lines 34–162)
  - `audit_sensor_reliability()`: Lines 36–54
  - `audit_advisory_citations()`: Lines 56–99
  - `audit_chemical_and_actuation_policy()`: Lines 101–131
  - `audit_complete_investigation()`: Lines 133–162
- **Proving Tests:**
  - `test_multi_agent_investigation.py::test_chemical_dosage_advice_rejected_by_safety_gate`
  - `test_multi_agent_investigation.py::test_autonomous_physical_actuation_rejected`
  - `test_multi_agent_investigation.py::test_hallucinated_citation_rejected`

### 2.7 TimescaleDB Persistence Integration
- **File:** [`packages/database-client/src/agri_persistence/repository.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/packages/database-client/src/agri_persistence/repository.py)
- **Symbols:**
  - `create_multi_agent_run()`: Lines 468–518
  - `update_multi_agent_run()`: Lines 520–537
  - `record_agent_message()`: Lines 539–577
  - `record_state_transition()`: Lines 579–603
  - `get_multi_agent_run()`: Lines 605–632
  - `get_run_messages()`: Lines 634–661
  - `get_run_state_transitions()`: Lines 663–684
- **Migration:** `infra/database/migrations/003_multi_agent_investigation.up.sql`
- **Proving Test:** `test_database_schema.py::test_migration_discovery_and_offline_validation`

### 2.8 Prometheus Metrics Instrumentation
- **File:** [`packages/shared-python/src/agri_shared/metrics.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/packages/shared-python/src/agri_shared/metrics.py)
- **Symbols:**
  - `MULTI_AGENT_INVOCATIONS_TOTAL`: Lines 229–234
  - `MULTI_AGENT_HANDOFFS_TOTAL`: Lines 236–241
  - `MULTI_AGENT_REVISIONS_TOTAL`: Lines 243–248
  - `MULTI_AGENT_ABSTENTIONS_TOTAL`: Lines 250–255
  - `MULTI_AGENT_AGENT_DURATION_SECONDS`: Lines 257–263
  - `MULTI_AGENT_RUN_DURATION_SECONDS`: Lines 265–271
- **Proving Test:** `test_metrics_instrumentation.py::test_metrics_conform_to_cardinality_rules`

