# Sprint 23.7: DEC Entries (Draft)

To be finalized during doc-sync after sprint completion.

**DEC-316: Time-aware indicator warm-up**
Date: 2026-03-11
Sprint: 23.7

Decision: Replace blocking per-symbol indicator warm-up with time-aware
approach. Pre-market boot (before 9:30 ET) skips warm-up entirely. Mid-session
boot sets lazy mode where each symbol is backfilled on first candle arrival.

Alternatives Rejected:
1. Batch ALL_SYMBOLS historical request: Unknown Databento API behavior for
   ALL_SYMBOLS in historical context; large response size risk.
2. Warm up only scanner symbols: Loses indicator state for all universe
   symbols on mid-session restart.
3. Keep blocking warm-up with parallelism: Still O(N) API calls; parallelism
   helps but doesn't solve the fundamental scaling problem.

Rationale: The warm-up was designed for 8–15 scanner symbols. With 6,000+
universe symbols, it takes 12+ hours sequentially. Pre-market boot needs no
warm-up because the live stream builds indicators from market open naturally.
Mid-session boot uses lazy backfill to spread the cost across only symbols
that actually trade.

Constraints: DEC-025 (FIFO ordering) requires backfill to complete before
candle dispatch. DEC-088 (Databento threading) requires thread-safe warm-up
tracking.

Supersedes: N/A
Cross-References: DEC-025, DEC-088, DEC-263

**DEC-317: Periodic reference cache saves**
Date: 2026-03-11
Sprint: 23.7

Decision: Save reference data cache to disk every 1,000 symbols during fetch
and on shutdown signal. Use atomic writes (temp file + rename).

Alternatives Rejected:
1. Save only on clean completion: Current behavior; loses all progress on
   interrupt (observed: 75 minutes of fetching lost on Ctrl+C).

Rationale: Cold-start reference fetch takes ~2 hours for ~37,000 symbols.
Interrupted fetches previously lost all progress. Periodic saves ensure at
most ~3 minutes of fetch time is lost on interrupt.

Supersedes: N/A
Cross-References: DEC-314

**DEC-318: API server port guard**
Date: 2026-03-11
Sprint: 23.7

Decision: Add port-availability check before uvicorn.run() as defense in
depth. Fix root cause of double-bind (root cause TBD — to be documented in
Session 2 close-out).

Alternatives Rejected:
1. Guard only (no root cause fix): Masks the underlying bug.
2. Root cause fix only (no guard): Doesn't protect against external port
   conflicts (e.g., stale process from previous run).

Rationale: Observed uvicorn starting twice on Boot 2 (March 10), crashing
with [Errno 48]. Both root cause fix and guard are needed for reliability.

Supersedes: N/A
Cross-References: None
