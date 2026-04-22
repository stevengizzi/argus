# FIX-02-config-drift-critical — Close-Out Report

> Tier 1 self-review produced per `workflow/claude/skills/close-out.md`.
> Paste the fenced block below into the Work Journal on Claude.ai.

```markdown
---BEGIN-CLOSE-OUT---

**Session:** audit-2026-04-21-phase-3 — FIX-02-config-drift-critical (overflow.yaml via DEC-384 standalone overlay)
**Date:** 2026-04-21
**Self-Assessment:** CLEAN

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| argus/core/config.py | modified | Extended `_STANDALONE_SYSTEM_OVERLAYS` tuple with `("overflow", "overflow.yaml")`; hardened non-dict overlay handling with WARNING log (was silent skip); updated registry comment + load_config docstring to reference FIX-02 + "bare fields at top level" convention |
| config/overflow.yaml | modified | Flattened — removed top-level `overflow:` wrapper; bare fields (`enabled: true`, `broker_capacity: 50`) at top. Added "standalone overlay convention" comment referencing DEC-384 / FIX-02 |
| config/system.yaml | modified | Removed `overflow:` block (lines 175–177). Replaced with a "do not re-add" pointer comment directing readers to `config/overflow.yaml` as the authoritative source |
| config/system_live.yaml | modified | Same removal + pointer comment as `system.yaml` |
| tests/test_overflow_routing.py | modified | Method renamed `test_overflow_yaml_broker_capacity_is_60` → `_is_50` (stale name; asserts 50). Key path updated `data["overflow"]["broker_capacity"]` → `data["broker_capacity"]` to match flattened file |
| tests/core/test_signal_cutoff.py | modified | Key path updated `raw["overflow"]["broker_capacity"]` → `raw["broker_capacity"]` to match flattened file |
| tests/test_fix01_load_config_merge.py | modified | +3 regression tests: `test_registry_includes_overflow_after_fix02`, `test_overflow_broker_capacity_loaded_from_standalone`, `test_non_dict_standalone_overlay_emits_warning`. Added `logging` import. Module docstring updated to reference FIX-02 |
| docs/audits/audit-2026-04-21/p1-d1-catalyst-quality.md | modified | Added "FIX-02 Resolution" section annotating **C3** as RESOLVED |
| docs/audits/audit-2026-04-21/p1-h2-config-consistency.md | modified | Added "FIX-02 Resolution" section annotating **D-05** + **DEAD-04** as RESOLVED; updated the "deferred to FIX-02" closing prose from the FIX-01 section to reference the new Resolution section |
| docs/audits/audit-2026-04-21/phase-2-review.csv | modified | Annotated P1-D1-C03 row + H2-D05 row with `**RESOLVED FIX-02-config-drift-critical** (DEC-384 registry extension)` in the notes column |
| CLAUDE.md | modified | Updated "Last updated" line; updated Active Sprint status ("FIX-02 just landed"); softened the forward-looking FIX-02 sentence in the FIX-01 entry; added a full FIX-02 follow-on block under Active Sprint |

### Judgment Calls
- **Option A (flatten `overflow.yaml`) was mandated by the prompt** (§3), not a judgment call. The prompt was explicit about avoiding Options B (registry shape branching) and C (implicit unwrap magic).
- **`overflow:` block fully removed from both system YAMLs (not just `broker_capacity`)** — step 7 option (a). Matches the quality_engine precedent under DEC-384 and prevents future reintroduction of a stale mirror value. Replaced with a pointer comment.
- **Non-dict overlay warning wording** — chose `"load_config: standalone overlay %s is not a dict (got %s) — skipping"` to match the existing "load_config: ..." prefix pattern on the merge-completed INFO log one block above. Single logger.warning call, no scope creep.
- **Did NOT modify `tests/intelligence/test_config.py`** — the prompt §3 explicitly said "leave it alone." It reads `system.yaml` (not `overflow.yaml`) and still passes because `raw.get("overflow", {})` returns `{}`, `OverflowConfig(**{})` uses the default 30, and the test asserts 30. Brittleness acknowledged; not in scope.
- **Back-annotation pattern** mirrors FIX-01's "Resolution" section block (not inline table-row strikethrough) because that's the precedent set by the FIX-01 landings in the same audit documents.

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| Pre-flight verification of Stage 1 infrastructure (§2) | DONE | 4 checks green: `_STANDALONE_SYSTEM_OVERLAYS` at line 1344, `deep_update` at line 39, registry prints `(('quality_engine', 'quality_engine.yaml'),)`, test file present |
| Flatten `config/overflow.yaml` to bare fields (§5 step 2) | DONE | `overflow:` wrapper removed; `enabled: true` + `broker_capacity: 50` at top level; documentation comment added |
| Update `tests/test_overflow_routing.py:471` (§5 step 3) | DONE | Method renamed `_is_60 → _is_50`; key path `data["overflow"]["broker_capacity"]` → `data["broker_capacity"]` |
| Update `tests/core/test_signal_cutoff.py:226` (§5 step 4) | DONE | Key path `raw["overflow"]["broker_capacity"]` → `raw["broker_capacity"]` |
| Extend `_STANDALONE_SYSTEM_OVERLAYS` (§5 step 5) | DONE | `("overflow", "overflow.yaml")` added as second tuple entry; registry comment expanded with "bare fields at top level" convention |
| Harden non-dict overlay handling (§5 step 6) | DONE | `logger.warning(...)` added before `continue` in `load_config()` at `argus/core/config.py:1423-1428` |
| Remove `overflow:` block from `system.yaml` + `system_live.yaml` (§5 step 7) | DONE | Both files: block removed, pointer comment added. Grep verification: `grep -rn "broker_capacity" config/` now returns only `overflow.yaml:11` |
| +3 regression tests (§5 step 8) | DONE | `test_registry_includes_overflow_after_fix02`, `test_overflow_broker_capacity_loaded_from_standalone` (end-to-end), `test_non_dict_standalone_overlay_emits_warning` (caplog) |
| Back-annotate P1-D1-C03 (§5 step 9) | DONE | New "FIX-02 Resolution" section in `p1-d1-catalyst-quality.md` annotating C3 as RESOLVED |
| Back-annotate H2-D05 (§5 step 9) | DONE | New "FIX-02 Resolution" section in `p1-h2-config-consistency.md` annotating D-05 + DEAD-04 as RESOLVED; "deferred to FIX-02" closing sentence updated |
| Annotate both rows in phase-2-review.csv (§5 step 9) | DONE | P1-D1-C03 row (line 106) + H2-D05 row (line 347) both carry `**RESOLVED FIX-02-config-drift-critical** (DEC-384 registry extension)` in notes column |
| Update CLAUDE.md overflow routing language (§5 step 10) | DONE | "Last updated" line refreshed; Active Sprint status reflects FIX-02 landed; FIX-01 entry's forward-reference softened; new FIX-02 follow-on block added |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| Live `load_config(Path("config"))` produces `config.system.overflow.broker_capacity == 50` | PASS | Direct invocation confirmed; also covered by new `test_overflow_broker_capacity_loaded_from_standalone` |
| `load_config()` still produces `quality_engine.weights.pattern_strength == 0.375` (FIX-01 path unbroken) | PASS | Same direct invocation confirmed |
| `grep -rn "broker_capacity" config/` returns only `overflow.yaml` | PASS | Single hit at `config/overflow.yaml:11` |
| pytest net delta ≥ 0 against baseline 4,943 | PASS (+3) | 4,946 passed — baseline 4,943 + 3 new FIX-02 regression tests |
| Pre-existing failures match known flake set (DEF-150, DEF-163) | PASS | 2 failures this run are both DEF-163 date-decay (`test_get_todays_pnl_excludes_unrecoverable`, `test_history_store_migration`); DEF-150 did not flake this run |
| No file outside declared 11-file scope was modified | PASS | `git diff --name-only` returns exactly the 11 expected files |
| Every resolved finding back-annotated | PASS | P1-D1-C03 + H2-D05 both carry **RESOLVED FIX-02-config-drift-critical** in CSV and markdown |
| DEC-384 registry extension does not require a new DEC | PASS | Prompt §1 explicit: FIX-02 is "the first extension of the existing `_STANDALONE_SYSTEM_OVERLAYS` registry" under DEC-384. No new DEC |
| No new DEFs opened | PASS | All work fits within FIX-02's declared scope |

### Test Results
- Tests run: 4,948 (collected)
- Tests passed: 4,946
- Tests failed: 2 (DEF-163 date-decay × 2 — pre-existing, known flake set)
- New tests added: 3 (registry, end-to-end merge, non-dict overlay warning)
- Command used: `python -m pytest --ignore=tests/test_main.py -n auto --tb=no -q`

### Unfinished Work
None.

### Notes for Reviewer

**1. Structural pivot from audit prompt's "Options A vs B" framing.** The
audit FIX-02 prompt offered two approaches (sync values OR extend registry).
The operator's explicit override (prompt §1) locked the session to the
registry-extension path because FIX-01 (`commit 59bb100` / DEC-384) already
built the infrastructure. FIX-02 is therefore the *first* extension of the
registry, not a choice of approach.

**2. Shape mismatch was the load-bearing discovery.** `quality_engine.yaml`
has bare top-level fields; the original `overflow.yaml` wrapped its contents
in `overflow:`. Naively appending the tuple entry would have produced a
double-nested `system_block["overflow"]["overflow"] = {...}` at merge time.
The prompt's §3 Option A (flatten the file, establish "bare fields at top
level" as the registry convention) is what the final implementation follows.
I verified the hypothetical double-nest outcome by reading the merge code
(lines 1416-1422) before editing.

**3. One test-level subtlety intentionally left alone.** `tests/intelligence/test_config.py::TestOverflowConfigYamlAlignment`
loads `system.yaml` (now missing the `overflow:` block), calls
`raw.get("overflow", {})` → `{}`, and asserts `broker_capacity == 30`. It
passes because `OverflowConfig(**{})` defaults `broker_capacity` to 30. The
test still exercises "YAML keys all recognized by model" (trivially, because
the key set is empty). The prompt §3 explicitly directed not to touch this
file. I flagged the brittleness but did not scope-creep.

**4. Pytest baseline math.** Baseline at Phase 3 kickoff (per CLAUDE.md):
"4,933 passed, 1 failed." FIX-11 landed at 4,943. FIX-02 arrives at 4,946.
The delta of +3 matches exactly the 3 new regression tests added in
`test_fix01_load_config_merge.py`. No test deletions. No test skips added.

**5. `test_overflow_routing.py::test_overflow_config_loads_with_capacity_60`
was not renamed.** That test (line 484 in the original, untouched here) uses
a programmatic `_build_overflow_system(...broker_capacity=60)` helper — not
a file read — so its name accurately reflects what it asserts. Only the
YAML-direct-read test was misnamed.

**6. Stage 1 deferred pickup (FIX-01 review INFO) fit cleanly.** Adding the
WARNING log + caplog test was +7 lines of `config.py` + 1 test. Well within
the "halt if > ~5 lines + 1 test" threshold the prompt §4 specified — I'm
flagging the +2 line overage (for the multi-arg log call's wrapping) as
below-threshold but transparent.

**7. Commit `9454df5` pushed to `origin/main`.**

---END-CLOSE-OUT---
```

```json:structured-closeout
{
  "schema_version": "1.0",
  "sprint": "audit-2026-04-21-phase-3",
  "session": "FIX-02-config-drift-critical",
  "verdict": "COMPLETE",
  "tests": {
    "before": 4943,
    "after": 4946,
    "new": 3,
    "all_pass": false
  },
  "files_created": [],
  "files_modified": [
    "CLAUDE.md",
    "argus/core/config.py",
    "config/overflow.yaml",
    "config/system.yaml",
    "config/system_live.yaml",
    "docs/audits/audit-2026-04-21/p1-d1-catalyst-quality.md",
    "docs/audits/audit-2026-04-21/p1-h2-config-consistency.md",
    "docs/audits/audit-2026-04-21/phase-2-review.csv",
    "tests/core/test_signal_cutoff.py",
    "tests/test_fix01_load_config_merge.py",
    "tests/test_overflow_routing.py"
  ],
  "files_deleted": [],
  "files_should_not_have_modified": [],
  "scope_additions": [],
  "scope_gaps": [],
  "prior_session_bugs": [],
  "deferred_observations": [
    "tests/intelligence/test_config.py::TestOverflowConfigYamlAlignment now exercises a trivial no-op (empty overflow block in system.yaml → OverflowConfig default = 30 which happens to match the assertion). Prompt §3 directed no change; future cleanup could retarget the test at config/overflow.yaml directly.",
    "DEF-150 did not flake this run — monitor whether the (minute - 2) % 60 arithmetic bug manifests in Stage 8 FIX-13 when scheduled."
  ],
  "doc_impacts": [
    {"document": "CLAUDE.md", "change_description": "FIX-02 follow-on block added; Active Sprint status updated; FIX-01 forward-reference to FIX-02 softened"},
    {"document": "docs/audits/audit-2026-04-21/p1-d1-catalyst-quality.md", "change_description": "FIX-02 Resolution section annotating C3 as RESOLVED"},
    {"document": "docs/audits/audit-2026-04-21/p1-h2-config-consistency.md", "change_description": "FIX-02 Resolution section annotating D-05 + DEAD-04 as RESOLVED"},
    {"document": "docs/audits/audit-2026-04-21/phase-2-review.csv", "change_description": "P1-D1-C03 + H2-D05 rows annotated RESOLVED"}
  ],
  "dec_entries_needed": [],
  "warnings": [],
  "implementation_notes": "FIX-02 is the first extension of DEC-384's _STANDALONE_SYSTEM_OVERLAYS registry. overflow.yaml flattened to bare-field shape (matching quality_engine.yaml); overflow: block removed from system.yaml + system_live.yaml. Stage 1 deferred pickup (non-dict overlay WARNING) folded in. +3 regression tests, 2 direct-read test call sites updated (method renamed in one). No new DEFs, no new DECs. Commit 9454df5 pushed to main."
}
```
