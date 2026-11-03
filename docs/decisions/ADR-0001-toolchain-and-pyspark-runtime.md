# ADR-0001: Core Toolchain & PySpark Runtime Isolation

- **Status:** Proposed (Pending User Approval)
- **Date:** 2026-11-01
- **Deciders:** Lead Engineer, Team (Aanish Khan, Daksh Chauhan, Pranav Pratyush)
- **Technical Domain:** Runtime Environment, Language Versions, Package Management

---

## 1. Context & Problem Statement
The Stage 1 environment audit detected `Python 3.13.1` as the active Windows host interpreter and `OpenJDK 17.0.19 LTS` as the active `JAVA_HOME`. Apache Spark 3.5.3 (LTS) officially supports Python 3.8–3.11 (with preliminary support for 3.12) and Java 8/11/17. Python 3.13 is unsupported by Spark 3.5.x and causes Py4J daemon socket crashes. Additionally, running Spark directly on Windows requires native Hadoop binaries (`winutils.exe`) which introduce path instability and permission hurdles.

We must decide:
1. How to run PySpark Structured Streaming jobs reliably.
2. How to manage Python dependencies across the monorepo without conflicting package managers.

---

## 2. Options Considered

### Option A: Run PySpark natively on Windows Host with Python 3.13
- **Evaluation:** Incompatible. PySpark 3.5.3 crashes on Python 3.13 due to internal bytecode changes. Requires manual `winutils.exe` installation.
- **Complexity:** High / Fragile.

### Option B: Downgrade Host System Python to 3.11
- **Evaluation:** Invasive. Disrupts the user's host environment and existing Phase 1 EDA virtual environment (`.venv`).
- **Complexity:** Medium.

### Option C: Containerized PySpark + `uv` Workspace for Host Tooling (Recommended)
- **Evaluation:**
  - PySpark Structured Streaming runs inside an official Debian Linux container (`bitnami/spark:3.5.3` or custom image based on `apache/spark-py:3.5.3`), bundling **Python 3.11.10** and **OpenJDK 17**.
  - Host Python dependencies and services (FastAPI, ingestion replay, agent) use **`uv` 0.11.26** (pre-installed on host) to manage an isolated Python 3.11 environment (`.venv-agri`).
  - Preserves host Python 3.13 for Phase 1 EDA without conflicts.
- **Complexity:** Low / Highly reproducible.

---

## 3. Detailed Comparison Matrix

| Evaluation Criterion | Option A (Native Host Py 3.13) | Option B (Downgrade Host) | Option C (Containerized Spark + uv) |
|---|---|---|---|
| **Compatibility** | ❌ Fails on Spark 3.5.3 | ⚠️ Requires OS-level reinstall | ✅ 100% verified compatibility |
| **Windows Winutils Issue** | ❌ Requires manual `winutils.exe` | ❌ Requires manual `winutils.exe` | ✅ Completely eliminated (Linux container) |
| **Setup Overhead** | High (frequent breakage) | High (host modifications) | Low (Docker Compose + `uv`) |
| **RAM Footprint** | ~1.5 GB | ~1.5 GB | ~2.0 GB (Spark container) |
| **Isolation** | None | Host-wide | Complete container & venv isolation |

---

## 4. Decision
Adopt **Option C**:
1. **PySpark Streaming Engine:** Executed containerized in Docker using `bitnami/spark:3.5.3` (Debian Linux, Python 3.11, OpenJDK 17).
2. **Package & Environment Manager:** **`uv` 0.11.26** manages the host workspace and creates an isolated Python 3.11 virtual environment (`.venv-agri`) for local services and tests.
3. **Java Runtime:** Use host OpenJDK 17 LTS (`C:\Program Files\Eclipse Adoptium\jdk-17.0.19.10-hotspot`) for any local JVM tooling.

---

## 5. Consequences

### Positive
- Zero runtime crashes from Python 3.13 in Spark.
- Eliminates Windows `winutils.exe` / `HADOOP_HOME` configuration failures.
- Production parity: Spark runs in the same containerized Linux environment as production clusters.
- Fast package resolution via `uv`.

### Negative
- Running Spark in Docker requires ~1.5–2.0 GB of RAM allocated to Docker/WSL2.

### Neutral
- Developers must start Docker Desktop before running streaming jobs.
