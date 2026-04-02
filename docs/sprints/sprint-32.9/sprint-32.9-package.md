# Sprint 32.9: Operational Hardening + Position Safety + Quality Recalibration

**Type:** Impromptu (post-market debrief findings)
**Priority:** HOTFIX — must complete before April 3 market open
**Predecessor:** Sprint 32.8 (Arena Latency + UI Polish Sweep)
**Active sprint:** 31A (Pattern Expansion III — paused, not yet started)
**Test baseline:** ~4,539 pytest + 846 Vitest (0 failures)

---

## Root Cause Discovery

**The `"qty"` vs `"shares"` attribute mismatch** is the single root cause of both DEF-139 (startup zombie flatten not draining) and the DEF-140 Pass 2 failure (broker-only positions never closed at EOD). The Position model uses `shares` but two code paths in `order_manager.py` read `getattr(pos, "qty", 0)`, which always returns 0:

1. **Line ~1627 (reconstruction):** Every zombie position hits the `abs(qty) <= 0` guard → "Skipping flatten for zero-quantity position" (DEBUG) → counted as "handled" but never flattened or queued. The "44 zombies handled" log was misleading — zero were actually processed.

2. **Line ~1499 (EOD Pass 2):** Every broker-only position has `qty=0` → fails `if qty > 0` → silently skipped. Pass 2 has been broken since Sprint 29.5 when it was added.

Fixing `"qty"` → `"shares"` in these two locations resolves the core mechanism for both DEFs.

---

## Scope

Fix the EOD flatten cascade, add permanent position safety infrastructure, recalibrate the quality engine, triage the worst-performing strategies into shadow mode, and enable the experiment pipeline for future parameter optimization. Every change is either a bug fix or a permanent feature.

### DEF Items Addressed
| DEF | Description | Session |
|-----|-------------|---------|
| DEF-139 | Startup flatten queue not draining — `"qty"` attribute mismatch | S1 |
| DEF-140 | EOD flatten Pass 2 broken — same `"qty"` mismatch + fire-and-forget | S1 |
| DEF-141 | Intelligence polling crash — unbound `symbols` variable | S2 |
| DEF-142 | Margin rejection snowball — no circuit breaker | S2 |
| NEW | Pre-EOD signal cutoff needed | S3 |
| NEW | Quality engine grade compression — all signals scoring B | S3 |
| NEW | ABCD + Flat-Top over-firing in bearish regime (triage) | S3 |

### Session Breakdown

| Session | Title | Primary Files | Compaction |
|---------|-------|---------------|------------|
| S1 | EOD Flatten + Startup Zombie Fix | order_manager.py, tests | 13 (High) |
| S2 | Margin Circuit Breaker + Intelligence Fix | order_manager.py, startup.py | 10 (Medium) |
| S3 | Position Safety + Quality Recalibration + Strategy Triage | orchestrator, config YAMLs, quality config | 10 (Medium) |

All sessions strictly sequential (S1 and S2 both modify order_manager.py).

---

## Session 1: EOD Flatten + Startup Zombie Fix (DEF-139, DEF-140)

### Objective
Fix the `"qty"` → `"shares"` attribute mismatch that breaks both startup zombie cleanup and EOD Pass 2. Then make `eod_flatten()` wait for fill verification before declaring completion and starting the shutdown timer.

### Root Cause Fix (both DEFs)
1. In reconstruction (~line 1627): change `getattr(pos, "qty", 0)` → `getattr(pos, "shares", 0)`
2. In eod_flatten Pass 2 (~line 1499): change `getattr(pos, "qty", 0)` → `getattr(pos, "shares", 0)`

### EOD Flatten Synchronous Verification
3. After Pass 1 submits flatten orders for managed positions, **wait for fill/reject callbacks** with a configurable timeout (`eod_flatten_timeout_seconds`, default 30s). Use per-symbol `asyncio.Event` objects set by fill/reject/cancel callbacks.
4. For rejected orders: retry ONCE after re-querying IBKR position qty for that symbol.
5. Track results: `{filled: list, rejected: list, timed_out: list}`. Log summary.
6. After Pass 2 completes: query `broker.get_positions()` one final time as verification. Log CRITICAL if positions remain.
7. Move auto-shutdown timer start to AFTER verification (not after order submission).

### Config Additions
- `eod_flatten_timeout_seconds: int = 30` on OrderManagerConfig
- `eod_flatten_retry_rejected: bool = True` on OrderManagerConfig

### Tests (minimum 8)
- Test `"shares"` attribute is read correctly in reconstruction (not `"qty"`)
- Test `"shares"` attribute is read correctly in EOD Pass 2
- Test eod_flatten waits for fills before declaring complete
- Test Pass 2 discovers and flattens broker-only positions
- Test rejected orders are retried once
- Test timeout path returns cleanly
- Test post-flatten verification logs remaining positions
- Test auto-shutdown starts after verification, not after submission

---

## Session 2: Margin Circuit Breaker + Intelligence Fix (DEF-141, DEF-142)

### Objective
Add a margin rejection circuit breaker that halts new entries when IBKR rejects too many orders for margin. Fix the intelligence polling crash.

### Margin Circuit Breaker
1. Track margin rejections (`_margin_rejection_count`, reset daily) in order rejection callback for Error 201 "Available Funds"/"insufficient" messages.
2. When count exceeds `margin_rejection_threshold` (config, default 10): set `_margin_circuit_open = True`, log WARNING.
3. Entry gate: in the code path for new BUY entry orders (NOT flattens, NOT bracket legs), check `_margin_circuit_open`. If True: publish `SignalRejectedEvent(stage=RISK_MANAGER, reason="Margin circuit breaker open")`, return without submitting to IBKR. Signals route to counterfactual tracker via existing overflow mechanics.
4. Auto-reset: when IBKR position count drops below `margin_circuit_reset_positions` (config, default 20), reset circuit.
5. Config: `margin_rejection_threshold: 10`, `margin_circuit_reset_positions: 20` on OrderManagerConfig.

### Intelligence Polling Fix (DEF-141)
6. In `argus/intelligence/startup.py`: find unbound `symbols` variable in polling loop, fix scoping.
7. Wrap polling loop body in try/except — single-cycle failures log ERROR and continue, never kill the task.

### Tests (minimum 7)
- Margin circuit opens after threshold rejections
- Margin circuit blocks new entries (with SignalRejectedEvent)
- Margin circuit does NOT block flatten orders
- Margin circuit resets when position count drops
- Margin circuit daily reset
- Polling loop survives single-cycle exception
- Config fields load correctly

---

## Session 3: Position Safety + Quality Recalibration + Strategy Triage

### Objective
Add pre-EOD signal cutoff, enable position limits, recalibrate quality engine scoring, demote underperforming strategies to shadow mode, enable experiment pipeline, update pre-live checklist.

### Pre-EOD Signal Cutoff
1. In signal processing path: before processing any new signal, check if current ET time is past `signal_cutoff_time` (default "15:30"). If so, skip signal (log once per session). Does NOT affect existing position management.
2. Config: `signal_cutoff_enabled: bool = True`, `signal_cutoff_time: str = "15:30"` on OrchestratorConfig.

### Position Limits
3. In `config/risk_limits.yaml`: set `max_concurrent_positions: 50` (enables existing DEC-367 feature).
4. In `config/overflow.yaml`: set `broker_capacity: 50` (align with position limit).

### Quality Engine Recalibration
5. In `config/quality_engine.yaml`, redistribute `historical_match` weight (it's a stub returning constant 50):
   - `pattern_strength: 0.375` (was 0.30)
   - `catalyst_quality: 0.25` (unchanged)
   - `volume_profile: 0.275` (was 0.20)
   - `historical_match: 0.0` (was 0.15 — stub, zero information)
   - `regime_alignment: 0.10` (unchanged)
   - Sum = 1.0 ✓ (QualityWeightsConfig validator passes)
6. Recalibrate grade thresholds for the actual score distribution (~35-77 range):
   - `a_plus: 72` (was 90), `a: 66` (was 80), `a_minus: 61` (was 70)
   - `b_plus: 56` (was 60), `b: 51` (was 50), `b_minus: 46` (was 40)
   - `c_plus: 40` (was 30)
7. Add code comment: "Thresholds recalibrated Sprint 32.9 for actual score distribution. historical_match weight zeroed (stub). Restore weight when historical_match has real data (post-Learning Loop V2)."

### Strategy Shadow Demotion
8. In `config/strategies/abcd.yaml`: change `mode: live` → `mode: shadow`
9. In `config/strategies/flat_top_breakout.yaml`: change `mode: live` → `mode: shadow`
   - Both continue generating counterfactual data. Zero data loss.

### Experiment Pipeline Enablement
10. In `config/experiments.yaml`: change `enabled: false` → `enabled: true`
    - With `variants: {}` this is a no-op — infrastructure initializes, spawns 0 variants, sits ready.
    - Removes "forgot to enable" blocker for future variant configuration.

### Pre-Live Transition Checklist
11. Update `docs/pre-live-transition-checklist.md` with all new config values and their live-trading review notes.

### Tests (minimum 6)
- Signal cutoff blocks after configured time
- Signal cutoff allows before configured time
- Signal cutoff disabled flag works
- Quality weights sum to 1.0 with new values
- Quality grade thresholds produce differentiated grades (mock signals at different pattern_strength + volume_profile levels, verify A/B/C grades all appear)
- max_concurrent_positions=50 loads from config

---

## Review Context

### Sprint-Level Regression Checklist
| Check | How to Verify |
|-------|---------------|
| All existing tests pass | `python -m pytest --ignore=tests/test_main.py -n auto -q` |
| Vitest passes | `cd ui && npx vitest run --reporter=verbose 2>&1 \| tail -5` |
| EOD flatten closes managed + broker-only positions | New tests (S1) |
| Startup with zombie positions → flatten at market open | New tests (S1) |
| Margin circuit breaker blocks entries after threshold | New tests (S2) |
| Pre-EOD signal cutoff stops entries at configured time | New tests (S3) |
| Quality grades span A through C range | New tests (S3) |
| Shadow-mode strategies still generate counterfactual data | Existing shadow mode tests |
| Paper trading overrides still active | Check system_live.yaml |
| Experiment pipeline boots cleanly with empty variants | Boot test / log check |

### Sprint-Level Escalation Criteria
- Any change to bracket order logic (stops, targets, amendments)
- Any change to existing risk manager check flow (margin circuit breaker is additive)
- Any change to how existing positions are managed (trail, escalation, time stops)
- Any modification to the broker abstraction interface
- Any data model changes to the trades table or events
- Test count drops by more than 5 from baseline

---

## Parallel Execution Analysis
Sessions MUST run sequentially:
- S1 and S2 both modify `order_manager.py`
- S3 depends on S1+S2 config changes being committed

---

## Post-Sprint Actions
1. **IBKR paper account reset** — submit before bed tonight
2. **Doc sync** — update project-knowledge.md, CLAUDE.md, sprint-history.md
3. **Verify tomorrow morning** — boot ARGUS, confirm 0 positions at IBKR, monitor first 30 minutes for clean startup, verify quality grades span A-C range in Quality Pipeline dashboard
4. **Run first experiment sweep** (post-sprint, offline):
   ```bash
   python scripts/run_experiment.py --pattern abcd --cache-dir data/databento_cache --dry-run
   ```
   Review results, then configure winning parameter sets as variants in `config/experiments.yaml`.
5. **Sprint 31A** — resume with updated context (2 strategies in shadow, position safety active, experiment pipeline ready)

---

## Strategy Optimization Next Steps (Post-Sprint Guide)

The Experiment Pipeline is now enabled. Here's the workflow for parameter optimization:

**Step 1: Run offline sweeps** (CLI, between market sessions)
```bash
# Dry run to see the parameter grid
python scripts/run_experiment.py --pattern abcd --cache-dir data/databento_cache --dry-run

# Full sweep with backtest pre-filter
python scripts/run_experiment.py --pattern abcd --cache-dir data/databento_cache

# Same for flat_top_breakout
python scripts/run_experiment.py --pattern flat_top_breakout --cache-dir data/databento_cache
```

**Step 2: Analyze results** — the sweep produces MultiObjectiveResult per parameter set. Look for Pareto-optimal variants with Sharpe > 1.0, win rate > 40%, walk-forward efficiency > 0.3.

**Step 3: Configure variants** in `config/experiments.yaml`:
```yaml
variants:
  abcd:
    - variant_id: "strat_abcd__v2_tight"
      mode: "shadow"
      params:
        min_swing_size: 0.03
        fib_tolerance: 0.05
    - variant_id: "strat_abcd__v3_wide_targets"
      mode: "shadow"
      params:
        target_1_atr_multiple: 2.0
```

**Step 4: Restart ARGUS** — VariantSpawner registers variants as shadow strategies alongside the base strategy. Both run in parallel.

**Step 5: Wait for shadow data** — `promotion_min_shadow_days: 5` (configurable). PromotionEvaluator auto-evaluates at session end.

**Step 6: Autonomous promotion** — when a variant outperforms the base on the Pareto frontier, PromotionEvaluator promotes it to live and demotes the base to shadow. Set `auto_promote: true` when comfortable with the process.
