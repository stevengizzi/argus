# Sprint 27.8: Operational Cleanup + Validation Tooling (Impromptu)

> **Type:** Impromptu (DISCOVERED during March 25 market session debrief)
> **Current sprint:** None (between sprints)
> **Urgency:** URGENT — ghost positions are the root cause of multiple paper trading issues
> **Sprint sub-number:** 27.8

---

## Impact Assessment

### Files touched:
- `argus/core/events.py` — Add `RECONCILIATION` ExitReason
- `argus/execution/order_manager.py` — Reconciliation cleanup + bracket exhaustion detection
- `argus/main.py` — Per-strategy health regime-aware reporting (lines 663–690)
- `config/system_live.yaml` — Add `reconciliation.auto_cleanup_orphans: true`
- `tests/backtest/test_engine_sizing.py` — Decouple from paper-trading config values (DEF-101)
- `tests/core/test_config.py` — Decouple from paper-trading config values (DEF-101)
- `scripts/validate_all_strategies.py` — NEW: validation orchestrator CLI

### Regression risk:
- **Medium** for S1 — changes to position lifecycle in Order Manager are safety-critical. Reconciliation was warn-only by design (DEC-365); promoting to auto-cleanup changes fundamental behavior. Config-gated to limit blast radius.
- **Low** for S2 — pure new script, no production code changes.

### Conflicts with in-progress work:
- None. No active sprint.

### Existing decisions affected:
- **DEC-365** (periodic position reconciliation): Currently warn-only. S1 adds an optional auto-cleanup mode. DEC-365 is not superseded — warn-only remains the default; auto-cleanup is an opt-in extension.

### Planned sprint work affected:
- None deferred. Sprint 28 (Learning Loop) planning not yet started.

---

## Session Breakdown

| Session | Scope | Compaction Risk |
|---------|-------|-----------------|
| S1 | Ghost Position Reconciliation Fix + Health Inconsistency + Config-Coupled Tests | 11 (Medium) |
| S2 | Validation Orchestrator Script | 6 (Low) |

### Compaction Scoring

**S1:**
| Factor | Points |
|--------|--------|
| Files created (1 test file) | 1 |
| Files modified (5: events.py, order_manager.py, main.py, test_engine_sizing.py, test_config.py) | 4 |
| Context reads (OM, main.py, events.py, existing tests, config YAMLs) | 3 |
| Tests (~14 new/rewritten) | 2 |
| Integration wiring (config gating) | 1 |
| External API debugging | 0 |
| Large files | 0 |
| **Total** | **11** |

**S2:**
| Factor | Points |
|--------|--------|
| Files created (1 script + 1 test file) | 2 |
| Files modified (0) | 0 |
| Context reads (revalidate_strategy.py, evaluation framework) | 2 |
| Tests (~6 new) | 1 |
| Integration wiring (0) | 0 |
| External API debugging | 0 |
| Large files | 1 |
| **Total** | **6** |

---

## Sprint Spec (Compact)

**Goal:** Fix ghost position reconciliation (DEF-099, highest-priority paper trading issue), fix health monitor inconsistency, decouple config-coupled tests (DEF-101), and add validation orchestrator script.

**Non-goals:**
- Do NOT change live trading behavior (all fixes config-gated or paper-trading-specific)
- Do NOT modify bracket order submission logic (the repricing storm DEF-100 is a separate issue)
- Do NOT add partial profit-taking or exit management (Proposal A — deferred to Sprint 28.5)
- Do NOT modify the StrategyCoverageTimeline or any frontend code

**Key constraints:**
- Config-gated: `reconciliation.auto_cleanup_orphans` defaults to `false` — must be explicitly enabled
- Synthetic close records MUST use `ExitReason.RECONCILIATION` to distinguish from real exits
- Synthetic close records use `exit_price=entry_price` (P&L=0) since actual exit price is unknown
- Health inconsistency fix must not change aggregate count logic (line 655 is correct)
- Validation script must not import any production code that triggers side effects at import time

## Specification by Contradiction

| If this happens... | Something went wrong |
|--------------------|---------------------|
| `reconcile_positions()` modifies positions when `auto_cleanup_orphans=False` | Config gate broken |
| A real position (IBKR=N, ARGUS=N) gets cleaned up | Cleanup triggered on non-orphan |
| Synthetic close records show non-zero P&L | Exit price not set to entry price |
| Aggregate health count changes behavior | Per-strategy fix leaked into aggregate |
| Production code imports fail when running validation script | Import side effects not guarded |

## Sprint-Level Regression Checklist

| Check | How to Verify |
|-------|---------------|
| Existing reconciliation warn-only mode unchanged when config disabled | `python -m pytest tests/execution/test_order_manager_reconciliation_log.py -x -q` |
| Order Manager fill handling unchanged | `python -m pytest tests/execution/test_order_manager.py -x -q` |
| Order Manager safety features unchanged | `python -m pytest tests/execution/test_order_manager_safety.py -x -q` |
| ExitReason enum backward compatible | `python -m pytest tests/ -k "ExitReason" -x -q` |
| No import errors in scripts | `python -c "from argus.core.events import ExitReason; print(ExitReason.RECONCILIATION)"` |

## Sprint-Level Escalation Criteria

- ESCALATE if: synthetic close record path could execute for non-orphan positions
- ESCALATE if: auto_cleanup code path is reachable when config flag is False
- ESCALATE if: any changes to bracket order submission, stop resubmission, or fill handling logic
- ESCALATE if: reconciliation changes affect the `_managed_positions` dict in ways that could race with `on_tick()` or `on_fill()`
