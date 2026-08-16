# JAMES Linux — Task List

Agents (including Jules): pick the first unchecked item. Full instructions in `JULES_WORK_QUEUE.md`.  
**Do not work on P0 items** (CI automerge, pytest GH Actions, remote API-key bind guard).

## Completed (historical)

- [x] Initialize `james-linux` Git repository and push to GitHub.
- [x] Scaffold `james/gui/` with basic PyQt5 application structure.
- [x] Implement `james/layers/native.py` exclusively for Linux bash execution.
- [x] Create `james/tools/parrot.py` wrappers for `airmon-ng`, `airodump-ng`, and `nmap`.
- [x] Define initial JSON skills in `james/skills/` (monitor mode, scan, deauth).
- [x] Test application components and mock CLI outputs on Windows before Linux deployment.

## Active queue (Jules — P1 → P2 → P3)

### P1
- [x] P1.1 Collapse duplicate SEDGE tests into one (or few) real suites; delete `test_sedge_core_idea*` thrash. See `JULES_WORK_QUEUE.md`. (only 3 suites remain; fixed duplicate method name)
- [x] P1.2 Freeze SEDGE scope (docs note; no new CORE IDEA feature PRs).
- [x] P1.3 Split `james/core/agent.py` into `james/core/agent/` package with stable public imports. (restored missing Agent implementation after incomplete split)
- [x] P1.4 Split `james/core/orchestrator.py` into `james/core/orchestrator/` package with stable public imports. (restored missing Orchestrator implementation after incomplete split)
- [ ] P1.5 (Optional) Modularize `james/tools/parrot.py` behind thin re-exports.

### P2
- [ ] P2.1 Choose/document one primary remote web client (`web/` vs `james/web/`); align README + server.
- [x] P2.2 Move root `test_*.py` into `tests/`, scripts into `scripts/`, plans into `docs/plans/`; add pytest config.
- [x] P2.3 Expand real `james/skills/*.json` playbooks (≥8) that call real orchestrator methods; fix README claims.
- [x] P2.4 Gate `auto_agent.py` behind opt-in; store graphs under `~/.james/`, not the git tree.

### P3
- [x] P3.1 Dependencies hygiene: clean `requirements.txt`, add `requirements-dev.txt`.
- [x] P3.2 Add real `LICENSE` + authorized-use README section.
- [x] P3.3 Harden `.gitignore` (venv, node_modules, logs, rockyou symlink, caches).
- [x] P3.4 Background process logging (ring buffer or `~/.james/logs/bg_*.log`) in `native.py`.
- [ ] P3.5 Tool inventory honesty — align README tool counts with code.

## Out of scope (P0 — humans only)

- [ ] P0 Automerge policy / CI test workflow / remote API-key bind requirement — **do not implement**
