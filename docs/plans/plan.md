# Plan — Start now (Jules)

**Full instructions:** `JULES_WORK_QUEUE.md`  
**Checklist:** `task_list.md`  
**Do not do P0** (CI automerge, GH Actions pytest, remote API-key bind).

## Cycle 1 (implement immediately)

1. Read `JULES_WORK_QUEUE.md` section **P1.1**.
2. Expand `test_sedge.py` if needed so it covers Node, Edge, DecisionGraph, LearningEngine, DecisionEngine, SelfEvolvingAgent, and persistence if present.
3. Delete redundant SEDGE test files (`test_sedge_core_idea*`, duplicate issue/proof/finalized clones). Keep at most a handful of unique suites.
4. Run: `python3 -m pytest test_sedge*.py -q --tb=line` (or only the files you kept).
5. Mark P1.1 done in `task_list.md` (`[x]`).
6. Submit PR: `chore(tests): collapse duplicate SEDGE test suite`

## After that

Follow the suggested PR sequence in `JULES_WORK_QUEUE.md` (P1.2 → P2.2 → P1.3 → P1.4 → …).

## Forbidden

- New PR titled anything like “Implement SELF-EVOLVING DECISION GRAPH ENGINE (SEDGE) CORE IDEA”
- Touching automerge workflow
- Security P0 bind/API-key changes
