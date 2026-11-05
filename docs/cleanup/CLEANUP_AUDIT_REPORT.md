# AgriKafka-Agent: Codebase Audit & Cleanup Plan

**Audit Date:** 2026-11-05T23:36:00+05:30  
**Repository:** `AgriKafka-Agent` (`agri_streaming_project`)  
**Scope:** Complete repository inspection, artifact classification, dependency analysis, and cleanup planning.

---

## 1. Executive Summary & Inventory

A comprehensive recursive audit of all files in the repository (excluding `.git/`, `.venv/`, and `apps/farmer-pwa/node_modules/`) was conducted.

| Category | Description | Count | Action |
|:---|:---|:---:|:---|
| **Category A — Essential** | Production source code, Kafka configs, PySpark streaming jobs, multi-agent investigator, RAG knowledge store, FastAPI backend, Farmer PWA, unit/integration/contract tests, Docker Compose, migrations, core documentation. | **452** | **Preserve Intact** |
| **Category B — Potentially Obsolete / Clutter** | Root duplicates, superseded initial proposals, unreferenced Stage 14 demo artifacts, legacy pip `requirements.txt`, unorganized root PDFs. | **12** | **Quarantine / Relocate / Delete with zero breaking risk** |
| **Category C — Safe Generated Artifacts** | Disposable CLI replay checkpoint files (`.replay_checkpoint_*.json`), Python bytecode caches (`__pycache__`), disposable frontend build outputs (`dist/`). | **67** | **Safe Removal (Reproducible/Disposable)** |
| **Category D — Uncertain / Historical Evidence** | Phase 1 EDA scripts, Jupyter notebooks, `eda_output/` figures, and `AgriKafka_EDA_Report/` artifacts supporting academic evaluations. | **54** | **Deliberately Retained** |
| **Total Inspected Files** | *(Excluding `.git/`, `.venv/`, `node_modules/`)* | **585** | — |

---

## 2. Classification & Disposition Table

### Category B: Potentially Obsolete / Clutter / Duplicate Files

| Original Path | Classification | Why Identified | Referenced Elsewhere? | Risk Assessment | Recommended Action |
|:---|:---|:---|:---|:---|:---|
| `AgriKafka-Agent_Development_Handover.md` (root) | Duplicate | Exact binary replica (SHA256: `0C2F27D8C89433F2346C8AAB4EFA7968B6C15ABC2AABED69DA2E490E31227726`) of canonical handover file. | `README.md` explicitly links to `docs/project/reference/AgriKafka-Agent_Development_Handover.md`. Root copy is not referenced. | None. Redundant duplicate. | **Remove root copy**; retain canonical copy in `docs/project/reference/`. |
| `AgriKafka-Agent Project Overview, Design and Plan.md` (root) | Superseded Planning | Early project concept from Oct 15, 2026. Superseded by `docs/project/PROJECT_BRIEF.md` and `docs/architecture/ARCHITECTURE_V1.md`. | No code or test imports. | Low. Contains historical framing. | **Quarantine / Move** to `docs/reference/historical_plans/PROJECT_INITIAL_CONCEPT_OCT2026.md`. |
| `AgriKafka-Agent_Antigravity_Development_Prompt_Playbook.md` (root) | Clutter (Root) | Comprehensive prompt playbook for Stages 0–22. Highly valuable development documentation that clutters project root. | Workflow reference. | Moderate if deleted; Zero if relocated. | **Relocate** to `docs/implementation/DEVELOPMENT_PROMPT_PLAYBOOK.md`. |
| `requirements.txt` (root) | Obsolete Config | Legacy pip requirements from early Phase 1. Superseded by `pyproject.toml` and `uv.lock`. Explicitly flagged by internal audit rules. | No build or Dockerfile uses it; internal test checks for absence. | Zero risk. | **Quarantine / Remove** to maintain clean uv-native packaging. |
| `SPA Lab-Dataset_Description_and_EDA [Edited].pdf` | Academic Document | SPA Lab Milestone 1 report PDF. Clutters root. | Course submission artifact. | Zero if organized into dedicated folder. | **Relocate** to `docs/reference/spa_lab_submissions/`. |
| `SPA Lab-Environment_Tools_and_Setup [Edited].pdf` | Academic Document | SPA Lab Milestone 2 report PDF. Clutters root. | Course submission artifact. | Zero if organized into dedicated folder. | **Relocate** to `docs/reference/spa_lab_submissions/`. |
| `SPA Lab-Literature Survey[Edited].pdf` | Academic Document | SPA Lab Milestone 3 report PDF. Clutters root. | Course submission artifact. | Zero if organized into dedicated folder. | **Relocate** to `docs/reference/spa_lab_submissions/`. |
| `SPA Lab-Synopsis[Edited].pdf` | Academic Document | SPA Lab Course Synopsis PDF. Clutters root. | Course submission artifact. | Zero if organized into dedicated folder. | **Relocate** to `docs/reference/spa_lab_submissions/`. |
| `docs/demo/STAGE_14_READINESS_REPORT.md` | Milestone Report | Stage 14 pre-multi-agent readiness report. Superseded by `STAGE_19_LIVE_DEMO_READINESS_REPORT.md`. | No active references. | Zero. | **Move to archive** `docs/demo/archive_stage_14/`. |
| `docs/demo/PROFESSOR_DEMO_RUNBOOK.md` | Milestone Runbook | Stage 14 single-agent demo runbook. Superseded by `PROFESSOR_LIVE_DEMO_RUNBOOK.md`. | No active references. | Zero. | **Move to archive** `docs/demo/archive_stage_14/`. |
| `docs/demo/PROFESSOR_DEMO_SPEAKING_SCRIPT.md` | Milestone Script | Stage 14 demo speaking script. Superseded by `PROFESSOR_LIVE_DEMO_SPEAKING_SCRIPT.md`. | No active references. | Zero. | **Move to archive** `docs/demo/archive_stage_14/`. |
| `docs/demo/TROUBLESHOOTING_AND_RECOVERY.md` | Milestone Guide | Stage 14 troubleshooting notes. Superseded by `DEMO_TROUBLESHOOTING_AND_RECOVERY.md`. | No active references. | Zero. | **Move to archive** `docs/demo/archive_stage_14/`. |

---

### Category C: Safe Generated Artifacts (Disposable)

| Artifact Pattern | Count | Source / Cause | Justification for Removal |
|:---|:---:|:---|:---|
| `.replay_checkpoint_*.json` | 26 | Ephemeral resume checkpoints generated by `services/ingestion/cli.py` during historical replay. | Ignored by `.gitignore:57`. Left behind by past local runs. Transient; regenerates automatically on new replay runs. |
| `*/__pycache__/*.pyc` (non-venv) | ~35 | Python bytecode compilation caches. | Fully reproducible by the Python runtime; non-essential. |
| `apps/farmer-pwa/dist/` | 6 | Disposable production build artifacts from `npm run build`. | Rebuilt instantly via `npm run build`; ignored by `.gitignore`. |

---

### Category D: Files Deliberately Retained Despite Appearing Unnecessary

| Path | Reason for Retention |
|:---|:---|
| `acquire_open_meteo.py` | Referenced directly in `README.md:144` as the canonical historical data acquisition command. |
| `eda_open_meteo.py` | Standalone script used to generate correlation matrices and summary statistics for Stage 1. |
| `phase1_acquisition_and_eda.ipynb` | Interactive exploratory notebook containing original data profiling and distributions. |
| `AgriKafka_EDA_Report/` | Contains report generation script (`generate_report.py`), figures, and PDF supporting academic review. |
| `eda_output/` (31 files) | Evidence files, correlation tables, and publication-ready charts supporting the academic report and paper. |
| `.agents/rules/` & `.agents/skills/` | Project development operating rules and architectural skills. |

---

## 3. Step-by-Step Cleanup Plan

1. **Typo Correction:** Remove inadvertent `\\` character on line 1 of `docs/demo/STAGE_19_LIVE_DEMO_READINESS_REPORT.md`.
2. **Remove Ephemeral Checkpoints:** Delete 26 root-level `.replay_checkpoint_*.json` files.
3. **Remove Python Bytecode Caches:** Clear repository `__pycache__` directories outside `.venv/`.
4. **Remove Root Duplicate:** Delete `AgriKafka-Agent_Development_Handover.md` at root (preserving `docs/project/reference/AgriKafka-Agent_Development_Handover.md`).
5. **Relocate Academic Submission PDFs:** Create `docs/reference/spa_lab_submissions/` and move the 4 SPA Lab PDFs into it.
6. **Relocate Development Playbook:** Move `AgriKafka-Agent_Antigravity_Development_Prompt_Playbook.md` to `docs/implementation/DEVELOPMENT_PROMPT_PLAYBOOK.md`.
7. **Quarantine Superseded Initial Concept:** Move `AgriKafka-Agent Project Overview, Design and Plan.md` to `docs/reference/historical_plans/PROJECT_INITIAL_CONCEPT_OCT2026.md`.
8. **Archive Stage 14 Demo Artifacts:** Create `docs/demo/archive_stage_14/` and move the 4 older Stage 14 demo files into it.
9. **Remove Obsolete `requirements.txt`:** Remove root `requirements.txt` so that the repository strictly conforms to uv-managed packaging.
10. **Execute Verification Suite:** Run Python syntax checks, full unit tests, contract tests, and frontend build to verify zero regressions.

