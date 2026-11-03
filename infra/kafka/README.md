# Infrastructure — Apache Kafka Configuration & Tooling

**Module:** `infra/kafka`  
**Purpose:** Declarative topic provisioning, client smoke tests, volume persistence verification, and local lifecycle management.  
**Architecture Specification:** [docs/architecture/KAFKA_TOPOLOGY.md](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/docs/architecture/KAFKA_TOPOLOGY.md)  
**Governing ADR:** [ADR-0002](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/docs/decisions/ADR-0002-kafka-broker-and-client.md)  

---

## 1. Directory Structure

- `init_topics.py`: Declaratively creates and tunes all canonical AgriKafka topics with explicit partitions, retention periods, and cleanup policies.
- `smoke_test.py`: End-to-end producer/consumer test asserting message delivery and schema validation using `confluent-kafka` and Pydantic v2 contracts.
- `verify_persistence.py`: Verifies message durability across a container restart (`docker compose restart kafka`).
- `manage.ps1`: Windows PowerShell lifecycle script for starting, inspecting, testing, and stopping Kafka without data loss.
- `manage.sh`: POSIX/Bash lifecycle script for Linux/WSL environments.

---

## 2. Quickstart Lifecycle Commands

### Windows (PowerShell)
```powershell
# 1. Start the single-broker KRaft container
.\infra\kafka\manage.ps1 start

# 2. Declaratively provision all 9 core topics
.\infra\kafka\manage.ps1 topics-init

# 3. Inspect topic partitions and leader assignments
.\infra\kafka\manage.ps1 topics-list

# 4. Run end-to-end smoke test
.\infra\kafka\manage.ps1 smoke-test

# 5. Run persistence verification across restart
.\infra\kafka\manage.ps1 persist-test

# 6. Stop Kafka safely without deleting the persistent volume
.\infra\kafka\manage.ps1 stop
```

### Linux / WSL (Bash)
```bash
./infra/kafka/manage.sh start
./infra/kafka/manage.sh topics-init
./infra/kafka/manage.sh topics-list
./infra/kafka/manage.sh smoke-test
./infra/kafka/manage.sh persist-test
./infra/kafka/manage.sh stop
```

---

## 3. Persistent Data Safety Invariant
The named Docker volume `agrikafka_dev_data` stores all Kafka log segments at `/var/lib/kafka/data`.
- Running `docker compose stop` or `docker compose down` will **never** delete the volume.
- Never use `docker compose down -v` or prune volumes without explicit manual sign-off.
