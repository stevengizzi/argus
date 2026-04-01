# Sprint 32, Session 3: Runtime Wiring — Tier 2 Review

---BEGIN-REVIEW---

## Summary

Session 3 replaces hardcoded pattern constructors in `main.py` and `PatternBacktester` with the generic factory from Session 2, wires parameter fingerprints onto `PatternBasedStrategy`, and adds the `config_fingerprint` column to the `trades` table schema. The implementation matches the spec closely with no scope creep and no behavioral changes to existing strategies.

## Change Manifest Verification

| Spec Requirement | Delivered | Status |
|-----------------|-----------|--------|
| 7 pattern constructions in main.py use factory | Yes -- all 7 `XxxPattern()` calls replaced with `build_pattern_from_config()` | PASS |
| Remove direct pattern class imports from main.py | Yes -- `from argus.strategies.patterns import ...` line removed | PASS |
| PatternBacktester supports all 7 patterns (DEF-121) | Yes -- `_create_pattern_by_name` delegates to `_load_pattern_config` + factory | PASS |
| trades table has config_fingerprint column (nullable) | Yes -- DDL updated + idempotent ALTER TABLE migration | PASS |
| PatternBasedStrategy has config_fingerprint attribute | Yes -- `_config_fingerprint` attr + `config_fingerprint` property | PASS |
| Fingerprint set after construction in main.py | Yes -- `compute_parameter_fingerprint()` called for all 7 strategies | PASS |
| Trade model carries fingerprint | Yes -- `config_fingerprint: str | None = None` on Trade model | PASS |
| TradeLogger persists fingerprint | Yes -- INSERT column list + `_row_to_trade` deserialization updated | PASS |
| New tests (min 8) | 33 tests in test_runtime_wiring.py (9 logical, 33 parametrized) | PASS |
| Close-out report | Written | PASS |

## Protected File Check

| File | Modified? | Status |
|------|-----------|--------|
| `argus/core/orchestrator.py` | No | PASS |
| `argus/strategies/orb_breakout.py` | No | PASS |
| `argus/strategies/orb_scalp.py` | No | PASS |
| `argus/strategies/vwap_reclaim.py` | No | PASS |
| `argus/strategies/afternoon_momentum.py` | No | PASS |
| `argus/strategies/red_to_green.py` | No | PASS |
| `argus/ui/` (any frontend file) | No | PASS |
| `argus/intelligence/learning/` | No | PASS |
| `argus/intelligence/counterfactual.py` | No | PASS |

## Session-Specific Focus Items

### 1. main.py pattern imports removed
**PASS.** The line `from argus.strategies.patterns import ABCDPattern, BullFlagPattern, DipAndRipPattern, FlatTopBreakoutPattern, GapAndGoPattern, HODBreakPattern, PreMarketHighBreakPattern` is confirmed removed. Replaced with `from argus.strategies.patterns.factory import build_pattern_from_config, compute_parameter_fingerprint, get_pattern_class`.

### 2. _create_pattern_by_name handles all 7 patterns
**PASS.** The old 3-pattern if/elif chain (bull_flag, flat_top_breakout, abcd) replaced with `_load_pattern_config()` helper mapping all 7 snake_case names to their `load_*_config()` functions + factory delegation. DEF-121 resolved.

### 3. Fingerprint column is nullable
**PASS.** Schema DDL: `config_fingerprint TEXT` (no NOT NULL). Migration: idempotent `ALTER TABLE trades ADD COLUMN config_fingerprint TEXT`. Trade model: `config_fingerprint: str | None = None`. Test `test_historical_trade_without_fingerprint_queryable` confirms backward compatibility.

### 4. pattern_strategy.py change is minimal
**PASS.** Only two additions: `self._config_fingerprint: str | None = None` in `__init__` and a `config_fingerprint` property (6 lines including docstring). No behavioral change.

### 5. No behavioral change to signal generation
**PASS.** The factory constructs patterns with the same detection parameters extracted from the same Pydantic configs. The only difference is that construction goes through `build_pattern_from_config()` instead of direct `XxxPattern()` calls. The factory tests verify that default-config construction produces equivalent pattern instances.

## Test Results

- **Scoped tests:** 61/61 passed (33 runtime wiring + 28 factory tests) in 0.10s
- **Full suite:** 4321 passed, 0 failures in 61.03s

## Regression Checklist

| # | Check | Result |
|---|-------|--------|
| R1 | All 12 strategies instantiate | PASS (4321 tests pass) |
| R3 | Defaults unchanged | PASS (factory tests verify default construction) |
| R4+R5 | Backtester supports all 7 | PASS (7 parametrized tests) |
| R8 | Non-PatternModule files untouched | PASS (git diff confirms) |
| R9 | Test suite passes | PASS (4321 passed, 0 failures) |
| R14 | Fingerprint deterministic | PASS (dedicated test) |
| R15 | trades migration backward compat | PASS (dedicated test) |
| R16 | Orchestrator unchanged | PASS (not in diff) |

## Escalation Criteria Check

| Criterion | Triggered? |
|-----------|-----------|
| Shadow variants >10% throughput degradation | N/A (no shadow variants in this session) |
| >2x memory at startup | No (factory adds negligible overhead) |
| Event Bus contention from 35+ subscribers | No |
| Fingerprint hash collision | No (SHA-256 truncated to 16 hex = 64 bits; collision space adequate for experiment scale) |
| Factory fails to construct existing pattern | No (7/7 pass) |
| ARGUS fails to start with experiments.enabled: false | N/A (config gate not introduced this session) |
| Pre-existing test failure introduced | No (0 failures) |
| YAML param silently ignored | No (factory extracts via PatternParam introspection) |

## Findings

### F1 (Low) -- Combined S2+S3 commit with misleading message
The commit `69c8745` is titled "feat(patterns): Sprint 32 S2 -- generic pattern factory + fingerprint" but contains all Session 3 deliverables (main.py wiring, vectorbt_pattern.py refactor, trade_logger, schema, manager, trading model, pattern_strategy, test_runtime_wiring.py, plus Session 2 closeout/review docs). This means Session 2 and Session 3 changes are not independently revertable. The commit message should reference S3 as well. Process issue only; no code impact.

### F2 (Low) -- `type: ignore[arg-type]` in vectorbt_pattern.py
The `_load_pattern_config` helper returns `object` (to avoid a union of 7 config types), requiring `# type: ignore[arg-type]` when passed to `build_pattern_from_config(config, name)` which expects `StrategyConfig`. This is documented in the close-out report as a judgment call. The runtime behavior is correct. A `Protocol` or `Union` type could restore type safety but adds complexity for minimal benefit in this internal helper.

### F3 (Low) -- Fingerprint not yet wired into trade close path
The close-out report correctly notes that the Order Manager does not yet carry the fingerprint from `PatternBasedStrategy._config_fingerprint` to the `Trade` object at close time. The column, model field, and TradeLogger INSERT are in place but will produce NULL until a future session wires the end-to-end path. This is explicitly deferred and documented.

## Verdict

All spec requirements met. All tests pass. Protected files untouched. No behavioral changes to existing strategies. Three low-severity findings (process, typing, incomplete wiring) all documented and none blocking.

---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CLEAR",
  "findings": [
    {
      "id": "F1",
      "severity": "low",
      "category": "process",
      "description": "Combined S2+S3 commit with misleading message -- commit 69c8745 titled 'S2' contains all S3 deliverables. Sessions not independently revertable.",
      "recommendation": "Use separate commits per session or include both session numbers in message."
    },
    {
      "id": "F2",
      "severity": "low",
      "category": "type-safety",
      "description": "_load_pattern_config returns object, requiring type: ignore[arg-type] in _create_pattern_by_name.",
      "recommendation": "Consider a Union type or Protocol if more callers emerge."
    },
    {
      "id": "F3",
      "severity": "low",
      "category": "incomplete-wiring",
      "description": "config_fingerprint column and model field in place but Order Manager does not yet populate it on trade close. All trades will have NULL fingerprint until future session.",
      "recommendation": "Already documented as deferred in close-out. Wire in experiment registry session."
    }
  ],
  "tests_passed": 4321,
  "tests_failed": 0,
  "new_tests": 33,
  "escalation_triggers": [],
  "regression_checklist_passed": true
}
```
