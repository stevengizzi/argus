/**
 * Calendar P&L View visualization.
 *
 * Shows a monthly calendar grid with daily P&L values.
 *
 * Features:
 * - Monthly calendar grid (7 cols: Sun-Sat, 5-6 rows)
 * - Month navigation (← →)
 * - Day cells with P&L value and colored background
 * - Weekend cells grayed out
 * - Click day: navigate to /trades?date={YYYY-MM-DD}
 * - Weekly totals summary
 */

import { useState, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Card } from '../../components/Card';
import {
  createDivergingScale,
  getContrastTextColor,
} from '../../utils/colorScales';
import type { DailyPnlEntry } from '../../api/types';

// Day of week headers
const DAY_HEADERS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

interface CalendarPnlViewProps {
  dailyPnl: DailyPnlEntry[];
}

export function CalendarPnlView({ dailyPnl }: CalendarPnlViewProps) {
  const navigate = useNavigate();

  // Current month being viewed
  const [currentMonth, setCurrentMonth] = useState(() => {
    // Start with the latest month in the data, or current month
    if (dailyPnl.length > 0) {
      const latestDate = new Date(dailyPnl[dailyPnl.length - 1].date);
      return { year: latestDate.getFullYear(), month: latestDate.getMonth() };
    }
    const now = new Date();
    return { year: now.getFullYear(), month: now.getMonth() };
  });

  // Build lookup map for P&L by date
  const pnlMap = useMemo(() => {
    const map = new Map<string, DailyPnlEntry>();
    for (const entry of dailyPnl) {
      map.set(entry.date, entry);
    }
    return map;
  }, [dailyPnl]);

  // Compute color scale based on P&L values
  const colorScale = useMemo(() => {
    if (dailyPnl.length === 0) {
      return createDivergingScale(-100, 100);
    }

    const values = dailyPnl.map((e) => e.pnl);
    const minVal = Math.min(...values);
    const maxVal = Math.max(...values);

    return createDivergingScale(minVal, maxVal);
  }, [dailyPnl]);

  // Get calendar data for current month
  const calendarData = useMemo(() => {
    const { year, month } = currentMonth;
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const startDayOfWeek = firstDay.getDay();
    const daysInMonth = lastDay.getDate();

    // Build weeks array
    const weeks: Array<Array<{ date: number | null; dateStr: string | null; isWeekend: boolean }>> = [];
    let currentWeek: Array<{ date: number | null; dateStr: string | null; isWeekend: boolean }> = [];

    // Fill in empty days at start
    for (let i = 0; i < startDayOfWeek; i++) {
      currentWeek.push({ date: null, dateStr: null, isWeekend: i === 0 || i === 6 });
    }

    // Fill in days
    for (let day = 1; day <= daysInMonth; day++) {
      const dayOfWeek = (startDayOfWeek + day - 1) % 7;
      const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
      currentWeek.push({
        date: day,
        dateStr,
        isWeekend: dayOfWeek === 0 || dayOfWeek === 6,
      });

      if (currentWeek.length === 7) {
        weeks.push(currentWeek);
        currentWeek = [];
      }
    }

    // Fill in empty days at end
    while (currentWeek.length > 0 && currentWeek.length < 7) {
      const dayOfWeek = currentWeek.length;
      currentWeek.push({ date: null, dateStr: null, isWeekend: dayOfWeek === 0 || dayOfWeek === 6 });
    }
    if (currentWeek.length > 0) {
      weeks.push(currentWeek);
    }

    return weeks;
  }, [currentMonth]);

  // Compute weekly totals
  const weeklyTotals = useMemo(() => {
    return calendarData.map((week, weekIdx) => {
      let total = 0;
      for (const day of week) {
        if (day.dateStr) {
          const entry = pnlMap.get(day.dateStr);
          if (entry) {
            total += entry.pnl;
          }
        }
      }
      return { week: weekIdx + 1, total };
    });
  }, [calendarData, pnlMap]);

  // Navigate to previous/next month
  const goToPrevMonth = useCallback(() => {
    setCurrentMonth((prev) => {
      if (prev.month === 0) {
        return { year: prev.year - 1, month: 11 };
      }
      return { year: prev.year, month: prev.month - 1 };
    });
  }, []);

  const goToNextMonth = useCallback(() => {
    setCurrentMonth((prev) => {
      if (prev.month === 11) {
        return { year: prev.year + 1, month: 0 };
      }
      return { year: prev.year, month: prev.month + 1 };
    });
  }, []);

  // Handle day click
  const handleDayClick = useCallback((dateStr: string | null) => {
    if (dateStr && pnlMap.has(dateStr)) {
      navigate(`/trades?date=${dateStr}`);
    }
  }, [navigate, pnlMap]);

  // Format month name
  const monthName = new Date(currentMonth.year, currentMonth.month).toLocaleDateString('en-US', {
    month: 'long',
    year: 'numeric',
  });

  // Format currency
  const formatCurrency = (value: number): string => {
    const sign = value >= 0 ? '+' : '-';
    return `${sign}$${Math.abs(value).toFixed(0)}`;
  };

  const isEmpty = dailyPnl.length === 0;

  return (
    <Card>
      {/* Header with month navigation */}
      <div className="flex items-center justify-between px-4 pt-4 pb-2">
        <h3 className="text-sm font-medium text-argus-text">Calendar P&L</h3>
        <div className="flex items-center gap-2">
          <button
            onClick={goToPrevMonth}
            className="p-1.5 rounded hover:bg-argus-surface-2 transition-colors"
            aria-label="Previous month"
          >
            <ChevronLeft className="w-4 h-4 text-argus-text-dim" />
          </button>
          <span className="text-sm font-medium text-argus-text min-w-[140px] text-center">
            {monthName}
          </span>
          <button
            onClick={goToNextMonth}
            className="p-1.5 rounded hover:bg-argus-surface-2 transition-colors"
            aria-label="Next month"
          >
            <ChevronRight className="w-4 h-4 text-argus-text-dim" />
          </button>
        </div>
      </div>

      <div className="p-4">
        {isEmpty ? (
          <div className="h-[200px] flex items-center justify-center">
            <p className="text-argus-text-dim">No P&L data available</p>
          </div>
        ) : (
          <>
            {/* Day headers */}
            <div className="grid grid-cols-7 gap-1 mb-1">
              {DAY_HEADERS.map((day) => (
                <div
                  key={day}
                  className="text-center text-xs text-argus-text-dim py-1"
                >
                  {day}
                </div>
              ))}
            </div>

            {/* Calendar grid */}
            <div className="grid grid-cols-7 gap-1">
              {calendarData.flat().map((day, idx) => {
                const entry = day.dateStr ? pnlMap.get(day.dateStr) : null;
                const hasData = entry && entry.trades > 0;

                // Background color
                let bgColor = 'transparent';
                if (day.isWeekend && day.date !== null) {
                  bgColor = 'rgba(55, 65, 81, 0.2)';
                } else if (hasData) {
                  bgColor = colorScale(entry.pnl);
                } else if (day.date !== null) {
                  bgColor = 'rgba(55, 65, 81, 0.1)';
                }

                // Dynamic text color based on background luminance
                const pnlColor = hasData
                  ? getContrastTextColor(bgColor)
                  : undefined;

                return (
                  <div
                    key={idx}
                    className={`
                      relative min-h-[52px] rounded-md p-1
                      ${day.date !== null ? 'cursor-pointer hover:opacity-80' : ''}
                      ${hasData ? 'transition-opacity' : ''}
                    `}
                    style={{ backgroundColor: bgColor }}
                    onClick={() => day.dateStr && handleDayClick(day.dateStr)}
                    role={hasData ? 'button' : undefined}
                    tabIndex={hasData ? 0 : undefined}
                  >
                    {day.date !== null && (
                      <>
                        {/* Date number */}
                        <span
                          className={`
                            absolute top-1 left-1.5 text-xs
                            ${day.isWeekend ? 'text-argus-text-dim/50' : 'text-argus-text-dim'}
                          `}
                        >
                          {day.date}
                        </span>

                        {/* P&L value */}
                        {hasData && (
                          <div className="absolute inset-0 flex items-center justify-center pt-2">
                            <span
                              className="text-xs font-medium"
                              style={{ color: pnlColor }}
                            >
                              {formatCurrency(entry.pnl)}
                            </span>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Weekly totals */}
            <div className="mt-4 pt-3 border-t border-argus-border">
              <div className="flex flex-wrap gap-3 justify-center">
                {weeklyTotals.map(({ week, total }) => (
                  <div key={week} className="text-xs">
                    <span className="text-argus-text-dim">Week {week}:</span>{' '}
                    <span className={total >= 0 ? 'text-argus-profit' : 'text-argus-loss'}>
                      {formatCurrency(total)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </Card>
  );
}
