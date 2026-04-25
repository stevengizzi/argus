# Sprint `post-31.9-alpaca-retirement` Discovery Notes

> Discovery-grade seed doc. Written at Sprint 31.9 SPRINT-CLOSE-A on 2026-04-24.
> Enough context to start a planning conversation without re-reading the full
> Sprint 31.9 history.
> **Not a plan; not a spec.** Planning conversation produces the actual sprint
> package.

## Sprint Identity

- **Sprint ID:** `post-31.9-alpaca-retirement`
- **Predecessor:** Sprint 31.9 (Health & Hardening campaign-close)
- **Build-track position:** post-31.9 named horizon. LOW priority — no active
  runtime harm (the Alpaca code paths are never selected in production
  config) but the dead branches are ongoing maintenance drag and the
  `alpaca-py` dependency is at core-runtime scope despite being incubator-only
  per DEC-086.
- **Discovery date:** 2026-04-24

## Theme

Fully retire the AlpacaBroker incubator path that was demoted in Sprint 21.6
(DEC-086) but never structurally removed.

Today (April 2026) `alpaca-py` is still listed in core `[project.dependencies]`
in `pyproject.toml`, four runtime files still `import alpaca*`
(`argus/execution/alpaca_broker.py`, `argus/data/alpaca_data_service.py`,
`argus/data/alpaca_scanner.py`, `argus/backtest/data_fetcher.py`), and
`argus/main.py:301-317` / `:339-346` carry `DataSource.ALPACA` /
`BrokerSource.ALPACA` branches that production config (`system_live.yaml`)
never selects.

This sprint moves `alpaca-py` to `[project.optional-dependencies.incubator]`
extras (DEF-178), removes the dead Alpaca-specific code/test paths from the
main argus runtime (DEF-183), and lands the remaining DEF-014 SystemAlertEvent
emission in `alpaca_data_service.py:593` (one of three sites flagged by FIX-06;
the IBKR sites live in `post-31.9-reconnect-recovery-and-rejectionstage`,
this Alpaca site is removed when DEF-183 lands).

## Deferred-Items Scope

DEFs explicitly queued for this sprint:

| DEF # | Title | Source | Notes |
|---|---|---|---|
| DEF-178 | `alpaca-py` core dep → `[incubator]` extras | CLAUDE.md (FIX-18 left in place with inline pointer) | LOW. Move to `[project.optional-dependencies].incubator`; feature-detect at the 4 import sites; gate activation via `BrokerSource.ALPACA` / `DataSource.ALPACA`. |
| DEF-183 | Full Alpaca code+test retirement | CLAUDE.md (FIX-06 P1-C2-10 flagged via config reachability) | LOW. Delete `argus/data/alpaca_data_service.py`, `argus/data/alpaca_scanner.py`, `argus/execution/alpaca_broker.py` + their test modules; simplify `argus/main.py:301-317` / `:339-346` to a single Databento+IBKR live path; update `system.yaml` defaults. **Pairs with DEF-178** — both should land in the same session if scope permits. |
| DEF-014 Alpaca emitter TODO | `argus/data/alpaca_data_service.py:593` | CLAUDE.md (FIX-06 partial) | LOW. The TODO disappears with DEF-183's deletion of the file. Listed for accounting clarity. |

Total: 3 items in scope (DEF-014 effectively folded into DEF-183).

## Known Dependencies / Constraints

- **No dependencies on other post-31.9 sprints.** Alpaca retirement is fully
  isolated from the reconciliation-drift / reconnect-recovery / component-ownership
  workstreams.
- **`pyproject.toml` move + lockfile regen.** The `alpaca-py` extras move
  requires regenerating `requirements.lock` + `requirements-dev.lock` per
  the IMPROMPTU-05 lockfile workflow (`docs/deps.md`). The `incubator` extra
  was deliberately excluded from the existing lockfiles in DEF-180 closure;
  this sprint adds it back.
- **CI workflow update.** The `pip install -e . --no-deps` line in
  `.github/workflows/ci.yml` should remain unchanged; the `incubator` extra
  is opt-in and not required for CI.
- **Verify production config doesn't reach `BrokerSource.ALPACA`.** Spot-check
  `system_live.yaml` and any operator deployment scripts before deletion.

## Open Questions (for planning conversation)

- Should DEF-178 and DEF-183 land in a single session (mechanical refactor,
  ~1 session) or split (DEF-178 lockfile move first, DEF-183 code deletion
  second)?
- Are there any Alpaca-related tests in `tests/integration/historical/`
  (FIX-13b moved sprint-dated tests there) that need to be updated alongside
  the deletion?
- Does `system.yaml` (the legacy Alpaca-incubator config) get deleted entirely
  or kept as a stub that points to `system_live.yaml`?

## Adversarial Review Profile

- **Standard Tier 2** review. Mechanical refactor; deletion of dead code
  paths that are never reached at runtime; no live trading risk.

## Context Pointers

- Sprint 31.9 summary: `docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md`
- DEC-086 (Alpaca incubator demotion, Sprint 21.6 pivot): `docs/decision-log.md`
- IMPROMPTU-05 closeout (lockfile workflow + `docs/deps.md` regen recipe):
  `docs/sprints/sprint-31.9/IMPROMPTU-05-closeout.md`
- Build-track queue: `docs/roadmap.md`

## Not-in-Scope

- IBKR emitter TODOs (`ibkr_broker.py:453,531`) — these live in
  `post-31.9-reconnect-recovery-and-rejectionstage`.
- Any change to the live Databento + IBKR runtime path beyond removing the
  ALPACA branches.
- Renaming `BrokerSource` / `DataSource` enums (the values can drop ALPACA
  members; the enums themselves stay).

## Pre-Planning Checklist

- [ ] All DEFs in scope still OPEN (verify CLAUDE.md)
- [ ] No dependencies blocked
- [ ] Build-track queue supports starting this sprint
- [ ] Sprint 31.9 SPRINT-CLOSE-B core-doc sync has landed (so docs reflect current state)
- [ ] Operator confirms no in-flight Alpaca-related deployment work
