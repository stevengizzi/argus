/**
 * Test mode utilities for verifying empty states and animations.
 *
 * Usage: Add ?empty=positions,trades,events to the URL
 *
 * Available keys:
 * - positions: Force OpenPositions to show empty state
 * - trades: Force RecentTrades and TradeTable to show empty state
 * - events: Force EventsLog to show empty state
 *
 * Examples:
 * - ?empty=positions          → Only positions empty
 * - ?empty=positions,trades   → Positions and trades empty
 * - ?empty=all                → Everything empty
 */

type EmptyKey = 'positions' | 'trades' | 'events' | 'all';

/**
 * Get the list of features that should show empty state.
 */
function getEmptyKeys(): Set<EmptyKey> {
  if (typeof window === 'undefined') return new Set();

  const params = new URLSearchParams(window.location.search);
  const emptyParam = params.get('empty');

  if (!emptyParam) return new Set();

  const keys = emptyParam.split(',').map((k) => k.trim().toLowerCase()) as EmptyKey[];
  return new Set(keys);
}

/**
 * Check if a specific feature should show empty state for testing.
 */
export function shouldShowEmpty(key: Exclude<EmptyKey, 'all'>): boolean {
  const emptyKeys = getEmptyKeys();
  return emptyKeys.has('all') || emptyKeys.has(key);
}

/**
 * Check if test mode is active (any empty param is set).
 */
export function isTestModeActive(): boolean {
  if (typeof window === 'undefined') return false;
  const params = new URLSearchParams(window.location.search);
  return params.has('empty');
}
