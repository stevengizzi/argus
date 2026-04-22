# FIX-01-catalyst-db-quality-pipeline — Close-Out Report

> Tier 1 self-review produced per `workflow/claude/skills/close-out.md`.
> Paste the fenced block below into the Work Journal on Claude.ai.

```markdown
---BEGIN-CLOSE-OUT---

**Session:** audit-2026-04-21-phase-3 — FIX-01-catalyst-db-quality-pipeline
**Date:** 2026-04-21
**Self-Assessment:** MINOR_DEVIATIONS

### Pivot Disclosure

The original FIX-01 session ran through every finding, landed a complete
implementation under **Option A** (sync `quality_engine.yaml` values into
`system.yaml` + `system_live.yaml`), and produced a FLAGGED close-out that
erroneously concluded "every edit was reverted turn-by-turn." That
conclusion was wrong. The work was intact in `git stash@{0}` (label
`fix01-wip-while-fix20-commits`, 10 files) plus 4 untracked new files on
disk. The "revert" system-reminders were cross-session write-races from a
parallel kickoff of FIX-00/15/17/20.

This recovery session operates under the operator's explicit **Option A →
Option B pivot** per the Work Journal Handoff: instead of syncing values,
`load_config()` now deep-merges registered standalone YAMLs over the
system block with precedence `standalone > live > base`. New **DEC-384**
codifies the pattern. `config/quality_engine.yaml` becomes the
authoritative file for quality weights + thresholds; the `quality_engine`
blocks in `system.yaml` / `system_live.yaml` remain as-is (untouched by
FIX-01) and are now documentation / fallback. FIX-02 extends
`_STANDALONE_SYSTEM_OVERLAYS` to cover `overflow.yaml` with one
tuple-entry — no new load logic.

### Stash Reconstruction Path

- Cherry-picked 7 tracked-file edits from `stash@{0}` via
  `git checkout stash@{0} -- <paths>`: `counterfactual.py`,
  `counterfactual_store.py`, `promotion.py`, `quality_engine.py`,
  `startup.py`, `main.py`, `tests/intelligence/test_quality_engine.py`.
- Deliberately **skipped** `config/system.yaml` and `config/system_live.yaml`
  (Option A syncs — now superseded).
- Deliberately **skipped** `.claude/rules/sprint_14_rules.md` (stash
  held an `A` entry for it because the stash was captured before FIX-17's
  `git mv` landed in `451b444`; `rm`ed the untracked orphan).
- 4 untracked new files from the original session were already on disk
  and carried forward unchanged: `scoring_fingerprint.py`,
  `tests/intelligence/test_scoring_fingerprint.py`,
  `tests/test_fix01_catalyst_db_path.py`, and the Option-A-era
  `tests/test_fix01_quality_yaml_parity.py` — the last one was
  `rm`ed and replaced by `tests/test_fix01_load_config_merge.py`
  (6 tests for the new merge semantics).
- Stash dropped after successful push.

### Mental-Model Correction

The original session's FLAGGED conclusion was wrong. Indicators that
should have been decisive earlier and were missed:

- The four new files (`scoring_fingerprint.py`, two test files, and the
  parity test) had recent mtimes and the `.pyc` cache for the fingerprint
  module existed in `__pycache__/` — pytest had imported the module
  successfully at Step 1G.
- `git stash list` / `git stash show --name-status stash@{0}` would have
  surfaced the ten-file stash.
- Every `system-reminder` message said the file "was modified, either by
  the user or by a linter" and instructed "don't revert it unless the
  user asks you to" — which meant the file was being kept in a state the
  environment wanted, not that my edits were disappearing.

Treating those reminders as evidence of reverts, rather than cross-session
writes, was the incorrect inference. Recovered in this session by
verifying the stash + untracked files against the directive and
reconstructing the state deterministically.

### Change Manifest

| File | Change Type | Rationale |
|------|-------------|-----------|
| `argus/intelligence/scoring_fingerprint.py` | **new** | Step 1A — `compute_scoring_fingerprint()` over weights + thresholds + risk_tiers; mirrors `compute_parameter_fingerprint()` (SHA-256 canonical JSON → first 16 hex). |
| `argus/intelligence/counterfactual_store.py` | modified | Step 1B — idempotent `ALTER TABLE ... ADD COLUMN scoring_fingerprint TEXT` migration; INSERT SQL updated; `scoring_fingerprint: str \| None` filter on `query()`. |
| `argus/intelligence/counterfactual.py` | modified | Step 1C+1D — `scoring_fingerprint` field on `CounterfactualPosition` + `_OpenPosition` (defaults `None`); `quality_config: QualityEngineConfig \| None` kwarg on `CounterfactualTracker.__init__` with startup INFO log; fingerprint computed per-call in `track()` and threaded through open + close snapshots. |
| `argus/intelligence/startup.py` | modified | Step 1D — `build_counterfactual_tracker` plumbs `config.quality_engine` into the tracker, gated via `isinstance(raw, QualityEngineConfig)` so MagicMock test configs don't crash the fingerprint path. |
| `argus/intelligence/experiments/promotion.py` | modified | Step 1E — optional `scoring_fingerprint: str \| None = None` kwarg on `evaluate_all_variants`, `_evaluate_for_promotion`, `_build_result_from_shadow`, `_count_shadow_trading_days`; default behaviour (no filter) unchanged. |
| `argus/main.py` | modified | Finding 6/7 / DEF-082 / P1-D1 C1 — Phase 10.25 `CatalystStorage` constructed against `catalyst.db` (12,114 catalysts) instead of `argus.db` (0 rows). |
| `argus/intelligence/quality_engine.py` | modified | Finding 8 / P1-D1-L01 — `_score_historical_match()` hardened `50.0 → 0.0`; dormancy comment explaining why the dimension is a strict no-op. |
| `argus/core/config.py` | modified | DEC-384 / Option B — new module-scope `_STANDALONE_SYSTEM_OVERLAYS` tuple; `load_config()` deep-merges registered standalone YAMLs (`quality_engine.yaml` as first entry) over the system block via existing `deep_update()`; INFO log enumerates merged sections. Also added `import logging` + `logger`. |
| `tests/intelligence/test_quality_engine.py` | modified | Existing `test_historical_match_returns_50` renamed to `test_historical_match_returns_dormant_zero` asserting `0.0`; full-pipeline test expected score `69.0 → 59.0`, grade `B+ → B` for the new stub contract. |
| `tests/intelligence/test_scoring_fingerprint.py` | **new** | 4 tests (stability, sensitivity, round-trip persistence, PromotionEvaluator filter). |
| `tests/test_fix01_catalyst_db_path.py` | **new** | Grep-guard asserting Phase 10.25 uses `catalyst.db` not `argus.db`. |
| `tests/test_fix01_load_config_merge.py` | **new** | 6 tests: baseline read, standalone override, missing-standalone fallback, standalone-only key preserved, live-only key preserved, overlay registry contains `quality_engine`. |
| `tests/test_fix01_quality_yaml_parity.py` | **removed** (never tracked) | Option A artifact. Replaced by `test_fix01_load_config_merge.py`. |
| `docs/decision-log.md` | modified | DEC-384 entry + footer updated to `Next DEC: 385`, `Last updated: 2026-04-21 (FIX-01 audit 2026-04-21 — DEC-384 load_config standalone overlay / Option B)`. |
| `docs/dec-index.md` | modified | Count 383 → 384; DEC-384 entry under Sprint 31.75 block. |
| `docs/audits/audit-2026-04-21/phase-2-review.csv` | modified | 9 rows back-annotated with `**RESOLVED FIX-01-catalyst-db-quality-pipeline**` (P1-D1-C01/C02/L01, DEF-082, DEF-142, H2-D01/D02/D03/DEAD05). |
| `docs/audits/audit-2026-04-21/p1-d1-catalyst-quality.md` | modified | `## FIX-01 Resolution` footer covering C1 / C2 / L1. C3 (overflow) explicitly deferred to FIX-02 under the same DEC-384 pattern. |
| `docs/audits/audit-2026-04-21/p1-h2-config-consistency.md` | modified | `## FIX-01 Resolution` footer covering D-01 / D-02 / D-03 / DEAD05. |
| `CLAUDE.md` | modified | Header "Last updated" bumped; `FIX-01-catalyst-db-quality-pipeline` entry under Active Sprint summarising the fix, DEC-384, regression guards; DEF-082 + DEF-142 rows flipped to strikethrough with `**RESOLVED** (audit 2026-04-21 FIX-01-catalyst-db-quality-pipeline)` context. |
| `.claude/rules/sprint_14_rules.md` | **removed** | Orphan. FIX-17 (commit `451b444`) deleted it from HEAD; the untracked copy on disk was a leftover from the stash-capture moment. `rm`ed in Phase B before Phase C cherry-picks. |

### Judgment Calls

- **Option B `_STANDALONE_SYSTEM_OVERLAYS` shape.** Chose a module-scope
  tuple of `(section_key, filename)` pairs rather than a dict or a
  Pydantic setting because it's dead-simple, immutable, and the
  extension-site (FIX-02) is a one-line tuple addition. The alternative
  (a registration decorator or auto-discovery) would be heavier for
  exactly two overlays.
- **Validate via `isinstance(overlay, dict)` before merge.** Top-level
  YAML *can* be a list or a scalar. The implementation silently skips
  non-dict overlays with no error — consistent with `load_yaml_file()`'s
  `return data if data is not None else {}` posture for empty files.
- **Fingerprint infra `isinstance` gate in `startup.py`.** The hook
  `getattr(config, "quality_engine", None)` returns a `MagicMock` when
  tests pass a `MagicMock()` SystemConfig (counterfactual wiring tests
  do exactly this), which then crashes `.weights.model_dump()`.
  `isinstance(raw_qe, QualityEngineConfig)` narrows the type cleanly —
  real configs produce fingerprints, test mocks don't. Documented in the
  code comment so a reviewer sees the rationale without needing the test
  file open.
- **CLAUDE.md DEF rows for DEF-082 + DEF-142 struck through.** Per project
  doc-sync convention (resolved DEFs use `~~strikethrough~~` with
  `**RESOLVED** (context)` so history + number-reuse protection both
  survive).
- **Did NOT delete `config/quality_engine.yaml` even though H2-DEAD05
  flagged it "dead."** Under Option B it's authoritative, not dead.
  Explicitly noted in the p1-h2 footer.
- **Audit-report back-annotation as footers rather than per-row edits.**
  The p1-d1 and p1-h2 reports have large finding tables; appending a
  `## FIX-01 Resolution` section at end-of-file is cleaner than 9+
  per-row edits, matches sibling FIX-17 style, and preserves the
  original audit text intact for history.
- **Sibling FIX-00/15/17 closeout + review reports in
  `docs/sprints/sprint-31.9/` intentionally NOT staged.** Those are
  sibling sessions' deliverables, outside FIX-01 scope per the directive's
  "nothing outside FIX-01 scope should be staged" sanity check.

### Scope Verification

| Spec Requirement | Status | Implementation |
|------------------|--------|----------------|
| Phase A orient — HEAD, stash, disk | DONE | HEAD `d8738ab` (one ahead of `9737e52` with sibling FIX-20 docs commit, benign). Stash label matched, 10 files as expected, 12 GB disk free. |
| Phase B orphan removed | DONE | `rm .claude/rules/sprint_14_rules.md` (3,651 bytes, confirmed gone). |
| Phase C cherry-pick | DONE | 7 files checked out from `stash@{0}`; Option A YAMLs skipped; sanity greps all passed (`compute_scoring_fingerprint` ≥ 1, `scoring_fingerprint` = 11 in counterfactual.py, `catalyst.db` present at Phase 10.25, `return 0.0` present in `_score_historical_match`). |
| Phase D fingerprint checkpoint | DONE | 4 passed, 0 failed. |
| Phase E Option B implemented | DONE | `_STANDALONE_SYSTEM_OVERLAYS` module-scope, `load_config()` extended, INFO log enumerates merged sections, `deep_update()` reused. |
| Phase F merge tests | DONE | `test_fix01_load_config_merge.py` — 6 tests covering baseline, override, fallback, standalone-only key, live-only key, registry sanity. |
| Phase G DEC-384 + index | DONE | Full decision entry written (Context / Decision / Alternatives / Rationale / Impact / Cross-References / Status); footer incremented; index count 383→384. |
| Phase H audit back-annotation | DONE | 9 CSV rows, 2 audit markdown footers, CLAUDE.md (DEF-082 + DEF-142 strikethrough + Active Sprint entry). |
| Phase I full suite | PASS | **4,947 passed / 0 failed** in 144.9s. Net delta vs directive baseline 4,933: **+14**. No DEF-150 flake surfaced. |
| Phase J commit + push | DONE | `59bb100 audit(FIX-01): catalyst DB + quality pipeline + scoring fingerprint + Option B load_config merge`. Pushed to `origin/main`. |
| Phase K stash drop | DONE | `stash@{0}` (FIX-01 WIP) dropped. Working tree clean except for sibling FIX-00/15/17 report files (out of scope). |

### Regression Checks

| Check | Result | Notes |
|-------|--------|-------|
| pytest net delta >= +8 vs 4,933 baseline | PASS | 4,947 passed; net +14. |
| Only pre-existing failure is DEF-150 (or absent) | PASS | 0 failures this run; DEF-150 minute-0/1 window wasn't hit. |
| No file outside FIX-01 scope staged in the commit | PASS | 18 files staged; all within declared scope. Sibling FIX-00/15/17 report files remained untracked. |
| Audit report back-annotation applied | PASS | CSV (9 rows), p1-d1 report footer, p1-h2 report footer, CLAUDE.md (DEF-082 + DEF-142). |
| DEF closures recorded in CLAUDE.md | PASS | DEF-082 and DEF-142 struck through with `**RESOLVED** (audit 2026-04-21 FIX-01-catalyst-db-quality-pipeline)`. |
| New DEC recorded | PASS | DEC-384 in `decision-log.md` + `dec-index.md`; referenced in commit message. |
| Fingerprint checkpoint clean before Option B work | PASS | 4 tests green at Phase D; no Option B code touched until after. |
| Scope-boundary discipline | PASS | No edits to `argus/execution/`, `argus/data/`, `argus/strategies/`, `ui/`, or `config/system{,_live}.yaml`. Workflow submodule pointer untouched. |

### Context State

**GREEN.** Recovery session ran cleanly end-to-end. Phase-by-phase
progression with explicit checkpoints kept context scoped to the current
step. No compaction observed.

### Deferred Observations

None outside the already-tracked FIX-02 follow-up. No new DEFs opened.

### Next Steps

- FIX-02 (`overflow.yaml` / P1-D1-C03) is now a one-tuple-entry extension
  of `_STANDALONE_SYSTEM_OVERLAYS` — no new load logic, no new parametric
  tests for the load path itself. Any FIX-02 session should inherit the
  Phase-E pattern verbatim.
- The scoring-context fingerprint is now wired end-to-end but shadow
  positions accumulated before this commit carry `scoring_fingerprint =
  NULL`. PromotionEvaluator's default behaviour (no fingerprint filter)
  preserves legacy aggregation; operators can pass a fingerprint
  explicitly to scope comparisons to post-fix data once a meaningful
  volume accumulates.

---END-CLOSE-OUT---
```

```json:structured-closeout
{
  "session_id": "FIX-01-catalyst-db-quality-pipeline",
  "sprint": "audit-2026-04-21-phase-3",
  "self_assessment": "MINOR_DEVIATIONS",
  "context_state": "GREEN",
  "baseline_tests_passed": 4933,
  "post_tests_passed": 4947,
  "post_tests_failed": 0,
  "net_delta_passed": 14,
  "net_delta_failed": 0,
  "commit_sha": "59bb100",
  "commit_pushed": true,
  "reviewer_invoked": false,
  "findings_resolved": [
    "P1-D1-C01",
    "P1-D1-C02",
    "P1-D1-L01",
    "H2-D01",
    "H2-D02",
    "H2-D03",
    "H2-DEAD05",
    "DEF-082",
    "DEF-142"
  ],
  "findings_deferred_to_follow_up": [
    "P1-D1-C03 (overflow.yaml divergence — FIX-02, one-tuple extension of _STANDALONE_SYSTEM_OVERLAYS)"
  ],
  "new_decs": ["DEC-384"],
  "new_defs": [],
  "operator_choice": "B (load_config() deep-merges standalone config/<name>.yaml over system block, precedence standalone > live > base)",
  "pivot_disclosure": "Original session implemented Option A (value sync into system*.yaml) and produced a FLAGGED close-out incorrectly concluding edits were reverted. Recovery session confirmed work was intact in git stash@{0} + untracked files, pivoted to Option B per operator handoff, discarded Option A YAML syncs, rewrote parity test as merge test, and landed DEC-384.",
  "regression_check_results": {
    "pytest_net_delta_at_least_8": "PASS",
    "only_def_150_flake_or_no_failures": "PASS",
    "scope_boundary_respected": "PASS",
    "audit_back_annotation": "PASS",
    "claudemd_def_closures": "PASS",
    "new_dec_recorded": "PASS",
    "fingerprint_checkpoint_before_option_b": "PASS"
  }
}
```
