# Environment Variable Reference Guide
**Project:** AgriKafka-Agent  
**File Location:** `.env` (derived from `.env.example`)  
**Security Classification:** Development Configuration (No Plaintext Production Secrets)  

---

## 1. Overview & File Precedence

AgriKafka-Agent follows the Twelve-Factor App methodology for configuration. Configuration values are resolved in the following priority order:

1. **System Environment Variables** (highest precedence)
2. **Local `.env` File** (loaded by Python services and Docker Compose)
3. **Application In-Code Defaults** (defined in Pydantic settings and Docker Compose defaults)

> [!CAUTION]
> The `.env` file contains local database passwords and API tokens. It is explicitly listed in `.gitignore` and must **never** be committed to version control.

---

## 2. Complete Environment Variable Inventory

### 2.1 Project Profile & Environment

| Variable Name | Default Value | Target Service | Sensitive? | Purpose & Constraints |
| :--- | :--- | :--- | :--- | :--- |
| `AGRI_ENV` | `development` | All services | No | Runtime profile (`development`, `test`, `production`). |
| `AGRI_LOG_LEVEL` | `INFO` | All services | No | Root logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |

---

### 2.2 Apache Kafka KRaft Infrastructure

| Variable Name | Default Value | Target Service | Sensitive? | Purpose & Constraints |
| :--- | :--- | :--- | :--- | :--- |
| `KAFKA_BOOTSTRAP_SERVERS` | `127.0.0.1:9092` | Ingestion, PySpark, DB Consumer | No | Host address of Kafka broker. Must bind to `127.0.0.1` locally. |
| `KAFKA_CLIENT_ID` | `agri-client-local` | Producers / Consumers | No | Client identifier sent in Kafka protocol request headers. |
| `KAFKA_CONSUMER_GROUP_PREFIX` | `agri-group` | PySpark, Persistence | No | Namespace prefix used to prevent consumer group ID collisions. |

---

### 2.3 TimescaleDB & PostgreSQL 16 Persistence

| Variable Name | Default Value | Target Service | Sensitive? | Purpose & Constraints |
| :--- | :--- | :--- | :--- | :--- |
| `POSTGRES_HOST` | `127.0.0.1` | DB Consumer, Alembic | No | Host binding for database server (`timescaledb` inside Docker network). |
| `POSTGRES_PORT` | `5432` | DB Consumer, Alembic | No | Standard PostgreSQL port. |
| `POSTGRES_DB` | `agrikafka` | Docker, Alembic, Grafana | No | Database catalog name. |
| `POSTGRES_USER` | `agri_admin` | Docker, Alembic | No | Superuser / DDL administrator account. |
| `POSTGRES_PASSWORD` | `agri_dev_password_insecure` | Docker, Alembic | **YES** | Local development password for `agri_admin`. Replace with secure secret in staging/prod. |
| `AGRI_READONLY_USER` | `agri_readonly` | Grafana Datasource | No | Least-privilege user account for dashboard reporting. |
| `AGRI_READONLY_PASSWORD` | `agri_readonly_password_insecure` | Grafana Datasource | **YES** | Password for `agri_readonly` role. |

---

### 2.4 Monitoring & Observability (Grafana & Prometheus)

| Variable Name | Default Value | Target Service | Sensitive? | Purpose & Constraints |
| :--- | :--- | :--- | :--- | :--- |
| `GRAFANA_ADMIN_USER` | `admin` | Grafana Container | No | Initial administrator username for Grafana. |
| `GRAFANA_ADMIN_PASSWORD` | `agri_admin_dev_insecure` | Grafana Container | **YES** | Initial administrator password for Grafana UI. |
| `PROMETHEUS_PORT` | `9090` | Docker, Prometheus | No | Port exposed on host for Prometheus UI. |
| `GRAFANA_PORT` | `3001` | Docker, Grafana | No | Host port mapped to Grafana container (avoids port 3000 conflicts). |

---

### 2.5 Live Telemetry Data Sources

| Variable Name | Default Value | Target Service | Sensitive? | Purpose & Constraints |
| :--- | :--- | :--- | :--- | :--- |
| `OPENSENSEMAP_API_BASE` | `https://api.opensensemap.org` | Ingestion Service | No | Base REST endpoint for physical OpenSenseMap API. |
| `OPENSENSEMAP_BOX_ID` | `689b2bdc569c2d0007586ae9` | Ingestion Service | No | Station ID for *Sarvamangalam* in Kolar district, Karnataka. |
| `IMD_API_KEY` | *(None / Optional)* | Ingestion Service | **YES** | India Meteorological Department token (if commercial feed enabled). |

---

### 2.6 Agentic RAG & LLM Providers (Stage 15+ Scope)

| Variable Name | Default Value | Target Service | Sensitive? | Purpose & Constraints |
| :--- | :--- | :--- | :--- | :--- |
| `GEMINI_API_KEY` | `your_gemini_api_key_here` | Alert Investigator | **YES** | Google AI Studio API key used for bounded alert investigation. |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Alert Investigator | No | Specific model variant (default: `gemini-2.0-flash`). |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Alert Investigator | No | Local Ollama endpoint if running offline LLM. |
| `OLLAMA_MODEL` | `llama3.2:latest` | Alert Investigator | No | Local model name for Ollama fallback. |

---

## 3. Manual Pre-Sharing Checklist for Repository Maintainer

Before zipping, sharing, or pushing the repository to your teammate:

1. **Verify `.env` is NOT Staged:**
   ```powershell
   git status --ignored
   ```
   Ensure `.env` appears under *Ignored files*, not *Changes to be committed*.

2. **Clean Ephemeral Run Artifacts:**
   Ensure temporary database caches and spark state are not shared:
   ```powershell
   # Clean python cache
   Get-ChildItem -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force
   Get-ChildItem -Recurse -Filter "*.pyc" | Remove-Item -Force
   ```

3. **Verify `.env.example` is Complete:**
   Ensure `.env.example` contains all keys listed above with safe placeholder values.

4. **Provide Gemini API Key Out-of-Band (if demonstrating Stage 15):**
   Send any necessary API keys via a secure messaging channel or password manager, never in the repository code or README files.

