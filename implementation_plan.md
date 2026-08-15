# Implementation Plan — Jules Maintenance Sprint

**Read first:** `JULES_WORK_QUEUE.md` (full instructions) and `task_list.md` (checkboxes).

## Objective

Stop SEDGE thrash. Improve maintainability of JAMES Linux via cleanup, modularization, and product hygiene.
**Do not implement P0** (GitHub automerge lockdown, pytest Actions CI, remote API-key bind guard).

## Core principles

- Never perform the same analysis twice.
- One theme per PR.
- Verify every modification with pytest.
- Prefer reusable structure over new toy features.
- Every completed task must leave the system easier to maintain than before.
- **No new “SEDGE CORE IDEA” implementations.**

## Hourly / cycle loop (for autonomous agents)

```text
while True:
    load JULES_WORK_QUEUE.md
    discover_next_task from task_list.md  # first "- [ ]" under Active queue
    if task is P0 or out-of-scope: skip
    implement ONE task only
    test
    mark task [x] in task_list.md and JULES_WORK_QUEUE.md if applicable
    open PR with chore|refactor|docs|feat scope
    stop cycle (do not chain infinite SEDGE work)
```

## Current next task

**P1.1 — Collapse duplicate SEDGE tests**

See `JULES_WORK_QUEUE.md` section P1.1 for exact steps, keep/delete rules, and done criteria.

## Phases (ordered)

1. P1.1 SEDGE test collapse  
2. P1.2 SEDGE freeze docs  
3. P2.2 tests/ directory reorganization  
4. P1.3 agent.py split  
5. P1.4 orchestrator.py split  
6. P2.4 auto_agent opt-in  
7. P2.1 single web UI story  
8. P2.3 skills expansion  
9. P3.* polish (deps, LICENSE, gitignore, bg logs, inventory)

## Governance

- Do not modify `.github/workflows/main.yml`.
- Do not change remote API-key / bind security policy (P0).
- Do not rewrite SEDGE algorithm unless a queue item explicitly requires a bugfix.
- Keep PRs small and green.

## Success criteria

- Duplicate SEDGE tests gone; suite still green.
- Agent and orchestrator split into packages with stable imports.
- Root directory clean; tests under `tests/`.
- Skills and README roughly honest.
- auto_agent safe by default.
