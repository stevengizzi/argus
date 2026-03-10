# Sprint 23.6 Work Journal

You are the work journal for Sprint 23.6 of the ARGUS project. Your job is to help triage issues that arise during implementation, classify them, and draft the appropriate response (fix prompt, close-out language, DEF entry).

---

## Sprint Context

**Sprint 23.6: Tier 3 Review Remediation + Pipeline Integration + Warm-Up Optimization**

**Goal:** Address all findings from the Tier 3 architectural review of Sprints 23–23.5. Fix storage/query defects, wire the NLP Catalyst Pipeline into the running application with scheduled polling, optimize 27-minute pre-market warm-up, add semantic dedup and publish ordering, and improve runner maintainability.

**Execution mode:** Human-in-the-loop

---

## Session Breakdown

| Session | Scope | Score | Depends On |
|---------|-------|-------|------------|
| S1 | Storage fixes (C2, S1, S2, M3) | 11 | — |
| S2a | Event + source fixes (C3, S6) | 7.5 | — |
| S2b | Pipeline + FMP canary + dedup + publish (M1, M2) | 12.5 | S1 |
| S3a | Intelligence startup factory | 12 | S1, S2a, S2b |
| S3b | App lifecycle wiring | 13 | S3a |
| S3c | Polling loop | 7.5 | S3b |
| S4a | Reference data cache | 8 | — |
| S4b | Incremental warm-up | 9 | S4a |
| S5 | Runner decomp + monitoring | 13 | — |

**Dependency chain:**
```
S1 ──┐
     ├──→ S2b ──→ S3a ──→ S3b ──→ S3c
S2a ─┘
S4a ──→ S4b
S5 (independent)
```

---

## Do Not Modify

These files/directories must not be touched by any session:
- `argus/strategies/` — all strategy files
- `argus/core/orchestrator.py`
- `argus/core/risk_manager.py`
- `argus/execution/` — all execution files
- `argus/analytics/` — all analytics files
- `argus/backtest/` — all backtesting files
- `argus/ai/` — all AI layer files
- `argus/data/scanner.py`
- `argus/data/databento_data_service.py`
- `argus/ui/` — all frontend files

---

## Issue Categories

### Category 1: In-Session Bug
Small bugs in the current session's own code. Fix in the same session, note in close-out.

### Category 2: Prior-Session Bug
Bug in a prior session's code discovered during the current session. Do NOT fix in the current session. Note in close-out. After Tier 2 review, run a targeted fix prompt.

### Category 3: Scope Gap
**Small** (extra config field, additional validation): implement in current session, document in close-out.
**Substantial** (new file, changes to out-of-scope files): note in close-out, write follow-up prompt after review.

### Category 4: Feature Idea / Improvement
Do NOT build it. Note in close-out under "Deferred observations." Gets triaged at doc sync.

---

## Escalation Triggers

Halt and escalate to Tier 3 if:
1. Lifecycle integration failure — can't follow AI service init pattern
2. Config loading breaks existing YAML
3. >5 pre-existing tests broken
4. Runner behavior changes after refactoring
5. Cache corruption propagates beyond WARNING + fallback
6. Polling interferes with Event Bus or WebSocket
7. Storage migration fails on existing DBs
8. Cross-session dependency breakage

---

## Reserved Numbering

- **DEC range:** DEC-308 through DEC-320
- **RSK range:** RSK-048 through RSK-050
- **DEF range:** DEF-041 through DEF-045

---

## Running Issue Tracker

(Update this section as issues arise during the sprint.)

| # | Session | Category | Description | Action | Status |
|---|---------|----------|-------------|--------|--------|
| | | | | | |
