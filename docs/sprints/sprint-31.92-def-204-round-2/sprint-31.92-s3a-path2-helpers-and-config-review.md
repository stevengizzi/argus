# Tier 2 Review: Sprint 31.92, Session S3a

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any source code files.

Follow the review skill in `.claude/skills/review.md`.

Your review report MUST include a structured JSON verdict at the end,
fenced with ` ```json:structured-verdict `. See the review skill for the full
schema and requirements.

**Write the review report to a file** (DEC-330):

```
docs/sprints/sprint-31.92-def-204-round-2/sprint-31.92-s3a-path2-helpers-and-config-review.md
```

Create the file, write the full report (including the structured JSON
verdict) to it, and commit it. This is the ONE exception to "do not modify
any files" — the review report file is the sole permitted write.

## Pre-Flight

1. **Read `.claude/rules/universal.md` in full and treat its contents as binding for this review.** The full set of universal RULE entries (currently RULE-001 through RULE-053) applies regardless of whether any specific rule is referenced inline in this prompt — particularly **RULE-013** (read-only mode), **RULE-038** (grep-verify factual claims), **RULE-050** (CI green required), **RULE-053** (architectural-seal verification — DEC-385 / DEC-386 / DEF-158 sealed; the new helpers are SIBLINGS to DEC-386's `_is_oca_already_filled_error`, not modifications).

## Review Context

Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist (34 invariants), and Sprint-Level Escalation Criteria:

```
docs/sprints/sprint-31.92-def-204-round-2/review-context.md
```

## Tier 1 Close-Out Report

Read the close-out report from:

```
docs/sprints/sprint-31.92-def-204-round-2/sprint-31.92-s3a-path2-helpers-and-config-closeout.md
```

(Per RULE-038, grep-verify the actual closeout filename if not present at the expected path — the corresponding impl prompt references `session-3a-closeout.md` as a candidate alternative. If neither file exists, flag as CONCERNS — the close-out report is required for review.)

## Review Scope

- **Diff to review:** `git diff HEAD~1` (or specify the correct range if the close-out cites multiple commits).
- **Test command** (non-final session, scoped per DEC-328):
  ```
  python -m pytest tests/execution/order_manager/ tests/execution/test_ibkr_broker.py -n auto -q
  ```
  Plus the config-validation test path under `tests/core/`:
  ```
  python -m pytest tests/core/ -n auto -q
  ```
- **Files that should NOT have been modified:**
  - `argus/execution/ibkr_broker.py::_is_oca_already_filled_error`, `_OCA_ALREADY_FILLED_FINGERPRINT`, `place_bracket_order` (DEC-386 — the new helpers are SIBLINGS, not modifications).
  - `argus/execution/order_manager.py::_handle_oca_already_filled` (DEC-386 S1b).
  - `argus/execution/order_manager.py::_trail_flatten` (S2a's surface).
  - `argus/execution/order_manager.py::_resubmit_stop_with_retry`, `_escalation_update_stop` (S2b's surfaces).
  - `argus/execution/order_manager.py::reconstruct_from_broker` (Sprint 31.94 D1 surface).
  - `argus/execution/order_manager.py::reconcile_positions` (DEC-385 L3 + L5).
  - `argus/execution/order_manager.py::_check_flatten_pending_timeouts` (DEF-158 3-branch side-check, lines ~3424–3489).
  - `argus/execution/order_manager.py::_check_sell_ceiling`, `_reserve_pending_or_fail` (S4a-i).
  - `argus/execution/order_manager.py::_flatten_position` and other emit sites (S3b's surface — helpers exist but are NOT yet consumed by emit-site code).
  - `argus/main.py` — entire file (Sprint 31.94 D1+D2 surfaces).
  - `argus/models/trading.py`.
  - `argus/execution/alpaca_broker.py` (Sprint 31.95 retirement scope).
  - `argus/data/alpaca_data_service.py`.
  - `argus/core/health.py`.
  - `argus/core/config.py::IBKRConfig` (no changes this session).
  - `argus/ui/`, `frontend/` (Vitest must remain at 913).
  - `workflow/` submodule (Universal RULE-018).

## Session-Specific Review Focus

1. **AC2.1 — `_LOCATE_REJECTED_FINGERPRINT` value verbatim from S1b JSON.** Verify the constant's value matches `scripts/spike-results/spike-def204-round2-path2-results.json` `fingerprint_string` field exactly, including case + whitespace. The substring match is case-insensitive at runtime per AC2.1, but the constant should be stored exactly as captured for forensic clarity. The close-out's "S1b Spike Output Consumed" section must cite the exact value. Reference pattern: DEC-386's `_OCA_ALREADY_FILLED_FINGERPRINT` placement and shape.

2. **Helper placement parity with DEC-386.** Verify `_LOCATE_REJECTED_FINGERPRINT` + `_is_locate_rejection` are placed adjacent to (typically immediately after) `_OCA_ALREADY_FILLED_FINGERPRINT` + `_is_oca_already_filled_error` in `argus/execution/ibkr_broker.py`. **Module scope, NOT inside a class.** Per RULE-053, DEC-386's pattern is sealed; the new siblings must mirror — not modify — the seal.

3. **AC2.2 — position-keyed (NOT symbol-keyed) suppression dict via `time.monotonic()` per H-R3-1.** Per Round-1 H-2 + regression invariant 14 specific edges:
   - `_locate_suppressed_until` keys are `position.id` (ULID per DEC-026), NOT `position.symbol`. Type annotation: `dict[ULID, float]`.
   - The helper accesses `position.id` (not `position.symbol`). Cross-position safety on the same symbol is the load-bearing property.
   - Suppression deadlines are stored in `time.monotonic()` units, NOT `time.time()`. The helper signature accepts `now: float` representing `time.monotonic()`, AND the docstring explicitly cites monotonic-time semantics. Verify test 4 uses `time.monotonic()` to construct both deadlines and the `now` argument.

4. **4 OrderManagerConfig fields' Pydantic validators (per Decision 4 + S1b spike value baked).** Verify the 4 new fields:
   - `locate_suppression_seconds`: `Field(ge=300, le=86400)`; default matches S1b spike's `recommended_locate_suppression_seconds` value (cross-check against the JSON). Footnote: bounds in monotonic time per H-R3-1.
   - `long_only_sell_ceiling_enabled`: `default=True` — fail-closed.
   - `long_only_sell_ceiling_alert_on_violation`: `default=True`.
   - `pending_sell_age_watchdog_enabled`: `Literal["auto", "enabled", "disabled"]` with `default="auto"` per Decision 4.

5. **YAML→Pydantic alignment + silent-drop class.** Verify the new test asserts YAML keys under `order_manager.*` are a subset of `OrderManagerConfig.model_fields.keys()`. Mental-revert: temporarily add a typo'd YAML key (e.g., `locate_supression_seconds` — note misspelling); the test should FAIL. The reviewer can request the close-out cite the mental-revert verification. The close-out's "YAML Overlay Path" section must document the actual YAML file path used for `pending_sell_age_watchdog_enabled` (in case the project's convention diverged from `config/order_manager.yaml`).

6. **No emit-site wiring (S3b's surface).** Verify the diff in `argus/execution/order_manager.py` does NOT touch any of `_flatten_position`, `_trail_flatten`, `_check_flatten_pending_timeouts`, or `_escalation_update_stop` exception handlers. The helpers exist but are NOT yet consumed by emit-site code; that's S3b.

7. **No production code touches `_check_sell_ceiling` or `_reserve_pending_or_fail`** (S4a-i's surface). Verify the diff does NOT add either method, even as a stub.

8. **DEC-386 surfaces unchanged.** Verify `_is_oca_already_filled_error` and `_OCA_ALREADY_FILLED_FINGERPRINT` are byte-for-byte unchanged. `git diff HEAD~1 -- argus/execution/ibkr_broker.py` should show only ADDITIONS, no MODIFICATIONS to existing helpers. Per RULE-053, the DEC-386 architectural seal must remain intact — the new helpers are siblings, not relocations.

9. **Close-out's "Helpers Established for S3b" section** must list the new helpers (`_is_locate_rejection`, `_is_locate_suppressed`) with their signatures, so S3b can wire them into the 4 standalone-SELL paths without re-discovering the helper shape.

## Additional Context

This session establishes the Path #2 detection primitives (the substring fingerprint helper + the position-keyed suppression dict) and adds 4 new `OrderManagerConfig` fields. The fingerprint string and seconds default are data-driven from S1b's JSON artifact. S3a is the first session where the per-position granularity (NOT per-symbol) is encoded; cross-position safety on the same symbol is the load-bearing property regression invariant 14 establishes here.

The full Sprint-Level Regression Checklist (34 invariants) is in `docs/sprints/sprint-31.92-def-204-round-2/regression-checklist.md`. S3a is ✓-mandatory for invariants **5, 6, 8, 9, 10, 11, 12, 14** (ESTABLISHES) and ✓ for invariant **26** (NEW per Decision 4 — AC2.7 watchdog Pydantic validation; field addition only at S3a).

The full Sprint-Level Escalation Criteria are in `docs/sprints/sprint-31.92-def-204-round-2/escalation-criteria.md`. Most relevant to S3a: A-class halts **A2** (S1b INCONCLUSIVE — pre-empted by Pre-Flight #6, defensive), **A4** (DEC-385/386/388 surface modified), **A6** (CONCERNS/ESCALATE verdict); B-class halts **B1**, **B3**, **B4**, **B5** (anchor mismatch), **B6** (do-not-modify file in diff), **B8** (frontend modified), **B9** (`release_p99_seconds > 86400` — pre-empted, defensive); C-class halts **C1**, **C5** (do-not-modify boundary uncertainty), **C8** (S1b JSON schema deviation), **C10** (curated list <5 symbols OR no rejections — H6 RULES-OUT path; NOT a halt).
