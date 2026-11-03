# Infrastructure — Docker & Compose

**Module:** `infra/docker`  
**Purpose:** Docker Compose topologies and Dockerfiles.  
**Scheduled Stage:** Stage 8  

## Topologies
- `docker-compose.dev.yml`: Single-broker KRaft Kafka + TimescaleDB for low-overhead local development (~2 GB RAM footprint).
- `docker-compose.yml`: 3-broker KRaft Kafka cluster + PySpark streaming worker + TimescaleDB + Prometheus + Grafana (~5 GB RAM footprint) for fault-tolerance drills and evaluation demo.
