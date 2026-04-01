# Sprint 32, Session 4 — Tier 2 Review Report

---BEGIN-REVIEW---

## Summary

Session 4 implements the experiment data model and SQLite-backed registry
store (`ExperimentStore`) as specified. Three new source files and two test
files were created under `argus/intelligence/experiments/` and
`tests/intelligence/experiments/`. No existing files were modified.

## Spec Compliance

| Requirement | Verdict | Notes |
|-------------|---------|-------|
| `ExperimentStatus` StrEnum (8 values) | PASS | All 8 values present |
| `VariantDefinition` frozen dataclass (7 fields) | PASS | Fields match spec |
| `ExperimentRecord` mutable dataclass (11 fields) | PASS | Fields match spec |
| `PromotionEvent` frozen dataclass (10 fields) | PASS | Fields match spec |
| `ExperimentStore.initialize()` — WAL + DDL | PASS | `PRAGMA journal_mode=WAL` on line 132 |
| 3 tables: experiments, variants, promotion_events | PASS | DDL + 7 indexes |
| `save_experiment` / `get_experiment` / `list_experiments` | PASS | INSERT OR REPLACE, filter by pattern_name, limit param |
| `get_baseline` / `set_baseline` (atomic unmark/mark) | PASS | Single connection context for atomicity |
| `save_variant` / `list_variants` / `get_variant` / `update_variant_mode` | PASS | All implemented per spec |
| `save_promotion_event` / `list_promotion_events` | PASS | Filter by variant_id, limit param |
| `enforce_retention` — 3-table sweep, returns count | PASS | Deletes from all 3 tables |
| `close()` — documented no-op | PASS | Per-operation connection pattern |
| Separate DB: `data/experiments.db` | PASS | Default in `_DEFAULT_DB_PATH` |
| JSON serialization (no pickle) | PASS | `json.dumps` / `json.loads` for dicts |
| ULID usage (DEC-026) | PASS | Tests use `generate_id()` from `argus.core.ids`; store accepts pre-generated IDs |
| DEC-345 pattern: WAL, fire-and-forget, rate-limited warnings | PASS | All write methods wrapped in try/except with `_rate_limited_warn` |
| No existing files modified | PASS | `git status` shows only new untracked files |
| Minimum 10 new tests | PASS | 13 tests delivered |

## Session-Specific Review Focus

1. **WAL mode explicitly enabled** — PASS. `await conn.execute("PRAGMA journal_mode=WAL")` in `initialize()` at line 132.

2. **Fire-and-forget pattern** — PASS. All 6 write methods (`save_experiment`, `set_baseline`, `save_variant`, `update_variant_mode`, `save_promotion_event`, `enforce_retention`) use try/except with `_rate_limited_warn()`. Read methods (`get_experiment`, `list_experiments`, `get_baseline`, `list_variants`, `get_variant`, `list_promotion_events`) do NOT have fire-and-forget wrappers, which is correct — read failures should propagate.

3. **Retention enforcement** — PASS. Deletes records from all 3 tables using ISO timestamp comparison against configurable `max_age_days`. Returns total deleted count. Test creates records 120 days old and verifies deletion with 90-day cutoff.

4. **JSON serialization** — PASS. `backtest_result` (dict) serialized via `json.dumps`/`json.loads`. `comparison_verdict` is typed `str | None` on the model — callers pre-serialize; the store writes it directly to the `comparison_verdict_json` column.

5. **ULID usage** — PASS. Tests import and use `generate_id()` from `argus.core.ids` (which calls `str(ULID())`). The store itself does not generate IDs — it accepts pre-generated IDs, consistent with the DEC-026 pattern where callers supply ULIDs.

6. **Separate DB file path** — PASS. Default `_DEFAULT_DB_PATH = "data/experiments.db"`.

## Regression Checklist (Sprint-Level)

| # | Check | Result |
|---|-------|--------|
| R8 | Non-PatternModule strategies untouched | PASS — no modifications to protected files |
| R9 | Test suite passes | PASS — 4,334 passed (full suite) |
| R16 | Orchestrator registration unchanged | PASS — orchestrator.py not touched |

## Findings

**F1 (LOW): Read methods lack fire-and-forget wrappers.** `get_experiment`, `list_experiments`, `get_baseline`, `list_variants`, `get_variant`, and `list_promotion_events` will propagate exceptions to callers. This is the correct design choice — callers need to know when reads fail to avoid acting on stale/missing data. Noting for completeness only; no action needed.

**F2 (LOW): Mutable dict in frozen dataclass.** `VariantDefinition` is `frozen=True` but its `parameters` field is `dict[str, Any]`, which is mutable. Callers could mutate the dict after construction. This is consistent with how the project handles similar patterns elsewhere (e.g., other frozen dataclasses with dict fields) and the spec explicitly requests `frozen=True`. No action needed.

## Escalation Criteria Check

| Criterion | Triggered? |
|-----------|-----------|
| Shadow variants >10% throughput degradation | N/A — no runtime wiring in this session |
| Variant spawning >2x memory increase | N/A — no variant spawning in this session |
| Event Bus contention from 35+ subscribers | N/A — no event bus changes |
| Parameter fingerprint hash collision | N/A — no fingerprint in this session |
| CounterfactualTracker volume handling | N/A — no counterfactual changes |
| Factory fails existing pattern construction | N/A — no factory changes |
| ARGUS fails to start with experiments.enabled: false | N/A — no startup wiring |
| Pre-existing test failure introduced | NO — 4,334 passed |
| YAML param silently ignored | N/A — no config loading in this session |

No escalation criteria triggered.

## Test Results

- Session tests: 13/13 passed (0.12s)
- Full suite: 4,334 passed, 59 warnings (48.75s)
- No pre-existing failures introduced

## Verdict

**CLEAR** — All spec requirements met. DEC-345 pattern correctly followed. No existing files modified. Full test suite green. Two LOW-severity observations documented for completeness; neither requires action.

---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CLEAR",
  "confidence": 0.97,
  "findings_count": 2,
  "findings_by_severity": {
    "critical": 0,
    "high": 0,
    "medium": 0,
    "low": 2
  },
  "escalation_triggered": false,
  "tests_pass": true,
  "test_count_session": 13,
  "test_count_full": 4334,
  "scope_adherence": "EXACT",
  "files_modified_outside_scope": [],
  "spec_items_missing": [],
  "spec_items_partial": [],
  "reviewer_notes": "Clean single-objective session. ExperimentStore follows established DEC-345 patterns faithfully. Per-operation connection model, WAL mode, fire-and-forget writes, rate-limited warnings all verified. 13 tests cover all CRUD paths including retention enforcement and error resilience."
}
```
