# Sprint 31.9 + Post-31.9 Campaign — Completeness Tracker

<!-- last-updated: 2026-04-23 (Stage 8 Wave 3 / FIX-13c complete) -->
<!-- canonical-source: true — this is the single master tracker; hydrate new conversations from here -->

## Purpose

This document tracks EVERY outstanding item across Sprint 31.9 Health &
Hardening and the planned post-31.9 Component Ownership Consolidation sprint.
The definition of "campaign complete" is that every line in every table below
is either RESOLVED, PLANNED-WITH-SESSION-ASSIGNED, or EXPLICITLY-DEFERRED with
a named future sprint.

Zero orphans, zero "we'll get to it eventually" items.

When the entire tracker shows RESOLVED for every row, the campaign is complete
and this document can be archived to `docs/sprints/archive/`.

## Stage progress

| Stage | Sessions | Status | Date |
|---|---|---|---|
| Stage 1 | FIX-00, FIX-15, FIX-17, FIX-20, FIX-01, FIX-11 + sweep | ✅ CLEAR | Pre-campaign-sealing |
| Stage 2 | FIX-02, FIX-03, FIX-12, FIX-19, FIX-21 | ✅ CLEAR | Pre-campaign-sealing |
| Impromptu (2→3) | DEF-172, DEF-173, DEF-175 (opened) | ✅ CLEAR | Pre-campaign-sealing |
| Stage 3 Wave 1 | FIX-14, FIX-16 | ✅ CLEAR | 2026-04-21 |
| Stage 3 Wave 2 | FIX-04 | ✅ CLEAR (Rule-4, gold-standard proof) | 2026-04-21 |
| Stage 4 Wave 1 | FIX-10, FIX-18 | ✅ CLEAR | 2026-04-22 |
| Stage 4 Wave 2 | FIX-05 | ✅ CLEAR | 2026-04-22 |
| **Stage 4** | **(complete)** | **✅ COMPLETE** | **2026-04-22** |
| Stage 5 Wave 1 | FIX-06 (data) | ✅ CLEAR | 2026-04-22 |
| Stage 5 Wave 2 | FIX-07 (intelligence/catalyst/quality) | ✅ CLEAR | 2026-04-22 |
| **Stage 5** | **(complete)** | **✅ COMPLETE** | **2026-04-22** |
| Stage 6 | FIX-08 (experiments + learning loop, solo) | ✅ CLEAR | 2026-04-22 |
| **Stage 6** | **(complete)** | **✅ COMPLETE** | **2026-04-22** |
| Stage 7 | FIX-09 (backtest-engine, solo) + IMPROMPTU-03 (CI tz flakes) | ✅ CLEAR / CLEAN | 2026-04-22 |
| **Stage 7** | **(complete)** | **✅ COMPLETE** | **2026-04-22** |
| Stage 8 Wave 1 | FIX-13a (test hygiene — tactical, solo) | ✅ CLEAR | 2026-04-23 |
| Stage 8 Wave 2 | FIX-13b (test hygiene — refactors, solo, 7 findings) | ✅ CONCERNS_RESOLVED | 2026-04-23 |
| Stage 8 Wave 3 | FIX-13c (ai-copilot-coverage, solo, F13 carry-over) | ✅ CLEAR | 2026-04-23 |
| Stage 8 Parallel | IMPROMPTU-01 (LIVE OK, parallel if scope-safe) | ⏸ PENDING | TBD |
| **Stage 8** | **(complete when both waves close)** | ⏸ PENDING | TBD |
| Stage 9A/B | IMPROMPTU-02 (scope TBD) | ⏸ PENDING | TBD |
| **Sprint 31.9** | | ⏸ IN PROGRESS | |
| Post-31.9 | Component Ownership Consolidation (DEF-175) | ⏸ PLANNED | After 31.9 closes |
| **Campaign** | | ⏸ IN PROGRESS | |

## CI infrastructure status

First fully passing CI at commit `793d4fd` (2026-04-22).
- pytest: ≈ 4,987 (local) / CI non-integration count pending next run (post-FIX-13a; up from 4,980 at IMPROMPTU-03 via +7 tactical test additions — DEF-190 regression guard + DEF-171 fixture counter coverage + F19 narrowing + DEF-150 time-window guard + date-decay conversion assertions)
- Vitest: 859 passed / 115 files (unchanged since Stage 5)
- Workflow: `.github/workflows/ci.yml`, Python 3.11.15, Node 20 (deprecation warning active — see DEF-181)
- Known flakes monitored in CI: DEF-150 ✅ closed, DEF-167 ✅ closed (scope-noted), DEF-171 ✅ closed, DEF-190 ✅ closed, DEF-192 PARTIAL (numpy cast closed; 5 categories remain)
- CI-green milestone means zero-tolerance on flakes is enforceable going forward: any red CI run is a real bug until proven otherwise

**Post-Stage-8 Wave 3 expected counts:** 5,039 pytest + 859 Vitest (+52 pytest from FIX-13c AI coverage expansion; Vitest unchanged).

## Sessions remaining (Sprint 31.9)

| Session | Scope | Stage |
|---|---|---|
| ~~FIX-13a~~ | ~~Test hygiene — tactical~~ | ~~Stage 8 Wave 1~~ ✅ CLEAR |
| ~~FIX-13b~~ | ~~Test hygiene — refactors (7 findings)~~ | ~~Stage 8 Wave 2~~ ✅ CONCERNS_RESOLVED |
| ~~FIX-13c~~ | ~~Test hygiene — AI Copilot coverage (Finding 13)~~ | ~~Stage 8 Wave 3~~ ✅ CLEAR |
| IMPROMPTU-01 | (scope TBD — Stage 8 Parallel slot) | Stage 8 Parallel |
| IMPROMPTU-02 | (scope TBD — 9A scoping + 9B fix) | Stage 9A / 9B |
| Sprint 31.9 seal | Final barrier + retrospective fold into `workflow/` | Stage 10 / sprint-close |

## Open DEF items — every known DEF with resolution assignment

### Will resolve within Sprint 31.9

| DEF | Title | Owner Session |
|---|---|---|
| DEF-192 | Test runtime warning cleanup (partial: numpy cast closed; 5 categories remain — TestBaseline blocked on workflow submodule per RULE-018) | FIX-13a (partial) → opportunistic cleanup |
| DEF-177 | `RejectionStage.MARGIN_CIRCUIT` addition | FIX-06 or cross-domain session |

### FIX-13b refactor queue

> **All 7 findings RESOLVED in Stage 8 Wave 2** (F5, F7+F8 linked, F9, F11,
> F18, F21, F23 — see "Already resolved during campaign" below). **F13 (AI
> Copilot coverage) RESOLVED in Stage 8 Wave 3 as FIX-13c-ai-copilot-coverage**
> — all FIX-13 family findings now closed.

### Will resolve in dedicated post-31.9 sprint

| DEF | Title | Owner |
|---|---|---|
| DEF-175 | Component ownership consolidation (lifespan phase duplication) | Post-31.9 sprint (2-3 sessions) |
| DEF-180 | Python lockfile via uv | Dedicated single-session sprint, post-31.9 |
| DEF-184 | RejectionStage → RejectionStage + TrackingReason split (coordinates with DEF-177) | Dedicated cross-domain session, post-31.9 |

### Opportunistic — no dedicated session, will fold into next touching session

| DEF | Title | Trigger |
|---|---|---|
| DEF-168 | `architecture.md` API catalog drift | If FIX-09 naturally touches API surfaces; otherwise scheduled post-campaign |
| DEF-174 | Tauri wrapper deprecated | When desktop-packaging decision is made |
| DEF-176 | `auto_cleanup_orphans` kwarg removal | Next Order Manager touch |
| DEF-178 | `alpaca-py` → `[incubator]` extras | Next dependency session |
| DEF-179 | `python-jose` → `PyJWT` migration | Next auth session |
| DEF-181 | Node 20 action deprecation (deadline 2026-06-02) | Before June 2, 2026; bump checkout/setup-python/setup-node |
| DEF-182 | Weekly Monday reconciliation stub (FIX-05 spawn) | Next ops/reconciliation session |
| DEF-183 | Full Alpaca code+test retirement (pairs with DEF-178) | Next execution-layer cleanup sprint |
| DEF-185 | Analytics-layer assert isinstance anti-pattern (5 sites, DEF-106 follow-on) | Next analytics-layer cleanup sprint |

### Monitor only — no action pending

| DEF | Title | Rationale |
|---|---|---|
| DEF-064 | Warm-up failure rate on mid-session boot | Unscheduled; observed but not triggering action |
| DEF-135 | Visual verification Shadow Trades/Experiments | Blocked on live-data accumulation (non-campaign) |
| DEF-169 | `--dev` mode retired | No action needed; informational |

### Already resolved during campaign (for completeness)

Closed by campaign sessions (grouped by closing session):

- FIX-21: DEF-097, DEF-162 (historical cache cron pair)
- IMPROMPTU-172-173-175: DEF-172 (RESOLVED-VERIFIED), DEF-173
- FIX-18: DEF-034, DEF-048, DEF-049, DEF-074, DEF-082, DEF-093, DEF-109, DEF-142
- FIX-05: **DEF-091, DEF-092, DEF-104, DEF-170** (DEF-163 was initially claimed but re-opened post-FIX-08 — SQL-side fix remains)
- FIX-06: DEF-032 (re-verified), DEF-037, DEF-165, DEF-014 (PARTIAL — emitter side), DEF-161 pending-action closed
- FIX-07: DEF-096, DEF-106
- FIX-08: DEF-107 (deleted raiseRec), DEF-123 (RESOLVED-VERIFIED)
- FIX-09: (no DEFs closed — retirements F23/F25/F26 don't close prior DEFs; F14/F17/F19 resolved inline; DEF-186, DEF-187 opened as new carries)
- IMPROMPTU-03: DEF-163 (re-opened at Stage 6, now fully resolved with in-window CI regression evidence), DEF-188 (opened and closed same session)
- FIX-13a: DEF-150 (time-of-day arithmetic), DEF-167 (Vitest hardcoded dates — 3 files; ~55 remaining files have no decay surface, closed-with-scope-note), DEF-171 (ULID xdist race — `itertools.count(1)`), DEF-190 (pyarrow/xdist prewarm with Period-dtype forcing function), DEF-192 PARTIAL (numpy cast closed; 5 categories remain per RULE-018 blocker on TestBaseline + pending DEF-176 for OrderManager kwarg migration)
- FIX-13b: 7 deferred findings from FIX-13 split (F5 `_build_system()` real `__init__`, F7+F8 6 sprint-dated integration files to `tests/integration/historical/`, F9 flatten monkeypatch, F11 13-file subpackage consolidation, F18 `_make_trade` helper, F21 `monitor_poll_seconds` injection, F23 `orb_config_factory` fixture). Zero new DEFs, zero net pytest delta.
- FIX-13c: Finding 13 (AI Copilot coverage expansion) RESOLVED. 4 AI modules lifted to ≥ 85% line coverage (prompts 56→99.4%, context 64→86.1%, client 71→95.6%, executors 69→88.5%). +52 pytest (72→124 in tests/ai/). Zero production code touched. Zero new DEFs. Two lines documented as defensively unreachable (prompts.py:95, client.py:267) — both mathematically verified, reported not patched.
- Campaign hotfixes (xdist + CI 4-bug): no DEFs closed directly; enabled CI-green milestone

### Post-31.9 deferred items (opened this campaign)

- DEF-189 — revalidate_strategy.py config_overrides param-name mismatch (MEDIUM, dedicated standalone micro-fix)
- DEF-191 — Latent get_todays_pnl SQL-side UTC normalization (LOW, pre-empts after-hours trading support)

These join the existing post-31.9 backlog: DEF-175 (Component Ownership Consolidation sprint), DEF-177 + DEF-184 coordination (RejectionStage split), DEF-178, DEF-183, DEF-185, DEF-186, DEF-187.

## Audit finding completion

Total findings at audit-2026-04-21 start: (reference audit summary for base count).

- Stage 1-4 closed: see per-audit-doc "FIX-NN Resolution" sections in `docs/audits/audit-2026-04-21/*.md`
- Remaining findings by owner:
  - P1-A3 data: FIX-06
  - P1-A4 intelligence: FIX-07
  - P1-E backtest-engine: FIX-09
  - P1-F frontend: FIX-08
  - P1-G1/G2 test coverage/quality (unclosed): FIX-13
  - P1-H1a docs/registry drift: FIX-09 (mostly); DEF-168 is a separate sub-item
  - P1-H4 DEF triage: closes as the above DEFs close

## Process & retrospective items

Campaign-wide lessons to fold into `workflow/` metarepo protocols before closing Sprint 31.9:

| # | Lesson | Trigger |
|---|---|---|
| P1 | Dep-related Tier 2 reviews should include fresh-venv install check | xdist + seaborn misses |
| P2 | Marker-adding sessions should `pytest -m "<marker>" --collect-only` validate | FIX-18 added markers but no tests used them initially |
| P3 | Grep-audit test-vs-production import drift (`jwt` vs `jose` class) | FIX-18 test import gap |
| P4 | Pre-commit `git diff --name-only --cached` scope check | c3bc758 chimera Pass 3 incident |
| P5 | Read-only orphan verification → report → halt → operator confirms → edit | Prompt 1 chore pre-edit verification caught 3 errors |
| P6 | Always verify handoff document correctness against actual source | FIX-04 DEF-152 root-cause correction |
| P7 | Small-sample sweep conclusions are directional only | Sweep Impromptu 2026-04-03/05 |
| P8 | Zero-tolerance on CI flakes requires catalog completeness | Any new flake must get DEF'd immediately |
| P9 | `getattr(pos, "qty", 0)` vs `pos.shares` silent-zero pattern worth grep-audit | FIX-04 root cause |
| P10 | Test-delta count must equal new-test count exactly (no offsetting gains/losses) | Campaign rule, reinforced FIX-05 |
| P11 | Sprint ops files (RUNNING-REGISTER.md) should be in Files Modified manifest | Tier 2 nit on FIX-05 |
| P12 | Spec file-path drift is a confirmed pattern, not a one-off | FIX-04/06/07 all encountered findings where spec cited wrong file or stale line numbers. FIX-07 had 3 CSV-garbled line drifts + Finding 17 in wrong file (`position_sizer.py` vs actual `quality_engine.py`) + Finding 21 in wrong file (`models/trading.py` vs actual `intelligence/learning/models.py`). Kickoffs should include a mandatory grep-verification step at session start. |
| P13 | Stage/Session tracker nicknames can diverge from actual spec filenames. Future stage barriers should grep the actual spec filename before drafting kickoffs that trust the tracker label. | Stage 6 was tracker-nicknamed "frontend, solo" but FIX-08's actual spec is `FIX-08-intelligence-experiments-learning` — a backend session; frontend work was entirely in FIX-12 Stage 2. |
| P14 | DEF strikethroughs should not be made until the regression test in question has been run across multiple time windows. DEF closures for time-sensitive or timezone-involved tests should require at least one regression run in the failing window OR an explicit argument why the window no longer exists. | DEF-163's FIX-05 strikethrough was premature because the Python-side fix didn't exercise the SQL-side comparator, and the test's failure mode is time-of-day-bounded (~4h daily window). |
| P15 | ET-based implementation vs local-tz/UTC assertion is a recurring test-flake pattern. DEF-163 (FIX-05-era), DEF-188 (Stage-4-era), and DEF-190's family (xdist/timezone-adjacent) all share the shape: implementation correctly uses `datetime.now(tz=_ET)` but test compares against `datetime.date.today()` or creates synthetic data with `datetime.now(UTC)`. When Python's local timezone (or the CI runner's UTC) differs from ET, the comparison drifts during the ET/UTC date-divergence window. When writing new timezone-sensitive tests: (a) always derive "today" the same way the implementation does; (b) avoid using `datetime.now(...)` for synthetic test data — use fixed wall-clock anchors (e.g., 15:00 ET); (c) if a test must mock "now", mock it explicitly rather than letting wall-clock variation drive the test. |
| P16 | Avoid `Test*`-prefixed class names in non-test code that pytest collects. `scripts/sprint_runner/state.py:158` defines a `TestBaseline` Pydantic model that triggers `PytestCollectionWarning: cannot collect test class 'TestBaseline' because it has a __init__ constructor`. Harmless but noisy. When naming internal classes, avoid the `Test*` prefix unless the class is an actual pytest test class. If historical refactoring means a non-test class must keep the `Test*` prefix, add `__test__ = False` as a class attribute to signal pytest to skip collection. |
| P17 | Broad `except Exception: pass` in test blocks can silently swallow `pytest.fail()` calls, converting the test from a real regression guard into a tautology. F19 in FIX-13a exposed exactly this pattern at `tests/api/test_observatory_ws.py` — the route-disabled test had been passing since Sprint 25 not because the behavior under test was correct, but because any failure (including the explicit `pytest.fail()`) was being caught and discarded. When replacing broad catches, verify that no `pytest.fail(...)`, `assert`, or other test-framework signal was relying on propagation. Systematic audit opportunity: grep for `except Exception` in test files and narrow each to a specific expected exception type. |
| P18 | Kickoff-suggested library-behavior fixes should be verified to actually trigger the behavior. FIX-13a's DEF-190 kickoff said "conftest.py-level eager pyarrow import" — but bare `import pyarrow` does NOT trigger `register_extension_type` because pyarrow's extension registration is lazy (runs on first DataFrame→Arrow conversion). Claude Code correctly identified the gap and strengthened the fix to an actual forcing function (`pd.DataFrame({...}) → pa.Table.from_pandas(df)`). When kickoffs propose "just import X," verify by observation (check the stack trace, run under `python -X tracemalloc`, or inspect the library source) that the import side-effect being relied on actually fires. |
| P19 | Audit observations with specific counts ("9 @patch decorators", "unused import X") can go stale between audit-generation and session execution. F22 (audit said 9 @patch decorators) and F24 (audit said "unused AfternoonMomentumStrategy import") were both wrong at re-verification time. Claude Code correctly marked them RESOLVED-VERIFIED with stale-observation annotations rather than inventing fixes. When audit findings reference specific counts or "unused" claims, grep-verify the observation before applying the suggested fix — if the observation no longer holds, mark the finding RESOLVED-VERIFIED with the verification evidence recorded. |
| P20 | When a kickoff claims runtime impact ("6 × 30s = 180s"), measure actual durations via `pytest --durations=10` rather than inferring from config defaults. F9 in FIX-13b revealed that 4 of 6 flatten tests had already been reduced to ~1s by an earlier fix (FIX-04 P1-G2-M04's shared `config` fixture override with `eod_flatten_timeout_seconds=1`); only 2 of 6 actually cost 30s each. The kickoff claim was partially stale. The fix itself (uniform monkeypatch) was still correct and future-proofing, but the kickoff's runtime-impact estimate was wrong. For future refactor kickoffs that cite runtime savings, run `pytest --durations=N` against the baseline HEAD in pre-draft investigation and cite the measured numbers, not the theoretical ceiling. |
| P21 | When a kickoff proposes a `git mv` that changes directory depth, pre-grep for `parents[N]` path-literal call sites in the moved files and enumerate the expected fix-count in the kickoff. FIX-13b F11 flagged the hazard generically but didn't specify count; Claude Code found 4 sites during execution (1 in `test_core.py`, 3 in `test_sprint329.py`). Specifying the expected count upfront gives the session a check against its own work — if only 3 sites fixed, it knows to keep looking; if 5 sites fixed, it knows to recheck the 5th. Pre-grep pattern: `grep -rn "parents\[[0-9]\]" {target_files}` for any `git mv` that reparents files into a deeper subpackage. |
| P22 | Audit-documented coverage percentages can be stale by >5pp when a session executes months after the audit. FIX-13c's pre-draft re-measurement found three of four AI modules were WORSE than the audit claimed (prompts 56% vs audit's 63%; executors 69% vs audit's 75%; client 71% vs audit's 73%). For any future audit finding that cites a measured metric (coverage %, LOC count, warning count, file count, test count), re-measure in pre-draft investigation and treat the re-measurement as authoritative. Audit values should be regarded as directional flags, not ground truth. Cross-references P19 (audit count claims go stale for grep-verifiable observations like `@patch` counts or "unused import" claims). |
| P23 | When a kickoff recommends a parametrized test pattern (`@pytest.mark.parametrize`), the test-delta estimate should multiply the single-test estimate by the number of parameter cases. FIX-13c's kickoff estimated +25 to +35 pytest; actual was +52, primarily because the recommended parametrized page-formatter test was counted as 1 test but pytest reports it as 5 (one per `(page, context_data, expected_substrings)` tuple). Additionally, exhaustive error-path tests (e.g., 10 tests for `_build_system_state` error paths: orchestrator × 2, broker × 3, account-equity × 2, circuit-breaker × 3) can drive delta beyond initial enumeration. When drafting a test-coverage kickoff: (a) count each `@parametrize` case as a separate test in the estimate; (b) enumerate expected error-path tests exhaustively rather than using "a few tests for error paths" language. |
| P24 | Test-only sessions that exercise optional runtime dependencies must mock those dependencies at the `sys.modules` level rather than relying on local package availability. FIX-13c's `test_get_client_caches_instance` called `client._get_client()` without mocking the anthropic import, which triggers a lazy `from anthropic import AsyncAnthropic`. Locally the test passed because pre-draft coverage measurement had pip-installed the `anthropic` package; on CI (where anthropic is not in any `[project.dependencies]` or `[project.optional-dependencies]` group — it's a pure runtime optional) the import raised `ImportError` and the test failed. This is a generalization of P18 (verify library-behavior assumptions): P18 covers the case where a kickoff's suggested import trigger doesn't actually fire the behavior; P24 covers the dual case where the local environment silently supplies a dependency that the test shouldn't assume. Rule of thumb: if a test touches any module that's lazy-imported or conditionally imported in production, mock at `sys.modules` level via `monkeypatch.setitem(sys.modules, "package", fake_or_None)` so the test works in environments without the optional package installed. Cross-reference the sibling test `test_get_client_raises_importerror_when_anthropic_missing` which uses this pattern correctly (sets `sys.modules["anthropic"] = None` to force the ImportError path). |
| P25 | CI results must be verified green before the next session starts. Six commits accumulated between FIX-13a (`c9c8891`) and FIX-13c hotfix (`ffcfb5c`) without anyone confirming CI passed. Each successive push arrived before the previous CI run completed, so GitHub cancelled prior runs and "red" was never explicitly observed — the FIX-13a timeout regression remained hidden across FIX-13b (7 commits), Stage 8 Wave 2 barrier, FIX-13c (3 commits), and Stage 8 Wave 3 barrier. It was only unmasked when the FIX-13c anthropic ImportError happened to be the first run to fail fast enough to produce visible output. Campaign rule going forward: each session's close-out must cite a green CI run link for the session's final commit (or the barrier commit if the session is bundled). Tier 2 reviewer verifies CI status as part of the checklist, not just local pytest. Without this, a red CI state can persist invisibly across multiple sessions. pytest-timeout (added permanently by FIX-13c CI diagnostic hotfix) partially defends this class of regression by converting future hangs into per-test failures with tracebacks, but does not catch non-hang regressions or green→red transitions that complete within the timeout budget. Operationally this also implies campaign sessions should not push commits faster than CI can run — roughly 4-minute intervals at current runtime — or explicitly wait on a green run before starting the next session. |

These become inputs to the campaign-close retrospective. They should be folded
into the `workflow/` metarepo protocols in a separate commit BEFORE Sprint 31.9
seals. Recommended: add them to the retrospective section of the final Sprint
31.9 summary doc.

## Acceptance criteria for "campaign complete"

Sprint 31.9 is complete when:
- [ ] Every session in "Sessions remaining" table has landed with CLEAR or MINOR_DEVIATIONS verdict
- [ ] Every DEF in "Will resolve within Sprint 31.9" table is strikethrough in CLAUDE.md
- [ ] CI remains green (4,992+ pytest, 859 Vitest, zero flakes firing during session runs)
- [ ] Every audit-2026-04-21 finding has a "FIX-NN Resolution" annotation in its audit doc
- [ ] Retrospective items (P1-P11) folded into `workflow/` metarepo
- [ ] Final Sprint 31.9 summary doc written
- [ ] RUNNING-REGISTER.md marked SEALED

Post-31.9 campaign is complete when:
- [ ] Component Ownership Consolidation sprint complete
- [ ] DEF-175 strikethrough in CLAUDE.md
- [ ] All "Opportunistic" DEFs have either fired their trigger session or been explicitly deferred to a NAMED post-campaign horizon
- [ ] All "Monitor only" DEFs have been re-evaluated for promotion or explicit close
- [ ] This tracker itself is moved to `docs/sprints/archive/sprint-31.9-campaign-tracker.md`

## How to update this doc

On close of any session that closes DEFs or lands findings:
1. Move resolved DEFs from "Open" → "Already resolved during campaign"
2. Update Stage progress table with the session verdict
3. Check off acceptance-criteria items if applicable
4. Update "last-updated" comment at top
5. Include this file in the session's docs commit if any changes

If a new DEF is opened, add it to the appropriate section based on ownership plan.
If a new session is added or removed, update Stage progress + Sessions remaining.
If a retrospective item is identified, append to the P# table.

## How to hydrate a fresh Claude.ai conversation

Paste at new-conversation-start:
1. This file (`CAMPAIGN-COMPLETENESS-TRACKER.md`)
2. Current `RUNNING-REGISTER.md`
3. Most recent FIX-NN close-out + Tier 2 review artifacts (the immediate prior session)
4. Next session's spec file from `docs/audits/audit-2026-04-21/phase-3-prompts/`

Project knowledge files (persistent in the Claude.ai project):
- `bootstrap-index.md` (workflow metarepo pointer)
- `ARGUS — Project Knowledge` (architecture + current state)
- `My Day Trading Manifesto` (personal context)

Starter prompt should reference the campaign HEAD SHA and the target session.