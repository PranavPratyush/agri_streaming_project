# AgriKafka-Agent: Codebase Walkthrough Guide (Stages 0–19)

**Purpose:** Professor-Facing Technical Source Code Walkthrough  
**Repository Working Directory:** `c:\Users\prana\OneDrive\Desktop\spa_pbl\agri_streaming_project`  
**Accuracy Invariant:** All line numbers, symbols, and variables are audited directly against the current implementation.  

---

## Recommended VS Code File-Opening Sequence

When presenting the codebase to professors, open these files in tabs from left to right:
1. `packages/event-contracts/src/agri_contracts/events/observation.py` (Canonical event schema)
2. `services/ingestion/src/agri_ingestion/adapters/live_opensensemap.py` (Physical telemetry ingestion)
3. `services/stream-processor/src/agri_stream_processor/pipeline.py` (PySpark Structured Streaming & DLQ)
4. `services/risk-engine/src/agri_risk_engine/health/detectors/flatline.py` (Sensor health & natural flatline differentiation)
5. `services/risk-engine/src/agri_risk_engine/risk/engine.py` (Deterministic FAO-56 crop risk engine)
6. `packages/agronomy-rag/src/agri_agronomy_rag/retriever.py` (Chroma vector retrieval & metadata filtering)
7. `services/alert-investigator/src/agri_investigator/supervisor.py` (Multi-agent supervisor & bounded state machine)
8. `services/alert-investigator/src/agri_investigator/safety.py` (Deterministic non-LLM safety gate)
9. `services/notification-worker/src/agri_notifications/dispatcher.py` (Compound idempotency & notification retries)
10. `services/api/src/agri_api/routers/advisories.py` (FastAPI human review lifecycle & feedback)
11. `apps/farmer-pwa/src/components/common/MultiAgentProgress.tsx` (Farmer 5-milestone investigation transparency)

---

## Component-by-Component Technical Walkthrough

### 1. Python Ingestion
- **File:** [`services/ingestion/src/agri_ingestion/adapters/live_opensensemap.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl\agri_streaming_project\services\ingestion\src\agri_ingestion\adapters\live_opensensemap.py#L25-L95)
- **Symbol / Class:** `OpenSenseMapAdapter`
- **Line Range:** Lines 25–95
- **Key Variables:** `station_id`, `box_data`, `sensors`, `val_str`, `event_time`, `unit_str`.
- **Input / Output:** HTTP REST JSON from openSenseMap API -> List of `SensorObservationEvent`.
- **Kafka Topic:** Produces to `agri.sensor-readings` (partition key: `field_id`).
- **Relevant Test:** `tests/unit/test_ingestion_adapters.py::test_opensensemap_adapter_parsing`
- **Runtime Evidence:** Polled station `Sarvamangalam` (`689b2bdc569c2d0007586ae9`) returning 5 real events with 19.6s latency.

### 2. Event Normalization and Validation
- **File:** [`packages/event-contracts/src/agri_contracts/events/observation.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl\agri_streaming_project\packages\event-contracts\src\agri_contracts\events\observation.py#L22-L75)
- **Symbol / Class:** `SensorObservationEvent`
- **Line Range:** Lines 22–75
- **Key Variables:** `event_id`, `schema_version` (`"1.0.0"`), `event_time`, `ingestion_time`, `field_id`, `idempotency_key`, `provenance`, `variable`, `value`, `unit`, `quality_flags`.
- **Input / Output:** Raw dict payload -> Validated Pydantic v2 event model.
- **Relevant Test:** `tests/contract/test_event_contracts.py::test_valid_observation_event_roundtrip`
- **Runtime Evidence:** Strict ISO-8601 UTC enforcement and automatic calculation of `freshness_latency_sec`.

### 3. Kafka Producer
- **File:** [`services/ingestion/src/agri_ingestion/producer.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl\agri_streaming_project\services\ingestion\src\agri_ingestion\producer.py#L28-L88)
- **Symbol / Class:** `AgriKafkaProducer.publish_observation()`
- **Line Range:** Lines 28–88
- **Key Variables:** `topic`, `key` (`field_id.encode('utf-8')`), `value` (JSON UTF-8 bytes), `delivery_callback`.
- **Kafka Topic:** `agri.sensor-readings`, with fallback routing to `agri.dead-letter-queue`.
- **Relevant Test:** `tests/integration/test_ingestion_kafka.py::test_kafka_producer_mock_publish`
- **Runtime Evidence:** Automatic dry-run fallback in development preventing crashes if local broker is down.

### 4. Kafka Topic Configuration
- **File:** [`infra/kafka/init_topics.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl\agri_streaming_project\infra\kafka\init_topics.py#L13-L96)
- **Symbol:** `CORE_TOPICS`
- **Line Range:** Lines 13–96
- **Key Variables:** 9 canonical topics (`agri.sensor-readings`, `agri.weather-data`, `agri.validated-observations`, `agri.sensor-health-events`, `agri.candidate-alerts`, `agri.investigation-results`, `agri.human-feedback`, `agri.dead-letter-queue`, `agri.operational-metrics`).
- **Relevant Test:** `tests/unit/test_prometheus_grafana_config.py`
- **Runtime Evidence:** Single-broker KRaft development profile with partitions=3, RF=1, and per-field keying.

### 5. Spark Kafka Consumer
- **File:** [`services/stream-processor/src/agri_stream_processor/pipeline.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl\agri_streaming_project\services\stream-processor\src\agri_stream_processor\pipeline.py#L58-L67)
- **Symbol:** `raw_obs_stream` in `build_streaming_pipeline()`
- **Line Range:** Lines 58–67
- **Key Variables:** `spark.readStream`, `format("kafka")`, `kafka.bootstrap.servers`, `subscribe` (`agri.sensor-readings`), `startingOffsets` (`latest`).
- **Input / Output:** Kafka binary stream `(key, value, timestamp)` -> Raw Spark DataFrame.
- **Relevant Test:** `tests/unit/test_stream_transformations.py::test_parse_kafka_stream_valid`

### 6. Spark Transformations
- **File:** [`services/stream-processor/src/agri_stream_processor/transformations.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl\agri_streaming_project\services\stream-processor\src\agri_stream_processor\transformations.py#L28-L115)
- **Symbols:** `parse_kafka_stream()`, `extract_validated_observations()`, `extract_dead_letter_records()`
- **Line Range:** Lines 28–115
- **Key Variables:** `from_json`, `obs_schema`, `watermark_duration`, `parsed_payload`.
- **Kafka Topics:** Reads `agri.sensor-readings`, writes to `agri.validated-observations` and `agri.dead-letter-queue`.
- **Relevant Test:** `tests/unit/test_stream_transformations.py`

### 7. Event-Time Processing, Windows & Watermarks
- **File:** [`services/stream-processor/src/agri_stream_processor/features.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl\agri_streaming_project\services\stream-processor\src\agri_stream_processor\features.py#L26-L88)
- **Symbols:** `calculate_windowed_aggregates()`, `calculate_soil_depletion()`
- **Line Range:** Lines 26–88
- **Key Variables:** `withWatermark("event_time", "10 minutes")`, `groupBy(window("event_time", "5 minutes"), "field_id", "variable")`.
- **Database Table:** Hypertables `windowed_features` in TimescaleDB.
- **Relevant Test:** `tests/unit/test_stream_transformations.py::test_windowed_aggregates`

### 8. Sensor-Health Detection
- **File:** [`services/risk-engine/src/agri_risk_engine/health/detectors/flatline.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl\agri_streaming_project\services\risk-engine\src\agri_risk_engine\health\detectors\flatline.py#L32-L105)
- **Symbol / Class:** `FlatlineDetector.detect()`
- **Line Range:** Lines 32–105
- **Key Variables:** `stuck_variance_epsilon` ($10^{-4}$), `min_consecutive_identical` (12), `is_rain_zero_exemption`, `is_soil_dry_plateau_exemption`.
- **Kafka Topic:** `agri.sensor-health-events` (Key: `sensor_id`).
- **Relevant Test:** `tests/unit/test_sensor_health_confusion_matrix.py` (24 fixtures, 0 False Positives).

### 9. Deterministic Crop-Risk Calculation
- **File:** [`services/risk-engine/src/agri_risk_engine/risk/engine.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl\agri_streaming_project\services\risk-engine\src\agri_risk_engine\risk\engine.py#L31-L150)
- **Symbol / Class:** `DeterministicCropRiskEngine.evaluate_field_risk()`
- **Line Range:** Lines 31–150
- **Key Variables:** `field_profile`, `fao56_depletion_fraction`, `composite_stress_index`, `thermal_stress_score`, `blast_risk_score`, `is_sensor_suppressed`.
- **Agronomic Grounding:** FAO-56 dual water balance for Ragi GPU-28 (TAW 60mm, RAW 27mm, threshold 0.166 m³/m³).
- **Relevant Test:** `tests/unit/test_crop_risk_scenarios.py`

### 10. Candidate Event Publication
- **File:** [`services/risk-engine/src/agri_risk_engine/risk/engine.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl\agri_streaming_project\services\risk-engine\src\agri_risk_engine\risk\engine.py#L125-L149)
- **Symbol:** `CropRiskCandidateAlertEvent` instantiation
- **Line Range:** Lines 125–149
- **Kafka Topic:** `agri.candidate-alerts` (Key: `field_id`).
- **Database Table:** `crop_candidate_alerts` hypertable.
- **Relevant Test:** `tests/unit/test_crop_risk_engine.py`

### 11. RAG Document Ingestion
- **File:** [`packages/agronomy-rag/src/agri_agronomy_rag/ingest.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl\agri_streaming_project\packages\agronomy-rag\src\agri_agronomy_rag\ingest.py#L35-L120)
- **Symbols:** `parse_and_chunk_document()`, `compute_corpus_version()`
- **Line Range:** Lines 35–120
- **Key Variables:** `source-register.csv`, `chunk_id`, `citation_id`, `section_heading`, `content_hash`.
- **Relevant Test:** `tests/unit/test_agronomy_rag.py::test_source_register_and_corpus_integrity`
- **Runtime Evidence:** 5 documents parsed into 21 chunks with corpus version `v1.0-1b95cf635c01`.

### 12. Embedding and Retrieval
- **File:** [`packages/agronomy-rag/src/agri_agronomy_rag/retriever.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl\agri_streaming_project\packages\agronomy-rag\src\agri_agronomy_rag\retriever.py#L23-L125)
- **Symbol / Class:** `AgronomyRetriever.retrieve()`
- **Line Range:** Lines 23–125
- **Key Variables:** `vector_store.query()`, `relevance_threshold` (0.50), `applied_filters`, `EvidenceBundle`.
- **Embedding Model:** `sentence-transformers/all-MiniLM-L6-v2 (ONNX)` (384d).
- **Relevant Test:** `tests/unit/test_agronomy_rag.py::test_rag_retrieval_and_filtering`
- **Runtime Evidence:** Mean Reciprocal Rank (MRR) = 0.7333.

### 13. Supervisor / Coordinator
- **File:** [`services/alert-investigator/src/agri_investigator/supervisor.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl\agri_streaming_project\services\alert-investigator\src\agri_investigator\supervisor.py#L170-L380)
- **Symbol / Class:** `MultiAgentSupervisor.investigate_alert()`
- **Line Range:** Lines 170–380
- **Key Variables:** `state`, `rel_task`, `ctx_task`, `risk_task`, `know_task`, `adv_task`, `critic_task`, `max_revisions` (2).
- **Relevant Test:** `tests/unit/test_multi_agent_investigation.py::test_end_to_end_investigation_success_flow`
- **Runtime Evidence:** 15-state bounded state machine without non-deterministic loops.

### 14. Shared Investigation State
- **File:** [`services/alert-investigator/src/agri_investigator/models.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl\agri_streaming_project\services\alert-investigator\src\agri_investigator\models.py#L173-L194)
- **Symbol:** `InvestigationState`
- **Line Range:** Lines 173–194
- **Key Variables:** `run_id`, `alert_id`, `field_id`, `current_state`, `sensor_reliability`, `field_context`, `risk_assessment`, `evidence_bundle`, `advisory_proposal`, `critic_review`, `safety_gate_result`, `messages`.
- **Database Table:** `multi_agent_investigation_runs` (persisted via `PersistenceRepository`).
- **Relevant Test:** `tests/unit/test_multi_agent_investigation.py`

### 15. Agent Message Schemas
- **File:** [`services/alert-investigator/src/agri_investigator/protocol.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl\agri_streaming_project\services\alert-investigator\src\agri_investigator\protocol.py#L15-L77)
- **Symbol:** `AgentMessage`
- **Line Range:** Lines 15–77
- **Key Variables:** `message_id`, `run_id`, `from_agent`, `to_agent`, `message_type`, `payload`, `idempotency_key`.
- **Database Table:** `agent_messages`.
- **Relevant Test:** `tests/unit/test_multi_agent_investigation.py::test_duplicate_message_idempotency_collision`

### 16. Specialist Agents (All 6)
- **Sensor Reliability Agent:** [`agents/sensor_reliability.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl\agri_streaming_project\services\alert-investigator\src\agri_investigator\agents\sensor_reliability.py#L28-L98) (Lines 28–98)
- **Field Context Agent:** [`agents/field_context.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl\agri_streaming_project\services\alert-investigator\src\agri_investigator\agents\field_context.py#L53-L112) (Lines 53–112)
- **Crop Risk Analyst Agent:** [`agents/crop_risk_analyst.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl\agri_streaming_project\services\alert-investigator\src\agri_investigator\agents\crop_risk_analyst.py#L35-L98) (Lines 35–98)
- **Agronomy Knowledge Agent:** [`agents/agronomy_knowledge.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl\agri_streaming_project\services\alert-investigator\src\agri_investigator\agents\agronomy_knowledge.py#L42-L108) (Lines 42–108)
- **Agricultural Advisory Agent:** [`agents/agricultural_advisory.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl\agri_streaming_project\services\alert-investigator\src\agri_investigator\agents\agricultural_advisory.py#L33-L114) (Lines 33–114)
- **Critic / Safety Agent:** [`agents/critic_safety.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl\agri_streaming_project\services\alert-investigator\src\agri_investigator\agents\critic_safety.py#L34-L106) (Lines 34–106)
- **Relevant Tests:** `tests/unit/test_multi_agent_investigation.py` (13 passed).

### 17. Agent Handoffs and Communication
- **File:** [`services/alert-investigator/src/agri_investigator/supervisor.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl\agri_streaming_project\services\alert-investigator\src\agri_investigator\supervisor.py#L210-L290)
- **Line Range:** Lines 210–290
- **Implementation Detail:** Sensor Reliability and Field Context run independently; outputs are stored in `InvestigationState` and then packaged into `CropRiskAnalystInput`.
- **Runtime Evidence:** Total 12 structured messages logged per successful investigation run.

### 18. Revision / Feedback Loop
- **File:** [`services/alert-investigator/src/agri_investigator/supervisor.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl\agri_streaming_project\services\alert-investigator\src\agri_investigator\supervisor.py#L291-L380)
- **Line Range:** Lines 291–380
- **Key Variables:** `while state.revision_count <= self.max_revisions:`, `state.revision_count += 1`, `instructions.issues`.
- **Relevant Test:** `tests/unit/test_multi_agent_investigation.py::test_critic_revision_routing_and_recovery`

### 19. Critic / Safety Validation
- **File:** [`services/alert-investigator/src/agri_investigator/safety.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl\agri_streaming_project\services\alert-investigator\src\agri_investigator\safety.py#L34-L162)
- **Symbol / Class:** `DeterministicSafetyGate.audit_complete_investigation()`
- **Line Range:** Lines 34–162
- **Hard Gates:** Rejection of chemical dosages (`audit_chemical_and_actuation_policy`), rejection of hallucinated citations (`audit_advisory_citations`), rejection of autonomous actuation.
- **Relevant Test:** `tests/unit/test_multi_agent_investigation.py::test_chemical_dosage_advice_rejected_by_safety_gate`

### 20. Database Persistence
- **File:** [`packages/database-client/src/agri_persistence/repository.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl\agri_streaming_project\packages\database-client\src\agri_persistence\repository.py#L470-L685)
- **Symbol / Class:** `PersistenceRepository`
- **Key Methods:** `create_multi_agent_run()`, `record_agent_message()`, `record_state_transition()`, `create_farmer_recommendation()`, `record_human_feedback()`.
- **Database Tables:** `multi_agent_investigation_runs`, `agent_messages`, `investigation_state_transitions`, `farmer_recommendations`, `human_feedback`, `notification_dispatches`.

### 21. Backend API Endpoints
- **File:** [`services/api/src/agri_api/routers/advisories.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl\agri_streaming_project\services\api\src\agri_api\routers\advisories.py#L23-L220)
- **Endpoints:** `GET /advisories`, `GET /advisories/{id}`, `POST /advisories/{id}/action`, `GET /feedback`, `POST /feedback`, `GET /notifications/dispatches`.
- **Security:** Scoped RBAC, parcel boundary verification (`verify_field_access`).
- **Relevant Test:** `tests/unit/test_api_endpoints.py`, `tests/unit/test_notifications_and_feedback.py`

### 22. Frontend Data-Fetching Functions
- **File:** [`apps/farmer-pwa/src/services/api.ts`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl\agri_streaming_project\apps\farmer-pwa\src\services\api.ts#L170-L380)
- **Methods:** `getFieldStatus()`, `getTrends()`, `getSensorFreshness()`, `getAlerts()`, `getAdvisories()`, `submitAdvisoryDecision()`, `submitFeedback()`.
- **Invariant:** Interacts strictly with `/api/v1/` REST routes; zero direct database or Kafka queries.

### 23. Human Approval Workflow
- **File:** [`services/notification-worker/src/agri_notifications/lifecycle.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl\agri_streaming_project\services\notification-worker\src\agri_notifications\lifecycle.py#L36-L140)
- **Symbol / Class:** `HumanReviewLifecycleManager.apply_action()`
- **Line Range:** Lines 36–140
- **States:** `AWAITING_REVIEW`, `APPROVED`, `REJECTED`, `ACKNOWLEDGED`, `REQUEST_INSPECTION`, `EXPIRED`, `SUPERSEDED`.
- **Invariant:** `actuation_command_dispatched: false` explicitly asserted on every outcome.

### 24. Prometheus Metric Definitions
- **File:** [`packages/shared-python/src/agri_shared/metrics.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl\agri_streaming_project\packages\shared-python\src\agri_shared\metrics.py#L40-L210)
- **Instruments:** 28 standardized Prometheus metrics (Ingestion, Kafka, Spark, Sensor Health, Crop Risk, Investigator, Database, Notifications).
- **Invariant:** Strict low-cardinality label whitelist preventing Prometheus memory exhaustion.
- **Relevant Test:** `tests/unit/test_metrics_instrumentation.py`

