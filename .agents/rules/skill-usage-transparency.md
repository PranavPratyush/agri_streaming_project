---
title: "Skill Usage Transparency"
description: "Mandatory protocol for tracking, activating, applying, and reporting skills. Enforces DISCOVERED vs ACTIVATED vs APPLIED distinction, pre-task selection, post-task reporting, and cumulative logging in docs/development/SKILL_USAGE_LOG.md."
always_apply: true
---

# Skill Usage Transparency — AgriKafka-Agent

This rule establishes a strict protocol for discovering, activating, applying, and logging agent skills across the AgriKafka-Agent workspace. It applies to all development stages, tasks, and subagents.

---

## 1. Skill Lifecycle Categorization

Agents must strictly differentiate between three operational states of any skill:

| Category | Definition | Verification Requirement |
|---|---|---|
| **DISCOVERED** | The skill's name and high-level description are visible in the workspace (`.agents/skills/`) or global registry. | The skill directory exists, but `SKILL.md` has not been opened in the current session/task. |
| **ACTIVATED** | The full `SKILL.md` (and any referenced templates/checklists) has been loaded into context using `view_file`. | A tool call reading the exact `SKILL.md` path exists in the conversation record. |
| **APPLIED** | The procedures, invariants, algorithms, or schemas defined in the activated skill were concrete inputs that directly guided code, tests, or documentation written during the task. | Concrete code diffs, contract schemas, test suites, or analysis outputs demonstrate adherence to the skill's specific procedures. |

### Invariant Rules
- **Never claim APPLIED without ACTIVATED:** A skill cannot be reported as applied unless its `SKILL.md` was explicitly read using `view_file` in the active trajectory or subagent.
- **Never claim APPLIED merely because installed:** Installing a skill or having it listed in `.agents/skills/` does not constitute usage.
- **No speculative or invented activations:** Every reported activation must have an empirical `view_file` trace.
- **Selective activation:** Do not mass-activate every installed skill. Only activate skills directly relevant to the active task.

---

## 2. Pre-Task Reporting Protocol

Before modifying code, running tests, or authoring architectural documents for any task or stage, the agent must output a **Pre-Task Skill Selection Block**:

```markdown
### Pre-Task Skill Selection
- **Task Identity:** [Stage / Feature / Task Description]
- **Skills Selected for Activation:**
  - `[skill-name]`: [Specific reason why its procedures/patterns are necessary for this task]
- **Relevant Skills Deliberately Excluded:**
  - `[skill-name]`: [Reason for exclusion, e.g., out of scope for current tier, premature at this stage]
- **Standard Baseline Note:** (If no skill is selected) "No specialized skills applied; standard agent capabilities were used."
```

---

## 3. Post-Task Reporting Protocol

Upon finishing the task, the agent must include a structured **Skill Usage Report** in its stage completion report:

```markdown
### Skill Usage Report
| Skill Name | Status | How It Influenced Implementation | Relevant Files & Outputs | Limitations / Unfollowed Items |
|---|---|---|---|---|
| `[skill-name]` | ACTIVATED & APPLIED | [Specific procedures, formulas, or patterns followed] | [Clickable links to files created/modified] | [None / Specific constraint not followed with rationale] |
| `[skill-name]` | ACTIVATED (NOT APPLIED) | [Why the skill was consulted but not applied] | [N/A] | [Explanation] |
```

If no skill was utilized, the report must state verbatim:
> *"No specialized skills applied; standard agent capabilities were used."*

---

## 4. Cumulative Log Maintenance (`docs/development/SKILL_USAGE_LOG.md`)

At the conclusion of each development stage, the agent must append an entry to [docs/development/SKILL_USAGE_LOG.md](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/docs/development/SKILL_USAGE_LOG.md) detailing:
1. Stage number and name.
2. Date and timestamp.
3. Specific task executed.
4. Skills Discovered, Activated, and Applied.
5. Verifiable evidence (files modified, test cases run, schema contracts created).
6. Explanations for any excluded or partially applied skills.
