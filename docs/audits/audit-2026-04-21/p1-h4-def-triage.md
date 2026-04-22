# Audit: Open DEF Triage

**Session:** P1-H4 (Claude.ai, not Claude Code)
**Date:** 2026-04-21 (amended with DEF-142 empirical verification)
**Scope:** 65 open DEFs in `CLAUDE.md`, spot-check of ~25 recently-resolved DEFs for suspicious strikethroughs
**Inputs:** `CLAUDE.md` DEF table (fresh clone 2026-04-21), all 18 Phase 1 findings reports at `docs/audits/audit-2026-04-21/`, live database query against `data/argus.db` on 2026-04-21
**Verdict categories:** OBSOLETE / SUPERSEDED-BY-FINDING / PROMOTABLE / CORRECTLY-DEFERRED / NEEDS-INFO

**Amendment note:** Post-initial-triage, the operator ran the DEF-142 verification query. The output empirically confirmed that Sprint 32.9's quality-engine recalibration never reached the runtime. See `## Empirical Verification — DEF-142` below. This upgrades DEF-142 from "high-confidence suspicious strikethrough" to "confirmed unresolved."

---

## Methodology

1. Extracted all 152 DEF rows from `CLAUDE.md`'s Deferred Items table. Classified 65 as open (no `~~strikethrough~~`), 87 as resolved.
2. For each open DEF, cross-referenced:
   - Audit findings reports (19 files) for any explicit or implicit mention
   - Recent sprint close-outs (31.5, 31.75, 31.8, 31.85 era) for potential obsolescence
   - Current code state via fresh repo clone for drift detection
3. For each resolved DEF from the last ~10 sprints, checked for suspicious strikethroughs (marked done but not actually landed).
4. Assigned one verdict per open DEF with concrete rationale and a reference pointer (audit finding ID or sprint note).

**Conservative bias:** where the audit findings re-frame a DEF's root cause (e.g., DEF-150, DEF-163, DEF-082), the verdict favors **PROMOTABLE** over **CORRECTLY-DEFERRED** because the re-framing changes both severity and safety tag.

---

## Major Cross-Cutting Discoveries

Three audit findings re-characterize multiple open DEFs simultaneously. Call them out here so the individual verdicts below don't bury the headline.

### Discovery 1 — P1-D1 C1: Quality engine is reading from the wrong catalyst DB

**P1-D1 finding C1** establishes that the live quality pipeline's `CatalystStorage` is pointed at `argus.db` while the catalyst ingestion pipeline writes to `catalyst.db`. Verified: `argus.db.catalyst_events` has **0** rows; `catalyst.db.catalyst_events` has **12,114** rows.

**This means:**
- `DEF-082` ("catalyst_quality always 50.0 neutral default — expected when no catalysts") is **not** an expected consequence of thin data. The data is there; the query is reading the wrong file. DEF-082's rationale is wrong. → promotable as a **CRITICAL** bug masquerading as a **LOW** deferral.
- All paper-trading signal quality scores since Sprint 24 (Quality Engine launch) have been computed with `catalyst_quality ≡ 50.0` as a baked-in constant. Shadow variant fleet (22 active) has been training on this corrupt dimension.
- Any **PROMOTABLE** DEF touching quality scoring must be fix-ordered AFTER this underlying C1 lands.

### Discovery 2 — P1-D1 C2: Sprint 32.9 quality recalibration was never activated at runtime (EMPIRICALLY CONFIRMED)

**P1-D1 finding C2** establishes that `config/quality_engine.yaml` carries the Sprint 32.9 recalibration weights/thresholds, but `load_config()` reads `system_live.yaml` — which still has the **pre-recalibration** values. The file exists only for `ConfigProposalManager` validation.

**Operator verification (2026-04-21) confirmed this empirically.** Query executed against the live `data/argus.db`:

```sql
SELECT grade, COUNT(*) as n,
  ROUND(MIN(composite_score), 1) as min_score,
  ROUND(AVG(composite_score), 1) as avg_score,
  ROUND(MAX(composite_score), 1) as max_score
FROM quality_history WHERE scored_at >= '2026-04-14'
GROUP BY grade ORDER BY grade;
```

Result (6,950 signals scored over 7 days):

| Grade | Count | Share | Min | Avg | Max |
|-------|------:|------:|----:|----:|----:|
| B+ | 620 | 8.9% | 60.0 | 62.8 | 67.0 |
| B | 6,128 | 88.2% | 50.0 | 55.6 | 60.0 |
| B- | 200 | 2.9% | 40.7 | 47.9 | 50.0 |
| C+ | 2 | 0.0% | 38.6 | 38.7 | 38.8 |

**Zero signals reached A-grade thresholds. Max composite score observed: 67.0 against an A- threshold of 70.** The distribution signature is diagnostic: 97% of signals fall in the B band because the live thresholds (90/80/70/…) remain calibrated to the pre-recalibration score distribution, while the actual scores concentrate in the middle third of the 0–100 range.

**This means:**
- `DEF-142` ("Quality engine grade compression — all signals scoring B") was marked RESOLVED in Sprint 32.9 strikethrough, but the resolution only edited the wrong file. **The production data proves grade compression is still happening verbatim as DEF-142 originally described.**
- The 50.0–67.0 observed ceiling is also a second symptom. With `catalyst_quality ≡ 50.0` (DEF-082 / Discovery 1 — wrong DB) and `historical_match ≡ 50.0` (constant-50 stub that Sprint 32.9 meant to zero-weight), **50% of every composite score is baked-in neutral**. Only `pattern_strength` (30%), `volume_profile` (20%), and `regime_alignment` (10%) contribute real variance. The 67 ceiling is mechanical, not a matter of setup quality.
- The 22 shadow variants currently collecting CounterfactualTracker data have been operating against this compressed grade distribution for the entire paper-trading window. Shadow outcomes remain valid for raw-P&L analysis; grade-conditional decisions (filter accuracy, grade-weighted promotion criteria) have been computed on degraded inputs.
- Any DEF touching quality thresholds needs ordering AFTER this resolves.
- **DEF-142 must be reopened** (strikethrough removed) in the CLAUDE.md doc-sync step.

### Discovery 3 — P1-G1 M5, M6, M7: DEF-150 and DEF-163 are mischaracterized

**P1-G1 findings M5, M6, M7 + P1-G2 §9** establish:
- `DEF-150` is **not** an xdist race. It's a time-of-day arithmetic bug: `(datetime.now(UTC).minute - 2) % 60` mis-computes to 58/59 when minute ∈ {0,1}, setting "last notification" in the future for the first 2 minutes of every hour. One-line fix, `safe-during-trading`.
- `DEF-163 (a)` (`test_get_todays_pnl_excludes_unrecoverable`) is **not** date-decay. It's a timezone-boundary bug: test writes `datetime.now(UTC)`, SQL filters by ET date. Fails every evening 20:00 ET to 00:00 ET. Fix: one-line timezone correction.
- `DEF-163 (b)` (`test_history_store_migration`) has a second hardcoded default at line 36 (`computed_at=datetime(2026, 3, 26, ...)` — latent issue; Sprint 32.8 fix only touched the explicit override at line 302. Fix: replace default with `datetime.now(UTC) - timedelta(hours=1)`.

All three become PROMOTABLE with clear fixes and clear safety tags.

---

## Open DEF Triage Matrix

Age in sprints is approximate, based on the original-open sprint reference in the DEF row or the context sentence.

| DEF ID | Brief Description | Age (sprints) | Verdict | Rationale | Reference |
|--------|-------------------|--------------:|---------|-----------|-----------|
| DEF-006 | Backtrader integration if Replay Harness too slow | ~45 | CORRECTLY-DEFERRED | Trigger-based (Replay Harness >1hr for 6mo data). Not met; BacktestEngine (Sprint 27) changed the landscape. Keep row but downgrade to "unlikely to trigger." | Sprint 27 superseded this context |
| DEF-007 | Pre-market data for scanner accuracy | ~44 | CORRECTLY-DEFERRED | P1-E1 notes scanner simulation currently fine for BacktestEngine; FMP Starter (DEC-258) provides what we need. | P1-E1 audit structure |
| DEF-011 | IQFeedDataService adapter | ~40 | CORRECTLY-DEFERRED | Trigger-based (forex strategy OR breadth indicator integration). $160–250/mo not worth activating speculatively. | none |
| DEF-012 | Databento L2 depth activation | ~38 | CORRECTLY-DEFERRED | Trigger-based (a strategy requires L2). Post-revenue per DEC-237. | DEC-237 |
| DEF-014 | SystemAlertEvent for dead data feed | ~35 | SUPERSEDED-BY-FINDING | P1-A1 M9 recommends health_monitor coverage expansion for optional subsystems. Same class of fix (wire an event/health hook so the frontend knows). Fold into P1-A1 M9 remediation. | P1-A1 M9 |
| DEF-017 | Performance-weighted + correlation-adjusted allocation | ~30 | CORRECTLY-DEFERRED | Sprint 34-35 Allocation Intelligence Phase 1 per `docs/architecture/allocation-intelligence-vision.md`. Don't promote; confirm target sprint in CLAUDE.md matches. | DEC-380, allocation-intelligence-vision.md |
| DEF-019 | Breadth indicators (advance/decline, TICK, TRIN) | ~30 | CORRECTLY-DEFERRED | Blocked on DEF-011 (IQFeed). Pair with DEF-011 when triggered. | none |
| DEF-020 | Cross-strategy sector exposure (max_single_sector_pct) | ~28 | CORRECTLY-DEFERRED | Requires SIC/GICS mapping. 5% single-stock cap provides interim concentration protection. | DEC-126 |
| DEF-021 | Sub-bar backtesting precision for ORB Scalp | ~27 | CORRECTLY-DEFERRED | Trigger-based (scalp paper results diverge from backtest). Not currently diverging; DEC-053 synthetic-tick ~15s granularity acceptable. | DEC-053 |
| DEF-022 | VwapBaseStrategy ABC extraction | ~25 | CORRECTLY-DEFERRED | Trigger-based (second VWAP-based strategy exists). Only one VWAP-Reclaim standalone strategy; VWAP Bounce is a PatternModule, different pattern. Trigger not met. | DEC-136 |
| DEF-025 | Shared Consolidation Base Class | ~22 | CORRECTLY-DEFERRED | Trigger-based (second consolidation strategy). Not met. | DEC-152 |
| DEF-028 | CalendarPnlView strategy filter | ~18 | CORRECTLY-DEFERRED | UX feature, low priority, workaround exists (Overview tab has strategy filter). Leave alone. | DEC-229 |
| DEF-029 | Persist Live Candle Data to Database | ~18 | OBSOLETE | **Superseded by Sprint 27.65 IntradayCandleStore + Sprint 32.75 Arena candle endpoint + Sprint 32.8 pre-market widening.** "Replay tab shows 'Bar data not available'" is no longer true — bars are accessible via `/api/v1/arena/candles/{symbol}` and IntradayCandleStore.get_bars(). Verify with a manual Replay-tab check before strikethrough-marking. Recommend: mark OBSOLETE with note "Addressed by IntradayCandleStore + Arena candle pipeline (DEC-368, Sprint 27.65/32.75/32.8)". | DEC-368 |
| DEF-030 | Live candlestick chart real-time updates | ~18 | OBSOLETE | Same rationale as DEF-029 — Arena WebSocket (`arena_candle` message type, Sprint 32.75) now pushes live candle formation. TradeChart may still load historical-only, but live updates are available via Arena. Confirm with operator whether TradeChart specifically still lacks WS vs whether the broader feature request has landed elsewhere. | Arena WS |
| DEF-031 | Orders table persistence | ~17 | CORRECTLY-DEFERRED | Trigger-based (post-hoc forensics beyond log analysis). Not currently needed; trade-close is persisted, orders are in logs. | none |
| DEF-032 | FMPScannerSource criteria_list filtering | ~17 | CORRECTLY-DEFERRED | Trigger-based. Quality Engine now scores signals (Sprint 24), so post-fetch filtering role subsumed. | P1-C2 skim noted |
| DEF-033 | Approve→Executed status transition faked with setTimeout | ~16 | NEEDS-INFO | Still cosmetic. Needs operator call: is Learning Loop V1's proposal-approval flow (Sprint 28) the new owner of this status transition, or does AI Copilot still have a separate path? If Copilot path still uses setTimeout(1500ms), recommend PROMOTABLE (small cosmetic WS push). | none |
| DEF-034 | ~~Pydantic serialization warnings on review_verdict field~~ **RESOLVED FIX-20-sprint-runner** | ~16 | PROMOTABLE | Cosmetic warning during test runs. Simple fix: `use_enum_values=True` on `SessionResult`, or emit `.value`. `safe-during-trading`, LOW severity, ~5-min fix. | none |
| DEF-035 | FMP Premium upgrade ($59/mo) | ~16 | CORRECTLY-DEFERRED | Trigger-based (batch-quote speed bottleneck). Finnhub free tier covers news; not triggered. | DEC-356 |
| DEF-037 | FMP API Key Redaction in Error Logs | ~15 | PROMOTABLE | Security hygiene. Add `.replace(api_key, "[REDACTED]")` before logging in `fmp_reference.py` error paths. `safe-during-trading`, MEDIUM severity, ~15-min fix. | none |
| DEF-038 | Fuzzy/Embedding-Based Catalyst Dedup | ~14 | CORRECTLY-DEFERRED | Rule-based dedup (DEC-311) currently sufficient. Triggering would require the dedup miss rate to become material, which it hasn't. | DEC-311 (also see P1-D1 M12 for a separate dedup semantics question) |
| DEF-039 | Runner Conformance Check Reliability Audit | ~14 | CORRECTLY-DEFERRED | Monitoring-only. Trigger (conformance_fallback_count >2) not hit. | none |
| DEF-040 | Runner main.py Further Decomposition | ~14 | NEEDS-INFO | Original threshold was "runner exceeds ~2,500 lines" at 2,067 lines. Need to check current runner main.py LOC. If still under 2,500, CORRECTLY-DEFERRED. If now over, PROMOTABLE. (Not in Phase 1 audit scope — `scripts/sprint-runner.py` is a thin entry point; check `workflow/runner/` submodule.) | Not in audit scope |
| DEF-047 | Bulk catalyst endpoint | ~13 | CORRECTLY-DEFERRED | Performance optimization. Unscheduled, low priority. Per-symbol volume not high enough to warrant. | none |
| DEF-048 | Additional test_main.py xdist failures (4 tests) | ~12 | PROMOTABLE | Root cause shared with resolved DEF-046 (`load_dotenv`/`AIConfig` race). Same fix approach is documented. `safe-during-trading`, MEDIUM severity, batch all 4 tests in one session. Pair with DEF-049 (probably the same root-cause family). | CLAUDE.md DEF-048 row itself |
| DEF-049 | test_orchestrator_uses_strategies_from_registry isolation failure | ~12 | PROMOTABLE | Isolation failure in `tests/test_main.py` — same file cluster as DEF-048. Likely same root cause or adjacent. Promote together with DEF-048 in a single "tests/test_main.py hygiene" fix session. `safe-during-trading`, LOW severity. | Bundle with DEF-048 |
| DEF-064 | Warm-up 78% failure rate on mid-session boot | ~10 | CORRECTLY-DEFERRED | Edge case (mid-session boot is unusual given pre-market boot pattern per DEC-316). Low priority while cold-start is the normal path. P1-B noted this is only relevant to mid-session path. | DEC-316 |
| DEF-074 | Dual regime recheck path consolidation | ~6 | SUPERSEDED-BY-FINDING | P1-A1 M10 + P1-A2 M4 + L7 confirm the duplication at concrete line ranges. Specific fix: delete `main.py._run_regime_reclassification` and its asyncio task; have `Orchestrator._poll_loop` own the cadence. Promote as a Phase 3 fix; this supersedes the DEF row. | P1-A1 M10, P1-A2 M4, P1-A2 L7 |
| DEF-082 | catalyst_quality always 50.0 (expected when no RVOL/catalysts) | ~9 | SUPERSEDED-BY-FINDING | **ROOT CAUSE DIFFERENT FROM DEF ROW.** Per P1-D1 C1, this is not "expected neutral default" — the quality engine is querying the wrong DB (`argus.db` instead of `catalyst.db`). Promote C1, which will close DEF-082 as a byproduct. The DEF row's rationale ("expected when no real-time RVOL or symbol-specific catalysts") is materially wrong. | P1-D1 C1 |
| DEF-084 | Full test suite runtime optimization | ~8 | CORRECTLY-DEFERRED | FMP rate-limit config already mitigated. Remaining slow tests documented with `slow` marker. P1-G1 top-30-slowest list provides actionable next-level optimization candidates if promoting later. | P1-G1 §5 |
| DEF-089 | ~~In-memory ResultsCollector for parallel sweeps~~ **RESOLVED FIX-00-doc-sync-obsoletes** | ~6 | OBSOLETE | **Superseded by Sprint 31.5 `ProcessPoolExecutor`**: fingerprint dedup + ExperimentStore writes are now pinned to main process (module-level worker function), removing the contention that motivated this DEF. The architecture described in DEF-089 ("per-run SQLite databases") was never built; the chosen approach removed the problem. Mark OBSOLETE. | Sprint 31.5 S1 |
| DEF-091 | Public accessors on V1 RegimeClassifier + VIX private attribute reach-in | ~5 | SUPERSEDED-BY-FINDING | **Scope expanded.** P1-A2 M10 + L15 + P1-F1 finding #4 concretely enumerate the private-attribute breaches: `_config`, `_compute_trend_score`, `_update_task`, `_vol_phase_calc`, `_vol_momentum_calc`, `_term_structure_calc`, `_vrp_calc`. Promote P1-A2 M10 as the canonical fix with explicit setter/getter proposals. | P1-A2 M10, P1-A2 L15, P1-F1 #4 |
| DEF-092 | Unused Protocol types in regime.py | ~5 | SUPERSEDED-BY-FINDING → PROMOTABLE | P1-A2 L1 confirms the 4 Protocol classes (`BreadthCalculator`, `CorrelationCalculator`, `SectorRotationCalculator`, `IntradayCalculator`) are orphaned — their `compute(indicators)` signatures don't match concrete implementations. Simple deletion. `safe-during-trading`, LOW severity, ~5-min fix. | P1-A2 L1 |
| DEF-093 | Duplicate orchestrator YAML load + `_latest_regime_vector` typing | ~5 | SUPERSEDED-BY-FINDING | P1-A1 M2 (triple load, not duplicate) + P1-A2 L8. Two findings both point at same fix target; promote M2 which is the biggest win. | P1-A1 M2, P1-A2 L8 |
| DEF-094 | ORB Scalp time-stop dominance | ~4 | CORRECTLY-DEFERRED | Trigger-based (5+ sessions of data). Data-dependent decision; re-evaluate after next paper-trading window accumulates. | none |
| DEF-095 | Submit-before-cancel bracket amendment pattern | ~4 | CORRECTLY-DEFERRED | MEDIUM priority for **live trading** hardening. Paper trading unaffected. Keep on the pre-live checklist; don't promote pre-live. | Sprint 27.65 S2 review |
| DEF-096 | ~~Protocol type for duck-typed candle store reference~~ **RESOLVED FIX-07-intelligence-catalyst-quality** | ~4 | SUPERSEDED-BY-FINDING → PROMOTABLE | P1-D1 L5 notes the same pattern recurs for CounterfactualTracker's `_store: object | None`. Batch fix: define `CandleStoreProtocol` + `CounterfactualStoreProtocol` in a shared typing module. `safe-during-trading`, LOW severity, ~30-min fix. | Sprint 27.65 S4 review, P1-D1 L5 |
| DEF-097 | ~~Monthly cache update cron (populate_historical_cache.py --update)~~ **RESOLVED FIX-21-ops-cron** | ~3 | PROMOTABLE | Ops task. Pair with DEF-162 (its companion). Together: one cron that runs `populate_historical_cache.py --update` then `consolidate_parquet_cache.py --resume`. `safe-during-trading` (it's scheduling infrastructure, not runtime code). LOW severity, ~15-min fix (edit crontab + add doc entry). | P1-I audit noted the pair |
| DEF-098 | Trade count inconsistency between Dashboard cards | ~3 | NEEDS-INFO | Rationale says "depends on DEF-099 resolution." DEF-099 is now PARTIALLY RESOLVED (Sprint 27.8). Operator should re-check: is the dashboard inconsistency still observed? If yes, promote. If no, mark OBSOLETE. | DEF-099 partial resolution |
| DEF-099 | Position reconciliation ghost positions in paper trading | ~3 | CORRECTLY-DEFERRED (monitoring) | Marked PARTIALLY RESOLVED in its own row. Monitoring period was "5+ sessions" — likely now satisfied given Sprint 27.95+28+32.9+31.8 all touched this area extensively. Operator should decide whether to convert partial-resolution to full-resolution strikethrough. | Sprint 27.8 S1 |
| DEF-100 | IBKR paper repricing storm (error 399 spam) | ~3 | CORRECTLY-DEFERRED | IBKR-paper-specific (live unaffected). Throttling mitigates; underlying fix is infrastructure for live-only. | P1-C1 audit noted error handling context |
| DEF-103 | yfinance reliability (unofficial scraping library) | ~2 | CORRECTLY-DEFERRED | Monitoring-only; mitigations already in place (cache, staleness self-disable, FMP fallback). Related: DEF-149 (FRED VIX backup) is the long-term defense. | P1-B noted the pattern |
| DEF-104 | Dual ExitReason enums (events.py + trading.py) | ~2 | PROMOTABLE | Root cause of 336 historical validation errors. MEDIUM priority per DEF row. Consolidate to single source of truth in `models/trading.py` with a re-export from `events.py`. `weekend-only` (touches trade-model imports). MEDIUM severity. | none |
| DEF-105 | Reconciliation trades inflate total_trades count | ~2 | CORRECTLY-DEFERRED | Related to DEF-098. Wait for DEF-098 disposition first. | DEF-098 |
| DEF-106 | ~~from_dict() in models.py contains ~8 assert statements~~ **RESOLVED FIX-07-intelligence-catalyst-quality** (actual file `intelligence/learning/models.py`; `analytics/ensemble_evaluation.py` + `intelligence/learning/outcome_collector.py` sites remain as analytics-layer follow-up) | ~2 | SUPERSEDED-BY-FINDING → PROMOTABLE | P1-F1 finding #7 extends scope with `routes/counterfactual.py:204`. Batch fix: replace all `assert isinstance` with `if/raise TypeError`. `safe-during-trading` (test surface, production-code but unreachable in `-O` mode so the bug surfaces only when someone runs `python -O`). LOW severity, ~20-min fix. | P1-F1 #7 |
| DEF-107 | Unused raiseRec destructured variable | ~2 | PROMOTABLE | 1-line deletion in `LearningInsightsPanel.tsx:388`. Trivial. `safe-during-trading`, COSMETIC. | none |
| DEF-108 | R2G _build_signal emits atr_value=None | ~2 | CORRECTLY-DEFERRED | Architectural constraint (sync method). Correctly handled via percent fallback. Row is informational, not a bug. Confirm with operator whether to keep as "known architectural limitation" or strikethrough-close as "working as designed." | P1-B noted as architectural |
| DEF-109 | V1 trailing stop config dead code on OrderManagerConfig | ~2 | SUPERSEDED-BY-FINDING → PROMOTABLE | Dead `enable_trailing_stop` + `trailing_stop_atr_multiplier` fields. Confirmed unused post-Sprint 28.5. `weekend-only` (touches OrderManagerConfig Pydantic model, impacts YAML parse if users have these set). LOW severity. Bundle with P1-H2 config-consistency cleanup. | P1-H2 scope |
| DEF-110 | Exit reason misattribution on escalation-failure + trail-active | ~2 | CORRECTLY-DEFERRED | Cosmetic only — position closes correctly. Low priority. | none |
| DEF-122 | ABCD swing detection O(n³) optimization | ~2 | CORRECTLY-DEFERRED | MEDIUM priority per DEF row. Trigger (parameter sweeps at scale in Sprint 32) is partially met — full-universe ABCD sweeps would time out. But shadow-first validation model (DEC-382) sidesteps the immediate need. Re-evaluate when shadow proves ABCD variants worth full-universe sweep. | P1-E1 10.2 notes inline warning |
| DEF-123 | build_parameter_grid() float accumulation | ~2 | PROMOTABLE | 3-line fix: use `numpy.arange` or integer-stepping. Mitigated by round(v,6)+dedup today. `safe-during-trading`, COSMETIC severity. | none |
| DEF-125 | Time-of-day signal conditioning | ~2 | CORRECTLY-DEFERRED | Sprint 32 (Parameterized Templates) per DEF row. Not yet scheduled directly; subsumed by experiment pipeline (time-of-day can be a sweep dimension now). Confirm target sprint with operator. | Sprint 32 infra |
| DEF-126 | Regime-strategy interaction profiles | ~2 | CORRECTLY-DEFERRED | Sprint 32.5 (Experiment Registry) per DEF row. Sprint 32.5 is complete; confirm what it delivered vs what DEF-126 wanted. May need re-scoping into Sprint 34 allocation intelligence. | Sprint 32.5 complete |
| DEF-127 | Virtual scrolling for trades table | ~2 | CORRECTLY-DEFERRED | Threshold-based (1000-row limit becomes insufficient). Not triggered. | Sprint 29.5 S3 |
| DEF-128 | IBKR error 404 root cause (multi-position qty divergence) | ~2 | CORRECTLY-DEFERRED | Sprint 30 target (Short Selling, deferred until longs profitable). Re-query-qty fix is in place. Deeper fix still valid future work. | Sprint 30 |
| DEF-135 | Full visual verification of Shadow Trades tab + Experiments page | ~2 | CORRECTLY-DEFERRED (data-dependent) | Requires data accumulation. 22 shadow variants are now collecting; this could be triggered once a week's worth of data lands. Put on a "post-paper-trading-window" checklist. | Sprint 32.5 |
| DEF-147 | DuckDB Research Console backend | ~1 | CORRECTLY-DEFERRED | Sprint 31B target (next sprint). Keep for Sprint 31B scope. | Sprint 31B queue |
| DEF-148 | FRED macro regime service | ~1 | CORRECTLY-DEFERRED | Sprint 34 target. Confirm. | Sprint 34 queue |
| DEF-149 | FRED VIX backup source | ~1 | CORRECTLY-DEFERRED | Opportunistic — pair with DEF-148 FRED work when Sprint 34 lands. | pair w/ DEF-148 |
| DEF-150 | "Flaky" pre-existing test (xdist race) | ~1 | SUPERSEDED-BY-FINDING → PROMOTABLE | **Re-characterized by P1-G1 M7.** Not xdist-specific; time-of-day arithmetic bug (first 2 min of every hour). One-line fix: replace `(datetime.now(UTC).minute - 2) % 60` with `datetime.now(UTC) - timedelta(minutes=2)`. `safe-during-trading`, LOW severity. **Update DEF row characterization when fixing.** | P1-G1 M7, P1-G2 §9 |
| DEF-160 | Shutdown race between bracket-cancel flatten and stop-retry | ~0.5 | CORRECTLY-DEFERRED | Cosmetic log noise (positions correctly flattened). May be partially subsumed by DEF-158 fix per row. Re-check after 1-2 shutdown cycles; likely OBSOLETE. | DEF-158 resolution |
| DEF-162 | ~~Monthly re-consolidation cron (pair with DEF-097)~~ **RESOLVED FIX-21-ops-cron** | ~0.5 | PROMOTABLE | Paired with DEF-097 as noted. Chain the crons. `safe-during-trading`. LOW severity. | DEF-097 pair |
| DEF-163 | Date-decay test hygiene batch | ~0.5 | SUPERSEDED-BY-FINDING → PROMOTABLE | **Re-characterized by P1-G1 M5, M6 + P1-F2 M9.** Not "date decay" — (a) `test_get_todays_pnl_excludes_unrecoverable` is a timezone-boundary bug; (b) `test_history_store_migration` has a second hardcoded default at line 36. Both have concrete 1-2 line fixes in the audit report. Plus 4 frontend tests (P1-F2 M9) with hardcoded absolute dates. Batch all 6 fixes into one "tests/time-handling hygiene" session. `safe-during-trading`, LOW severity. | P1-G1 M5, M6; P1-F2 M9 |
| DEF-164 | Late-night ARGUS boot collides with after-hours auto-shutdown | ~0 | PROMOTABLE (doc) | Simplest fix per DEF row: document "do not start ARGUS between ~22:30 ET and pre-market" in `docs/live-operations.md`. Code fixes (shutdown waits for init, or auto-shutdown suppressed after boot) are weekend-only. Doc-only fix: `safe-during-trading`, LOW. Operator call on which approach. | none |
| DEF-165 | DuckDB close hangs when CREATE VIEW is interrupted | ~0 | PROMOTABLE | `HistoricalQueryService.close()` calls `conn.interrupt()` before `conn.close()` — 2-line fix. Only manifests under DEF-164 conditions. `weekend-only` (touches a live-path service). LOW severity. | none |

---

## Promotable DEFs — Detail

These are ready to become Phase 3 fix sessions. Most group together cleanly by theme.

| DEF ID | Severity | Safety | Suggested Fix | Proposed Phase 3 Group |
|--------|----------|--------|---------------|------------------------|
| DEF-014 | MEDIUM | weekend-only | Fold into P1-A1 M9 health_monitor expansion — emit a `SystemAlertEvent` when Databento max-retries exceeded. | **FIX-health-monitor** (with P1-A1 M9) |
| DEF-034 | LOW | safe-during-trading | `use_enum_values=True` on `SessionResult` model OR serialize with `.value`. | **FIX-sprint-runner-cleanup** |
| DEF-037 | MEDIUM | safe-during-trading | Redact `apikey=…` in FMP error log helpers. | **FIX-logging-hygiene** |
| DEF-048 + DEF-049 | MEDIUM+LOW | safe-during-trading | Apply DEF-046's fix pattern to 4 more xdist-failing tests in `tests/test_main.py`; fix isolation for `test_orchestrator_uses_strategies_from_registry`. | **FIX-test-main-hygiene** |
| DEF-074 | MEDIUM | weekend-only | Delete `main.py._run_regime_reclassification` + `_regime_task`; rely on `Orchestrator._poll_loop` sole cadence (P1-A1 M10). | **FIX-regime-dedup** |
| DEF-082 | CRITICAL | weekend-only | Fix `CatalystStorage(argus.db)` → `CatalystStorage(catalyst.db)` in main.py:1113 (P1-D1 C1). Add boot-time WARN if `argus.db.catalyst_events` has rows. | **FIX-quality-pipeline-catalyst-db** (ordering: BEFORE any other quality-engine fix) |
| DEF-091 | MEDIUM | weekend-only | Add public setters/getters: `attach_vix_service()`, `compute_trend_score_public()`, `_config` → property. Replace 7+ private-attribute breaches. | **FIX-regime-encapsulation** |
| DEF-092 | LOW | safe-during-trading | Delete 4 unused Protocol classes (`BreadthCalculator`, `CorrelationCalculator`, `SectorRotationCalculator`, `IntradayCalculator`) in `argus/core/regime.py:343-376`. | **FIX-regime-dead-code** |
| DEF-093 | MEDIUM | weekend-only | Delete duplicate YAML loads at `main.py:739-740` + `main.py:792-793`; use `self._config.orchestrator` everywhere (P1-A1 M2). Type `_latest_regime_vector` as `RegimeVector | None` via `TYPE_CHECKING` block (P1-A2 L8). | **FIX-config-use-self-config** |
| DEF-096 | LOW | safe-during-trading | Define `CandleStoreProtocol` + `CounterfactualStoreProtocol` in `argus/core/protocols.py`; replace `object + hasattr()` duck-typing at 2+ sites. | **FIX-protocol-types** |
| DEF-097 + DEF-162 | LOW | safe-during-trading | Schedule paired cron: `populate_historical_cache.py --update && consolidate_parquet_cache.py --resume`. Edit crontab + add line to `docs/live-operations.md`. | **FIX-cache-cron** |
| DEF-104 | MEDIUM | weekend-only | Consolidate `ExitReason` enum to single source (`argus/models/trading.py`); re-export from `argus/core/events.py`. | **FIX-exit-reason-dedup** |
| DEF-106 | LOW | safe-during-trading | Replace `assert isinstance(...)` → `if not isinstance(...): raise TypeError(...)` in `argus/models/trading.py` (~8 sites) + `argus/api/routes/counterfactual.py:204` (+ the `routes/learning.py` sites already fixed in Sprint 28 — verify no regressions). | **FIX-assert-to-raise** |
| DEF-107 | COSMETIC | safe-during-trading | Delete `raiseRec` destructured variable in `LearningInsightsPanel.tsx:388`. | **FIX-ui-dead-code** |
| DEF-109 | LOW | weekend-only | Delete `enable_trailing_stop` + `trailing_stop_atr_multiplier` fields from `OrderManagerConfig`. Check callers & YAML before deleting. | **FIX-config-dead-code** (batch with P1-H2 findings) |
| DEF-123 | COSMETIC | safe-during-trading | Replace while-loop float accumulation in `build_parameter_grid()` with `numpy.arange` or integer-stepping. | **FIX-grid-builder-cleanup** |
| DEF-150 | LOW | safe-during-trading | Replace `(datetime.now(UTC).minute - 2) % 60` with `datetime.now(UTC) - timedelta(minutes=2)` in `tests/sprint_runner/test_notifications.py:313-315`. **Also update CLAUDE.md DEF-150 row — it's NOT an xdist race.** | **FIX-time-test-hygiene** (with DEF-163) |
| DEF-163 | LOW | safe-during-trading | (a) `test_get_todays_pnl_excludes_unrecoverable` — use `datetime.now(ZoneInfo("America/New_York"))` for `exit_time`, OR normalize in `trade_logger.log_trade()`. (b) `test_history_store_migration` — replace `_make_vector()` default at line 36 with `datetime.now(UTC) - timedelta(hours=1)`. **Also update CLAUDE.md DEF-163 row — these are timezone-boundary bugs, not date-decay.** Plus 4 Vitest date fixtures (P1-F2 M9). | **FIX-time-test-hygiene** (with DEF-150) |
| DEF-164 | LOW | safe-during-trading | Doc fix: add "do not start ARGUS between ~22:30 ET and pre-market" to `docs/live-operations.md`. Optional follow-up: suppress auto-shutdown for N minutes after boot (weekend-only, larger). | **FIX-live-ops-doc** |
| DEF-165 | LOW | weekend-only | `HistoricalQueryService.close()` calls `conn.interrupt()` before `conn.close()`. 2-line change + test. | **FIX-duckdb-close** |

**Suggested grouping summary (10 Phase 3 fix sessions):**

| Group | DEFs + findings | Safety | Notes |
|-------|-----------------|--------|-------|
| FIX-quality-pipeline-catalyst-db | DEF-082 + P1-D1 C1 | weekend-only | **HIGHEST PRIORITY** — masks all catalyst scoring |
| FIX-config-recalibration | P1-D1 C2 + C3 (DEF-142 never landed, overflow divergence) | weekend-only | **HIGH PRIORITY** — Sprint 32.9 intent not realized |
| FIX-regime-dedup | DEF-074 + P1-A1 M10 + P1-A2 M4 | weekend-only | Clean delete, big LOC reduction |
| FIX-regime-encapsulation | DEF-091 + P1-A2 M10 + L15 + P1-F1 #4 | weekend-only | Private-attr cleanup across 7+ sites |
| FIX-config-use-self-config | DEF-093 + P1-A1 M2 + P1-A2 L8 | weekend-only | Delete triple YAML load |
| FIX-config-dead-code | DEF-109 + P1-H2 findings | weekend-only | Config Pydantic cleanup |
| FIX-health-monitor | DEF-014 + P1-A1 M9 | weekend-only | Add SystemAlertEvent + optional-subsystem health coverage |
| FIX-exit-reason-dedup | DEF-104 | weekend-only | Consolidate enum |
| FIX-duckdb-close | DEF-165 | weekend-only | 2-line fix |
| FIX-logging-hygiene | DEF-037 (+ P1-A1 M6, M7) | safe-during-trading | Redaction + exc_info additions |
| FIX-test-main-hygiene | DEF-048 + DEF-049 | safe-during-trading | Apply DEF-046 pattern |
| FIX-time-test-hygiene | DEF-150 + DEF-163 (a,b) + P1-F2 M9 | safe-during-trading | 6 test fixes, single file-set |
| FIX-sprint-runner-cleanup | DEF-034 + DEF-123 | safe-during-trading | Low-effort cosmetic batch |
| FIX-assert-to-raise | DEF-106 + P1-F1 #7 | safe-during-trading | Batch isinstance replacements |
| FIX-protocol-types | DEF-096 + P1-D1 L5 | safe-during-trading | Add shared Protocol module |
| FIX-regime-dead-code | DEF-092 + P1-A2 L1 | safe-during-trading | Delete 4 Protocol classes |
| FIX-ui-dead-code | DEF-107 | safe-during-trading | 1-line deletion |
| FIX-cache-cron | DEF-097 + DEF-162 | safe-during-trading | Ops cron pair |
| FIX-live-ops-doc | DEF-164 | safe-during-trading | Doc-only |
| FIX-grid-builder-cleanup | DEF-123 (if not bundled) | safe-during-trading | 3-line numeric fix |

That's ~18-20 Phase 3 sessions. Some will be merged further when Phase 2 runs (e.g., FIX-regime-* could become one session if touched files overlap).

---

## Superseded-By-Finding Cross-Reference

| DEF ID | Audit Finding(s) | Notes |
|--------|------------------|-------|
| DEF-014 | P1-A1 M9 | DEF says "add SystemAlertEvent"; M9 says "add health_monitor.update_component for all optional subsystems." Fold the event-emission into M9's broader coverage. |
| DEF-074 | P1-A1 M10, P1-A2 M4, P1-A2 L7 | Three findings all converge on the same dual-poll fix. |
| DEF-082 | P1-D1 C1 | **Root cause re-diagnosed.** Not "expected neutral default" — it's reading the wrong DB. CRITICAL. |
| DEF-091 | P1-A2 M10, P1-A2 L15, P1-F1 #4 | Three findings expand scope; add `vix_calculators`, `vix routes`, `server.py` sites. |
| DEF-092 | P1-A2 L1 | Concrete deletion target. |
| DEF-093 | P1-A1 M2 (triple load, not duplicate), P1-A2 L8 | Line-range-precise. |
| DEF-096 | P1-D1 L5 | Same pattern recurs in CounterfactualTracker. |
| DEF-106 | P1-F1 #7 | Extends scope to `routes/counterfactual.py:204`. |
| DEF-109 | P1-H2 config-consistency findings (when read) | Dead-code in Pydantic; batch with config cleanup. |
| DEF-150 | P1-G1 M7, P1-G2 §9 | **Re-characterized.** Not xdist race — time-of-day bug. One-line fix. |
| DEF-163 | P1-G1 M5 + M6, P1-F2 M9 | **Re-characterized.** Two separate timezone-boundary bugs + 4 frontend date fixtures. |

---

## Suspicious-Strikethrough Audit

I walked the resolved (strikethrough) DEFs from Sprint 28 onward (~25 rows) and checked each resolution claim against visible code state or the referenced sprint close-out. One resolution was empirically disproved by a live-database query (DEF-142); see the Empirical Verification subsection that follows.

| DEF ID | Concern | Status |
|--------|---------|--------|
| **DEF-142** | **CONFIRMED UNRESOLVED (empirical).** Strikethrough claims Sprint 32.9 S3 fixed "quality engine grade compression" by editing `config/quality_engine.yaml`. Per P1-D1 C2, `load_config()` does not read that file — the live runtime reads the `quality_engine:` block inside `system_live.yaml`, which still carries pre-recalibration values. **Verified 2026-04-21 via live `quality_history` query: 97% of the last 7 days' signals graded B, zero A-grades, max composite score 67.0 against an A- threshold of 70.** See `## Empirical Verification — DEF-142` below. | Reopen: remove strikethrough from CLAUDE.md, add to FIX-config-recalibration Phase 3 group. |
| **DEF-099** | **PARTIALLY RESOLVED** per its own row (Sprint 27.8 S1). The row itself admits monitoring is still needed. Since 27.8 was 10+ sprints ago, either confirm fully resolved and strike through, or reopen to "monitoring concluded / still intermittent." | Operator call — has ghost-position behavior been observed in the last 10 sessions? |
| DEF-131 through DEF-141, DEF-143 through DEF-146, DEF-151 through DEF-161 | Spot-checked all: sprint close-outs + code state confirm. No other suspicious strikethroughs. | None. |

**One new-flake discovery** from P1-G1: `test_speed_benchmark` surfaced as flaky under coverage runs and is **not** in the CLAUDE.md DEF table. Not a strikethrough concern, but worth flagging for inclusion. Suggested: add as **DEF-166** (Phase 2 doc-sync action).

---

## Empirical Verification — DEF-142

After the initial triage recommended verifying DEF-142's status, the operator ran the suggested diagnostic query against the live `data/argus.db` on 2026-04-21. The output conclusively confirmed that Sprint 32.9's quality-engine recalibration has never reached the runtime.

### Query executed

```sql
SELECT grade, COUNT(*) as n,
  ROUND(MIN(composite_score), 1) as min_score,
  ROUND(AVG(composite_score), 1) as avg_score,
  ROUND(MAX(composite_score), 1) as max_score
FROM quality_history WHERE scored_at >= '2026-04-14'
GROUP BY grade ORDER BY grade;
```

Note on schema: the `quality_history` table uses `grade` (not `quality_grade`) and `scored_at` (not `created_at`); `scored_at` is stored as an ET-timezone ISO string per `quality_engine.py:220`.

### Result (7-day window, 6,950 total signals)

| Grade | Count | Share | Min Score | Avg Score | Max Score |
|-------|------:|------:|----------:|----------:|----------:|
| A+ | 0 | 0.0% | — | — | — |
| A | 0 | 0.0% | — | — | — |
| A- | 0 | 0.0% | — | — | — |
| B+ | 620 | 8.9% | 60.0 | 62.8 | 67.0 |
| B | 6,128 | 88.2% | 50.0 | 55.6 | 60.0 |
| B- | 200 | 2.9% | 40.7 | 47.9 | 50.0 |
| C+ | 2 | 0.0% | 38.6 | 38.7 | 38.8 |
| C / C- | 0 | 0.0% | — | — | — |

### Interpretation

**Primary symptom — grade compression:** 97% of signals fall into the B band (B-/B/B+). Zero signals reached any A-grade. This is exactly the behavior DEF-142 described and that Sprint 32.9 claimed to fix.

**Secondary symptom — composite score ceiling at 67:** The theoretical range for `composite_score` is 0–100. Actual variance is concentrated between 38.6 and 67.0 — the middle third of the theoretical range. The ceiling of 67 is **mechanically enforced**, not a result of consistently mediocre setups:

- `catalyst_quality ≡ 50.0` for every signal (DEF-082 / P1-D1 C1 — the catalyst-DB misconfiguration means the engine never sees any catalyst data, so every signal gets the neutral default).
- `historical_match ≡ 50.0` for every signal (the constant-50 stub that Sprint 32.9's recalibration was supposed to zero-weight, but the zero-weighting lives in the unread `config/quality_engine.yaml`).
- Combined: at the live weights (pattern 0.30, catalyst 0.25, volume 0.20, historical 0.15, regime 0.10), **40%** of every composite score (catalyst + historical) is pinned at 50.0. Only `pattern_strength` (30%), `volume_profile` (20%), and `regime_alignment` (10%) can contribute any real variance.

**Cross-referencing with P1-D1 C2's intended thresholds:** The Sprint 32.9 recalibration in `config/quality_engine.yaml` sets grade thresholds at A+=72, A=66, A-=61, B+=56, B=51, B-=46, C+=40. If those had been active at runtime, the observed score distribution would grade:

- Observed 60.0–67.0 (620 signals currently B+) → would mostly grade **A-** or **A**
- Observed 50.0–60.0 (6,128 signals currently B) → would mostly grade **B+** or **A-**
- Observed 40.7–50.0 (200 signals currently B-) → would mostly grade **B** or **B-**
- Observed 38.6–38.8 (2 signals currently C+) → would grade **C-** (below C+ 40 threshold)

This is why Sprint 32.9 recalibrated in the first place. The recalibration was correct; its application was not.

### Implications for the 22 shadow variants

CounterfactualTracker data collected since Sprint 32.9 has been recorded against this compressed grade distribution. Concrete consequences:

1. **Raw P&L per variant is still valid.** Shadow positions open when a variant's pattern detection fires and a position would have been sized; the actual subsequent price action determines P&L regardless of grade. That data remains usable.
2. **Grade-conditional analysis is degraded.** Filter-accuracy breakdowns by grade (`FilterAccuracy.by_grade`), grade-weighted promotion criteria, and any "high-grade setups perform better" inference drawn from pre-fix shadow data are operating on a compressed distribution where almost all signals are grade B. The signal is not meaningfully separable by grade in the current data.
3. **Promotion ordering.** PromotionEvaluator Pareto comparison uses metrics that are not themselves grade-weighted (Sharpe, win rate, expectancy, drawdown, profit factor) — those should remain valid. Any future promotion logic that incorporates grade-conditional filtering should be held until post-fix data accumulates.

### Recommendation

Adjust Phase 3 ordering: **FIX-quality-pipeline-catalyst-db (DEF-082) and FIX-config-recalibration (DEF-142) should land together in a single weekend session**, not sequentially. The two fixes are independent in what they touch but tightly coupled in their observable effect:

- Fix catalyst DB alone → `catalyst_quality` contributes real variance (no longer 50.0), but grades remain compressed because thresholds are still miscalibrated.
- Fix config loading alone → grades distribute properly, but 40% of composite remains pinned (catalyst still reading wrong DB, historical still at constant 50).
- Fix both → catalysts contribute variance, historical_match drops to zero weight, A-grade tier becomes reachable, composite range opens up.

After both fixes land, flag the pre-fix CounterfactualTracker data in the PromotionEvaluator as "pre-recalibration" so any rolling-window promotion check does not mix pre-fix and post-fix scoring contexts. Give the shadow fleet 5+ sessions of post-fix data before treating grade-conditional outputs as meaningful.

---

## Aggregate Statistics

| Metric | Count |
|--------|------:|
| Total open DEFs triaged | 65 |
| Resolved DEFs spot-checked | 25 (roughly last 10 sprints) |
| **Suspicious strikethroughs** | **1 CONFIRMED via live DB query (DEF-142)** + 1 status-stale (DEF-099) |
| New DEFs recommended | 1 (`test_speed_benchmark` flake — DEF-166) |

**Verdict distribution:**

| Verdict | Count |
|---------|------:|
| OBSOLETE (mark done) | 3 (DEF-029, DEF-030, DEF-089) |
| SUPERSEDED-BY-FINDING | 11 (DEF-014, 074, 082, 091, 092, 093, 096, 104 partial, 106, 109, 150, 163) — several also PROMOTABLE |
| PROMOTABLE (unique) | 8 net (DEF-034, 037, 048+049 combined, 097+162 combined, 104, 107, 123, 164, 165) |
| CORRECTLY-DEFERRED | 38 |
| NEEDS-INFO | 4 (DEF-033, 040, 098, 108) |

(Numbers overlap — SUPERSEDED-BY-FINDING items are frequently ALSO PROMOTABLE.)

**Promotable DEFs going into Phase 3:** ~20 unique DEFs across ~14 groups (after merging cross-cutting findings).

**Expected CLAUDE.md DEF table reduction after Phase 3 + doc-sync:** 
- Strikethrough-mark as resolved after Phase 3: 20
- Mark OBSOLETE with pointer: 3
- Leave CORRECTLY-DEFERRED: 38
- NEEDS-INFO left open pending operator decisions: 4
- **Net open-DEF reduction: –23 rows** (65 → 42 open) after Phase 3 completes, assuming all promotable groups land successfully.

---

## Recommended `CLAUDE.md` Doc-Sync Operations (Single Commit)

Apply these edits in one doc-sync commit at Phase 2 end (before Phase 3 begins), so the DEF table reflects the triage:

### A. Re-characterizations (update descriptions without strikethrough)

1. **DEF-082** — update description and trigger: `"catalyst_quality always 50.0 — root cause is CatalystStorage pointing at argus.db instead of catalyst.db (P1-D1 C1). Promoted to FIX-quality-pipeline-catalyst-db in audit Phase 3."` Target field → `FIX session`, not `Unscheduled`.
2. **DEF-142** — REOPEN (remove strikethrough) and update: `"Sprint 32.9 recalibration edited config/quality_engine.yaml but load_config() reads system_live.yaml, which still carries pre-recal values. CONFIRMED unresolved via live quality_history query 2026-04-21: 97% of 7-day signals grade B, zero A-grades, max composite 67.0 vs A- threshold 70. Promoted to FIX-config-recalibration in audit Phase 3 (P1-D1 C2)."`
3. **DEF-150** — update description: `"Time-of-day arithmetic bug in test_check_reminder_sends_after_interval — (datetime.now(UTC).minute - 2) % 60 mis-computes to 58/59 in first 2 min of every hour. NOT xdist race. Promoted to FIX-time-test-hygiene (P1-G1 M7)."`
4. **DEF-163** — update description: `"Two timezone-boundary bugs + 4 Vitest date fixtures. Not date-decay. Root causes: (a) test_def159_entry_price_known writes UTC, SQL filters ET; (b) test_history_store_migration has second hardcoded default at line 36; (c) P1-F2 M9 lists 4 hardcoded Vitest dates. Promoted to FIX-time-test-hygiene (P1-G1 M5, M6; P1-F2 M9)."`

### B. Mark OBSOLETE (strikethrough with obsolescence note)

5. **DEF-029** — strikethrough with: `"OBSOLETE: Superseded by IntradayCandleStore (DEC-368, Sprint 27.65) + Arena candle endpoint (Sprint 32.75) + pre-market widening (Sprint 32.8)."`
6. **DEF-030** — strikethrough with: `"OBSOLETE: Arena WebSocket arena_candle message (Sprint 32.75) provides real-time candle push. TradeChart-specific replay may still warrant a separate DEF if needed — operator to confirm."`
7. **DEF-089** — strikethrough with: `"OBSOLETE: Sprint 31.5 ProcessPoolExecutor approach removed the contention this DEF was designed to solve. Main-process fingerprint dedup + ExperimentStore writes are sufficient."`

### C. Promotion (link to Phase 3 group)

Each of the PROMOTABLE DEFs gets its `Trigger` column updated to a FIX-group name from the Suggested Grouping table above. When the corresponding Phase 3 session lands, the DEF is struck through with `"RESOLVED: FIX-<groupname>, commit <sha>"`.

### D. NEEDS-INFO

Annotate DEF-033, DEF-040, DEF-098, DEF-108 with `"NEEDS-INFO: audit P1-H4. See docs/audits/audit-2026-04-21/p1-h4-def-triage.md for specific questions."` — keeps them open but signals that their disposition is pending operator decision.

### E. New DEF

Add DEF-166: `"test_speed_benchmark flaky under pytest-cov (not previously tracked). Surfaced by P1-G1. Priority: LOW."`

---

## Handoff

This triage output is the last Phase 1 deliverable. Adding all Phase 1 findings + this triage yields Phase 2 review spreadsheet inputs.

Critical ordering for Phase 3:

1. **FIX-quality-pipeline-catalyst-db** (DEF-082 / P1-D1 C1) and **FIX-config-recalibration** (DEF-142 / P1-D1 C2, C3) should land **together in a single weekend session**, not sequentially. Per the `## Empirical Verification — DEF-142` section above, the two fixes are independent in what they touch but tightly coupled in their observable effect on signal grading. Fixing one without the other leaves grade compression or constant-50 dimensions in place. Every additional day of paper trading produces more shadow data against the corrupted scoring pipeline.
2. After that session lands, flag all pre-fix CounterfactualTracker data in the PromotionEvaluator as "pre-recalibration" and give the shadow fleet 5+ sessions of post-fix data accumulation before treating grade-conditional outputs as meaningful.
3. All other FIX groups can then proceed in parallel respecting safety tags.

I have **not** committed this file. Paste-ready content above; operator reviews and commits as `docs/audits/audit-2026-04-21/p1-h4-def-triage.md` with:

```
git add docs/audits/audit-2026-04-21/p1-h4-def-triage.md
git commit -m "audit(P1-H4): DEF triage findings report

Part of codebase audit 2026-04-21.
Open DEFs triaged: 65.
Verdict distribution: 3 OBSOLETE / 11 SUPERSEDED-BY-FINDING / 8 PROMOTABLE-unique / 38 CORRECTLY-DEFERRED / 4 NEEDS-INFO.
Suspicious strikethroughs: 1 CONFIRMED via live DB query (DEF-142)."
git push origin main
```

---

## FIX-05 Resolution (2026-04-22)

DEFs closed in this session:
- **DEF-091** ~~V1/V2 RegimeClassifier private-attribute access + VIXDataService private attrs~~ → **RESOLVED FIX-05-core-orchestrator-risk-regime**. Public accessors: `VIXDataService.config`, `RegimeClassifier.compute_trend_score()`, `RegimeClassifier.vol_low_threshold` / `.vol_high_threshold`.
- **DEF-092** ~~Unused Protocol types in regime.py~~ → **RESOLVED FIX-05-core-orchestrator-risk-regime**. All 4 Protocol classes deleted.
- **DEF-104** ~~Dual ExitReason enums~~ → **RESOLVED FIX-05-core-orchestrator-risk-regime**. Single source of truth in `argus.models.trading`; re-export from `argus.core.events`.
- **DEF-163** ~~Timezone-boundary bugs (Python side)~~ → **RESOLVED FIX-05-core-orchestrator-risk-regime**. Vitest remainder tracked under DEF-167 (FIX-13).
- **DEF-170** ~~VIX regime calculators stay None in production~~ → **RESOLVED FIX-05-core-orchestrator-risk-regime**. `attach_vix_service()` re-instantiates calculators.

New DEFs opened:
- **DEF-182** — Weekly reconciliation full implementation (promoted from P1-A2-L11 stub).
