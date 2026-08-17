# JAMES Linux — Jules Work Queue

All P1–P3 items in `task_list.md` are complete.

## Critical outstanding
- Agent/Orchestrator on master are minimal stubs (functional for basic intents + security quoting).
- Full implementations live in pre-split history (commit 8d84715). Repeated restore attempts have not fully succeeded.
- Guard test `tests/test_no_placeholders.py` exists to prevent pure PLACEHOLDER regression.

## Remaining hygiene (optional)
- Clean stale Jules feature branches after merge.
- Extract full Agent + Orchestrator from 8d84715 into package paths and land a focused restore PR.

Do not touch P0 (CI automerge / API-key bind).
