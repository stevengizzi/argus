/**
 * Polling-cadence constants for TanStack Query `refetchInterval`.
 *
 * Centralized so the steady-state API chatter of the Command Center can be
 * reasoned about in one place. Audit FIX-12 finding P1-F2-L04 flagged
 * uncoordinated intervals (5 s / 15 s / 30 s / 60 s with no documented
 * convention) across ~35 hooks. This file documents the intended convention;
 * individual hooks adopt it opportunistically during page touches. Migrating
 * every call site at once is not a goal — the convention just needs to exist
 * so the next hook author has a reference.
 *
 * Convention:
 * - `CRITICAL` — positions / P&L / account equity. Sub-10 s cadence acceptable.
 * - `LIVE`     — tick-like data a user is actively watching. ~5 s cadence.
 * - `HOT`      — market-hours data that changes per-minute. 15 s.
 * - `ACTIVE`   — session-level aggregates, performance, quality. 30 s.
 * - `WARM`     — per-minute aggregates, universe, briefings. 60 s.
 * - `COLD`     — static-ish or operator-authored content. 5 min.
 *
 * All of these are maximums for *background* polling. Hooks that need
 * faster response should subscribe to a WebSocket channel instead (see
 * `argus/api/websocket/*`).
 *
 * Market-hours gating: hooks whose data only changes during the live session
 * (catalysts, briefings, tick overlays) should wrap with
 * `() => (isMarketOpen() ? X : false)` per the `useCatalysts`/`useBriefings`
 * pattern — do not poll off-hours.
 */

export const POLL_MS = {
  CRITICAL: 5_000,
  LIVE: 5_000,
  HOT: 15_000,
  ACTIVE: 30_000,
  WARM: 60_000,
  COLD: 5 * 60_000,
} as const;

export type PollCadence = keyof typeof POLL_MS;
