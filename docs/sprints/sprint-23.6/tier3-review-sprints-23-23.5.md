# Tier 3 Architectural Review: Sprints 23–23.5 (Infrastructure Arc)

**Reviewer:** Claude.ai (Tier 3)
**Date:** March 10, 2026
**Branch:** `sprint-23.5`
**Scope:** Sprints 23, 23.05, 23.1, 23.2, 23.3, 23.5

---

## Verdict: REVISE_PLAN

Merge Sprint 23.5 to main — the code is sound and no regressions were observed. However, **address the items listed below before beginning Sprint 24 planning**, as several affect the integration surface that Sprint 24 will build on.

---

## 1. Architectural Coherence

### 1.1 Pattern Consistency: Universe Manager ↔ Catalyst Pipeline

The two subsystems follow remarkably consistent patterns:

- **Config gating:** Both use `enabled: false` default with Pydantic models. Consistent.
- **Error handling:** Both use fail-closed on missing data (DEC-277). Consistent.
- **Event Bus usage:** CatalystEvent is additive, published but unsubscribed. Clean.
- **SQLite storage:** CatalystStorage follows the same WAL-mode, aiosqlite pattern as the existing ai.db. Consistent.
- **API endpoint style:** JWT-protected, proper HTTP status codes, Pydantic response models. Consistent.
- **Test coverage:** Intelligence module has dedicated test directories mirroring source structure. Consistent.

One inconsistency: the intelligence router has **no URL prefix** in route registration (line 55, `routes/__init__.py`), while every other router uses an explicit prefix (`/universe`, `/ai`, `/watchlist`, etc.). The intelligence endpoints occupy the top-level API namespace at `/api/v1/catalysts/*` and `/api/v1/premarket/*`. This is cosmetic but breaks the pattern. Recommend adding `prefix="/intelligence"` for consistency — this would make endpoints `/api/v1/intelligence/catalysts/*` and `/api/v1/intelligence/premarket/*`. The frontend hooks would need corresponding updates.

### 1.2 Module Separation

The `argus/intelligence/` module is well-separated:

- No imports from `argus/strategies/`, `argus/core/orchestrator.py`, `argus/core/risk_manager.py`, or `argus/execution/`.
- Dependencies are narrow: `argus/core/events.py` (CatalystEvent), `argus/core/event_bus.py` (publishing), `argus/core/ids.py` (ULID generation), `argus/ai/client.py` and `argus/ai/usage.py` (Claude API access).
- The only import directionality concern is the classifier's dependency on `ClaudeClient` and `UsageTracker` from the AI layer. These are injected, not imported at module level (TYPE_CHECKING guard). Clean.

### 1.3 Autonomous Runner Isolation

**Verified: zero imports from `argus/` in `scripts/sprint_runner/`.** The runner interacts with the codebase exclusively through CLI invocation, git operations, and filesystem reads. The boundary is perfect.

---

## 2. Critical Findings

### C1: Catalyst Pipeline Not Wired into Application Startup

**Severity: Critical for Sprint 24 planning**

`AppState` declares `catalyst_storage: CatalystStorage | None = None` and `briefing_generator: BriefingGenerator | None = None`, but **nothing initializes them** during application startup. The API endpoints protect themselves with 503 checks (`_ensure_catalyst_storage`), so the system doesn't crash — but the entire pipeline (sources, classifier, storage, pipeline orchestrator, briefing generator) has no bootstrap code.

The `CatalystPipeline.run_poll()` method is ready to go but nobody calls it. There's no scheduled polling loop registered in the event system.

**Impact:** Before Sprint 24 (Quality Engine) can subscribe to CatalystEvents, someone needs to write the initialization code in the API server startup that: (a) reads `catalyst.enabled` from config, (b) instantiates CatalystStorage, sources, classifier, pipeline, and briefing generator, (c) registers a polling loop, and (d) sets the AppState fields.

**Recommendation:** Add a "Sprint 23.6 — Catalyst Pipeline Integration" mini-sprint (2-3 sessions) or fold this into Sprint 24's early sessions. This is the missing piece between "all components built" and "pipeline actually runs."

### C2: Total Count Query Will Degrade With Scale

**Severity: Critical (performance)**

In `argus/api/routes/intelligence.py` lines 200-203:

```python
all_catalysts = await state.catalyst_storage.get_recent_catalysts(
    limit=10000, offset=0
)
total = len(all_catalysts)
```

This fetches up to 10,000 full catalyst rows (with all fields) into memory just to count them. As catalysts accumulate (hundreds per day × months of operation), this becomes:

1. **Memory pressure:** Each ClassifiedCatalyst is ~15 fields including full headline and summary text.
2. **Query performance:** Full table scan with ORDER BY, every single request.
3. **Unnecessary:** SQLite's `SELECT COUNT(*) FROM catalyst_events` is instant with the existing index.

**Recommendation:** Add `get_total_count()` to CatalystStorage:
```python
async def get_total_count(self) -> int:
    conn = self._ensure_connected()
    cursor = await conn.execute("SELECT COUNT(*) FROM catalyst_events")
    row = await cursor.fetchone()
    return row[0]
```

### C3: Timezone Dual-Convention (UTC vs ET) in CatalystEvent

**Severity: Critical (latent bug)**

`CatalystEvent` in `argus/core/events.py` lines 317-318:
```python
published_at: datetime = field(default_factory=lambda: datetime.now(UTC))
classified_at: datetime = field(default_factory=lambda: datetime.now(UTC))
```

All intelligence layer models and storage use ET (per DEC-276). The pipeline currently overrides these defaults when constructing CatalystEvent (lines 191-203 of `__init__.py`), so the system works correctly *today*.

But when Sprint 24's Quality Engine subscribes to CatalystEvent and reads `published_at` or `classified_at`, it will receive ET timestamps — unless someone constructs a CatalystEvent using defaults, in which case those fields would be UTC. This is a trap for future code.

**Recommendation:** Either:
- (A) Change CatalystEvent defaults to ET (matches DEC-276), or
- (B) Add a docstring warning that defaults are UTC but the pipeline always passes ET values, and add a comment in CatalystPipeline that the timezone override is intentional.

Option A is cleaner. The Event Bus convention of UTC defaults (mentioned in the sprint review) doesn't need to be absolute — DEC-276 already established ET as the AI/Intelligence layer standard. CatalystEvent belongs to the intelligence domain, not the trading engine.

---

## 3. Significant Findings

### S1: `fetched_at` Not Persisted — Data Loss on Round-Trip

`CatalystStorage._row_to_catalyst()` (line 289):
```python
fetched_at=datetime.fromisoformat(r["created_at"]),  # Use created_at as fetched_at
```

The `catalyst_events` table has no `fetched_at` column. When a catalyst is stored, the original fetch timestamp is lost. On read-back, `created_at` (storage insertion time) substitutes for `fetched_at` (source API call time). These can differ by seconds to minutes depending on classification pipeline latency.

**Impact today:** Minimal — no current consumer relies on fetched_at precision.
**Impact for Sprint 24:** If Quality Engine uses fetched_at to assess data freshness (e.g., "how stale is this catalyst?"), the wrong timestamp could affect scoring.

**Recommendation:** Add a `fetched_at TEXT` column to the catalyst_events table in a migration. Low effort, prevents a class of subtle bugs.

### S2: Per-Row Commits in Pipeline Batch Processing

`CatalystPipeline.run_poll()` calls `self._storage.store_catalyst(catalyst)` in a loop, and each `store_catalyst()` call ends with `await conn.commit()`. For a batch of 50 catalysts, that's 50 SQLite commits — each requiring an fsync.

**Impact:** At current scale (maybe 20-50 catalysts per poll cycle), this is fine. At higher volumes or on slower storage, this will become a bottleneck.

**Recommendation:** Add a `store_catalysts_batch()` method to CatalystStorage that wraps multiple inserts in a single transaction. Or move the commit to the pipeline level after the loop.

### S3: 27-Minute Pre-Market Warm-Up (DEF-025)

The full-universe fetch takes ~27 minutes for ~8,000 symbols (5 concurrent requests × 0.2s spacing). This eats into Steven's pre-market preparation window. Starting at ~9:00 PM Taipei time for a 9:30 PM market open, the system might not be ready until after the open.

**Current mitigation:** None beyond DEF-025 (stock-list response caching).
**Recommendation:** Promote DEF-025 to sprint scope. Caching yesterday's reference data and doing an incremental update (only re-fetch symbols where data is stale or missing) could reduce warm-up to 2-5 minutes. This is operationally important for the Taipei timezone constraint.

### S4: Runner `main.py` at 2,187 Lines

This is the largest file in the project by a wide margin. It contains the state machine, CLI parsing, notification formatting, session execution, triage orchestration, conformance checking, parallel execution coordination, and print formatting all in one file.

**Impact:** Not blocking, but will make future runner modifications harder to reason about and increase compaction risk for any runner-focused sprint.

**Recommendation:** DEF this for a future sprint. Natural extraction candidates: `cli.py` (argument parsing + print helpers, ~200 lines), notification formatting (already has helpers, could be fully extracted from main), and the auto-split logic (~50 lines).

### S5: Conformance CONFORMANT-on-Failure Warrants Monitoring

The asymmetry is documented and intentionally conservative in different directions:
- **Triage failure → HALT** (conservative: don't proceed without safety check)
- **Conformance failure → CONFORMANT** (permissive: avoid false halts)

The rationale is sound for the current state — conformance is defense-in-depth, not a critical gate. But there's no counter tracking how often the fallback fires. If conformance checking silently fails 80% of the time due to, say, a prompt format issue, you lose the defense-in-depth without knowing it.

**Recommendation:** Add a `conformance_fallback_count` field to RunState. Log a WARNING if it exceeds 2 per sprint run. This preserves the permissive behavior while making silent degradation visible.

### S6: SEC EDGAR `user_agent_email` Empty Default

`SECEdgarConfig.user_agent_email: str = ""` — if someone enables `catalyst.enabled: true` and `sources.sec_edgar.enabled: true` without setting this, SEC requests will lack a proper User-Agent header. SEC EDGAR may rate-limit or block the requests.

**Recommendation:** Add validation in `CatalystPipeline.start()` or `SECEdgarClient.start()` that raises a clear error if `user_agent_email` is empty when the source is enabled. Better to fail loudly at startup than silently at first request.

---

## 4. Moderate Findings

### M1: Headline Dedup is Exact-Hash Only

`compute_headline_hash()` normalizes by lowercasing and stripping, but two sources reporting the same event with different wording will both be stored and classified. Example:
- FMP: "Apple Reports Record Q4 Revenue of $95B"
- Finnhub: "AAPL posts record fourth-quarter sales"

Both pass dedup, both get classified (costing API calls), both get stored.

**Impact:** Higher classification costs and duplicate data. Not a correctness issue — both catalysts are valid data points.

**Recommendation:** Log as a known limitation, not a bug. Fuzzy dedup (embedding similarity, etc.) is a Sprint 28+ concern if cost becomes an issue.

### M2: Pipeline Publish → Store Is Not Transactional

In `CatalystPipeline.run_poll()`, the loop (lines 186-203) stores first, then publishes:
```python
await self._storage.store_catalyst(catalyst)
event = CatalystEvent(...)
await self._event_bus.publish(event)
```

If `publish()` fails after `store_catalyst()` succeeds, you get a stored catalyst with no event notification. If `store_catalyst()` fails, you get neither (correct). If the process crashes mid-loop, you get partial storage with no events.

**Impact today:** Zero — CatalystEvent has no subscribers.
**Impact for Sprint 24:** Quality Engine subscribing to CatalystEvent could miss catalysts stored during a failed publish cycle. However, the Quality Engine can also query CatalystStorage directly as a fallback, so this isn't a data loss issue — just a notification gap.

**Recommendation:** Acceptable for now. If Sprint 24 relies heavily on real-time event notification rather than polling storage, add a retry wrapper around the publish call.

### M3: No Pagination for Symbol-Filtered Catalyst API

`get_catalysts_by_symbol` fetches all catalysts for a symbol (up to `limit`), then the API route applies `since` filtering in Python (lines 239-253 of `intelligence.py`):

```python
if since is not None:
    catalysts = [c for c in catalysts if _make_aware(c.published_at) >= since_dt]
```

This means if a symbol has 1,000 catalysts but only 5 are after `since`, you fetch and deserialize all 1,000 first. The filter should be pushed to the SQL query.

**Recommendation:** Add a `since` parameter to `CatalystStorage.get_catalysts_by_symbol()` and use a WHERE clause.

---

## 5. Decision Quality Assessment (31 DECs)

### 5.1 Overall Quality

31 decisions in ~3 days is aggressive but the quality is high. Each DEC has clear rationale, alternatives considered, and cross-references. No contradictions found between entries.

### 5.2 Specific Assessments

**DEC-298 (FMP stable API migration):** Forced by runtime discovery — FMP deprecated endpoints without notice. RSK-031 captures this, but I'd weight it higher. FMP is a load-bearing dependency for Universe Manager's warm-up and the Catalyst Pipeline's news source. If FMP changes their stable API endpoint schema without notice (as they did with legacy endpoints), it could break pre-market preparation.

**Recommendation:** Add a canary test that runs daily (or at startup) to verify FMP stable API response schema matches expectations. Simple: fetch one known symbol's profile, verify expected keys exist.

**DEC-301 (dynamic batch classification):** Good decision. The max_batch_size cap prevents prompt-length blowouts.

**DEC-302 (daily cost ceiling):** Well-designed. $5/day is conservative and the fallback classifier provides continued operation.

**DEC-307 (headline hash dedup):** Appropriate for V1. See M1 above for future considerations.

### 5.3 Missing Decisions

One implicit decision escaped logging:

- **Missing DEC: CatalystPipeline initialization deferred.** The decision to build all pipeline components but defer system integration (no startup wiring, no polling loop) was made during Sprint 23.5 session planning but never logged as a DEC. It should be, because Sprint 24 planning needs to know this explicitly.

- **Missing DEC: Separate catalyst.db.** The Catalyst Pipeline uses its own SQLite database file (`catalyst.db`) rather than the existing application database. This is a good decision (isolation, independent lifecycle), but the rationale isn't logged.

---

## 6. Boundary Compliance

### 6.1 Specification by Contradiction

All sprints respected their stated boundaries. Verified:

- Sprint 23: No strategy `.py` files modified. No AI layer, Risk Manager, Orchestrator, execution, analytics, or backtesting modifications. ✓
- Sprint 23.1: No source code under `argus/`, `tests/`, `scripts/`, or `config/` modified. ✓
- Sprint 23.2: Nothing under `argus/`, existing `scripts/*.py`, `config/`, or `docs/protocols/` modified. ✓
- Sprint 23.5: No modifications to `argus/ai/`, `argus/strategies/`, `argus/core/risk_manager.py`, `argus/core/orchestrator.py`, `argus/execution/`, `argus/data/universe_manager.py`, `argus/data/fmp_scanner.py`, `argus/analytics/`, `argus/backtest/`. ✓

### 6.2 DEC-170 (AI Layer Strict Separation)

**Preserved.** The intelligence layer reads from and publishes to the Event Bus but never modifies core trading components. CatalystEvent is published with zero subscribers. The classifier uses ClaudeClient but only for classification — it never calls any strategy, orchestrator, or risk manager method.

---

## 7. Sprint 24 Readiness Assessment

### Ready:
- Universe Manager is stable and fully functional. Reference data cache, routing table, and fast-path discard all working.
- CatalystEvent type is defined and publishable. Quality Engine can subscribe.
- CatalystStorage has query methods for fetching recent and per-symbol catalysts.
- Config-gating pattern is established and can be extended to quality scoring.
- Autonomous runner is available for Sprint 24 execution (first production use in Sprint 23.5 was successful).

### Not Ready — Must Address:
1. **Pipeline initialization code** (C1): Sprint 24 can't subscribe to CatalystEvents that never fire. Either fold initialization into Sprint 24's early sessions or run a 23.6 mini-sprint.
2. **CatalystEvent timezone defaults** (C3): Fix before Quality Engine subscribes. 5-minute change.
3. **Total count query** (C2): Fix before production use of intelligence endpoints. 10-minute change.

### Recommended Before Sprint 24 But Not Blocking:
4. **Add `fetched_at` column** (S1): Schema migration, low effort.
5. **Batch commits** (S2): Performance improvement, low effort.
6. **SEC EDGAR email validation** (S6): Startup safety, low effort.

---

## 8. Risk Assessment

### RSK-031 (FMP Deprecation): Under-Weighted

FMP deprecated legacy endpoints without notice. The stable API migration (DEC-298) addressed the immediate issue, but the underlying risk remains: FMP is a commercial API vendor who can change their interface at any time. ARGUS now depends on FMP for (a) Universe Manager stock-list + reference data, (b) pre-market scanner, and (c) Catalyst Pipeline news.

**Recommendation:** Elevate RSK-031 likelihood from MEDIUM to HIGH. Add a canary test for schema validation at startup. Consider logging a DEC about FMP concentration risk and whether a backup reference data source should be investigated.

### RSK-046 (Claude API Classification Cost): Adequately Mitigated

The daily cost ceiling (DEC-302) plus fallback classifier (DEC-306) provide robust mitigation. $5/day is well within budget.

### RSK-047 (SEC EDGAR Rate Limiting): Adequately Mitigated

Rate limiter at 10 req/sec with User-Agent compliance. Appropriate.

### New Risk: External API Concentration

Three of four intelligence sources (FMP, Finnhub, SEC EDGAR) are free or cheap. This is a feature (low cost) but also a risk — free tiers can be deprecated, rate-limited, or degraded without notice. The system is designed to degrade gracefully (source failure → logged error, pipeline continues with remaining sources), which is the right architecture. But if FMP (the only paid source) degrades, both Universe Manager and Catalyst Pipeline are affected simultaneously.

**Recommendation:** Log as RSK-048 with MEDIUM likelihood, HIGH impact. No action needed now, but monitor.

### 27-Minute Warm-Up: Operational Risk, Not Just Deferred

See S3 above. Reclassify DEF-025 from "nice to have" to "operationally important." The Taipei timezone constraint makes this more than a convenience issue.

---

## 9. Deferred Items Assessment

### Accumulation Rate
4 new DEF items (DEF-024 through DEF-034, minus duplicates) in 6 sprint-units. This is a healthy rate — items are being created when appropriate, not being ignored.

### Status Review

- **DEF-024 (FMP Premium $59/mo):** Sprint 23.5 worked fine on Starter. De-prioritize. FMP Starter is adequate for current needs.
- **DEF-025 (Stock-list caching):** **Promote to sprint scope** — see S3 above.
- **DEF-026 (FMP API key redaction):** Code review shows API keys are passed as request params, not logged directly in error messages. LOW severity. Keep as DEF.
- **DEF-034 (Pydantic serialization warnings):** Cosmetic. Not growing into a real problem — it's a WARNING-level log message during runner operation. Keep as DEF, fix opportunistically.

---

## 10. New Decisions to Log

| DEC | Decision | Rationale |
|-----|----------|-----------|
| DEC-308 | CatalystPipeline initialization deferred to separate sprint/session (not wired into app startup in Sprint 23.5) | Sprint 23.5 built all components; integration deferred to allow config-gated activation. Must be completed before Sprint 24 Quality Engine can subscribe to CatalystEvents. |
| DEC-309 | Catalyst data stored in separate `catalyst.db` SQLite file, not main application database | Isolation: intelligence data lifecycle is independent of trading data. Separate DB avoids WAL contention between high-frequency trading writes and batch catalyst inserts. |

---

## 11. Documentation Reconciliation

### Architecture Document
Needs updates for:
- `argus/intelligence/` module description (if not already added in 23.5 doc sync)
- Pipeline initialization gap (pending integration sprint)

### Risk Register
- RSK-031: Elevate likelihood to HIGH
- RSK-048 (new): External API concentration risk

### Deferred Items
- DEF-025: Promote to sprint scope (pre-Sprint 24)
- DEF-035 (new): Add `fetched_at` column to catalyst_events
- DEF-036 (new): Intelligence router prefix consistency
- DEF-037 (new): Push `since` filter to SQL in catalyst API
- DEF-038 (new): Batch commits in pipeline store loop
- DEF-039 (new): Runner main.py decomposition (2,187 lines)
- DEF-040 (new): Conformance fallback counter for silent degradation tracking

---

## 12. Summary

The infrastructure arc is architecturally sound. Three subsystems (Universe Manager, Autonomous Runner, NLP Catalyst Pipeline) were built with consistent patterns, clean boundaries, and solid test coverage. The code quality is high — no regressions, proper error handling, appropriate use of config gating.

The critical gap is C1: the Catalyst Pipeline is fully built but not wired into the running application. Sprint 24 cannot use CatalystEvents until this is resolved. The other critical items (C2, C3) are quick fixes that should be done pre-merge or in the first Sprint 24 session.

The 27-minute warm-up (S3/DEF-025) is the highest-impact operational concern for Steven's real workflow from Taipei. Recommend addressing before or alongside Sprint 24.

**Action items for Sprint 24 planning conversation:**
1. Decide: fold pipeline initialization into Sprint 24 Session 1, or run Sprint 23.6?
2. Fix C2 (total count query) and C3 (timezone defaults) — can be quick pre-merge patches.
3. Promote DEF-025 (stock-list caching) to sprint scope.
4. Log DEC-308, DEC-309.
5. Update RSK-031, add RSK-048.
6. Log new DEF entries (DEF-035 through DEF-040).
