---
name: "agrikafka-evaluation-harness"
description: "Experimental harness for benchmarking AgriKafka-Agent against baseline systems (B1 static rules/EWMA, B2 single LLM+RAG, B3 bounded investigator agent) across ~60 labeled scenarios."
---

# AgriKafka Skill: Evaluation Harness & Comparative Benchmarks

## Purpose
This skill governs the systematic experimental evaluation of stream detectors and agentic triage architectures to answer Research Questions RQ1, RQ2, and RQ3 for course AI372IA and the IEEE technical paper.

---

## When to Use
- Running or modifying experimental benchmarks in `tests/scenarios/` and `docs/experiments/`.
- Generating precision, recall, and Macro-F1 comparative tables across the three architectural variants.
- Measuring false-alert reduction rate, citation grounding percentage, and end-to-end reasoning latency.
- Validating detector performance on injected test suites.

## When NOT to Use
- Running continuous integration unit tests on individual utility functions.
- Performing live production data streaming.

---

## The Three Comparative Architectural Variants

| Variant ID | Architecture Description | Triage & Advisory Mechanism |
|---|---|---|
| **B1** | **Deterministic Baseline** | Static thresholding + EWMA statistical detection only. No LLM or RAG. Fixed rule templates. |
| **B2** | **Single LLM + RAG** | Single LLM invocation with pre-assembled prompt context (history, weather, retrieved RAG passages). No interactive tool calling. |
| **B3** | **Bounded Investigator Agent** | Bounded tool-using agent (LangGraph / direct Python state machine) with conditional tool sequencing, deterministic guardrails, and citation verification. |

---

## Benchmark Scenario Corpus (~60 Labeled Events)
Scenarios stored in `data/scenarios/` must include:
- **30 Real Crop Stress Events:**
  - 15 Drought dry-downs (gradual soil moisture drop below wilting point).
  - 10 Heatwave events (sustained temperatures $> 36^\circ\text{C}$ with high VPD).
  - 5 Disease-risk windows (high humidity $> 85\%$ + mild temperature $\ge 6\text{h}$).
- **20 Sensor Fault Scenarios:**
  - 5 Stuck moisture sensors (flatline during rain or drying).
  - 5 High drift errors (cumulative $+0.15\text{ m}^3/\text{m}^3$ over 48 hours).
  - 5 Sudden impulse spikes (physically impossible $+0.25\text{ m}^3/\text{m}^3$ single-step jump).
  - 5 Intermittent signal dropouts (periodic drop to 0.0).
- **10 Transient Noise Scenarios:**
  - Natural passing cloud cover, brief wind gusts, short solar radiation dips that should NOT trigger farmer alarms.

---

## Quantitative Metrics to Measure
1. **Classification Performance:** Macro-F1 across classes `real_stress`, `sensor_fault`, and `noise`.
2. **Alert Reduction Rate:**
   $$\text{ARR} = 1 - \frac{\text{Alerts Sent to Farmer (B3)}}{\text{Alerts Triggered by Stream Detectors (B1)}}$$
   Measured at equal recall of genuine crop stress ($\ge 95\%$).
3. **Citation Grounding Rate:** Percentage of generated recommendations where 100% of factual statements cite valid retrieved document IDs.
4. **Safety & Hallucination Rate:** Percentage of recommendations rejected by deterministic guardrails (unauthorized dosage, unsupported pathogen diagnosis).
5. **Cost & Latency:** P95/P99 latency (seconds) and average token cost per alert.

---

## Execution Command
```bash
pytest tests/scenarios/test_comparative_harness.py --variant=all --output=docs/experiments/02_agentic_triage.md
```
Results must be logged verbatim with experiment seeds and parameters.
