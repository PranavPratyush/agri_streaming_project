# Agent Communication Protocol Specification

- **Module:** `services/alert-investigator` (`src/agri_investigator/protocol.py`)
- **Status:** IMPLEMENTED AND VERIFIED
- **Date:** 2026-11-04
- **Author:** AgriKafka Engineering Team

---

## 1. Message Envelope Architecture

All communication between the Supervisor and specialist agents is encapsulated within an immutable, strongly-typed **`AgentMessage`** Pydantic v2 contract.

```json
{
  "message_id": "a3b4c5d6-e7f8-4901-abcd-ef0123456789",
  "run_id": "9fab0029-8b7c-4362-85f6-8a9d1dbb850e",
  "correlation_id": "c1a4169f-48bd-494d-a2e0-32c3f2e9688a",
  "parent_message_id": "12345678-abcd-ef01-2345-6789abcdef01",
  "from_agent": "supervisor",
  "to_agent": "sensor_reliability_agent",
  "message_type": "task_request",
  "payload_schema_version": "1.0.0",
  "payload": {
    "candidate_alert": { ... },
    "sensor_health_results": [ ... ]
  },
  "created_at": "2026-11-04T19:15:39.123456+00:00",
  "deadline": null,
  "idempotency_key": "9fab0029:root:rev0:supervisor:sensor_reliability_agent:task_request:f3a...",
  "status": "ACCEPTED",
  "error_details": null
}
```

### Key Field Specifications

| Field | Type | Description & Semantic Constraints |
|---|---|---|
| `message_id` | UUID (string) | Universally unique message identifier generated per dispatch. |
| `run_id` | UUID (string) | Foreign key tying the message to an active `multi_agent_investigation_runs` record. |
| `correlation_id` | UUID (string) | Trace identifier (typically the triggering `alert_id`). |
| `parent_message_id` | UUID (optional) | Points to the predecessor message in a request/response or revision exchange. |
| `from_agent` | String | Sender role identifier (e.g. `supervisor`, `critic_safety_agent`). |
| `to_agent` | String | Recipient role identifier. Must include `supervisor` in one of `from_agent` or `to_agent`. |
| `message_type` | Enum | `task_request`, `task_response`, `revision_request`, `revision_response`, `supervisor_decision`, `error_notification`. |
| `payload_schema_version` | String | Pinned contract version (currently `"1.0.0"`). |
| `payload` | Dict / Model | Strongly validated input/output payload adhering to the recipient's schema. |
| `idempotency_key` | String (SHA-256) | Deterministic composite hash preventing duplicate message side effects. |
| `status` | String | Processing state: `ACCEPTED`, `REJECTED`, or `ERROR`. |

---

## 2. Idempotency Key Generation & Duplicate Rejection

To ensure safe replays and prevent accidental double-processing during retries or network pauses, the `MessageRouter` enforces strict idempotency checking:

$$\text{idempotency\_key} = \text{SHA256}(\text{run\_id} : \text{parent\_id} : \text{rev\_count} : \text{from} : \text{to} : \text{type} : \text{JSON}(\text{payload}))[:32]$$

- If an incoming message presents an `idempotency_key` already registered in the active router:
  - It is immediately rejected with `DuplicateMessageError`.
- In the database persistence layer:
  - An `idempotency_key TEXT UNIQUE` constraint on the `agent_messages` table prevents duplicate rows (`ON CONFLICT DO NOTHING`).

---

## 3. Communication Topologies & Anti-Patterns

### Enforced Rules
1. **Hub-and-Spoke Mediation:** The `Supervisor` is the only entity authorized to dispatch tasks.
2. **Prohibition of Direct Agent Mesh:** If an agent attempts to dispatch directly to another agent (e.g., `sensor_reliability_agent` -> `crop_risk_analyst_agent`), the `MessageRouter.validate_message()` method raises `InvalidMessageError`.
3. **Structured Handoff Traceability:** Every specialist response must supply a `parent_message_id` referencing the task request that triggered it, maintaining a complete causal DAG.

