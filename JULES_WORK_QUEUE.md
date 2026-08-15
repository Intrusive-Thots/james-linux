# Jules Work Queue — JAMES Linux Maintenance Sprint

**Audience:** Jules (google-labs-jules) and any autonomous agent loop reading this repo.  
**Source of truth:** This file + `task_list.md` (unchecked items).  
**Created:** 2026-08-15  
**Do NOT implement P0 items** (CI auto-merge lockdown, pytest GitHub Actions workflow, remote API-key bind guard). Humans own those.

---

## Mission

Improve maintainability, reduce noise, and make real product code easier to ship.  
**Stop** inventing new SEDGE “core idea” PRs. **Start** cleanup, structure, and product hygiene.

### Core rules for every PR

1. **One theme per PR.** Do not mix “delete tests” with “split orchestrator”.
2. **Verify before submit.** Run the relevant tests; they must pass.
3. **No drive-by SEDGE rewrites.** SEDGE is frozen except where a task explicitly says otherwise.
4. **Do not touch** `.github/workflows/main.yml` (automerge). Leave P0 alone.
5. **Do not change** remote server API-key / bind security policy (P0).
6. Prefer small, reviewable diffs. Squash noise; keep behavior unless the task says otherwise.
7. Update this file and `task_list.md` when a checkbox item is done (mark `[x]`).
8. PR title format: `chore|refactor|docs|feat(scope): short description`
9. After finishing a task, pick the **next unchecked** item in priority order (P1 → P2 → P3).

### Preferred test command (local)

```bash
python3 -m pytest test_orchestrator.py test_net_guard.py test_native.py test_sedge.py test_agent_security_fixes.py -q --tb=line
```

When tests have been moved under `tests/`, use:

```bash
python3 -m pytest tests/ -q --tb=line
```

---

## P1 — High impact (do these first)

### P1.1 — Collapse duplicate SEDGE tests ⭐ START HERE

**Why:** ~38 near-duplicate `test_sedge_*.py` files (~5.8k lines) re-test the same Node/Edge/score paths. Bot thrash, zero product value.

**Do:**

1. Keep **one** comprehensive unit suite: prefer `test_sedge.py` (expand it if needed).
2. Keep **one** integration-oriented suite if useful: e.g. `test_sedge_engine.py` or `test_auto_agent.py` / `test_sedge_persistence.py` — only if they cover unique behavior (persistence, agent feedback loop).
3. **Delete** redundant files, especially names like:
   - `test_sedge_core_idea*.py`
   - `test_sedge_core_idea_mathematical_proof.py`
   - `test_sedge_core_idea_finalized.py`
   - `test_sedge_core_idea_verified.py`
   - `test_sedge_issue*.py`
   - Near-clones that only reassert `edge.score()` / Node model
4. Ensure remaining tests still cover:
   - Node / Edge models
   - DecisionGraph add/get_best_next
   - LearningEngine success/failure weight updates
   - DecisionEngine stochastic / zero-utility fallback
   - SelfEvolvingAgent feedback loop (if present)
   - Persistence save/load (if implemented)
5. Run: `python3 -m pytest test_sedge*.py -q` (or the kept file list) — all pass.

**Do not:** Rewrite `james/core/sedge.py` “from scratch” or add more “CORE IDEA” documentation tests.

**Done when:** ≤ ~5 SEDGE-related test files remain, suite is green, no duplicate `test_state_node_model` sprawl.

---

### P1.2 — Freeze SEDGE product scope

**Why:** SEDGE is only lightly wired via `auto_agent.py`, not the main pentest path. Stop expanding the graph engine until structure work lands.

**Do:**

1. Add a short note at the top of `james/core/sedge.py` and/or `docs/sedge_engine.md`:
   - Status: **stable / frozen**
   - New features require an explicit task in this queue
2. Ensure `build_parrot_wifi_graph()` and existing API remain; no behavior change required.
3. Do **not** open PRs titled “Implement SEDGE CORE IDEA”.

**Done when:** Freeze note exists; no new SEDGE feature code in the same PR as unrelated work.

---

### P1.3 — Split `james/core/agent.py` (~3.2k lines)

**Why:** God module blocks review and safe changes.

**Target layout (adjust names if cleaner, keep imports working):**

```text
james/core/agent/
  __init__.py          # re-export Agent, public API used by GUI/API
  models.py            # AgentAction, AgentPlan, PlanStep, AttackPlan, …
  intents.py           # intent matching / routing tables
  plans.py             # multi-step plan builders
  wifi_chains.py       # wifi blitz / PMKID / handshake chains
  network_chains.py    # network dominate / recon chains
  web_chains.py        # web pwn chains
  shell.py             # reverse_shell helpers (keep security constraints)
  brain.py             # main Agent class process() / execute path
```

**Do:**

1. Move code without changing public behavior.
2. Keep `from james.core.agent import …` working via package `__init__.py` (or temporary shim module).
3. Update imports across GUI/API/tests.
4. Run existing agent/intent/security tests.

**Done when:** No single agent module > ~800 lines; tests for intents + security still pass.

---

### P1.4 — Split `james/core/orchestrator.py` (~2.4k lines)

**Why:** Same as agent — too large to maintain.

**Target layout:**

```text
james/core/orchestrator/
  __init__.py          # re-export Orchestrator
  base.py              # context, loot, shared helpers
  wifi.py              # monitor, airodump, deauth, crack paths
  network.py           # nmap, host scans
  web.py               # dirbust, sqlmap, etc.
  loot.py              # cracked key cache, results.json
  skills.py            # load/run james/skills/*.json
```

**Do:**

1. Mechanical split; preserve method names used by Agent/GUI.
2. Shim so `from james.core.orchestrator import Orchestrator` still works.
3. Run `test_orchestrator.py`, `test_net_guard.py`.

**Done when:** Orchestrator package exists, public API stable, tests green.

---

### P1.5 — Split or modularize `james/tools/parrot.py` (optional follow-on)

**Why:** ~1.3k lines of mixed tool wrappers.

**Do only after P1.3–P1.4:**

```text
james/tools/wifi.py
james/tools/nmap_tools.py
james/tools/hashcat_tools.py
…
james/tools/parrot.py   # thin re-export for compatibility
```

**Done when:** Call sites still import cleanly; no behavior change.

---

## P2 — Structure & product clarity

### P2.1 — Choose one remote web client (document + align)

**Why:** Dual UIs: `james/web/` (static PWA) and `web/` (React/Vite ~259MB with node_modules).

**Do:**

1. Inspect what `main.py --server` / `james/api/server.py` / `james/remote/server.py` actually serve.
2. Pick **one** primary:
   - **Option A (recommended if React is complete):** React app in `web/` is primary; document build + static serve path.
   - **Option B:** Keep lightweight `james/web/` PWA; mark `web/` as experimental or remove from default docs.
3. Update `README.md` “Remote Access” section to match reality (ports, how to build, which folder).
4. If React is primary: add short `web/README.md` build steps (`npm install && npm run build`) and where assets are mounted.
5. Do **not** delete the secondary UI in the first PR unless README and server paths are already aligned — prefer document + wire first, delete later in a dedicated PR.

**Done when:** README + server code agree on a single primary remote UI path.

---

### P2.2 — Reorganize root clutter into `tests/` and `scripts/`

**Why:** 60+ test files and scratch scripts at repo root.

**Do:**

1. Create:

```text
tests/
  unit/
  security/
  integration/
scripts/
docs/plans/
```

2. Move:
   - `test_*.py` → `tests/…` (group by theme: sedge, agent, gui, api, security)
   - `clean_*.py`, `generate_wordlists.py`, `benchmark_stat.py` → `scripts/`
   - `implementation_plan*.md`, `plan.md`, `pr.md`, `pr_desc.txt`, old task dumps → `docs/plans/` (keep `task_list.md` and `JULES_WORK_QUEUE.md` at root so agents find them)
3. Add or update `pytest.ini` / `pyproject.toml`:

```ini
[pytest]
testpaths = tests
pythonpath = .
```

4. Fix any import path issues.
5. Run full moved suite.

**Done when:** Root is clean of `test_*.py`; pytest discovers tests under `tests/`.

---

### P2.3 — Expand real skills (JSON playbooks)

**Why:** README markets rich automation; `james/skills/` only has 5 JSON skills.

**Do:**

1. Inventory orchestrator methods that are real end-to-end chains.
2. Add skills that map to working methods, e.g.:
   - `wifi_blitz.json`
   - `network_dominate.json`
   - `web_pwn.json`
   - `stealth_recon.json`
   - `evil_twin.json` (only if orchestrator supports it)
3. Each skill must be valid JSON and loadable by the skill runner.
4. Add a small unit test that loads every skill file and checks required keys.
5. Align README skill/tool claims with actual counts (or generate count from code).

**Done when:** ≥ 8 skills that reference real orchestrator entrypoints; README not wildly overstated.

---

### P2.4 — Gate `auto_agent.py` self-modification

**Why:** Self-improving loop encourages endless SEDGE thrash and unreviewed tree writes.

**Do:**

1. Require explicit opt-in, e.g. env `JAMES_AUTO_AGENT=1` or CLI flag; default **off**.
2. Never write learned graphs into the **git working tree** by default — use `~/.james/knowledge_graph.json` (or similar under home config).
3. Do not auto-edit tracked source files without an explicit dangerous flag (document as experimental).
4. Add a short unit test: default init does not enable write-to-repo behavior.

**Done when:** Default path is safe; docs mention the opt-in.

---

## P3 — Polish & hygiene

### P3.1 — Dependencies hygiene

**Do:**

1. Review `requirements.txt`:
   - Pin reasonable lower bounds that match reality (local pydantic is 2.x; avoid claiming v1-only APIs).
   - Document or replace `google-antigravity` if unused; if used, document what for.
2. Add `requirements-dev.txt` with `pytest`, `httpx` (for API tests), etc.
3. Optionally add a lock note in README (“pip install -r requirements.txt”).
4. Do not upgrade PyQt5 → PyQt6 in this task (large; separate future epic).

**Done when:** Dev can install runtime + test deps cleanly; unused deps noted or removed.

---

### P3.2 — Real LICENSE + legal notice

**Do:**

1. Add a real `LICENSE` file (prefer MIT unless owner specifies otherwise — if unsure, use MIT and state “authorized testing only” in README).
2. Replace “FAFO” badge with the real license badge, or keep tone but link LICENSE.
3. Add a short **Authorized use only** section to README (lab/owned networks only).

**Done when:** `LICENSE` exists; README references it.

---

### P3.3 — `.gitignore` hardening

**Do:** Ensure ignored:

```text
__pycache__/
*.pyc
.venv/
venv/
node_modules/
web/node_modules/
.james/
*.log
.jules/*.local
wordlists/rockyou.txt
.pytest_cache/
.mypy_cache/
dist/
build/
```

Do not force-delete tracked secrets; just prevent future junk.

**Done when:** `.gitignore` covers the above; `git status` stays clean for local venv/node_modules.

---

### P3.4 — Background process logging improvement

**Why:** `run_background` discards stdout/stderr to `DEVNULL` — hard to debug captures.

**Do:**

1. Optional ring-buffer or temp log path per background proc in `native.py`.
2. Expose last N lines via orchestrator/API if easy; otherwise write under `~/.james/logs/bg_*.log`.
3. Keep default performance reasonable (don’t spam GUI).

**Done when:** Long-running tools (airodump, etc.) leave inspectable logs without breaking current callers.

---

### P3.5 — Tool inventory honesty

**Do:**

1. Script or doc section listing tool wrapper classes/methods in `james/tools/`.
2. Update README badges/claims (“35+ tools”) to match the real inventory, or implement missing advertised wrappers.

**Done when:** Marketing numbers ≤ actual implemented wrappers.

---

## Explicitly out of scope (P0 — humans only)

Do **not** work on these unless a human rewrites this queue:

- [ ] Changing `.github/workflows/main.yml` automerge policy
- [ ] Adding GitHub Actions pytest CI workflow
- [ ] Requiring API key before binding remote server on `0.0.0.0`
- [ ] Broad sudo/shell=True security rewrite of `native.py` (can be a future P0/P1 security epic after structure work)

---

## Suggested PR sequence

| Order | Task ID | PR theme |
|------:|---------|----------|
| 1 | P1.1 | `chore(tests): collapse duplicate SEDGE test suite` |
| 2 | P1.2 | `docs(sedge): freeze engine scope` |
| 3 | P2.2 | `chore: move tests to tests/ and clean root` |
| 4 | P1.3 | `refactor(agent): split agent.py into package` |
| 5 | P1.4 | `refactor(orchestrator): split orchestrator into package` |
| 6 | P2.4 | `fix(auto_agent): opt-in only, graph under ~/.james` |
| 7 | P2.1 | `docs(web): single primary remote UI` |
| 8 | P2.3 | `feat(skills): expand real JSON playbooks` |
| 9 | P3.1–P3.3 | deps, LICENSE, gitignore |
| 10 | P3.4–P3.5 | bg logs, tool inventory |

---

## How Jules should start **right now**

1. Read this file completely.
2. Implement **P1.1** only (collapse duplicate SEDGE tests).
3. Run pytest on remaining SEDGE tests; fix failures.
4. Mark P1.1 done in `task_list.md` and here.
5. Open PR with title: `chore(tests): collapse duplicate SEDGE test suite`
6. On next cycle, continue with P1.2, then P2.2, then P1.3, etc.

**Do not** start a new “Implement SELF-EVOLVING DECISION GRAPH ENGINE (SEDGE) CORE IDEA” task.

---

## Context snapshot (repo health)

- Remote: `https://github.com/Intrusive-Thots/james-linux`
- Large modules: `agent.py` ~3284, `orchestrator.py` ~2432, `ai_engine.py` ~1423, `parrot.py` ~1322
- Skills today: 5 JSON files under `james/skills/`
- Dual web: `james/web/` + `web/`
- History heavily bot-driven; prefer cleanup PRs over feature thrash

End of queue.
