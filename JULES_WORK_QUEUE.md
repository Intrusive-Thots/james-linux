# JAMES Linux — Jules Work Queue

All P1–P3 items in `task_list.md` are complete.

## Critical outstanding — RESOLVED (2026-08-17)
- Full Agent (~3000 lines), Orchestrator (~2400 lines), and parrot.py tool wrappers restored from commit 8d84715 into the package layout (`james/core/agent/`, `james/core/orchestrator/`).
- Models and INTENT_PATTERNS remain split for stable public imports.
- Guard test `tests/test_no_placeholders.py` remains to prevent regression.

## Remaining hygiene (optional)
- Clean stale Jules feature branches after merge.
- Further test coverage for restored methods.

Do not touch P0 (CI automerge / API-key bind).
