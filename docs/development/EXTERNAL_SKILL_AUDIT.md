# AgriKafka-Agent — External Agent Skills Audit

**Document:** `docs/development/EXTERNAL_SKILL_AUDIT.md`  
**Stage:** Stage 3 — External Skills Audit and Verification  
**Audit Date:** 2026-11-01T19:47:00+05:30  
**Audit Status:** Complete — Pending User Selection Approval  
**Audit Policy:** Strict verification against live GitHub repository default branches and trees. Zero skills installed prior to explicit user sign-off.

---

## 1. Upstream Repositories Audited

All four candidate repositories were inspected via GitHub API endpoints for default branches, latest commit hashes, licensing, and structural directory layouts:

| # | Repository URL | Default Branch | Latest Commit SHA | Commit Date | License | Total Skills |
|---|---|---|---|---|---|---|
| 1 | https://github.com/addyosmani/agent-skills | `main` | `8bfcc1f991f24d40e11807662c118e597c4e5186` | 2026-03-31 | MIT | 25 |
| 2 | https://github.com/vaquarkhan/data-engineering-agent-skills | `main` | `421ef57e8d6f51cb7e72a08a2ff5077dc4442efc` | 2026-03-29 | MIT | 74 |
| 3 | https://github.com/lensesio/agentic-engineering-for-apache-kafka | `main` | `8cee08b168ff0dcbc8eafe2f6d6283b9cfab17b9` | 2026-03-24 | MIT | 10 |
| 4 | https://github.com/sickn33/agentic-awesome-skills | `main` | `66f1301eb45c2250ea543a010471b6d2e82522ae` | 2026-03-31 | MIT | 8,890 |

---

## 2. Granular Candidate Skill Audit

Every candidate skill was checked for:
- Exact directory path and presence of `SKILL.md`.
- Valid YAML frontmatter (`name`, `description`).
- Supplementary files (references, anti-patterns, checks, templates).
- Absence of malicious shell scripts, unverified curl downloads, or out-of-workspace writes.
- Compatibility with Google Antigravity IDE open Agent Skills specification.

### A. Software Engineering — `addyosmani/agent-skills`

| Exact Folder | Verified Skill Name | Purpose & Workflow Fit | Supplementary Files | Risk | Compatibility | Recommendation |
|---|---|---|---|---|---|---|
| `skills/spec-driven-development` | `spec-driven-development` | Drafts structured specifications, capability maps, and requirements before any code is written. Essential for stage-by-stage engineering. | Single `SKILL.md` (12.9 KB) | Safe (no shell/exec) | Full Antigravity format | **RECOMMEND (Initial Pack)** |
| `skills/planning-and-task-breakdown` | `planning-and-task-breakdown` | Decomposes specifications into ordered, implementable, testable tasks. Prevents scope drift. | Single `SKILL.md` (10.4 KB) | Safe (no shell/exec) | Full Antigravity format | **RECOMMEND (Initial Pack)** |
| `skills/incremental-implementation` | `incremental-implementation` | Enforces delivering changes in thin, verifiable slices; protects existing code from sweeping overwrites. | Single `SKILL.md` (9.3 KB) | Safe (no shell/exec) | Full Antigravity format | **RECOMMEND (Initial Pack)** |
| `skills/test-driven-development` | `test-driven-development` | Drives development using Red-Green-Refactor testing cycle; mandates test evidence before marking work complete. | Single `SKILL.md` (16.6 KB) | Safe (no shell/exec) | Full Antigravity format | **RECOMMEND (Initial Pack)** |
| `skills/code-review-and-quality` | `code-review-and-quality` | Multi-axis code review covering correctness, performance, edge cases, and maintainability. | Single `SKILL.md` (20.8 KB) | Safe (no shell/exec) | Full Antigravity format | **DEFER** (Useful during Phase IV evaluation) |

### B. Data Engineering — `vaquarkhan/data-engineering-agent-skills`

| Exact Folder | Verified Skill Name | Purpose & Workflow Fit | Supplementary Files | Risk | Compatibility | Recommendation |
|---|---|---|---|---|---|---|
| `skills/data-specification` | `data-specification` | Creates structured specifications for data contracts, ingestion flows, and pipelines. | Single `SKILL.md` (2.5 KB) | Safe | Full Antigravity format | **DEFER** (Overlaps with `spec-driven-development`) |
| `skills/data-quality-and-contract-testing` | `data-quality-and-contract-testing` | Enforces contracts, assertions, null-rate checks, and validation gates at producer/consumer boundaries. | `SKILL.md` + 4 Python checks/anti-patterns (contract completeness, freshness, null rate) | Safe (code templates only) | Full Antigravity format | **RECOMMEND (Initial Pack)** |
| `skills/safe-backfill-and-replay-orchestration` | `safe-backfill-and-replay-orchestration` | Governs accelerated historical replay, watermark synchronization, reconciliation gates, and prevents duplicate-action state corruption. | Single `SKILL.md` (4.9 KB) | Safe | Full Antigravity format | **RECOMMEND (Initial Pack)** |
| `skills/kafka-resilience-and-schema-evolution` | `kafka-resilience-and-schema-evolution` | Enforces non-breaking schema evolution, dead-letter queue routing, and `acks=all` producer durability. | Single `SKILL.md` (4.8 KB) | Safe | Full Antigravity format | **DEFER** (Covered by Lenses Kafka skills & custom skill) |
| `skills/data-resiliency-testing-and-failure-injection` | `data-resiliency-testing-and-failure-injection` | Guides failure drills, recovery validation, failover tests, and fault injection for streaming pipelines. | Single `SKILL.md` (4.6 KB) | Safe | Full Antigravity format | **DEFER** (Deploy in Stage 20 chaos drills) |
| `skills/spark-and-distributed-processing` | `spark-and-distributed-processing` | Guides PySpark stream processing design, state stores, watermarking, and partition skew avoidance. | `SKILL.md` + checks/anti-patterns (collect on driver, partition skew) | Safe | Full Antigravity format | **DEFER** (Deploy in Stage 10 Spark implementation) |
| `skills/data-contract-testing-with-schema-registry` | `data-contract-testing-with-schema-registry` | Schema registry compatibility and contract testing for Avro/Protobuf/JSON Schema. | Single `SKILL.md` (5.5 KB) | Safe | Full Antigravity format | **DEFER** (Conditional on Confluent Schema Registry adoption) |

### C. Kafka Engineering — `lensesio/agentic-engineering-for-apache-kafka`

| Exact Folder | Verified Skill Name | Purpose & Workflow Fit | Supplementary Files | Risk | Compatibility | Recommendation |
|---|---|---|---|---|---|---|
| `skills/kafka-python-client` | `kafka-python-client` | Scaffolds production-grade `confluent-kafka` producers and consumers with graceful shutdown, partition keys, idempotent settings, and tests. | `SKILL.md` + 8 template references (producer, consumer, tests, common mistakes) + evals | Safe (falls back to codebase inspection when no MCP attached) | Full Antigravity format | **RECOMMEND (Initial Pack)** |
| `skills/kafka-topic-audit` | `kafka-topic-audit` | Audits topic configurations, partitions, retention, replication factor, and cleanup policies against best practices. | `SKILL.md` + `audit-rules.md` | Safe (read-only audit) | Full Antigravity format | **RECOMMEND (Initial Pack)** |
| `skills/kafka-consumer-lag` | `kafka-consumer-lag` | Diagnoses consumer lag, partition skew, stalled consumers, and throughput bottlenecks. | `SKILL.md` + test cases | Safe (diagnostic only) | Full Antigravity format | **DEFER** (Deploy in Stage 14 with Prometheus/Grafana) |
| `skills/kafka-dlq-review` | `kafka-dlq-review` | Audits dead-letter queue implementation, metadata preservation, retry backoff, and poison message routing. | `SKILL.md` + references | Safe (review only) | Full Antigravity format | **DEFER** (Deploy in Stage 13 DLQ implementation) |

### D. Agentic AI & RAG — `sickn33/agentic-awesome-skills`

| Exact Folder | Verified Skill Name | Purpose & Workflow Fit | Supplementary Files | Risk | Compatibility | Recommendation |
|---|---|---|---|---|---|---|
| `skills/ai-agents-architect` | `ai-agents-architect` | Bounded agent architecture, tool definitions, structured outputs, deterministic guardrails, state graphs, and uncertainty handling. | Single `SKILL.md` (10.3 KB) | Safe (architectural instructions) | Full Antigravity format | **RECOMMEND (Initial Pack)** |
| `skills/rag-engineer` | `rag-engineer` | RAG pipeline design: document chunking, embeddings, Chroma vector store indexing, retrieval evaluation, and citation validation. | Single `SKILL.md` (10.8 KB) | Safe (tag `risk: critical` refers to domain hallucination risk, not file safety) | Full Antigravity format | **RECOMMEND (Initial Pack)** |

---

## 3. Recommended Initial Pack (9 Focused Skills)

To prevent cognitive overload while ensuring complete coverage of the upcoming Stage 4–Stage 16 development phases, the following **9 skills** are formally recommended for installation into `.agents/skills/<exact-folder>/`:

```text
1. spec-driven-development          (addyosmani/agent-skills)
2. planning-and-task-breakdown       (addyosmani/agent-skills)
3. incremental-implementation        (addyosmani/agent-skills)
4. test-driven-development           (addyosmani/agent-skills)
5. kafka-python-client               (lensesio/agentic-engineering-for-apache-kafka)
6. kafka-topic-audit                 (lensesio/agentic-engineering-for-apache-kafka)
7. data-quality-and-contract-testing (vaquarkhan/data-engineering-agent-skills)
8. safe-backfill-and-replay-orchestration (vaquarkhan/data-engineering-agent-skills)
9. ai-agents-architect               (sickn33/agentic-awesome-skills)
10. rag-engineer                     (sickn33/agentic-awesome-skills)
```

### Coverage by Required Domain
1. **Specification & Planning:** `spec-driven-development`, `planning-and-task-breakdown`.
2. **Incremental Implementation & Testing:** `incremental-implementation`, `test-driven-development`.
3. **Kafka Python & Topic Operations:** `kafka-python-client`, `kafka-topic-audit`.
4. **Data Contracts & Quality:** `data-quality-and-contract-testing`.
5. **Replay & Resilience:** `safe-backfill-and-replay-orchestration`.
6. **Bounded Agent & RAG Design:** `ai-agents-architect`, `rag-engineer`.

---

## 4. Deferred Skills Register

The following candidate skills were audited and verified, but are deferred to later stages when their specific subsystems are being implemented:

| Deferred Skill | Reason for Deferral | Scheduled Stage |
|---|---|---|
| `code-review-and-quality` | Code review automation is best activated during Phase IV final validation. | Stage 22 |
| `spark-and-distributed-processing` | Specialized Spark anti-patterns; best introduced when PySpark streaming is implemented. | Stage 10 |
| `kafka-consumer-lag` | Requires active consumer groups and Prometheus/Lenses metrics to be meaningful. | Stage 14 |
| `kafka-dlq-review` | Requires active dead-letter topic and error handler implementation. | Stage 13 |
| `data-resiliency-testing-and-failure-injection` | Focuses on chaos engineering drills; matches Phase IV resilience testing. | Stage 20 |
| `data-contract-testing-with-schema-registry` | Defer until decision OD-09 confirms whether external schema registry is required. | Stage 7 |
| `data-specification` | Overlaps substantially with `spec-driven-development`. | N/A (Excluded) |
| `kafka-resilience-and-schema-evolution` | Overlaps with `kafka-python-client` and custom `agri-event-contracts`. | N/A (Excluded) |

## 5. Installed Skills & Antigravity Invocation Guide

All 10 approved skills have been installed under `.agents/skills/<exact-folder>/` with their complete supplementary references, templates, checks, and anti-patterns preserved without flattening.

### Installed Inventory

| Skill Name | Local Path | Files | Key Reference Artifacts |
|---|---|---|---|
| `spec-driven-development` | `.agents/skills/spec-driven-development/` | 1 | `SKILL.md` (12.9 KB) |
| `planning-and-task-breakdown` | `.agents/skills/planning-and-task-breakdown/` | 1 | `SKILL.md` (10.4 KB) |
| `incremental-implementation` | `.agents/skills/incremental-implementation/` | 1 | `SKILL.md` (9.3 KB) |
| `test-driven-development` | `.agents/skills/test-driven-development/` | 1 | `SKILL.md` (16.6 KB) |
| `kafka-python-client` | `.agents/skills/kafka-python-client/` | 11 | `references/common-template.py`, `producer-template.py`, `consumer-template.py`, `tests-template.py`, `common-mistakes.md`, `evals/` |
| `kafka-topic-audit` | `.agents/skills/kafka-topic-audit/` | 3 | `references/audit-rules.md`, `test-cases.md` |
| `data-quality-and-contract-testing` | `.agents/skills/data-quality-and-contract-testing/` | 5 | `anti-patterns/no_quality_gate_before_publish.py`, `checks/contract_completeness.py`, `freshness.py`, `null_rate.py` |
| `safe-backfill-and-replay-orchestration` | `.agents/skills/safe-backfill-and-replay-orchestration/` | 1 | `SKILL.md` (4.9 KB) |
| `ai-agents-architect` | `.agents/skills/ai-agents-architect/` | 1 | `SKILL.md` (10.3 KB) |
| `rag-engineer` | `.agents/skills/rag-engineer/` | 1 | `SKILL.md` (10.8 KB) |

---

## 6. How to Invoke Skills in Google Antigravity

In Google Antigravity IDE, skills located under `.agents/skills/<skill-folder>/SKILL.md` are dynamically discovered through their YAML frontmatter:

1. **Implicit Triggering via Model Selection:** Antigravity matches the user's task prompt against the skill's `description` frontmatter. For example, asking *"scaffold a Kafka consumer in Python with idempotent settings"* automatically triggers `kafka-python-client`.
2. **Explicit Skill View / Execution:** When executing tasks related to a skill, the lead engineer views `SKILL.md` using `view_file` to load the exact instructions into context.
3. **Trigger Reference by Stage:**
   - **Stage 4 & 5 (Rules & Contracts):** Invoke `spec-driven-development` and `data-quality-and-contract-testing`.
   - **Stage 7 & 8 (Kafka Ingestion):** Invoke `kafka-python-client` and `kafka-topic-audit`.
   - **Stage 9 (Historical Replay):** Invoke `safe-backfill-and-replay-orchestration`.
   - **Stage 10 (Spark Streaming):** Invoke `test-driven-development` and `incremental-implementation`.
   - **Stage 15 & 16 (RAG & Agent):** Invoke `ai-agents-architect` and `rag-engineer`.

