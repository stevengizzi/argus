# Sprint 23.3 — DEC / RSK / DEF Entries

---

## Decision Entries

**DEC-298:** FMP Stable API Migration (Legacy v3/v4 → Stable Endpoints)
**Date:** 2026-03-09
**Sprint:** Impromptu 23.3

**Decision:**
Migrate FMPReferenceClient from legacy `/api/v3/` and `/api/v4/` endpoints to
FMP's `/stable/` endpoint family. Profile fetches change from path-based
(`/api/v3/profile/AAPL`) to query-param-based (`/stable/profile?symbol=AAPL`).
Batch profile requests (comma-separated symbols) are replaced with per-symbol
calls because the stable API on Starter tier does not support batch. Field name
mappings updated: `mktCap` → `marketCap`, `exchangeShortName` → `exchange`,
`volAvg` → `averageVolume`.

**Alternatives Rejected:**
1. Stay on legacy endpoints: Not viable — FMP returns "Legacy Endpoint" errors
   for accounts created after August 31, 2025. ARGUS account activated March 2026.
2. Upgrade to FMP Premium for batch support: Rejected for now — $59/mo vs $22/mo,
   and per-symbol calls work within rate limits. Deferred as DEF entry.

**Rationale:**
Discovered during live deployment testing on March 9, 2026. The FMP Scanner
(`fmp_scanner.py`) was already on `/stable/` endpoints, but FMPReferenceClient
was not. Hotfix applied during live session and committed to `main`.

**Constraints:**
FMP unilaterally deprecated legacy endpoints for new accounts. No migration
notice was received — discovered at runtime.

**Supersedes:** N/A

**Cross-References:**
- Related decisions: DEC-258 (FMP Starter activation), DEC-263 (full-universe monitoring)
- Related risks: RSK-031 (FMP endpoint deprecation risk)
- Related deferred items: DEF-024 (FMP Premium upgrade)

---

**DEC-299:** Full-Universe Input Pipe via FMP Stock-List Endpoint
**Date:** 2026-03-09
**Sprint:** Impromptu 23.3

**Decision:**
Feed the Universe Manager the complete FMP stock-list (~8,000 symbols) instead of
the FMP Scanner's 15-symbol pre-market watchlist. The pipeline:
1. `FMPReferenceClient.fetch_stock_list()` fetches `/stable/stock-list` (~8,000 symbols)
2. No pre-filtering — pass all symbols to `fetch_reference_data()` for profile retrieval
3. `UniverseManager.build_viable_universe()` applies system-level filters (price, volume,
   OTC exclusion, exchange checks) to reduce to ~3,000–4,000 viable symbols
4. Strategy-level filters in routing table further narrow per-strategy

Profile fetches run with async concurrency (semaphore=5) at FMP's 300 calls/min
rate limit. Total pre-market load time: ~27 minutes, which is acceptable — the
system starts early enough to accommodate this.

If the stock-list endpoint fails entirely, fall back to scanner symbols with a
loud WARNING log. Individual symbol failures are handled fail-closed per DEC-277.

**Alternatives Rejected:**
1. Symbol-pattern pre-filter (exclude OTC-looking tickers by regex): Rejected —
   cannot reliably determine security type from ticker alone. False-positive risk
   on legitimate equities (e.g., `BRK-B` contains `-`, `BLDR` ends in `R`).
   System-level filters in `build_viable_universe()` already handle this correctly
   using actual exchange and volume data from profile responses.
2. FMP exchange-specific endpoint: Not confirmed available on Starter tier. Even if
   available, the timing constraint was relaxed (can start earlier), removing the
   motivation for a faster but riskier approach.

**Rationale:**
DEC-263 specified full-universe monitoring with ~3,000–5,000 viable symbols.
Sprint 23 built the infrastructure correctly (`build_viable_universe()` accepts
any symbol list) but `main.py` was wired to pass only the 15 scanner symbols.
This completes the DEC-263 architecture as originally designed. The 27-minute
load time was accepted because the operator can start ARGUS as early as needed
and pre-market fetch time is not a hard constraint.

**Constraints:**
FMP Starter tier ($22/mo): 300 API calls/min, no batch endpoints, no screener.
Per-symbol profile calls are the only option at this tier.

**Supersedes:** N/A

**Cross-References:**
- Related decisions: DEC-263 (full-universe monitoring), DEC-277 (fail-closed),
  DEC-298 (stable API migration)
- Related risks: RSK-031 (FMP endpoint deprecation)
- Related deferred items: DEF-024 (FMP Premium for batch), DEF-025 (stock-list caching)

---

## Risk Entries

**RSK-031:** FMP Endpoint Deprecation Risk
**Date:** 2026-03-09
**Sprint:** Impromptu 23.3
**Likelihood:** MEDIUM
**Impact:** HIGH (breaks Universe Manager and Scanner at startup)
**Status:** OPEN

**Description:**
FMP deprecated all legacy v3/v4 endpoints for accounts created after August 2025
with no advance notice. The `/stable/` endpoints could similarly change or be
restructured. ARGUS now depends on FMP for both scanning (Sprint 21.7) and
universe construction (Sprint 23/23.3).

**Mitigation:**
1. Monitor FMP changelog and documentation for deprecation notices
2. FMP API URLs are centralized in `fmp_scanner.py` and `fmp_reference.py` —
   migration requires changing two files, not a systemic refactor
3. Fallback behavior: Universe Manager degrades to scanner symbols if stock-list
   fails; Scanner has its own error handling

**Trigger:** FMP returns unexpected errors or changes field names in stable API

---

## Deferred Item Entries

**DEF-024:** FMP Premium Upgrade ($59/mo)
**Date:** 2026-03-09
**Sprint:** 23.3
**Priority:** MEDIUM
**Target:** Sprint 23.5 or when batch-quote speed becomes a bottleneck

**Description:**
FMP Premium ($59/mo, up from Starter $22/mo) enables batch-quote endpoints that
could reduce Universe Manager pre-market load from ~27 minutes to ~2 minutes.
Also required for Sprint 23.5 NLP endpoints (SEC filings, news sentiment).

**Why Deferred:**
27-minute load time is acceptable for now. The cost increase is modest but
unnecessary until either (a) the load time becomes a real constraint, or
(b) Sprint 23.5 NLP work begins and requires Premium-tier endpoints.

---

**DEF-025:** Stock-List Response Caching
**Date:** 2026-03-09
**Sprint:** 23.3
**Priority:** LOW
**Target:** Unscheduled

**Description:**
Cache yesterday's viable universe and only fetch profiles for new/changed symbols
(diff against fresh stock-list) plus a random refresh sample. Could reduce
subsequent days' load from ~27 min to ~2–3 min.

**Why Deferred:**
27-minute load is acceptable. Caching adds staleness risk (price and volume
change daily). Get the simple path stable first.

---

**DEF-026:** FMP API Key Redaction in Error Logs
**Date:** 2026-03-09
**Sprint:** 23.3
**Priority:** MEDIUM
**Target:** Next cleanup sprint

**Description:**
FMP API URLs containing the API key appear in error log messages when requests
fail. URLs should be redacted before logging (replace `apikey=XXX` with
`apikey=REDACTED`).

**Why Deferred:**
Low security risk in practice (logs are local, not transmitted), but poor
hygiene. Should be addressed in a cleanup pass across both FMP clients.
