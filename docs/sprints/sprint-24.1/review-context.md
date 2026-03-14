# Sprint 24.1 Review Context File

> This file is shared by all session-level Tier 2 review prompts.
> Reviewers: read this file in full before beginning any session review.
> This is a READ-ONLY reference. Do NOT modify this file.

---

## Review Instructions

You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any source code files. The ONLY file you may create is the review report.

Follow the review skill in `.claude/skills/review.md`.

Your review report MUST include a structured JSON verdict at the end,
fenced with ` ```json:structured-verdict `. See the review skill for the
full schema and requirements.

---

## Sprint Spec

# Sprint 24.1: Post-Sprint Cleanup & Housekeeping

### Goal
Clean up 13 accumulated housekeeping items (DEF-050 through DEF-062) from Sprint 24 reviews before the Phase 5 Gate strategic check-in. No new features or architectural changes.

### Deliverables

1. **Trades DB quality columns (DEF-058):** Quality grade and score persisted through ManagedPosition → Trade model → trades table → TradeLogger.
2. **SetupQualityEngine public accessors (DEF-061):** API routes use `engine.db` and `engine.config` instead of private `_db`/`_config`.
3. **CatalystStorage init log level:** `logger.debug` → `logger.warning` on failure in `main.py`.
4. **EFTS URL live validation (DEF-057):** Diagnostic curl, document result, fix if broken.
5. **Orchestrator 3-column layout (DEF-055):** Decision Log, Catalyst Alerts, Recent Signals in shared row.
6. **QualityOutcomeScatter relocation (DEF-056):** Move from Debrief to Performance. Remove Quality tab from Debrief.
7. **TypeScript build errors (DEF-059):** Fix all 22 `tsc --noEmit` errors.
8. **ArgusSystem e2e test (DEF-050):** Full pipeline: signal → quality → sizer → RM.
9. **Dashboard quality card interactivity (DEF-052):** Tooltips, legend on donut.
10. **Quality column in Dashboard tables (DEF-053):** QualityBadge in Positions + Recent Trades.
11. **Orchestrator clickable signal rows (DEF-054):** Click to show quality breakdown.
12. **PROVISIONAL comment (DEF-060):** Add to system.yaml and system_live.yaml.
13. **Seed script guard (DEF-062):** Require `--i-know-this-is-dev` flag.

### Acceptance Criteria

1. Trades table has quality_grade TEXT and quality_score REAL columns (nullable). ManagedPosition has quality fields with defaults. Trade model has optional quality fields. TradeLogger persists and reads quality. _handle_entry_fill populates from signal. _close_position passes to Trade. Existing NULL trades load without error. Schema migration idempotent.
2. SetupQualityEngine has @property db and config. Routes use public accessors. No type: ignore comments for these.
3. Line 559 of main.py uses logger.warning.
4. Live curl documented. Fix applied if broken.
5. Desktop: 3-column row. Mobile: vertical stack.
6. Scatter on Performance Distribution tab. Debrief has 5 sections. No 'q' shortcut.
7. `tsc --noEmit` exits 0. Vitest passes.
8. Test: ArgusSystem with quality enabled, feed signal, assert quality/sizer/RM called with correct data.
9. Donut tooltips + legend. Histogram tooltips.
10. QualityBadge in both Dashboard tables. Null shows "—".
11. Click signal row → detail view with grade, score, breakdown, prices.
12. PROVISIONAL note in both system YAMLs.
13. Script without flag exits non-zero with warning.

### Config Changes
No config schema changes. YAML comment additions only.

### Session Map

| Session | Items | Scope |
|---------|-------|-------|
| S1a | 2 | Trades quality column wiring |
| S1b | 1, 3, 12, 13 | Trivial backend fixes |
| S2 | 8, 4 | ArgusSystem e2e test + EFTS |
| S3 | 7 | TypeScript build fixes |
| S4a | 5, 6 | Frontend layout fixes |
| S4b | 9, 10, 11 | Frontend interactivity |
| S4f | — | Visual review fixes (contingency) |

---

## Specification by Contradiction

### Out of Scope
- No new API endpoints
- No new database tables (only add columns to trades)
- No strategy logic changes
- No Intelligence Pipeline changes (except log level)
- No Quality Engine scoring logic changes
- No Dynamic Position Sizer logic changes
- No Risk Manager logic changes
- No config schema changes
- No dependency upgrades
- Donut clickable segments are stretch goal, defer if not trivial

### Scope Boundaries
- Do NOT modify: `argus/core/events.py`, `argus/strategies/*`, `argus/intelligence/__init__.py`, `argus/intelligence/classifier.py`, `argus/intelligence/sources/*` (except sec_edgar.py for EFTS fix if needed), `argus/core/risk_manager.py`, `argus/data/*`, `argus/core/orchestrator.py`, `argus/intelligence/config.py`
- Do NOT optimize: performance of TradeLogger, quality engine, or frontend rendering
- Do NOT refactor: Order Manager architecture, Trade model inheritance, TradeLogger method signatures beyond minimum

### Interaction Boundaries
- Does NOT change: quality scoring pipeline, event bus contract, Risk Manager evaluation contract, broker interface, any API response shapes

---

## Sprint-Level Regression Checklist

- [ ] Order Manager position lifecycle unchanged (entry fills, stops, T1/T2, closing)
- [ ] TradeLogger handles quality-present and quality-absent trades
- [ ] Schema migration idempotent, no data loss
- [ ] Quality engine bypass path intact (SIMULATED or enabled=false)
- [ ] All pytest pass (full suite with `-n auto`)
- [ ] All Vitest pass
- [ ] TypeScript build clean after S3 (`tsc --noEmit` exits 0)
- [ ] API response shapes unchanged
- [ ] Frontend renders without console errors

---

## Sprint-Level Escalation Criteria

### Critical (Halt immediately)
1. Order Manager behavioral change — position lifecycle tests fail after S1a
2. Schema migration data loss
3. Quality pipeline bypass path broken
4. E2E test reveals architectural deficiency requiring init path changes

### Warning (Proceed with caution, document)
5. EFTS URL broken — document and defer if fix exceeds URL parameter change
6. TypeScript errors exceed 22 — fix only pre-existing, document new
7. CardHeaderProps icon fix requires upstream component change with >5 file blast radius
8. Frontend layout breaks mobile rendering
