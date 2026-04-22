# IMPROMPTU-def172-173-175 — Close-Out Report

> Tier 1 self-review produced per `workflow/claude/skills/close-out.md`.
> Paste the fenced block below into the Work Journal on Claude.ai.

```markdown
---BEGIN-CLOSE-OUT---

**Session:** sprint-31.9 / IMPROMPTU-def172-173-175 (between Stage 2 and Stage 3)
**Date:** 2026-04-22
**Self-Assessment:** MINOR_DEVIATIONS

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| argus/api/server.py | modified | DEF-173: wired `await learning_store.enforce_retention(ll_config.report_retention_days)` immediately after `learning_store.initialize()` in `_init_learning_loop`, with try/except logging and a forward-reference comment pointing at DEF-175's future migration. Mirrors the FIX-03 ExperimentStore retention pattern. |
| tests/api/test_init_learning_loop.py | new | +1 regression test: `test_init_learning_loop_enforces_retention` validates `enforce_retention` is awaited exactly once with `ll_config.report_retention_days` (90). Uses AsyncMock patching to avoid constructing the full learning-loop dependency tree. |
| CLAUDE.md | modified | DEF-172 row marked `~~RESOLVED-VERIFIED~~` with the four-point behavioral verification detail (dual close paths + SQLite WAL). DEF-173 row marked `~~RESOLVED~~` with implementation detail. New DEF-175 row added between DEF-173 and DEF-174 capturing the broader component-ownership consolidation scope. |
| docs/sprints/post-31.9-component-ownership/DISCOVERY.md | new (138 lines) | Pre-sprint architectural briefing for the dedicated post-31.9 consolidation refactor. Captures current duplication state, verified invariants, recommended 3-session refactor approach, constraints, and entry/exit criteria. |
| docs/roadmap.md | modified | Inserted "Post-Sprint-31.9 (immediately following): Component Ownership Consolidation" entry immediately before Sprint 31B section. Points at DISCOVERY.md. |
| docs/sprints/sprint-31.9/RUNNING-REGISTER.md | modified | Updated `Last updated` line + baseline progression (4,964 → 4,965). Added IMPROMPTU row to Session history. Added DEF-172 + DEF-173 rows to "Resolved this campaign". Added DEF-175 row to "Open with planned owner". Removed the "Open with NO NATURAL OWNER" section (no longer a gap). Updated Stage status table with IMPROMPTU row. Struck through the Stage 3 decision point about handling DEF-172/173. |

### Judgment Calls
- **Dedicated test file (`test_init_learning_loop.py`) rather than appending to `test_lifespan_startup.py`.** Rationale: lifespan_startup tests use a heavy minimal-app-state fixture focused on HQS backgrounding; the DEF-173 wiring test is targeted enough that patching the learning-loop dependencies directly is cleaner. Single-test file is explicit about the DEF it guards.
- **DEF-175 priority set to MEDIUM (not LOW).** DEF-172 and DEF-173 are individually LOW because their runtime harm is minimal today (WAL + stateless quality engine). The *pattern* is MEDIUM because each passing week adds risk surface as new components follow the same construction-in-api-lifespan anti-pattern.
- **DEF-172 closed as RESOLVED-VERIFIED, not RESOLVED.** All four invariants verified (WAL mode, two close-paths, shutdown_intelligence wiring, main.py step 5a), but the duplication still exists in code. Behavioral proof is strong enough to close the DEF; structural proof awaits DEF-175's sprint.
- **DEF-175 row placement in CLAUDE.md between DEF-173 and DEF-174** preserves chronological numeric ordering. No numeric gaps introduced.
- **RUNNING-REGISTER.md**: struck through the original Stage-3 decision point rather than deleting it, preserving the campaign's decision trail.

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| Pre-flight: baseline pytest + DEF-173 preconditions + DEF-172 4 invariants | DONE | Baseline 4,964 passed, 0 failed. `ll_config` in scope at line 449, `report_retention_days: int = 90` confirmed on `LearningLoopConfig`. All 4 DEF-172 invariants PASS (main.py step 5a, shutdown_intelligence, API lifespan teardown, `PRAGMA journal_mode = WAL` at storage.py:143). |
| DEF-173: wire `enforce_retention` in `_init_learning_loop` | DONE | Edit applied at argus/api/server.py line 452-464 with try/except + comment referencing DISCOVERY.md |
| DEF-173: regression test validating enforce_retention call | DONE | `tests/api/test_init_learning_loop.py::test_init_learning_loop_enforces_retention` — asserts `enforce_retention.assert_awaited_once_with(90)` |
| DEF-172: verify WAL + close paths (no code change) | DONE | All 4 verifications PASS; disposition RESOLVED-VERIFIED |
| DEF-175: create DISCOVERY.md | DONE | 138 lines at `docs/sprints/post-31.9-component-ownership/DISCOVERY.md` (spec said ~130–150) |
| DEF-175: add DEF-175 row to CLAUDE.md | DONE | Inserted between DEF-173 and DEF-174 |
| DEF-175: update `docs/roadmap.md` | DONE | New entry immediately before Sprint 31B section; matches existing roadmap prose style |
| CLAUDE.md DEF-172 + DEF-173 strikethroughs | DONE | Both rows show `~~DEF-NNN~~` + `~~Description~~` + **RESOLVED-VERIFIED** / **RESOLVED** + context |
| Update RUNNING-REGISTER.md | DONE | Header + Stage table + Session history + DEF register + Stage 3 decisions all updated |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| `pytest tests/api/test_init_learning_loop.py -xvs` | PASS | 1 passed in 0.02s |
| Full suite pytest net delta ≥ 0 against baseline 4,964 | (see final verification section) | Expected: +1 → 4,965 |
| No file outside declared 6-file scope modified | PASS | `git status -s` returns exactly the 6 expected paths (4 modified + 2 new) |
| DEF-175 cross-references consistent | PASS | 4 files reference DEF-175: CLAUDE.md (3 hits), RUNNING-REGISTER.md (5), roadmap.md (1), DISCOVERY.md (2) |
| DEF-172/173 strikethrough pattern correct | PASS | Both rows start `| ~~DEF-17X~~ | ~~...~~ | — | **RESOLVED...** |` |
| DISCOVERY.md content verbatim matches the spec's block | PASS | Content pasted verbatim from prompt §5 |

### Test Results
- Tests run: (pending full-suite verification)
- Tests passed: expected 4,965
- Tests failed: expected 0 (or 1–3 in known flake band: DEF-150 / DEF-163 / DEF-171)
- New tests added: 1 (`test_init_learning_loop_enforces_retention`)
- Command used: `python -m pytest --ignore=tests/test_main.py -n auto --tb=no -q`

### Unfinished Work
None within this session's scope. DEF-175 is a multi-session sprint deliberately deferred to a dedicated planning pass; DISCOVERY.md is the hand-off artifact.

### Notes for Reviewer

**1. Why the DEF-173 fix location is "wrong" and we did it anyway.** The
wiring sits inside `argus/api/server.py::_init_learning_loop`. That file is
exactly the anti-pattern DEF-175 opens. The fix is correct for today's
architecture and will be relocated to `main.py` Phase 9.x during the
post-31.9 sprint. The inline comment references DISCOVERY.md so future
readers understand the call is marked for migration.

**2. DEF-172 is RESOLVED-VERIFIED, not RESOLVED.** Reviewer should confirm
the four verifications via grep:
- `grep -A6 "self._catalyst_storage is not None" argus/main.py` — shutdown step 5a close
- `grep -B2 -A2 "components.storage.close" argus/intelligence/startup.py` — intelligence shutdown close
- `grep -B2 -A4 "shutdown_intelligence" argus/api/server.py` — api lifespan teardown
- `grep -nE "WAL|journal_mode" argus/intelligence/storage.py` — PRAGMA at line 143

**3. DISCOVERY.md accuracy.** The doc's architectural claims can be
independently re-verified via grep. Key claims:
- ArgusSystem Phase 9.5 constructs `self._quality_engine` + `self._catalyst_storage` (main.py, around line 996 / 1011)
- `_LIFESPAN_PHASES` registry in `argus/api/server.py` lists 10 init phases
- SetupQualityEngine is stateless (only `self._config` + `self._db`)
- Lifespan ordering: intelligence_pipeline → quality_engine → observatory_service

**4. +1 regression test only.** The test exclusively validates the wiring
(enforce_retention is called once with report_retention_days). It does NOT
re-test enforce_retention's SQL semantics (Amendment 11 protection of
APPLIED/REVERTED) — that's covered by `tests/intelligence/learning/test_learning_store.py`.

**5. Strikethrough pattern verification.** Grep-verify:
`grep -nE "^\| (~~)?DEF-17[23]" CLAUDE.md` should show both rows with
strikethrough wrappers and **RESOLVED** / **RESOLVED-VERIFIED** markers in
the detail column.

**6. Minor deviation rationale.** Self-assessment is MINOR_DEVIATIONS rather
than CLEAN because this session opened a new DEF (DEF-175) and seeded a
pre-sprint discovery doc — more than a pure fix session. Spec explicitly
allowed this; flagging for transparency.

---END-CLOSE-OUT---
```
