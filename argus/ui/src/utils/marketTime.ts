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

// NYSE market holidays — computed algorithmically from fixed rules.
// Covers all years. No manual updates needed.
// Source: NYSE Rule 7.2 — Regular Holidays
// Note: Does not handle early closes (day before Independence Day,
// day after Thanksgiving, Christmas Eve) — these are half days, not closures.

// Cache holidays per year to avoid recomputation
const holidayCache = new Map<number, Set<string>>();

/**
 * Compute Easter Sunday for a given year using the Anonymous Gregorian algorithm.
 * Returns [month (1-indexed), day].
 */
function computeEasterSunday(year: number): [number, number] {
  const a = year % 19;
  const b = Math.floor(year / 100);
  const c = year % 100;
  const d = Math.floor(b / 4);
  const e = b % 4;
  const f = Math.floor((b + 8) / 25);
  const g = Math.floor((b - f + 1) / 3);
  const h = (19 * a + b - d - g + 15) % 30;
  const i = Math.floor(c / 4);
  const k = c % 4;
  const l = (32 + 2 * e + 2 * i - h - k) % 7;
  const m = Math.floor((a + 11 * h + 22 * l) / 451);
  const month = Math.floor((h + l - 7 * m + 114) / 31);
  const day = ((h + l - 7 * m + 114) % 31) + 1;
  return [month, day];
}

/** Get the Nth occurrence of a weekday in a given month/year. weekday: 0=Sun, 1=Mon, ... */
function nthWeekday(year: number, month: number, weekday: number, n: number): number {
  const firstDay = new Date(year, month - 1, 1).getDay();
  const day = 1 + ((weekday - firstDay + 7) % 7) + (n - 1) * 7;
  return day;
}

/** Get the last occurrence of a weekday in a given month/year. */
function lastWeekday(year: number, month: number, weekday: number): number {
  const lastDate = new Date(year, month, 0).getDate(); // last day of month
  const lastDay = new Date(year, month - 1, lastDate).getDay();
  const diff = (lastDay - weekday + 7) % 7;
  return lastDate - diff;
}

/** Format a date as "YYYY-MM-DD" string, handling month overflow. */
function formatHolidayDate(year: number, month: number, day: number): string {
  const d = new Date(year, month - 1, day);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

/** Apply NYSE weekend-observed rule to a fixed-date holiday. */
function observedDate(year: number, month: number, day: number): string {
  const date = new Date(year, month - 1, day);
  const dow = date.getDay();
  if (dow === 6) {
    // Saturday → observed Friday
    return formatHolidayDate(year, month, day - 1);
  }
  if (dow === 0) {
    // Sunday → observed Monday
    return formatHolidayDate(year, month, day + 1);
  }
  return formatHolidayDate(year, month, day);
}

/**
 * Get NYSE market holidays for a given year.
 * Returns a Set of "YYYY-MM-DD" strings for fast lookup.
 */
function getMarketHolidays(year: number): Set<string> {
  if (holidayCache.has(year)) return holidayCache.get(year)!;

  const holidays = new Set<string>();

  // Fixed-date holidays (with weekend-observed rule)
  holidays.add(observedDate(year, 1, 1));   // New Year's Day
  holidays.add(observedDate(year, 6, 19));  // Juneteenth
  holidays.add(observedDate(year, 7, 4));   // Independence Day
  holidays.add(observedDate(year, 12, 25)); // Christmas

  // Nth-weekday holidays (always land on the correct day, no observed rule needed)
  const mlk = nthWeekday(year, 1, 1, 3);        // 3rd Monday of Jan
  holidays.add(formatHolidayDate(year, 1, mlk));

  const presidents = nthWeekday(year, 2, 1, 3);  // 3rd Monday of Feb
  holidays.add(formatHolidayDate(year, 2, presidents));

  const memorial = lastWeekday(year, 5, 1);       // Last Monday of May
  holidays.add(formatHolidayDate(year, 5, memorial));

  const labor = nthWeekday(year, 9, 1, 1);        // 1st Monday of Sep
  holidays.add(formatHolidayDate(year, 9, labor));

  const thanksgiving = nthWeekday(year, 11, 4, 4); // 4th Thursday of Nov
  holidays.add(formatHolidayDate(year, 11, thanksgiving));

  // Good Friday = 2 days before Easter Sunday
  const [easterMonth, easterDay] = computeEasterSunday(year);
  const goodFriday = new Date(year, easterMonth - 1, easterDay - 2);
  holidays.add(formatHolidayDate(goodFriday.getFullYear(), goodFriday.getMonth() + 1, goodFriday.getDate()));

  holidayCache.set(year, holidays);
  return holidays;
}

/**
 * Check if a given ET date is a market holiday.
 */
function isMarketHoliday(etNow: Date): boolean {
  const year = etNow.getFullYear();
  const month = etNow.getMonth() + 1;
  const day = etNow.getDate();
  const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
  return getMarketHolidays(year).has(dateStr);
}

/**
 * Get the next trading day, skipping weekends and holidays.
 */
function getNextTradingDay(etNow: Date): string {
  const d = new Date(etNow);
  const hour = d.getHours();
  const minute = d.getMinutes();

  // If before market open today AND today is a trading day, next session is today
  const beforeOpen = hour < MARKET_OPEN_HOUR || (hour === MARKET_OPEN_HOUR && minute < MARKET_OPEN_MINUTE);
  if (beforeOpen && d.getDay() >= 1 && d.getDay() <= 5 && !isMarketHoliday(d)) {
    return 'today';
  }

  // Check next 7 days
  for (let i = 1; i <= 7; i++) {
    const next = new Date(d);
    next.setDate(next.getDate() + i);
    const dow = next.getDay();
    if (dow >= 1 && dow <= 5 && !isMarketHoliday(next)) {
      return i === 1 ? 'tomorrow' : next.toLocaleDateString('en-US', { weekday: 'long' });
    }
  }

  return 'next week';  // fallback (should never happen)
}

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
    const nextDay = getNextTradingDay(etNow);
    return {
      status: 'closed',
      message: `Market closed — next session: ${nextDay} 9:30 AM ET`,
    };
  }

  // Holiday check
  if (isMarketHoliday(etNow)) {
    const nextDay = getNextTradingDay(etNow);
    return {
      status: 'closed',
      message: `Market closed (holiday) — next session: ${nextDay} 9:30 AM ET`,
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
  const nextDay = getNextTradingDay(etNow);
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

/**
 * Get today's date in ET timezone as YYYY-MM-DD string.
 *
 * Useful for filtering trades to "today" in API calls.
 */
export function getTodayET(): string {
  const now = new Date();
  // Intl.DateTimeFormat with 'en-CA' locale returns YYYY-MM-DD format
  const etDate = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/New_York',
  }).format(now);
  return etDate;
}
