# Doc-Sync Patch 5 — `docs/pre-live-transition-checklist.md`

**Purpose:** Add a new section "Sprint 31.91 — OCA Architecture & Reconciliation Drift" near the end of the file (just before "Cross-References") capturing the live-trading prerequisites surfaced by Tier 3 review #1.

**Anchor verification (must hold before applying):**
- Line 196 ends with `- [ ] \`experiments.enabled\`: keep true, configure \`auto_promote\` based on confidence`
- Line 197 is `---` (separator)
- Line 198 is blank
- Line 199 is `## Cross-References`

The new section lands at the position currently occupied by line 197's `---`.

---

## Patch — Insert Sprint 31.91 section before Cross-References

### Find:

```
- [ ] `experiments.enabled`: keep true, configure `auto_promote` based on confidence

---

## Cross-References
```

### Replace with:

```
- [ ] `experiments.enabled`: keep true, configure `auto_promote` based on confidence

---

## Sprint 31.91 — OCA Architecture & Reconciliation Drift

> Sprint 31.91 (Reconciliation Drift / Phantom-Short Fix + Alert Observability) is the sprint that closes DEF-204. **Live trading MUST NOT proceed until ALL of the following gates are satisfied.** Sprint 31.91 itself is a multi-week sprint; these checklist items become live-trading-blocking the moment 31.91 is sealed.

### Sprint 31.91 must be sealed (all 18 sessions complete)

- [ ] Sessions 0 + 1a + 1b + 1c (OCA architecture; DEC-386) — **LANDED 2026-04-27**, Tier 3 review #1 verdict PROCEED.
- [ ] Sessions 2a / 2b.1 / 2b.2 / 2c.1 / 2c.2 / 2d (side-aware reconciliation contract; DEC-385 reserved) — **NOT YET LANDED.**
- [ ] Session 3 (DEF-158 retry side-check) — **NOT YET LANDED.**
- [ ] Session 4 (mass-balance + IMSR replay validation; pre-live-gate criteria 3a + 3b decomposition) — **NOT YET LANDED.**
- [ ] Sessions 5a.1 + 5a.2 + 5b + 5c + 5d + 5e (alert observability; DEC-388 reserved; resolves DEF-014) — **NOT YET LANDED.**

### Session 5a.1 (HealthMonitor consumer) is a HARD live-trading prerequisite

- [ ] Session 5a.1 lands. Until then, the new `cancel_propagation_timeout` and `phantom_short`/`phantom_short_retry_blocked` `SystemAlertEvent`s emitted by Sessions 1c / 2b / 3 are visible **only in logs** — there is no Command Center surface, no banner, no toast. A leaked-long position from a `cancel_propagation_timeout` (Session 1c's failure mode trade-off) would be invisible to anyone not actively tailing logs. Per Tier 3 review #1 Focus Area 1 caveat (2026-04-27), this is a strict gating condition, not a soft preference.

### Mass-balance + zero-alert gate (Session 4 deliverable)

- [ ] ≥3 paper-trading sessions with **zero `unaccounted_leak`** rows from `scripts/validate_session_oca_mass_balance.py logs/argus_YYYYMMDD.jsonl` (categorized variance per Sprint 31.91 SbC §H2).
- [ ] **Zero `phantom_short` alerts** across those same 3+ sessions.
- [ ] **Zero `phantom_short_retry_blocked` alerts** across those same 3+ sessions.
- [ ] **Zero `cancel_propagation_timeout` alerts** for EOD-flatten-path symbols across those same 3+ sessions (per Sprint 31.91 Session 1c failure-mode documentation; if this alert fires, operator manually flattens before next session).

### Pre-live paper stress test (gate criterion 3a per Sprint Spec §D7 HIGH #4)

- [ ] ≥1 paper-trading session under **live-config simulation:**
  - Paper-trading data-capture overrides removed (`daily_loss_limit_pct: 0.03`, `weekly_loss_limit_pct: 0.05`, `throttler_suspend_enabled: true`, `orb_family_mutual_exclusion: true` restored — see top of this file's "Config Files to Restore" section).
  - Risk limits restored to production values (10x quality_engine.yaml risk tiers, etc.).
  - Overflow capacity restored.
  - ≥10 entries placed during the session.
- [ ] Zero `phantom_short` alerts during the stress-test session.
- [ ] Zero `unaccounted_leak` mass-balance rows during the stress-test session.

### Live rollback policy (gate criterion 3b per Sprint Spec §D7 HIGH #4)

- [ ] First live-trading session caps position size at **$50–$500 notional** on a single operator-selected symbol.
- [ ] **Trigger condition:** any `phantom_short`, `phantom_short_retry_blocked`, or `cancel_propagation_timeout` alert during the live window triggers immediate suspension via operator-manual halt. (The formal `POST /api/v1/system/suspend` endpoint is deferred to DEF-210; until DEF-210 lands, suspension is operator-manual.)
- [ ] After session-end clean (no triggering alerts), expand to standard sizing on day 2.

### Spike script freshness (per Sprint 31.91 regression invariant 22 / HIGH #5)

- [ ] `scripts/spike-results/spike-results-YYYYMMDD.json` dated within the last 30 days.
- [ ] Verdict in that file is `PATH_1_SAFE`.
- [ ] Re-run `scripts/spike_ibkr_oca_late_add.py` before the live-trading transition decision (trigger registry per `docs/live-operations.md`'s OCA Architecture Rollback section).

### `bracket_oca_type` config posture for live

- [ ] Confirm `IBKRConfig.bracket_oca_type` is `1` in both `config/system.yaml` and `config/system_live.yaml` (default; the OCA architecture is enabled).
- [ ] If you've flipped to `0` for any rollback investigation, restore to `1` and restart ARGUS (RESTART-REQUIRED — mid-session flip explicitly unsupported per Sprint Spec §"Performance Considerations").

### Operator daily-flatten mitigation removal

- [ ] Once all gates above are satisfied, **operator daily flatten via `scripts/ibkr_close_all_positions.py` becomes optional rather than required.** Until that point — including throughout the entire Sprint 31.91 sprint window and the gate-satisfaction window — continue running it daily at session close.
```

---

## Application notes

- The new section is roughly 60 lines, inserted just before `## Cross-References`. Existing `## Cross-References` content is unchanged.
- Pattern matches the file's existing checkbox-driven format (square-bracket boxes with backticked field names).
- Each gate is independently checkable, so the operator can tick them off as Sessions 2a-d / 3 / 4 / 5a-e land.
- The "Operator daily-flatten mitigation removal" item is the operational endpoint of the entire sprint — the explicit unblock criterion for retiring the daily mitigation.

One surgical replacement. No other lines in `pre-live-transition-checklist.md` are touched.
