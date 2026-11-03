# Fresh Windows Laptop Setup Guide for AgriKafka-Agent
**Project:** AgriKafka-Agent (Stream Processing & Analytics)  
**Target Audience:** Teammates or Evaluators setting up the platform on a fresh Windows 10/11 machine.  
**Estimated Setup Time:** 20–30 minutes  

---

## 1. Architectural Summary & Component Boundaries

AgriKafka-Agent is built with a container-first design. **You do NOT need to install Java, Scala, Kafka, Zookeeper, Spark, PostgreSQL, TimescaleDB, Prometheus, or Grafana on your Windows host.** All heavy infrastructure runs inside pre-configured Docker containers.

### Component Distribution Matrix

| Layer / Service | Running Location | Host Port | Requires Local Install? |
| :--- | :--- | :--- | :--- |
| **Apache Kafka 3.8.0 (KRaft mode)** | Docker Container (`agrikafka-broker-dev`) | `127.0.0.1:9092` | ❌ No (Provided by Docker) |
| **PySpark 3.5.3 Streaming Engine** | Docker Container (`agrikafka-stream-processor`) | Internal network | ❌ No (Provided by Docker) |
| **TimescaleDB (PostgreSQL 16)** | Docker Container (`agrikafka-timescaledb`) | `127.0.0.1:5432` | ❌ No (Provided by Docker) |
| **Prometheus v2.54.1** | Docker Container (`agrikafka-prometheus`) | `127.0.0.1:9090` | ❌ No (Provided by Docker) |
| **Grafana v11.2.0** | Docker Container (`agrikafka-grafana`) | `127.0.0.1:3001` | ❌ No (Provided by Docker) |
| **Python Ingestion & CLI Adapters** | Windows Host / WSL2 Virtualenv | N/A | ✅ Yes (Python 3.11+ or `uv`) |
| **Source Code & Git Management** | Windows Host / VS Code | N/A | ✅ Yes (Git, VS Code) |
| **WSL 2 (Ubuntu Backend)** | Windows Virtualization Layer | N/A | ✅ Yes (Powers Docker Desktop) |

---

## 2. Prerequisites & Software Installation (Windows Host)

Run these steps in an elevated **PowerShell** terminal (Right click PowerShell -> *Run as Administrator*).

### Step 2.1: Enable WSL 2 & Install Ubuntu
```powershell
# Enable WSL and install Ubuntu default distribution
wsl --install

# Verify status after reboot (if prompted)
wsl --status
```

### Step 2.2: Install Core Tools via Winget
```powershell
# Install Git for Windows
winget install --id Git.Git -e --source winget

# Install Visual Studio Code
winget install --id Microsoft.VisualStudioCode -e --source winget

# Install Docker Desktop
winget install --id Docker.DockerDesktop -e --source winget

# Install modern Python (Python 3.11 or 3.12)
winget install --id Python.Python.3.11 -e --source winget

# Install uv (extremely fast Python package manager)
winget install --id astral-sh.uv -e --source winget
```

### Step 2.3: Configure Docker Desktop for WSL 2
1. Launch **Docker Desktop** from the Start Menu.
2. Complete the initial setup wizard (Accept Docker Subscription Service Agreement).
3. Open **Settings** (gear icon in the top toolbar):
   - **General:** Check `Use the WSL 2 based engine`.
   - **Resources -> WSL Integration:** Turn ON `Enable integration with my default WSL distro` and enable the toggle for `Ubuntu`.
4. Click **Apply & restart**.
5. Verify Docker in PowerShell:
   ```powershell
   docker --version
   docker compose version
   ```

### Step 2.4: Prevent WSL 2 Memory Exhaustion (Recommended)
By default, WSL 2 can consume up to 50% of host RAM. Create a `.wslconfig` file in your Windows user profile folder (`C:\Users\<YourUsername>\.wslconfig`):

```ini
[wsl2]
memory=4GB
processors=4
swap=2GB
```
Then restart WSL in PowerShell:
```powershell
wsl --shutdown
```

---

## 3. Recommended VS Code Extensions

Open VS Code and install the following official extensions (or paste these IDs into the Extensions Search Bar `Ctrl+Shift+X`):

1. **Python**: `ms-python.python` (Language support, debugging, formatting)
2. **Pylance**: `ms-python.vscode-pylance` (Type checking and autocomplete)
3. **Docker**: `ms-azuretools.vscode-docker` (Container management, logs, inspection)
4. **WSL**: `ms-vscode-remote.remote-wsl` (Seamless terminal and development in WSL2)
5. **Even Better TOML**: `tamasfe.even-better-toml` (Syntax highlighting for `pyproject.toml`)
6. **SQLTools + PostgreSQL Driver**: `mtxr.sqltools` and `mtxr.sqltools-driver-pg` (Interactive database browsing for TimescaleDB)

---

## 4. Obtaining the Repository & Workspace Setup

### Step 4.1: Clone the Repository
Open PowerShell or Git Bash:
```powershell
cd C:\Users\<YourUsername>\Projects
git clone https://github.com/<your-repo>/agri_streaming_project.git
cd agri_streaming_project
```

### Step 4.2: Open in VS Code
```powershell
code .
```

---

## 5. Python Environment Configuration

We use `uv` (recommended) or standard `venv` with Python 3.11+.

### Option A: Fast Setup with `uv` (Recommended)
```powershell
# Create dedicated virtual environment pinned to Python 3.11
uv venv --python 3.11 .venv

# Activate environment
.\.venv\Scripts\Activate.ps1

# Install all workspace packages in editable mode
uv pip install -e packages/event-contracts
uv pip install -e packages/database-client
uv pip install -e packages/shared-python
uv pip install -e services/ingestion
uv pip install -e services/risk-engine
uv pip install confluent-kafka pydantic psycopg[binary] pytest prometheus-client
```

### Option B: Standard Python `venv`
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e packages/event-contracts
pip install -e packages/database-client
pip install -e packages/shared-python
pip install -e services/ingestion
pip install -e services/risk-engine
pip install confluent-kafka pydantic psycopg[binary] pytest prometheus-client
```

---

## 6. Environment Files & Secrets Configuration

The repository uses environment variables loaded from a `.env` file at the root.

### Step 6.1: Copy Template
```powershell
# In root directory:
Copy-Item .env.example .env
```

### Step 6.2: Review Local Settings in `.env`
Open `.env` in VS Code. The default values are pre-configured for local development:
```dotenv
# Infrastructure Ports & Hosts
KAFKA_BOOTSTRAP_SERVERS=127.0.0.1:9092
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_DB=agrikafka
POSTGRES_USER=agri_admin
POSTGRES_PASSWORD=agri_dev_password_insecure
AGRI_READONLY_USER=agri_readonly
AGRI_READONLY_PASSWORD=agri_readonly_password_insecure
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=agri_admin_dev_insecure

# Physical Live Station (Sarvamangalam, Kolar, Karnataka)
OPENSENSEMAP_API_BASE=https://api.opensensemap.org
OPENSENSEMAP_BOX_ID=689b2bdc569c2d0007586ae9

# LLM Providers (Required only for Stage 15+ Agentic RAG)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.0-flash
```

> [!IMPORTANT]
> Never commit `.env` to Git. The `.gitignore` file already ignores `.env`.

---

## 7. Starting the Entire Platform

Follow this strictly sequential startup sequence:

### Step 7.1: Start Infrastructure Containers
In your root terminal:
```powershell
docker-compose up -d
```
*Wait 15–20 seconds for the Kafka KRaft broker and TimescaleDB containers to complete startup.*

### Step 7.2: Verify Container Health
```powershell
docker-compose ps
```
You should see 5 running containers:
- `agrikafka-broker-dev`: `Up (healthy)` on `127.0.0.1:9092`
- `agrikafka-timescaledb`: `Up (healthy)` on `127.0.0.1:5432`
- `agrikafka-prometheus`: `Up` on `127.0.0.1:9090`
- `agrikafka-grafana`: `Up` on `127.0.0.1:3001`
- `agrikafka-stream-processor`: `Up` (executing PySpark streaming)

### Step 7.3: Provision Kafka Topics (Idempotent)
Run the automated topic creation script:
```powershell
python infra/kafka/init_topics.py --bootstrap-server 127.0.0.1:9092
```
*Expected Output:* Confirms creation of all 9 canonical topics (`agri.sensor-readings`, `agri.validated-observations`, `agri.dead-letter-queue`, etc.).

---

## 8. Verifying Application Health & Endpoints

Open your browser to test each web service:

| Service | Local URL | Default Login | Verification Check |
| :--- | :--- | :--- | :--- |
| **Grafana Operations** | [http://127.0.0.1:3001](http://127.0.0.1:3001) | `admin` / `agri_admin_dev_insecure` | Folder `AgriKafka-Operations` contains 7 dashboards |
| **Prometheus Engine** | [http://127.0.0.1:9090](http://127.0.0.1:9090) | No auth | Target status at `http://127.0.0.1:9090/targets` |
| **Kafka Broker** | `127.0.0.1:9092` | TCP socket | `docker exec agrikafka-broker-dev /opt/kafka/bin/kafka-topics.sh --bootstrap-server 127.0.0.1:9092 --list` |
| **TimescaleDB** | `127.0.0.1:5432` | `agri_admin` / `agri_dev_password_insecure` | `docker exec agrikafka-timescaledb psql -U agri_admin -d agrikafka -c "SELECT count(*) FROM observations;"` |

### Step 8.4: Run Automated Regression Tests
Verify that all unit and contract tests pass locally:
```powershell
pytest tests/unit tests/contract
```
*Expected Result:* **All tests pass with 0 failures.**

---

## 9. Running Telemetry Streams (Demo Execution)

### Scenario A: Ingest Live Physical Data from Kolar
Poll the live OpenSenseMap hardware station `Sarvamangalam`:
```powershell
python services/ingestion/src/agri_ingestion/cli.py live-osm --station-id 689b2bdc569c2d0007586ae9 --once
```

### Scenario B: High-Speed Historical Replay
Replay historical weather telemetry at 50x speed:
```powershell
python services/ingestion/src/agri_ingestion/cli.py replay --speed 50
```

### Scenario C: Demonstrate Dead-Letter Queue (DLQ)
Inject a malformed packet to prove stream resilience:
```powershell
python scripts/demo/inject_fault.py --scenario corrupt_payload
```

---

## 10. Clean Teardown & Restart Procedures

### To Pause / Stop All Services (Data Preserved in Named Volumes):
```powershell
docker-compose down
```

### To Restart Services:
```powershell
docker-compose up -d
```

### To Completely Wipe and Reset All Databases/State:
```powershell
docker-compose down -v
```
*(Warning: Destroys persistent volumes. Re-run `init_topics.py` after starting up).*

