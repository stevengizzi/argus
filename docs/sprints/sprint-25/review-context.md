# Sprint 25 Review Context

> This file provides shared context for all Tier 2 reviews in Sprint 25.
> Each session's review prompt references this file. The reviewer reads this
> once to load sprint-level context, then applies session-specific review
> scope from the individual review prompt.

## Sprint Goal

Build "The Observatory" — a new Command Center page (page 8) providing immersive, real-time and post-session visualization of the entire ARGUS trading pipeline. Four views (Funnel, Radar, Matrix, Timeline), keyboard-first navigation, detail panel with live candlestick charts, session vitals, and debrief mode.

## Sprint Spec Summary

See `docs/sprints/sprint-25/sprint-spec.md` for full spec. Key points:

- **12 deliverables:** Observatory API (4 endpoints), WebSocket, page shell, keyboard system, detail panel + candlestick, Funnel (Three.js), Radar (camera animation), Matrix (condition heatmap), Timeline (strategy lanes), session vitals, debrief mode, ObservatoryConfig
- **Read-only visualization layer** — zero modifications to trading pipeline
- **Keyboard-first** — all navigation possible without mouse
- **Performance targets:** 30+ fps with 3,000+ particles, < 500ms view transitions, < 100ms panel updates

## Specification by Contradiction Summary

See `docs/sprints/sprint-25/spec-by-contradiction.md`. Critical boundaries:

- Do NOT modify: `argus/strategies/`, `argus/core/orchestrator.py`, `argus/core/risk_manager.py`, `argus/execution/`, `argus/intelligence/quality_engine.py`, `argus/intelligence/position_sizer.py`, `argus/intelligence/catalyst/`, `argus/data/`, `argus/ai/`, existing page components
- Do NOT add Event Bus subscribers
- Do NOT change evaluation telemetry schema
- Observatory is additive (page 8), not a replacement

## Regression Checklist

See `docs/sprints/sprint-25/regression-checklist.md`. Critical checks:

1. No trading pipeline files modified (strategies, orchestrator, risk manager, execution, data, AI)
2. No new Event Bus subscribers
3. All 7 existing pages render and function unchanged
4. Existing AI Copilot WebSocket unaffected
5. Three.js code-split — not in main bundle
6. Non-Observatory page load time not degraded
7. New config fields verified against Pydantic model
8. All existing tests pass (2,768 pytest + 523 Vitest baseline)

## Escalation Criteria

See `docs/sprints/sprint-25/escalation-criteria.md`. Automatic halts:

1. Three.js < 30fps with 3,000+ particles → HALT
2. Bundle size increase > 500KB gzipped → HALT
3. Observatory WS degrades Copilot WS → HALT
4. Any trading pipeline modification required → HALT + Tier 3
5. Non-Observatory page load > 100ms increase → HALT

## Session Dependency Chain

```
S1 → S2 → S3 → S4a → S4b
              → S5a → S5b
              → S6a → S6b → S7
              → S8
S3 + all views + S4a/b → S9
All → S10
```

## Config Changes

| YAML Path | Pydantic Model | Field Name | Default |
|-----------|---------------|------------|---------|
| observatory.enabled | ObservatoryConfig | enabled | true |
| observatory.ws_update_interval_ms | ObservatoryConfig | ws_update_interval_ms | 1000 |
| observatory.timeline_bucket_seconds | ObservatoryConfig | timeline_bucket_seconds | 60 |
| observatory.matrix_max_rows | ObservatoryConfig | matrix_max_rows | 100 |
| observatory.debrief_retention_days | ObservatoryConfig | debrief_retention_days | 7 |

## Test Baseline

- pytest: 2,768 (run with `--ignore=tests/test_main.py` per DEF-048)
- Vitest: 523
- Total: 3,291
