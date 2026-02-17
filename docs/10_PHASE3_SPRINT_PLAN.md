# ARGUS — Phase 3 Sprint Plan (Comprehensive Validation)

> *Version 1.0 | February 17, 2026*
> *Active sprint tracking document. Supersedes Phase 2 Sprint Plan for current work.*
> *Phase 2 Sprint Plan (`09_PHASE2_SPRINT_PLAN.md`) is now historical reference.*

---

## Phase 3 Goal

Validate the ORB strategy with both extended historical data and live paper trading before committing real capital. Phase 3 has two parallel tracks and a gate at the end.

**Track A — Extended Backtest (Sprint 11):** Extend historical data to ~3 years, re-run parameter sweeps and walk-forward validation, produce a definitive answer on parameter generalization.

**Track B — Paper Trading:** Deploy Argus with recommended parameters (DEC-076) on Alpaca's paper trading account. Accumulate forward-looking performance data. Validate system stability, execution quality, and strategy edge in real market conditions.

**Exit Gate:** Both tracks must produce acceptable results before proceeding to Phase 4 (Live Trading).

---

## Track A: Extended Backtest

### Sprint 11 — Extended Backtest & Walk-Forward Revalidation ✅ COMPLETE
**Spec:** `docs/sprints/SPRINT_11_SPEC.md`
**Completed:** February 17, 2026

**Steps:**
- ✅ **Step 1:** Downloaded historical data to March 2023 (35 months, 7M bars, 29 symbols)
- ✅ **Step 2:** VectorBT sweep on extended dataset complete
- ✅ **Step 3:** Walk-forward validation with 15 windows (optimizer + fixed-params)
- ✅ **Step 4:** Results interpreted — Scenario C with caveats (see below)
- ✅ **Step 5:** Parameter Validation Report and documentation updated

**Results Summary:**
| Mode | Windows | Avg WFE (Sharpe) | OOS Trades | Overall OOS Sharpe | OOS P&L |
|------|---------|-----------------|------------|-------------------|---------|
| Optimizer | 15 | -0.38 | 93 | **-11.46** | $7,204 |
| Fixed-params (DEC-076) | 15 | -0.91 | 378 | **+0.34** | $7,741 |

**Interpretation:** Traditional WFE threshold (≥0.3) not met, BUT:
- Fixed params produce **positive aggregate OOS returns** (Sharpe +0.34)
- Fixed params **outperform adaptive optimization** (which overfits)
- 67% of windows (10/15) had positive OOS Sharpe
- Strategy has a real but inconsistent edge that accumulates over time

**Recommendation:** Proceed with paper trading using DEC-076 parameters. Expect high period-to-period variance but aggregate profitability. No parameter changes recommended.

---

## Track B: Paper Trading

Paper trading is not structured as numbered sprints — it's a continuous validation track that starts immediately and runs in parallel with Sprint 11 and beyond. The user decides when confidence is sufficient to proceed.

### Configuration
- **Parameters:** DEC-076 recommended (or=5, hold=15, gap=2.0, stop_buf=0.0, target_r=2.0, atr=999.0)
- **Account:** Alpaca paper trading ($100K simulated)
- **Position sizing:** Start with 10–25 shares per trade (minimum size regardless of model output)
- **Guide:** `docs/08_PAPER_TRADING_GUIDE.md`

### Ramp Schedule (Advisory, Not Rigid)
| Stage | Position Size | Purpose |
|-------|--------------|---------|
| Initial | 10 shares per trade | Verify fills, slippage, execution quality, system stability |
| Intermediate | 25 shares per trade | Increased size, still minimal risk |
| Full | Model-calculated size | Transition to algorithmic sizing when metrics are acceptable |

Timing of transitions is at the user's discretion based on observed performance and confidence level.

### Kill Criteria (Hard Stops)
1. Account drawdown exceeds 15%
2. Profit Factor below 0.7 after 50+ trades
3. Win rate below 25% over any 30-trade window
4. System errors: missed fills, orphaned orders, position tracking discrepancies
5. Zero trades for 5 consecutive trading days when gap candidates exist

### Monitoring (Ongoing)
- Target hit rate (backtest showed 0% — does this persist?)
- Time stop profitability (net P&L of time-stopped trades)
- Slippage vs. backtest assumption ($0.01/share)
- Trade frequency (~12–14 trades/month expected)
- Monthly P&L pattern (seasonal sensitivity signal)
- System uptime and health alerts

### Paper Trading Deliverable
When the user decides paper trading validation is sufficient, document:
- Total trades, duration, key metrics
- Comparison to backtest expectations
- Any parameter adjustments made during paper trading
- Go/no-go recommendation for live capital

---

## Phase 3 Exit Gate

Both conditions must be met before proceeding to Phase 4:

1. **Sprint 11 (Track A):** ✅ **COMPLETE** — WFE < 0.3 but aggregate OOS returns are positive. Decision: **Proceed with paper trading using DEC-076 parameters.** Documented in PARAMETER_VALIDATION_REPORT.md Section 5b.
2. **Paper Trading (Track B):** User is satisfied that system stability and strategy performance justify live capital. No kill criteria triggered. No fixed duration requirement — the user decides when confidence is sufficient.
3. **CPA consultation** on capital/risk implications (DEF-004 from Risk Register).
4. **Explicit go/no-go decision** by the user to commit real capital.

---

## What Changed From Previous Phase Structure

| Change | Why |
|--------|-----|
| Old Phase 3 ("Live Validation") renamed to Phase 4 | Paper trading validation was an informal parallel track. Making it a first-class phase activity with explicit exit criteria ensures it's not rushed. |
| Sprint 11 added for extended backtest | 11 months of data produced an inconclusive walk-forward. Extending to 3 years costs 1–2 days and produces a definitive answer — cheap insurance before committing months to paper trading. |
| Paper trading not structured as sprints | Calendar-bound activities with flexible endpoints don't fit sprint structure. Kill criteria and monitoring provide guardrails without artificial checkpoints. |
| All subsequent phases shifted +1 | Phase 4 = Live Trading, Phase 5 = Orchestrator + Second Strategy, etc. |

---

## Updated Phase Roadmap

| Phase | Scope | Est. | Notes |
|-------|-------|------|-------|
| 1 | Core Engine + ORB Strategy | ✅ COMPLETE | Feb 14–16, 2026. 362 tests. |
| 2 | Backtesting Validation | ✅ COMPLETE | Feb 16–17, 2026. 542 tests. Parameter Validation Report written. |
| 3 | **Comprehensive Validation** | **IN PROGRESS** | Sprint 11 (1–2 days build) + Paper Trading (flexible duration). |
| 4 | Live Trading | Calendar-bound | Real capital at minimum size. Shadow system. Min 20 trading days. |
| 5 | Orchestrator + Second Strategy | 2–4 days | Orchestrator framework, ORB Scalp, cross-strategy risk. |
| 6 | Command Center MVP | 1–2 weeks | Tauri desktop + web, real-time dashboard, controls. |
| 7 | AI Layer + News Intelligence | 3–5 days | Claude API, approval workflow, Tier 1–3 news. |
| 8 | Expand Strategies | Ongoing | Per-strategy: ~1–2 days build + validation. |
| 9 | Multi-Asset Expansion | Future | Crypto via Alpaca → Forex → Futures. |

---

*End of Phase 3 Sprint Plan v1.0*
*Update this document when sprint scope changes or sprints complete.*
