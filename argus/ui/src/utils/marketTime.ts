/**
 * Market time utilities for contextual empty states.
 *
 * Provides time-aware messages based on US market hours.
 * Uses America/New_York timezone for all calculations.
 */

export type MarketStatus = 'pre_market' | 'open' | 'after_hours' | 'closed';

export interface MarketContext {
  status: MarketStatus;
  message: string;
  timeToOpen?: string;
}

const MARKET_OPEN_HOUR = 9;
const MARKET_OPEN_MINUTE = 30;
const MARKET_CLOSE_HOUR = 16;
const AFTER_HOURS_END_HOUR = 20;

/**
 * Get the current time in Eastern Time (America/New_York).
 */
function getETNow(): Date {
  // Create a date in ET timezone
  const now = new Date();
  const etString = now.toLocaleString('en-US', { timeZone: 'America/New_York' });
  return new Date(etString);
}

/**
 * Format time difference as "Xh Xm" or "Xm" if less than an hour.
 */
function formatTimeDiff(minutesTotal: number): string {
  if (minutesTotal < 0) return '0m';
  const hours = Math.floor(minutesTotal / 60);
  const minutes = minutesTotal % 60;
  if (hours === 0) return `${minutes}m`;
  if (minutes === 0) return `${hours}h`;
  return `${hours}h ${minutes}m`;
}

/**
 * Get the day name for next market session.
 */
function getNextSessionDay(etNow: Date): string {
  const day = etNow.getDay();
  const hour = etNow.getHours();
  const minute = etNow.getMinutes();

  // If it's before market open today (Mon-Fri), next session is today
  const beforeOpen =
    hour < MARKET_OPEN_HOUR || (hour === MARKET_OPEN_HOUR && minute < MARKET_OPEN_MINUTE);

  // Weekday check (0 = Sunday, 6 = Saturday)
  if (day >= 1 && day <= 5) {
    // Monday - Friday
    if (beforeOpen) {
      return 'today';
    }
    // After market on Friday → Monday
    if (day === 5) {
      return 'Monday';
    }
    // After market on Mon-Thu → tomorrow
    return 'tomorrow';
  }

  // Saturday → Monday
  if (day === 6) {
    return 'Monday';
  }

  // Sunday → tomorrow (Monday)
  return 'tomorrow';
}

/**
 * Get market context including status and appropriate message.
 *
 * Returns:
 * - Pre-market (before 9:30 ET on trading days): "Market opens in Xh Xm"
 * - Market hours (9:30-16:00 ET): "Market is open"
 * - After hours (16:00-20:00 ET): "After hours — market closed"
 * - Closed (other times, weekends): "Market closed — next session: [day] 9:30 AM ET"
 */
export function getMarketContext(): MarketContext {
  const etNow = getETNow();
  const day = etNow.getDay();
  const hour = etNow.getHours();
  const minute = etNow.getMinutes();
  const currentMinutes = hour * 60 + minute;

  const openMinutes = MARKET_OPEN_HOUR * 60 + MARKET_OPEN_MINUTE;
  const closeMinutes = MARKET_CLOSE_HOUR * 60;
  const afterHoursEndMinutes = AFTER_HOURS_END_HOUR * 60;

  // Weekend: market closed
  if (day === 0 || day === 6) {
    const nextDay = getNextSessionDay(etNow);
    return {
      status: 'closed',
      message: `Market closed — next session: ${nextDay} 9:30 AM ET`,
    };
  }

  // Pre-market (before 9:30)
  if (currentMinutes < openMinutes) {
    const minutesToOpen = openMinutes - currentMinutes;
    return {
      status: 'pre_market',
      message: `Market opens in ${formatTimeDiff(minutesToOpen)}`,
      timeToOpen: formatTimeDiff(minutesToOpen),
    };
  }

  // Market hours (9:30 - 16:00)
  if (currentMinutes >= openMinutes && currentMinutes < closeMinutes) {
    return {
      status: 'open',
      message: 'Market is open',
    };
  }

  // After hours (16:00 - 20:00)
  if (currentMinutes >= closeMinutes && currentMinutes < afterHoursEndMinutes) {
    return {
      status: 'after_hours',
      message: 'After hours — market closed',
    };
  }

  // After 20:00 on weekdays
  const nextDay = getNextSessionDay(etNow);
  return {
    status: 'closed',
    message: `Market closed — next session: ${nextDay} 9:30 AM ET`,
  };
}

/**
 * Check if currently within market hours (9:30 AM - 4:00 PM ET, weekdays).
 */
export function isMarketOpen(): boolean {
  return getMarketContext().status === 'open';
}

/**
 * Check if currently pre-market (before 9:30 AM ET on weekdays).
 */
export function isPreMarket(): boolean {
  return getMarketContext().status === 'pre_market';
}
