# Backend API Service

**Module:** `services/api`  
**Purpose:** Asynchronous REST API serving the Farmer PWA and Grafana dashboard.  
**Scheduled Stage:** Stage 17  

## Responsibilities
- Field registration and management.
- Alert querying and status tracking.
- Farmer feedback endpoint (recording approvals/rejections to Kafka topic `feedback`).
- Health and readiness endpoints.
