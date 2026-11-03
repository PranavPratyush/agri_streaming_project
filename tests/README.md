# Test Suite Hierarchy

**Directory:** `tests`  
**Framework:** `pytest`  

## Structure
- `tests/unit/`: Isolated unit tests for deterministic math, sensor health calculations, and utility functions.
- `tests/contract/`: Pydantic schema validation and event serialization/deserialization compliance.
- `tests/integration/`: Service-to-Kafka, service-to-database, and API endpoint integration tests.
- `tests/scenarios/`: End-to-end evaluation harness running the ~60 labeled fault/stress scenarios against detectors and agents.
- `tests/resilience/`: Automated chaos testing (broker failure, worker termination, network partition, LLM timeout fallback).
