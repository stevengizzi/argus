# Doc-Sync Patch 2 — `docs/dec-index.md`

**Purpose:** (a) Add a Sprint 31.91 section to the index after the Sprint 31.9 entry, listing DEC-386 with its Tier-3-reviewed status. (b) Update the header counts and the `Next DEC` footer.

**Anchor verification (must hold before applying):**
- Line 1: `# ARGUS — Decision Index`
- Line 3: `> 384 decisions (DEC-001 through DEC-384)`
- Line 4: `> Generated: April 21, 2026 (FIX-01 audit — DEC-384 load_config standalone overlay) | Source: \`docs/decision-log.md\``
- Lines 507–511: Sprint 31.9 — Campaign-Close section + `Next DEC: 385.` footer.

---

## Patch A — Update header (3 lines)

### Find:

```
# ARGUS — Decision Index

> 384 decisions (DEC-001 through DEC-384)
> Generated: April 21, 2026 (FIX-01 audit — DEC-384 load_config standalone overlay) | Source: `docs/decision-log.md`
> Legend: ● Active | ○ Superseded | △ Amended | ✗ Duplicate entry
```

### Replace with:

```
# ARGUS — Decision Index

> 385 decisions (DEC-001 through DEC-386, with DEC-385 reserved for Sprint 31.91 Sessions 2a-d)
> Generated: April 27, 2026 (Sprint 31.91 Tier 3 review #1 — DEC-386 OCA-group threading + broker-only safety) | Source: `docs/decision-log.md`
> Legend: ● Active | ○ Superseded | △ Amended | ✗ Duplicate entry | ⊘ Reserved
```

---

## Patch B — Append Sprint 31.91 section + update footer

### Find (the existing Sprint 31.9 closing block):

```
## Sprint 31.9 — Campaign-Close (April 22 – April 24, 2026)

No new DECs across 11 named sessions + 3 paper-session debriefs. All design decisions followed established patterns. See `docs/decision-log.md` Sprint 31.9 entry for per-session rationale. Sprint outcomes summarized in `docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md`.

Next DEC: 385.
```

### Replace with:

```
## Sprint 31.9 — Campaign-Close (April 22 – April 24, 2026)

No new DECs across 11 named sessions + 3 paper-session debriefs. All design decisions followed established patterns. See `docs/decision-log.md` Sprint 31.9 entry for per-session rationale. Sprint outcomes summarized in `docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md`.

## Sprint 31.91 — Reconciliation Drift / Phantom-Short Fix + Alert Observability (April 27, 2026 onward)

DEC-385 / 387 / 388 reserved during Sprint 31.91 planning. DEC-386 written following Tier 3 architectural review #1 (CLEAR, 2026-04-27) covering Sessions 0+1a+1b+1c.

- ⊘ **DEC-385**: RESERVED — Side-aware reconciliation contract (Sessions 2a / 2b.1 / 2b.2 / 2c.1 / 2c.2 / 2d). Will be written at Session 2d close.
- ● **DEC-386**: OCA-group threading + broker-only safety — 4-layer architecture: (1) `Broker.cancel_all_orders(symbol, *, await_propagation)` ABC extension + `CancelPropagationTimeout` exception (S0); (2) bracket OCA grouping with `ocaGroup=f"oca_{parent_ulid}"` + `ocaType=1` on children only + `ManagedPosition.oca_group_id` + Error-201/OCA-filled distinguishing helper (S1a); (3) standalone-SELL OCA threading on 4 paths + `redundant_exit_observed` SAFE-outcome marker + grep regression guard with `# OCA-EXEMPT:` exemption mechanism (S1b); (4) broker-only safety via cancel-then-SELL/wire on 3 paths + `reconstruct_from_broker` STARTUP-ONLY contract docstring + `_emit_cancel_propagation_timeout_alert` shared helper (S1c). Closes ~98% of DEF-204's mechanism per IMPROMPTU-11. Tier 3 PROCEED verdict 2026-04-27. Cross-refs: DEF-211 (Sprint 31.93 `ReconstructContext` parameter), DEF-212 (Sprint 31.92 `IBKRConfig` wiring into `OrderManager`), Phase A spike `PATH_1_SAFE` (2026-04-25).
- ⊘ **DEC-387**: RESERVED — Placeholder; allocation TBD during Session 3 / Session 4 planning if a non-trivial design decision surfaces.
- ⊘ **DEC-388**: RESERVED — Alert observability architecture (Sessions 5a.1 / 5a.2 / 5b / 5c / 5d / 5e). Resolves DEF-014. Will be written at Session 5e close.

Next DEC: 387 (385/388 reserved as noted above).
```

---

## Application notes

- The `⊘ Reserved` legend entry is new; the symbol is added to the legend (Patch A) and used at four ⊘ entries (DEC-385, 387, 388 in Patch B; DEC-385 will eventually be marked ● when Sessions 2a-d close).
- The `385 decisions (DEC-001 through DEC-386, with DEC-385 reserved...)` count is **deliberately phrased**: the highest written DEC is 386, but two intervening numbers (385 and 387 in the reserved block) are not yet "decisions" — only one numbered slot has been filled in this sprint, but it lands at 386 not 385. The header text makes that explicit so a reader scanning for DEC-385 doesn't think the file is missing it.

Apply with two surgical replacements per the find/replace blocks above. No other lines in `dec-index.md` are touched.
