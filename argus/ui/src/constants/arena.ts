/**
 * Arena page tuning constants.
 *
 * Hoisted from `ArenaPage.tsx` during audit FIX-12 (P1-F2-M07) so the Arena
 * attention heuristics can be changed without hunting through JSX. If Arena
 * tuning ever moves into a `config/arena.yaml`, the backend values should
 * override these at fetch time — but until then the page reads these
 * module-level constants directly.
 */

/**
 * Priority-score threshold above which a card spans two grid columns.
 * Priority is computed in `ArenaPage.computePriorityScore()` as a [0, 1]
 * value where 1 = price is near stop OR near T1 (high attention).
 */
export const ARENA_PRIORITY_SPAN_THRESHOLD = 0.7;

/**
 * Interval (milliseconds) at which the page recomputes per-card priority
 * spans. Longer intervals reduce layout thrashing; shorter intervals make
 * the 2-column promotion feel more responsive to live ticks.
 */
export const ARENA_PRIORITY_RECOMPUTE_MS = 2_000;
