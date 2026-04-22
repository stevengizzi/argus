---BEGIN-CLOSE-OUT---

**Session:** sprint-31.9 — Stage 1 close-out sweep (doc cleanup + DEF logging)
**Date:** 2026-04-21
**Self-Assessment:** CLEAN
**Context State:** GREEN
**Commit SHA:** f3b0464 (pushed to origin/main)

### Session Scope

Documentation-only sweep of residual items surfaced during Stage 1 Work
Journal verification (FIX-00, FIX-15, FIX-17, FIX-20, FIX-01, FIX-11 all
landed on origin/main). Goal: enter Stage 2 with a clean docs slate, log
two new DEFs for code fixes that belong to future sessions' natural
scope, and touch zero `argus/*.py` / `config/*.yaml` / `workflow/*`.

### Change Manifest

| File | Change Type | Rationale |
|------|-------------|-----------|
| docs/dec-index.md | modified | Footer off-by-one: `Next DEC: 384.` → `Next DEC: 385.` (post-FIX-01 DEC-384 landed but footer wasn't bumped) |
| docs/strategies/STRATEGY_AFTERNOON_MOMENTUM.md | modified | FIX-15 F1: `allowed_regimes` citation corrected from YAML path (`config/strategies/afternoon_momentum.yaml`) to Python source (`argus/strategies/afternoon_momentum.py:1160` — verified line via grep) |
| docs/strategies/STRATEGY_BULL_FLAG.md | modified | FIX-15 F1: `allowed_regimes` citation corrected from YAML path (`config/strategies/bull_flag.yaml`) to Python source (`argus/strategies/pattern_strategy.py:504` — verified line via grep) |
| .claude/rules/code-style.md | modified | FIX-17 LOW-1: `ThrottledLogger` module path corrected in bracketed link + import example: `argus/utils/throttled_logger.py` → `argus/utils/log_throttle.py` (actual module name on disk) |
| .claude/rules/api-conventions.md | modified | FIX-17 LOW-2: OrderManager API surface aligned with `argus/execution/order_manager.py`: (a) `get_managed_positions` return type `list[ManagedPosition]` → `dict[str, list[ManagedPosition]]`; (b) non-existent singular `get_managed_position(symbol)` line removed; (c) `close_position` signature `(self, symbol: str) -> None` → `(self, symbol: str, reason: str = "api_close") -> bool` |
| docs/audits/audit-2026-04-21/phase-2-review.csv | modified | FIX-20 LOW-1: DEF-034 row column-4 `file` corrected from stale `workflow/runner/models.py (SessionResult)` → `workflow/runner/sprint_runner/state.py (SessionResult)` (CSV quoting preserved) |
| CLAUDE.md | modified | DEF-170 + DEF-171 appended to DEF table in numerical order (before `## Reference` section). Both log-only — no code fix in this session. |

Total: **7 files**, +10/-9 lines.

### Judgment Calls

- **B.2 wording:** The existing FIX-15 F1 text said "`bearish_trending` is present in **every strategy's** `allowed_regimes` list via `config/strategies/afternoon_momentum.yaml`." That was doubly wrong — the sentence described a per-strategy fact but cited a YAML path, and in AFTERNOON_MOMENTUM's case the YAML doesn't define `allowed_regimes` at all. Tightened the phrasing to "this strategy's" to match the Python-source citation (the claim is now locally accurate to the file being documented). Same treatment for BULL_FLAG, though kept "every PatternBasedStrategy" there because `pattern_strategy.py:504` genuinely is the shared source for all PatternBasedStrategy variants.
- **B.4 signature choice:** `close_position` on disk is `async def close_position(self, symbol: str, reason: str = "api_close") -> bool`. Kept the `reason: str = "api_close"` default in the api-conventions snippet (rather than dropping to the minimal required arg) because the default is part of the public contract routes rely on.
- **B.6 ownership:** Placed DEF-170 under FIX-05-core rather than filing it as a standalone impromptu because (a) `argus/core/regime.py` and `argus/core/orchestrator.py` are both in FIX-05's declared scope and (b) the fix surface is small enough that batching with FIX-05 is cheaper than a dedicated session.
- **B.7 ownership:** DEF-171 assigned to FIX-13-test-hygiene (already on the campaign register). Resisted the temptation to investigate the flake in this session — explicitly out of scope (docs-only).
- **B.8 no-op:** CLAUDE.md does not maintain a running DEF counter anywhere (grep returned empty). No edit needed — noted and moved on.

### Scope Verification

| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| B.1 dec-index.md footer 384→385 | DONE | Line 507 edited in place. dec-index.md line 3 header "384 decisions (DEC-001 through DEC-384)" left untouched — DEC-384 is the latest USED DEC, so the header is correct. |
| B.2 AFTERNOON_MOMENTUM allowed_regimes citation | DONE | Verified line 1160 via grep before editing. |
| B.2 BULL_FLAG allowed_regimes citation | DONE | Verified line 504 via grep before editing. |
| B.3 throttled_logger → log_throttle | DONE | Verified `argus/utils/log_throttle.py` exists and `throttled_logger.py` does not. `grep throttled_logger .claude/rules/code-style.md` returns empty post-fix. |
| B.4 OrderManager API drift | DONE | Verified actual signatures via grep against `argus/execution/order_manager.py` before editing (close_position: line 1740; get_managed_positions: line 2833; no singular `get_managed_position`). |
| B.5 phase-2-review.csv:274 stale path | DONE | CSV quoting preserved; column count unchanged. |
| B.6 DEF-170 logged | DONE | Placed in numerical order after DEF-169, before `## Reference` section. Owner: FIX-05-core. Priority: MEDIUM. |
| B.7 DEF-171 logged | DONE | Placed after DEF-170. Owner: FIX-13-test-hygiene. Priority: LOW. |
| B.8 CLAUDE.md DEF counter | N/A | No counter exists (grep confirmed). |

### Regression Checks

| Check | Result | Notes |
|-------|--------|-------|
| Phase A baseline: Stage 1 chain on origin/main | PASS | Top commit `b5986b3 docs(FIX-11)...` matches expected chain + 1 additional docs commit. |
| Phase A submodule at FIX-20 bump | PASS | `workflow` at `942c53a`. |
| Phase A FIX-01/FIX-11 artifacts land | PASS | `_STANDALONE_SYSTEM_OVERLAYS` in config.py (3 hits), `catalyst.db` in main.py (5 hits), DEF-167/168/169 in CLAUDE.md, DEC-384 in decision-log.md, `scoring_fingerprint.py` + `test_fix01_load_config_merge.py` exist. |
| Phase A baseline pytest | PASS | 4,943 passed, 2 failed. Both failures are DEF-163 (known date-decay). Within expected 0–3 range. |
| Phase C.1 Next DEC footer | PASS | Exactly one hit, `Next DEC: 385.` |
| Phase C.2 throttled_logger gone from code-style.md | PASS | empty |
| Phase C.3 DEF-170 + DEF-171 in CLAUDE.md | PASS | 2 hits |
| Phase C.4 No code edits (`argus/*.py` / `config/*.yaml`) | PASS | `git diff --stat` filter empty |
| Phase C.5 File count | PASS | 7 files (5 doc + 2 .claude/rules + CLAUDE.md counted once) — matches spec. |
| Phase C.6 post-sweep pytest | PASS | 4,943 passed, 2 failed (identical to baseline — 0 test delta). |
| pytest net delta ≥ 0 | PASS | 0 delta (no test changes in this sweep). |
| commit pushed | PASS | `f3b04642` on origin/main, force push not used. |

### Test Results

- Tests run (pytest): 4,945 (4,943 + 2 failed)
- Tests passed (pytest): 4,943
- Tests failed (pytest): 2 — `tests/analytics/test_def159_entry_price_known.py::test_get_todays_pnl_excludes_unrecoverable` and `tests/core/test_regime_vector_expansion.py::TestHistoryStoreMigration::test_history_store_migration` (both DEF-163, pre-existing, identical to baseline)
- Tests added / deleted / modified: 0 / 0 / 0
- Command: `python -m pytest --ignore=tests/test_main.py -n auto --tb=no -q`

### Unfinished Work

None. All 8 Phase B sub-items completed and verified.

### Residual Items NOT Swept (intentionally)

These were considered during Stage 1 verification but left in place — each is explained with its deferral target:

1. **FIX-11 M1 / M2 judgment calls** (F1-9 `min_length=1` on ValidateCoverageRequest; F1-15 flat `_LIFESPAN_PHASES` tuple vs. graph). Both accepted at Tier 2 review. No follow-up action required.

2. **`_STANDALONE_SYSTEM_OVERLAYS` silent skip when overlay is not a dict** (FIX-01 review observation). Deferred to FIX-02-overflow-yaml — that session adds the second registry entry and is the natural place to harden the type-check. Priority: LOW.

3. **DEF-170 code fix** (RegimeClassifierV2 VIX calculators inert in production). Deferred to FIX-05-core (natural scope: `argus/core/regime.py` + `argus/core/orchestrator.py`). Logged in CLAUDE.md this session so the fix won't be forgotten. Priority: MEDIUM.

4. **DEF-171 xdist flake** (`test_all_ulids_mapped_bidirectionally`). Deferred to FIX-13-test-hygiene — already on the campaign register, and diagnosing xdist isolation requires a targeted investigation that doesn't belong in a doc sweep. Priority: LOW.

### Notes for Reviewer

- This session strictly observed the docs-only boundary. `git diff --name-only` post-commit showed 7 files, zero of them `argus/*.py` or `config/*.yaml` or `workflow/*`.
- Phase A and Phase C both ran the full pytest suite (`-n auto`). Both produced **identical** 4,943-passed / 2-failed outputs. Zero test delta confirms no behavior change — as expected from a doc-only edit set.
- All Phase B edits were grep-verified against the actual source of truth before editing (python source lines, module filenames, signature strings). The FIX-17 review's `.claude/rules/api-conventions.md` disclaimer ("code wins") was honored — I read `order_manager.py` and used its actual signatures, not the review's paraphrase.
- DEF-170 text includes the verification recipe ("hit `GET /vix/current` in a live boot and confirm non-None classifications") so FIX-05 has a pre-written acceptance criterion.
- DEF-171 text includes a repro strategy (`-p no:xdist` vs. `-n auto` diff) so FIX-13 has a pre-written first investigative step.
- Commit `f3b0464` on origin/main. Force push not used.

---END-CLOSE-OUT---
