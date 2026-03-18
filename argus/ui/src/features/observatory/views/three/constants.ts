/**
 * Shared constants for Three.js funnel visualization.
 *
 * Single source of truth for tier definitions used by both
 * FunnelScene and FunnelSymbolManager.
 *
 * Sprint 25, Session 10.
 */

/** Tier definition: name, vertical position, disc radius, color. */
export interface TierDef {
  name: string;
  y: number;
  radius: number;
  color: number;
}

export const TIER_DEFS: TierDef[] = [
  { name: 'Universe',      y: 6, radius: 5.0, color: 0x6b7b8d },
  { name: 'Viable',        y: 5, radius: 4.2, color: 0x7b8d9e },
  { name: 'Routed',        y: 4, radius: 3.4, color: 0xc9963a },
  { name: 'Evaluating',    y: 3, radius: 2.6, color: 0x8b6bb5 },
  { name: 'Near-trigger',  y: 2, radius: 1.8, color: 0xd4a03c },
  { name: 'Signal',        y: 1, radius: 1.0, color: 0x4caf50 },
  { name: 'Traded',        y: 0, radius: 0.4, color: 0x66bb6a },
];
