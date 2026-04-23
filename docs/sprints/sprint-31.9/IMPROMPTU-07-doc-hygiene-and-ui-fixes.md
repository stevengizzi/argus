# Sprint 31.9 IMPROMPTU-07: Doc-Hygiene + Small Ops + UI Bug Fixes Bundle

> Drafted Phase 1b. Paste into a fresh Claude Code session. This prompt is **standalone** — do not read other session prompts in this campaign.

## Scope

**Findings addressed (11 items in one bundle):**

### DEFs resolved
- **DEF-198** — Boot phase labels in `argus/main.py` show `[N/12]` but FIX-03 handoff described a 17-phase sequence. Reconcile: either renumber labels to `/17` and re-verify ordering, or correct the handoff docs.
- **DEF-189** — `scripts/revalidate_strategy.py:383` builds `config_overrides` with VectorBT-style flat param names, but BacktestEngine config path is dot-separated nested. Fix the mapping. (Bug fix only; re-run of contaminated revalidations is named-horizon-deferred to Sprint 33 Statistical Validation — do NOT re-run here.)
- **DEF-164** — Late-night ARGUS boot collides with after-hours auto-shutdown. Fix candidates: shutdown waits for init, or suppress auto-shutdown N min post-boot.
- **DEF-191** — Latent `TradeLogger.get_todays_pnl()` SQL-side UTC normalization. **Doc-only**: add a module-level comment + cross-ref from `CLAUDE.md`. No code change.
- **DEF-169** — `--dev` mode retired (informational only). Reclassify as CLOSED in CLAUDE.md; no code change.

### Apr 21 debrief residuals
- **F-05** — `trade.id[:8]` at `argus/analytics/trade_logger.py:126` and `decision_id[:8]` at `:648` truncate ULIDs to 8 chars, causing "duplicate trade_id" log confusion. Fix: `[:8]` → `[:12]`.
- **F-06** — MFE/MAE unit mismatch. Backend `CounterfactualTracker` stores `max_favorable_excursion` / `max_adverse_excursion` as dollar amounts. Frontend `ShadowTradesTab.tsx` displays them via `RMultipleCell` formatted as `${value.toFixed(2)}R`. Fix option (a) per debrief: convert to R-multiples in the REST response (divide by `entry_price - stop_price`), then display correctly.
- **F-08** — `PRIORITY_BY_WIN_RATE is not fully implemented` at `argus/core/risk_manager.py:622` emits WARNING 100+ times per session. Downgrade to DEBUG (or INFO) — this is a known unfinished-feature warning, not an operational alert.

### Non-DEF items
- **Cosmetic X1–X6** — main.py sprint/DEC/AMD archaeology comments per RUNNING-REGISTER "Outstanding code-level items." Specific set enumerated in FIX-03 close-out; trivially deletable.
- **Shadow-variant badge rendering** — `v2_*` / `v3_*` variants still show as greyed-out in the UI despite being active shadow variants. Fix in `argus/ui/src/utils/strategyConfig.ts` + wherever the Badge styling branches on variant status.
- **CLAUDE.md variant count clarification** — Debrief §B2 claimed "22 vs 15" discrepancy. **CLAUDE.md "22" is correct** (verified via `yaml.safe_load(config/experiments.yaml)` — 10 patterns × 2–3 variants each = 22). Add a one-liner to CLAUDE.md explaining the enumeration methodology so the same miscount doesn't recur.

**Files touched:**
- `argus/main.py` — DEF-198 phase label renumbering (if path (a) chosen) or no change (if path (b)); Cosmetic X1–X6 deletions
- `scripts/revalidate_strategy.py` — DEF-189 config_overrides param-name fix
- Candidate for DEF-164: `argus/main.py` or new `scripts/launch_monitor.sh` logic (suppress auto-shutdown post-boot)
- `argus/analytics/trade_logger.py` — F-05 lines 126 and 648
- `argus/intelligence/counterfactual.py` — F-06 backend: add `mfe_r` / `mae_r` computation
- `argus/api/routes/counterfactual.py` — F-06 REST response: include `mfe_r` / `mae_r` fields
- `argus/ui/src/api/types.ts` — F-06 TypeScript: add new fields
- `argus/ui/src/features/trades/ShadowTradesTab.tsx` — F-06 UI: switch columns from `max_favorable_excursion` (dollars) to `mfe_r` / `mae_r` (R-multiples)
- `argus/core/risk_manager.py:622` — F-08 log level downgrade
- `argus/ui/src/utils/strategyConfig.ts` — Shadow-variant badge rendering
- Possibly `argus/ui/src/components/Badge.tsx` or wherever greyed-out styling applies
- `CLAUDE.md` — DEF strikethroughs + handoff reconciliation (DEF-198 path (b)) + variant enumeration note
- `docs/sprint-history.md` or FIX-03 close-out — if DEF-198 path (b) chosen
- Test files: `tests/analytics/test_trade_logger.py` (F-05), `tests/api/test_counterfactual_route.py` (F-06), `tests/api/` or `tests/execution/` (F-08), Vitest frontend (F-06 UI + badge)

**Safety tag:** `safe-during-trading` — no runtime logic changes. Log-level tweaks, REST response shape additions (backward-compat: new fields only, existing fields preserved), UI styling, doc updates.

**Theme:** Consolidate 11 small items that share the "documentation, logging, or UI cosmetic" shape. None are safety-critical. Together they significantly improve operator experience and campaign hygiene.

## Pre-Session Verification (REQUIRED — do not skip)

### 1. Environment check

```bash
./scripts/launch_monitor.sh status 2>/dev/null || echo "monitor offline — OK"
# Paper trading MAY continue.
```

### 2. Baseline test run

```bash
python -m pytest --ignore=tests/test_main.py -n auto -q 2>&1 | tail -3
# Record PASS count here: __________ (baseline)
cd argus/ui && npx vitest run --reporter=dot 2>&1 | tail -5 && cd -
# Record Vitest count here: __________ (baseline)
```

**Expected baseline:** Post-IMPROMPTU-06 count. Obtain from that close-out.

### 3. Orphaned Vitest worker cleanup (required for frontend sessions)

```bash
pkill -f "vitest/dist/workers" 2>/dev/null; echo "Cleaned"
```

Unmocked WebSocket / EventSource hooks in jsdom can hang Vitest fork workers. This session touches UI components; clean first.

### 4. Branch & workspace

```bash
git checkout main
git pull --ff-only
git status  # Expected: clean
```

## Pre-Flight Context Reading

1. Read these files:
   - `docs/sprints/sprint-31.9/CAMPAIGN-CLOSE-PLAN.md` §"IMPROMPTU-07"
   - `CLAUDE.md` DEF-164, DEF-169, DEF-189, DEF-191, DEF-198 entries
   - `docs/sprints/sprint-31.9/debrief-2026-04-21.md` (Apr 21 debrief) §F-05, F-06, F-08 — detailed context for each
   - `docs/sprints/sprint-31.9/impromptu-01-log-ui-hygiene.md` — the original Apr-21 placeholder that scoped F-05/F-06/F-08 (this session retires that placeholder's scope)
   - `argus/main.py` lines 230–1120 — all phase label emissions for DEF-198
   - `docs/sprints/sprint-31.9/FIX-03-closeout.md` — what FIX-03 actually changed re: phase sequence (confirms path (a) vs (b) choice below)
   - `scripts/revalidate_strategy.py` lines 375–400 — DEF-189 config_overrides construction
   - `argus/analytics/trade_logger.py` lines 120–135 + 640–655 — F-05 sites
   - `argus/intelligence/counterfactual.py` lines 105–200 + 560–580 — MFE/MAE storage (F-06)
   - `argus/api/routes/counterfactual.py` full file — F-06 REST response shape
   - `argus/ui/src/features/trades/ShadowTradesTab.tsx` lines 30–40, 110–130, 410–490 — F-06 frontend
   - `argus/core/risk_manager.py` lines 614–630 — F-08 warning emission
   - `argus/ui/src/utils/strategyConfig.ts` — getStrategyLetter logic; variant rendering
   - `config/experiments.yaml` — variant count verification (expect 22)

2. Verify variant count before drafting the CLAUDE.md note:
   ```python
   python3 -c "
   import yaml
   with open('config/experiments.yaml') as f:
       d = yaml.safe_load(f)
   total = sum(len(v) for v in d['variants'].values() if isinstance(v, list))
   print(f'{total} variants across {len(d[\"variants\"])} patterns')
   "
   # Expected: 22 variants across 10 patterns
   ```

3. DEF-198 decision — the kickoff defaults to **path (b)** (correct the handoff docs) because:
   - Re-numbering 20+ phase labels is error-prone and cosmetic
   - The FIX-03 handoff's "17-phase" claim may have been an aspirational target never executed
   - The operational boot sequence works correctly regardless of the numbering label

   If after reading FIX-03-closeout.md you determine path (a) (renumber labels) is appropriate, document the decision in the close-out with rationale.

## Objective

Close 5 DEFs (DEF-164, DEF-169, DEF-189, DEF-191, DEF-198) + 3 Apr 21 debrief
residuals (F-05, F-06, F-08) + 3 non-DEF items (Cosmetic X1-X6, shadow-variant
badge, CLAUDE.md variant count clarification) in one bundled session.

## Requirements

### Requirement 1: DEF-198 — Boot phase labels

**Recommended path (b): correct the handoff docs.**

1. Verify actual phase count via grep: `grep -E "^\s*logger\.info\(\"\[[0-9]" argus/main.py` — count distinct phase numbers.
2. Update `docs/sprints/sprint-31.9/FIX-03-closeout.md` and `docs/project-knowledge.md` (if they claim 17 phases) to reflect the actual boot sequence phase count.
3. In `CLAUDE.md` DEF-198 entry, mark as RESOLVED-VERIFIED with commit SHA + one-line explanation: "handoff reconciled against actual boot log — there are N phases; the 17-phase number was aspirational."

**Alternative path (a):** if operator wants labels actually renumbered, do so in `argus/main.py` — renumber all `[N/12]` (and `[10.3/12]` style half-phases) to a consistent `[M/K]` scheme where K is the true phase count.

### Requirement 2: DEF-189 — revalidate_strategy.py config_overrides

1. At `scripts/revalidate_strategy.py:383`, the current code is:
   ```python
   config_overrides = {f"{yaml_name}.{k}": v for k, v in fixed_params.items()}
   ```
   This produces keys like `"orb_breakout.or_minutes": 30`, but `OrbBreakoutConfig` uses `orb_window_minutes`, not `or_minutes`. Under the post-FIX-09 strict-dot-path behavior, these silently no-op.

2. Add a param-name mapping dict for each supported strategy:
   ```python
   _PARAM_NAME_MAP = {
       "orb_breakout": {
           "or_minutes": "orb_window_minutes",
           # ... other known renames
       },
       # ... per strategy
   }

   def _translate_params(strategy_key: str, fixed_params: dict) -> dict:
       mapping = _PARAM_NAME_MAP.get(strategy_key, {})
       return {mapping.get(k, k): v for k, v in fixed_params.items()}
   ```

3. Alternatively (cleaner): inspect each `*Config` Pydantic model at runtime and validate that every `fixed_params` key maps to a real field. Raise `ValueError` on mismatch.

4. Add a regression test at `tests/scripts/test_revalidate_strategy.py` (new if needed) that constructs a `config_overrides` dict with a known param name and asserts the resulting BacktestEngineConfig has the override actually applied (not silently dropped).

5. **Do NOT re-run** any contaminated revalidations. That's Sprint 33 scope. Log a DEF-189 annotation in the close-out pointing at Sprint 33 for the re-run.

### Requirement 3: DEF-164 — Late-night boot auto-shutdown collision

1. The existing scenario per CLAUDE.md: operator boots ARGUS late at night to verify service init; auto-shutdown fires before HistoricalQueryService completes VIEW creation; interrupted DuckDB operation then hangs the shutdown path.
2. Simplest fix: add a `boot_grace_period_minutes` config field (default 10) to `config/system.yaml` under a new `shutdown:` section. The auto-shutdown handler checks `time_since_boot < boot_grace_period_minutes` and skips shutdown if so (logs a deferral).
3. Alternative: the shutdown path already handles the DEF-165 interrupt-close cleanup; if that's sufficient, upgrade the close-out hang robustness instead.
4. Regression test: `tests/core/test_boot_grace.py` — assert the auto-shutdown skips when boot time < grace period.

If either fix touches more than ~30 LOC, scope-check: this is an "IMPROMPTU-07 small ops" item. If bigger, document in close-out, apply the simpler fix (e.g., just increase grace period config), and leave the larger refactor as a deferred annotation on DEF-164.

### Requirement 4: DEF-191 — SQL-side UTC normalization (doc-only)

1. In `argus/analytics/trade_logger.py` at the `get_todays_pnl()` method, add a module-level comment:
   ```python
   # NOTE (DEF-191, 2026-04-23): SQLite's date() function normalizes stored
   # ISO timestamps with tz offsets to UTC before extracting the date. For
   # market-hours-only trades (exits 9:30–16:00 ET), the UTC date equals
   # the ET date, so this query works correctly. If ARGUS ever supports
   # after-hours trading (pre-market >= 4:00 ET or after-hours <= 20:00 ET),
   # trades exiting in the 20:00–24:00 ET window would be miscounted.
   # Resolution deferred to a future after-hours-trading sprint.
   ```
2. Update `CLAUDE.md` DEF-191 entry with strikethrough and "RESOLVED-DOC-ONLY" annotation + commit SHA. No code change.

### Requirement 5: DEF-169 — `--dev` mode retired

1. No code change. The `--dev` mode was already removed by FIX-11.
2. In `CLAUDE.md`, update DEF-169 from open/informational to **strikethrough CLOSED** with the annotation: "resolved-verified 2026-04-23: `dev_state.py` deleted by FIX-11 (commit fc7eb7c); `--dev` mode retirement complete; no open follow-up."

### Requirement 6: Apr 21 F-05 — ULID log-truncation width

1. In `argus/analytics/trade_logger.py`:
   - Line 126: `trade.id[:8]` → `trade.id[:12]`
   - Line 648: `decision_id[:8]` → `decision_id[:12]`
2. Regression test in `tests/analytics/test_trade_logger.py` — assert the log message contains the 12-char prefix, not 8.

### Requirement 7: Apr 21 F-06 — MFE/MAE unit fix

**Option (a) from the debrief: convert to R-multiples in the REST response.**

1. In `argus/api/routes/counterfactual.py`, the `get_counterfactual_positions` endpoint (line ~75): when serializing each position, compute the R-multiples:
   ```python
   def _compute_r_multiple(excursion: float, entry: float, stop: float) -> float | None:
       risk = abs(entry - stop)
       if risk <= 0:
           return None
       return excursion / risk

   # In the position serialization:
   position_dict = {
       ...existing fields...
       "mfe_r": _compute_r_multiple(pos.max_favorable_excursion, pos.entry_price, pos.stop_price),
       "mae_r": _compute_r_multiple(pos.max_adverse_excursion, pos.entry_price, pos.stop_price),
   }
   ```
   Preserve the existing `max_favorable_excursion` / `max_adverse_excursion` fields (backward compat). Add `mfe_r` / `mae_r` as new fields.
2. In `argus/ui/src/api/types.ts`, add the two new fields:
   ```typescript
   mfe_r: number | null;
   mae_r: number | null;
   ```
3. In `argus/ui/src/features/trades/ShadowTradesTab.tsx`:
   - Update the sort-key type union (lines 35–36) to add `'mfe_r' | 'mae_r'` (keep the dollar fields for now; operator can opt to remove later)
   - Change the cell rendering at lines 477, 480 from `<RMultipleCell value={trade.max_favorable_excursion} />` to `<RMultipleCell value={trade.mfe_r} />` (and same for `mae_r`)
   - Update column headers if they currently say "MFE ($)" / "MAE ($)" — should now read "MFE (R)" / "MAE (R)"
4. Regression tests:
   - `tests/api/test_counterfactual_route.py` — assert `mfe_r` and `mae_r` fields present in response; assert correct R-multiple calculation for a known-value fixture
   - Frontend Vitest: update `ShadowTradesTab.test.tsx` fixture data to include `mfe_r`/`mae_r` fields + assert display format is `+1.23R` etc.

### Requirement 8: Apr 21 F-08 — PRIORITY_BY_WIN_RATE log level

1. In `argus/core/risk_manager.py:622`, change `logger.warning(` → `logger.debug(` (or `logger.info(` — debug preferred since this is a known-unfinished-feature notification, not even informational-grade).
2. No regression test needed for this one-liner; existing tests still pass.

### Requirement 9: Cosmetic X1–X6 archaeology comments

1. Consult `docs/sprints/sprint-31.9/FIX-03-closeout.md` (or the RUNNING-REGISTER outstanding-items table) for the specific X1–X6 designation.
2. Delete the 6 cosmetic comments from `argus/main.py`.
3. If the exact X1–X6 list cannot be found, grep for `# Sprint [0-9]+:|# DEC-[0-9]+|# AMD-[0-9]+` that appear isolated on their own line (not as part of a logical block header) and delete those that are pure archaeology. Err on the side of keeping anything that provides current context.

### Requirement 10: Shadow-variant badge rendering

1. In the UI, shadow variants (`strat_*__v2_*`, `strat_*__v3_*`) appear greyed out even when they're active shadow variants (per `config/experiments.yaml`).
2. Investigate `argus/ui/src/utils/strategyConfig.ts`'s `getStrategyLetter` function and the Badge styling logic. The likely root cause: the greyed-out style is conditional on a `mode === 'retired'` or similar status check, and shadow variants are being misclassified as retired.
3. Fix: shadow variants should have their own visual status (perhaps a distinct color or a subtle "shadow" indicator) rather than greyed-out. Consult existing Badge variants (live vs retired vs shadow) and route shadow to a visually-active style.
4. Vitest regression: `Badge.test.tsx` (if exists, else add) — assert a shadow-variant strategy ID renders with the active-shadow style, not the retired-style.

### Requirement 11: CLAUDE.md variant enumeration note

1. In `CLAUDE.md` near the line "22 shadow variants collecting CounterfactualTracker data," add a brief clarifying footnote or inline parenthetical:
   ```
   > **Variant count methodology:** The "22 variants" figure is computed via
   > `yaml.safe_load(config/experiments.yaml)['variants']` — 10 base patterns
   > × 2–3 named variants each. Casual enumeration of only the named sub-
   > variants (e.g., `__v2_tight_dip`, `__v3_strict_volume`) misses the base
   > `_v1` entries and underestimates to 15; confirm via parsed YAML.
   ```
2. Also update `docs/project-knowledge.md` if it mentions the count.

## Constraints

- **Do NOT modify** the storage schema for `CounterfactualPosition` or `counterfactual_positions` SQLite table (F-06). The R-multiples are computed at serialization time, not stored.
- **Do NOT remove** the existing `max_favorable_excursion` / `max_adverse_excursion` fields from the REST response — those may have downstream consumers (F-06 is additive).
- **Do NOT re-run** any contaminated revalidations from DEF-189. Bug fix only.
- **Do NOT change** the phase-label renumbering to path (a) unless the operator explicitly sanctions; default is path (b) (doc correction).
- **Do NOT rewrite** the JWT, reconciliation, or order-manager code paths in this session — those are other impromptus' scope.
- **Do NOT modify** the `workflow/` submodule (Universal RULE-018).
- Work directly on `main`.

## Test Targets

- New tests: +3 to +6 (F-05 log format, F-06 REST response shape + frontend fixtures, DEF-189 override regression, DEF-164 grace period if implemented)
- Net test delta: **+3 to +6** (pytest) + **+1 to +3** (Vitest for F-06 + badge)
- Test commands:
  ```bash
  python -m pytest tests/analytics/ tests/api/test_counterfactual_route.py tests/scripts/ -xvs -n 0
  cd argus/ui && npx vitest run --reporter=dot && cd -
  # Full suite:
  python -m pytest --ignore=tests/test_main.py -n auto -q
  ```

## Visual Review (frontend changes)

After F-06 + badge work, the operator should visually verify:
1. **Shadow Trades page:** MFE and MAE columns now display R-multiples (e.g., `+1.23R`, `-0.85R`), not tiny dollar values like `+0.00R` (which was the debrief symptom).
2. **Strategy badge display:** shadow variants (`__v2_*`, `__v3_*`) no longer appear greyed out — they should have a distinct "active shadow" visual status.
3. **Dashboard + Trades pages:** verify no regression on existing badge rendering for live + retired strategies.

Verification conditions:
- With experiments enabled in config (`experiments.enabled: true`)
- With sample data: at least one closed shadow position in `counterfactual_positions` table
- Browser DevTools network tab: inspect the `/counterfactual/positions` response to confirm `mfe_r` / `mae_r` fields present

## Definition of Done

- [ ] All 11 requirements implemented
- [ ] All existing tests pass (pytest + Vitest)
- [ ] +3 to +6 new pytest tests
- [ ] +1 to +3 new Vitest tests (F-06 + badge)
- [ ] `CLAUDE.md` DEF-164, DEF-169, DEF-189, DEF-191, DEF-198 all updated with strikethrough + commit SHA (DEF-169 marked RESOLVED-VERIFIED with FIX-11 reference; DEF-191 marked RESOLVED-DOC-ONLY)
- [ ] `CLAUDE.md` "22 shadow variants" line annotated with enumeration methodology footnote
- [ ] `docs/project-knowledge.md` updated if it mentions variant count
- [ ] If path (b) chosen for DEF-198: FIX-03 handoff docs corrected
- [ ] Apr 21 debrief `docs/debriefs/debrief-2026-04-21.md` §F-05, F-06, F-08 entries annotated with **RESOLVED IMPROMPTU-07** + commit SHA
- [ ] Apr 21 impromptu-01 placeholder file (`impromptu-01-log-ui-hygiene.md`) annotated at top with "Scope executed by IMPROMPTU-07 2026-04-23; file retained for archive reference only"
- [ ] `RUNNING-REGISTER.md` updated: DEFs moved to "Resolved this campaign" table
- [ ] `CAMPAIGN-COMPLETENESS-TRACKER.md` Stage 9B row for IMPROMPTU-07 marked CLEAR
- [ ] Close-out at `docs/sprints/sprint-31.9/IMPROMPTU-07-closeout.md`
- [ ] Tier 2 review at `docs/sprints/sprint-31.9/IMPROMPTU-07-review.md`
- [ ] Green CI URL cited (P25 rule)

## Regression Checklist (Session-Specific)

| Check | How to Verify |
|-------|---------------|
| Phase labels reconciled (path (a) or (b)) | Read CLAUDE.md + `argus/main.py`; they agree |
| `revalidate_strategy.py` config_overrides produces valid dot-paths | Regression test |
| Log messages include 12-char ULID prefix (F-05) | New pytest |
| `/counterfactual/positions` response includes `mfe_r` + `mae_r` | New pytest |
| Shadow Trades UI displays R-multiples not dollar values | Visual review + Vitest |
| Shadow variants no longer greyed out in UI | Visual review |
| `PRIORITY_BY_WIN_RATE` warning downgraded to DEBUG | Log-capture test in existing risk_manager tests |
| CLAUDE.md variant count annotation added | Manual doc read |
| Apr 21 placeholder file annotated | Manual doc read |
| No revalidation runs executed during this session | Grep commit diff for any `revalidate_strategy.py` output files |
| Full suite net delta ≥ +3 | Test count comparison |
| Vitest net delta ≥ +1 | Vitest count comparison |

## Close-Out

Write close-out to: `docs/sprints/sprint-31.9/IMPROMPTU-07-closeout.md`

Include:
1. **DEF-198 path decision** (path (a) renumber labels, or path (b) correct handoff docs) with rationale
2. **DEF-189 fix verification:** grep + regression test demonstrating the old silent-no-op behavior is now a strict-dot-path correct mapping
3. **F-06 REST response schema:** example JSON showing `mfe_r` / `mae_r` alongside preserved `max_favorable_excursion` / `max_adverse_excursion` fields
4. **UI changes visual-verification checklist** for operator
5. **Apr 21 placeholder retirement note:** confirm `impromptu-01-log-ui-hygiene.md` has been annotated as executed
6. **Green CI URL** for final commit

## Tier 2 Review (Mandatory — @reviewer subagent, standard profile)

Invoke @reviewer after close-out writes.

Provide:
1. Review context: this kickoff file + CLAUDE.md DEF entries + Apr 21 debrief §F-05/F-06/F-08
2. Close-out path: `docs/sprints/sprint-31.9/IMPROMPTU-07-closeout.md`
3. Diff range: `git diff HEAD~N`
4. Test command: `python -m pytest --ignore=tests/test_main.py -n auto -q` + `cd argus/ui && npx vitest run && cd -`
5. Files that should NOT have been modified:
   - Any workflow/ submodule file
   - Any audit-2026-04-21 doc back-annotation
   - `argus/execution/order_manager.py` (IMPROMPTU-06 scope)
   - `argus/api/auth.py` or JWT-related files (IMPROMPTU-05 scope)
   - `config/experiments.yaml` (not this session's scope to modify)
   - `CounterfactualPosition` SQLite schema

The @reviewer writes to `docs/sprints/sprint-31.9/IMPROMPTU-07-review.md`.

## Session-Specific Review Focus (for @reviewer)

1. **Verify F-06 is backward-compatible.** The REST response must still include `max_favorable_excursion` and `max_adverse_excursion` (dollars); new fields are additive only. Any consumer relying on the dollar fields must still work.
2. **Verify DEF-189 fix handles all strategy types.** The `_PARAM_NAME_MAP` (or equivalent validation) must cover every strategy that `revalidate_strategy.py` can target. An unchecked strategy would silently no-op again.
3. **Verify shadow-variant badge fix is visual not structural.** The Badge logic should route based on `strategy.mode` or `strategy.status`, not on arbitrary name-pattern matching. Name-based heuristics are brittle.
4. **Verify DEF-198 path decision is documented.** The close-out must state the decision explicitly; CLAUDE.md DEF-198 must reflect the chosen path.
5. **Verify no DEF-189 re-run was executed.** Check the diff for any `output_dir` or `data/revalidation/` file changes; there should be none.
6. **Verify Apr 21 placeholder file annotation.** The operator's request is to track that this session retires that scope; the annotation must exist.
7. **Verify variant count methodology note is in CLAUDE.md.**
8. **Verify green CI URL for final commit.**

## Sprint-Level Regression Checklist (for @reviewer)

- pytest net delta ≥ +3
- Vitest net delta ≥ +1 (this is a UI-touching session)
- No scope boundary violation
- CLAUDE.md DEF strikethroughs present

## Sprint-Level Escalation Criteria (for @reviewer)

Trigger ESCALATE if ANY of:
- Existing `/counterfactual/positions` REST response breaks backward compatibility
- `CounterfactualPosition` SQLite schema modified
- `revalidate_strategy.py` re-run with contaminated params executed
- Phase-label renumbering path (a) chosen without operator authorization
- Shadow-variant Badge logic changed via name-pattern heuristic (fragile — should be status-based)
- Vitest worker hang during test run (unmocked hook)
- Full pytest suite net delta < +3
- Green CI URL missing or CI red
- Audit-report back-annotation modified
- Apr 21 placeholder file NOT annotated post-execution

## Post-Review Fix Documentation

Standard protocol per the implementation-prompt template.

## Operator Handoff

1. Close-out markdown block
2. Review markdown block
3. **DEF-198 path decision:** path (a) renumber or path (b) doc-correct
4. **F-06 API change:** new fields list + backward-compat note
5. **Visual review items** (Shadow Trades MFE/MAE in R, shadow-variant badges no longer grey)
6. **Apr 21 placeholder retirement note**
7. Green CI URL
8. One-line summary: `Session IMPROMPTU-07 complete. Close-out: {verdict}. Review: {verdict}. Commits: {SHAs}. Test delta: {pre} → {post} pytest, {pre} → {post} Vitest. CI: {URL}. DEFs closed: DEF-164, DEF-169, DEF-189, DEF-191, DEF-198 + Apr 21 F-05/F-06/F-08.`
