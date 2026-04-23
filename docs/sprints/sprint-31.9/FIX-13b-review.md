---BEGIN-REVIEW---

# Tier 2 Review — FIX-13b-test-hygiene-refactors

**Commit:** `4aebeb5` (main, pushed)
**Baseline HEAD:** `0ed59b3` (Stage 8a barrier — FIX-13a complete)
**Date:** 2026-04-23
**Verdict:** **CONCERNS_RESOLVED** (minor nits; the implementer's MINOR_DEVIATIONS self-assessment matches the reviewer's read)

## Scope Compliance — 7 findings + 1 deferral

| Finding | ID | Severity | Verification |
|---|---|---|---|
| F5 | P1-G2-C01 | CRITICAL | `tests/strategies/test_shadow_mode.py:93-97` — real `ArgusSystem(config_dir=Path("/tmp/argus-test-fixture"), dry_run=True, enable_api=False)` invocation. `object.__new__` removed. Independently verified `argus/main.py:126-194` is pure attribute-init (no I/O, all deferred to `start()`). 21/21 shadow_mode tests pass in 0.35s. |
| F7 | P1-G1-L01 | LOW | `tests/integration/historical/` created with `__init__.py` + `README.md` + 6 moved files (sprint2, sprint3, sprint4a, sprint4b, sprint5, sprint13). `ls tests/test_integration_sprint*.py` confirms sprint18/19/20/26 still at top level. 31/31 moved tests pass in 2.73s. README clearly frames the directory as frozen and articulates the sprint13 triage. |
| F8 | P1-G2-M10 | MEDIUM | Linked pair with F7 — same commit. Verified identical. |
| F9 | P1-G1-M04 | MEDIUM | 6 `monkeypatch.setattr(..., "eod_flatten_timeout_seconds", 0.1)` sites at `tests/execution/order_manager/test_core.py:680,734,763,1154,2354` + `test_sprint295.py:384`. `argus/core/config.py:930` still `default=30`. Scoped run of the 6 flatten tests completes in well under 1s (8 related tests in 0.25s; slowest 0.10s each — matches the ≤1s kickoff target and the close-out's 0.79s claim). |
| F11 | P1-G1-M09 | MEDIUM | `tests/execution/order_manager/` contains exactly 14 entries (13 test files + `__init__.py`). `git log --follow` on `test_core.py` traverses back through `test_order_manager.py` (rename history preserved). `Path(__file__).parents[3]` appears 1× in `test_core.py` and 3× in `test_sprint329.py` as claimed. 238/238 tests pass in 5.33s. |
| F18 | P1-G2-L03 | LOW | `git show d9d3fe2 --stat` confirms `tests/api/conftest.py` at exactly `+103 / -226`. `_make_trade` helper at `tests/api/conftest.py:237-273`; rewritten seeded list at :292-357 with 15 `t(...)` calls. Spot-checked 2 seeds (NVDA and MSFT) against the pre-session file at `git show 0ed59b3:tests/api/conftest.py` — all 12 fields match exactly including nested `target_prices` and `timedelta` offsets. 552/552 `tests/api/` tests pass in 29.80s. |
| F21 | P1-G2-M05 | MEDIUM | `argus/data/alpaca_data_service.py:73` adds `monitor_poll_seconds: float = 5.0` (production default preserved). `self._monitor_poll_seconds` is read at **both** line 636 (main loop body) and line 706 (exception-retry path) — `grep "asyncio\.sleep\(5\)"` returns zero matches. `tests/data/test_alpaca_data_service.py` stale-monitor tests run at 0.40s + 0.31s (well under 0.5s target; matches close-out's ~0.7s scoped claim). |
| F23 | P1-G2-L02 | LOW | `grep -c "make_orb_config" tests/strategies/test_orb_breakout.py` = 1 (the fixture's historical-note docstring only). `grep -c "orb_config_factory" tests/strategies/test_orb_breakout.py` = 74 (fixture def + 2 references in `default_orb_config` wrapper + ~35 signature injections + ~35 call sites — shape matches the 35-call migration claim). 37/37 ORB breakout tests pass in 0.05s. |
| F13 | P1-G1-L05 | LOW | Correctly **DEFERRED TO FIX-13c-ai-copilot-coverage** per kickoff. Spec back-annotation confirmed. |

**Scope boundary verification:**
- `git diff 0ed59b3 HEAD -- workflow/` returns zero lines — Universal RULE-018 respected.
- `git diff 0ed59b3 HEAD --name-only | grep "^argus/"` returns exactly one file: `argus/data/alpaca_data_service.py` (F21 production-injection point). No other production code touched.
- Spec back-annotations at `docs/audits/audit-2026-04-21/phase-3-prompts/FIX-13-test-hygiene.md`: Findings 5/7/8/9/11/18/21/23 marked `RESOLVED FIX-13b-test-hygiene-refactors` with commit SHAs; Finding 13 marked `DEFERRED TO FIX-13c-ai-copilot-coverage`; Split Notice header at line 92 references both sibling sessions correctly.

## Regression Checks

| Check | Expected | Actual | Pass |
|-------|----------|--------|------|
| pytest full suite (`-n auto --ignore=tests/test_main.py`) | ≥ 4987 | 4987 | ✅ |
| Vitest full suite | 859 | 859 | ✅ |
| Zero net test count delta | ± 0 | ± 0 | ✅ |
| F9 scoped timing | 64.11s → ~1s | 0.25s (8 flatten tests under `-k flatten_all*` via the broader keyword) | ✅ |
| F21 scoped timing | ~12s → ~1s | stale-monitor class 0.71s total (0.40 + 0.31) | ✅ |
| F18 fixture body LOC | `-123` net | `-123` net (exactly) | ✅ |
| Production `eod_flatten_timeout_seconds` default | 30 | 30 | ✅ |
| Production `monitor_poll_seconds` default | 5.0 | 5.0 | ✅ |
| No `--skip-validation`/`--force` introduced | none | none | ✅ |
| No workflow/ submodule edits | none | none | ✅ |
| All spec findings back-annotated | 9/9 | 9/9 | ✅ |

Full-suite runtime this run: **55.22s** under `-n auto` (close-out reports 56.42s — consistent within xdist worker jitter). This is a ~62s improvement on the pre-FIX-13b scoped picture dominated by F9's 30s/test flatten wait, though the absolute number is not strictly comparable because I did not benchmark 0ed59b3 fresh in this review pass.

## Judgment Calls — Independent Evaluation

1. **F7/F8 sprint13 triage — moved, not deleted. AGREE.**
   The kickoff's "read first, then decide" language explicitly allowed either outcome. Reading the new `README.md` and spot-checking `test_integration_sprint13.py`, the close-out's claim that `TestBrokerSourceConfig` exercises live `BrokerSource`/`IBKRConfig` surfaces is correct — those are still the production types. `TestBrokerSelection` + `TestIBKRBrokerIntegration` are indeed redundant with `tests/execution/test_ibkr_broker.py`, but moving preserves the historical regression-guard character of the file at zero test-runtime cost (the whole directory collects in 2.73s). Delete would have been defensible but move is the lower-risk choice, consistent with RULE-007.

2. **F9 — monkeypatch applied to all 6 tests even though 4 already ran at ~1s via FIX-04. AGREE.**
   The kickoff said "do NOT skip any of the 6 tests." Applying the monkeypatch uniformly regardless of which FIX-04 fixture state already reached them is the literal spec-compliant behavior. The implementer's "kickoff assumed all 6 took 30s; empirically only 2 did" observation is accurate — I confirmed only `test_eod_flatten_closes_all_positions` and `test_eod_flatten_broker_only_positions` are the 30s offenders, both at 0.10s post-monkeypatch. Uniform treatment is also a small future-proofing win: if the shared `config` fixture's `eod_flatten_timeout_seconds=1` ever gets changed, the per-test monkeypatch still anchors these tests at 0.1s.

3. **F23 — callable-returning-fixture pattern, not `default_orb_config.model_copy(update={...})`. AGREE.**
   The kickoff Hazard explicitly allowed either approach. The implementer's reasoning — that `OrbBreakoutConfig.risk_limits` (`StrategyRiskLimits`) and `operating_window` (`OperatingWindow`) are nested Pydantic sub-models, and 6 of 35 call sites update fields inside those sub-models — is correct. The `model_copy(update={...})` approach would require per-site `default.risk_limits.model_copy(update={...})` chaining for those 6 sites, losing the clean kwarg ergonomics of the original `make_orb_config(...)`. The chosen pattern preserves the exact call shape. One minor cost: `default_orb_config` fixture is defined (lines 66-69) but has only its own self-reference in the file (see Nit #2) — a dead fixture, arguably. Not verdict-affecting.

## Nits

- **N1 — residual `make_orb_config` reference in the fixture docstring** (`tests/strategies/test_orb_breakout.py:20`). This is intentionally preserved as a migration breadcrumb per the close-out (§8, note on "in-session Python script"). Future maintainers may find the reference confusing if they grep without reading the surrounding docstring. Acceptable; a future cleanup could tighten the wording to "former module-level helper" without the exact identifier.
- **N2 — `default_orb_config` fixture is declared but unused** (`tests/strategies/test_orb_breakout.py:66-69`). `grep -c "default_orb_config"` = 1 (the declaration itself). Close-out §3 acknowledges this: "`default_orb_config` fixture added but unused for now (call sites with no overrides still use `orb_config_factory()` for consistency)." No verdict impact. A zero-arg call-site rollup to `default_orb_config` would be a natural follow-on but is strictly optional; the consistency argument (every call site uses the same callable) is also defensible.
- **N3 — `tests/execution/order_manager/test_reconciliation.py` still uses deprecated `OrderManager(auto_cleanup_orphans=...)` kwarg** (3 `DeprecationWarning` sites). Pre-existing, tracked in **DEF-176**, correctly out of scope for FIX-13b. Not introduced by this session.
- **N4 — one minor close-out wording drift**: the close-out at §4 lists `tests/execution/order_manager/test_core.py:680-763` as the F9 monkeypatch pointer, but the actual call sites span lines 680, 734, 763, 1154, 2354 (5 in `test_core.py`). The count (5 in `test_core.py` + 1 in `test_sprint295.py` = 6) is correct — just the line-range compression in the table understates. Cosmetic.
- **N5 — `_make_trade` privacy** is well-chosen (leading underscore, file-local scope, documented in close-out §8 that cross-module reuse would require a promoted helper module). Good discipline.

## Escalation Criteria Review

- CRITICAL finding incomplete? F5 is CRITICAL and **RESOLVED**; 21/21 shadow_mode tests pass. No trigger.
- pytest net delta < 0? No (+0). No trigger.
- Scope-boundary violation? No — only `argus/data/alpaca_data_service.py` touched in production (F21 scope), zero workflow/ changes. No trigger.
- Different test failures vs baseline? No — 4987 passing, same as baseline. No trigger.
- Back-annotation missing/incorrect? 9/9 status lines present with correct category + commit SHA. No trigger.
- Rule-4 sensitive file (CLAUDE.md / decision-log.md / architecture.md / risk-register.md / sprint-campaign.md)? None touched. No trigger.
- New DEF opened? None. No trigger.

**No escalation criteria triggered.**

## Verdict

**CONCERNS_RESOLVED.** FIX-13b is a clean pure-refactor session with zero behavior change, zero net test delta, production defaults preserved on both touched surfaces (F21 `monitor_poll_seconds=5.0`, F9 `eod_flatten_timeout_seconds=30`), and disciplined scope boundaries (one production file touched, zero workflow edits). All three documented judgment calls hold up under independent review and are the literal spec-compliant interpretations of kickoff language that explicitly permitted alternatives. The F9 per-test monkeypatch applied uniformly is future-proofing, not over-reach. The F23 callable-fixture pattern is the correct shape for Pydantic configs with nested sub-models.

Self-assessment is **MINOR_DEVIATIONS** because the implementer flagged the three judgment calls where kickoff phrasing and in-session reality diverged; the reviewer agrees the deviations are minor and well-reasoned. CONCERNS_RESOLVED reflects that the flags are documented, the reviewer can confirm each one, and none rise to the level of an unreconciled issue.

Proceed to the Stage 8 Wave 2 barrier update to seal FIX-13b and unblock FIX-13c (AI Copilot coverage expansion, F13 carry-over).

## Follow-on Suggestions (non-blocking)

1. A future test-hygiene pass could drop the unused `default_orb_config` fixture (N2) — either inline it into call sites that currently call `orb_config_factory()` with no args, or delete it. Strictly optional; the "every call site uses `orb_config_factory(...)`" consistency rationale is also valid.
2. If **DEF-176** (`OrderManager(auto_cleanup_orphans=...)` deprecation removal) gets scheduled, the 3 deprecation-warning sites now live at `tests/execution/order_manager/test_reconciliation.py` (post-rename) — the DEF-176 row in CLAUDE.md references the pre-rename path `tests/execution/test_order_manager_reconciliation.py`. A CLAUDE.md DEF-176 path update is a trivial doc-sync follow-on, but not urgent.
3. The in-session Python migration script used for F23 (close-out §8) was not committed. If future sprints want to do similar fixture conversions, capturing that script as a reusable `scripts/dev/` helper could be useful — but only if a second-occurrence warrants it. Premature to lift now.

---END-REVIEW---

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "audit-2026-04-21-phase-3",
  "session": "FIX-13b-test-hygiene-refactors",
  "verdict": "CONCERNS_RESOLVED",
  "commit_reviewed": "4aebeb5",
  "baseline_head": "0ed59b3",
  "tests": {
    "before": 4987,
    "after": 4987,
    "delta": 0,
    "all_pass": true,
    "vitest_before": 859,
    "vitest_after": 859
  },
  "escalation_triggers": {
    "critical_finding_incomplete": false,
    "pytest_net_delta_negative": false,
    "scope_boundary_violation": false,
    "different_test_failures": false,
    "back_annotation_missing": false,
    "rule4_sensitive_file_touched": false,
    "new_def_opened": false
  },
  "findings_accounting": {
    "resolved": 8,
    "deferred_to_fix13c": 1,
    "total": 9,
    "note": "7 finding units (F5, F7+F8 as linked pair, F9, F11, F18, F21, F23) RESOLVED + F13 DEFERRED. Counts match close-out change manifest and spec back-annotations 1:1."
  },
  "scope_violations": [],
  "judgment_calls_evaluated": [
    {"id": "F7F8_sprint13_moved_not_deleted", "verdict": "AGREE", "note": "Kickoff permitted either. TestBrokerSourceConfig genuinely exercises live BrokerSource enum + IBKRConfig defaults; move preserves historical regression value at zero runtime cost."},
    {"id": "F9_monkeypatch_uniform_on_all_6", "verdict": "AGREE", "note": "Kickoff said 'do NOT skip any'. Empirically only 2 of the 6 ran at 30s pre-monkeypatch (4 were already at 1s via FIX-04's fixture override). Uniform treatment is the literal spec compliance and future-proofs against fixture drift."},
    {"id": "F23_callable_fixture_not_model_copy", "verdict": "AGREE", "note": "Kickoff explicitly permitted either. OrbBreakoutConfig has nested StrategyRiskLimits + OperatingWindow sub-models; 6 of 35 call sites update fields inside those sub-models, where model_copy(update=...) would require per-site sub-model chaining. Callable fixture preserves original kwarg ergonomics."}
  ],
  "nits": [
    "Residual 'make_orb_config' in fixture historical-note docstring at test_orb_breakout.py:20 (intentional breadcrumb).",
    "default_orb_config fixture declared but unused (grep -c = 1, self-reference only). Close-out explicitly acknowledges.",
    "Deprecated OrderManager(auto_cleanup_orphans=...) sites in test_reconciliation.py (3 DeprecationWarning) — pre-existing, tracked by DEF-176, out of scope.",
    "Close-out §4 compresses the F9 monkeypatch line-range (680-763) when actual span is 680, 734, 763, 1154, 2354 in test_core.py. Cosmetic."
  ],
  "concerns": [],
  "follow_on_suggestions": [
    "Drop unused default_orb_config fixture OR roll zero-arg call sites onto it — strictly optional.",
    "When DEF-176 is scheduled, update CLAUDE.md DEF-176 row path refs from pre-rename test_order_manager_reconciliation.py to post-rename tests/execution/order_manager/test_reconciliation.py.",
    "F23 in-session Python migration script was not committed; capture in scripts/dev/ only if a second similar conversion warrants it."
  ],
  "notes": "Clean pure-refactor session with zero behavior change. Production defaults preserved (eod_flatten_timeout_seconds=30, monitor_poll_seconds=5.0). One production file touched (argus/data/alpaca_data_service.py, F21 injection point only). Zero workflow/ changes. All three judgment calls are the literal spec-compliant interpretations of kickoff language that explicitly permitted alternatives. Self-assessment MINOR_DEVIATIONS matches reviewer's read.",
  "recommended_next_action": "Proceed to Stage 8 Wave 2 barrier update to seal FIX-13b and unblock FIX-13c (AI Copilot coverage, F13 carry-over)."
}
```
