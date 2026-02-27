/**
 * Market countdown component showing time until market open.
 *
 * Sprint 21d Session 5 (DEC-204): Pre-market countdown.
 * - Live countdown to 9:30 AM ET
 * - Format: "2h 14m" or "14m 30s" (under 1 hour) or "Market Open" (green pulse)
 * - Uses setInterval(1000) to update
 * - Subtle animation on number transitions
 */

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface TimeRemaining {
  hours: number;
  minutes: number;
  seconds: number;
  totalSeconds: number;
  isOpen: boolean;
}

/**
 * Calculate time remaining until next market open (9:30 AM ET).
 */
function getTimeUntilOpen(): TimeRemaining {
  const now = new Date();

  // Convert to ET timezone
  const etOptions: Intl.DateTimeFormatOptions = {
    timeZone: 'America/New_York',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  };
  const etTimeStr = now.toLocaleTimeString('en-US', etOptions);
  const [hours, minutes, seconds] = etTimeStr.split(':').map(Number);

  // Market open at 9:30 ET
  const openHour = 9;
  const openMinute = 30;

  // Market close at 16:00 ET
  const closeHour = 16;
  const closeMinute = 0;

  const currentMinutes = hours * 60 + minutes;
  const openMinutes = openHour * 60 + openMinute;
  const closeMinutes = closeHour * 60 + closeMinute;

  // Check if market is currently open
  const isWeekday = (() => {
    const day = new Date().toLocaleDateString('en-US', {
      timeZone: 'America/New_York',
      weekday: 'short',
    });
    return !['Sat', 'Sun'].includes(day);
  })();

  const isOpen =
    isWeekday && currentMinutes >= openMinutes && currentMinutes < closeMinutes;

  if (isOpen) {
    return { hours: 0, minutes: 0, seconds: 0, totalSeconds: 0, isOpen: true };
  }

  // Calculate time until next open
  let targetMinutes = openMinutes - currentMinutes;

  // If past market open today, count to tomorrow
  if (currentMinutes >= openMinutes) {
    // Minutes remaining today + 24h - minutes until open tomorrow
    targetMinutes = 24 * 60 - currentMinutes + openMinutes;
  }

  // Adjust for weekends
  const etDay = new Date().toLocaleDateString('en-US', {
    timeZone: 'America/New_York',
    weekday: 'short',
  });

  let daysToAdd = 0;
  if (etDay === 'Sat') {
    daysToAdd = currentMinutes < openMinutes ? 1 : 2;
  } else if (etDay === 'Sun') {
    daysToAdd = currentMinutes < openMinutes ? 0 : 1;
  } else if (etDay === 'Fri' && currentMinutes >= openMinutes) {
    daysToAdd = 2; // Skip to Monday
  }

  targetMinutes += daysToAdd * 24 * 60;

  // Subtract current seconds for accuracy
  const totalSeconds = targetMinutes * 60 - seconds;
  const remainingHours = Math.floor(totalSeconds / 3600);
  const remainingMinutes = Math.floor((totalSeconds % 3600) / 60);
  const remainingSeconds = totalSeconds % 60;

  return {
    hours: remainingHours,
    minutes: remainingMinutes,
    seconds: remainingSeconds,
    totalSeconds,
    isOpen: false,
  };
}

/**
 * Format countdown display string.
 * - Over 1 hour: "2h 14m"
 * - Under 1 hour: "14m 30s"
 * - Under 1 minute: "30s"
 */
function formatCountdown(time: TimeRemaining): string {
  if (time.isOpen) return 'Market Open';

  if (time.hours > 0) {
    return `${time.hours}h ${time.minutes}m`;
  }

  if (time.minutes > 0) {
    return `${time.minutes}m ${time.seconds.toString().padStart(2, '0')}s`;
  }

  return `${time.seconds}s`;
}

export function MarketCountdown() {
  const [time, setTime] = useState<TimeRemaining>(getTimeUntilOpen);

  useEffect(() => {
    const interval = setInterval(() => {
      setTime(getTimeUntilOpen());
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="text-center py-8">
      <div className="text-sm text-argus-text-dim uppercase tracking-wider mb-2">
        {time.isOpen ? '' : 'Market Opens In'}
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={time.isOpen ? 'open' : time.totalSeconds}
          initial={{ opacity: 0.5, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0.5, scale: 0.95 }}
          transition={{ duration: 0.2 }}
          className={`text-4xl font-semibold ${
            time.isOpen ? 'text-argus-profit' : 'text-argus-text'
          }`}
        >
          {formatCountdown(time)}
        </motion.div>
      </AnimatePresence>

      {time.isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ repeat: Infinity, duration: 2 }}
          className="mt-2 inline-block w-2 h-2 bg-argus-profit rounded-full"
        />
      )}
    </div>
  );
}
