/**
 * Manages debrief mode state for the Observatory page.
 *
 * When debrief is active, all data hooks switch from live WebSocket/polling
 * to one-time REST fetches with a date parameter. WebSocket connections are
 * not established in debrief mode.
 *
 * Sprint 25, Session 9.
 */

import { useState, useCallback, useMemo } from 'react';

/** Default retention window in days for debrief history. */
const DEBRIEF_RETENTION_DAYS = 7;

interface DebriefState {
  isDebrief: boolean;
  selectedDate: string | null;
}

export interface UseDebriefModeResult {
  isDebrief: boolean;
  selectedDate: string | null;
  enterDebrief: (date: string) => void;
  exitDebrief: () => void;
  availableDates: DebriefDate[];
  validationError: string | null;
}

export interface DebriefDate {
  date: string;      // YYYY-MM-DD
  label: string;     // "Mon Mar 16"
  isWeekend: boolean;
}

function formatDateLabel(date: Date): string {
  return date.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  });
}

function isWeekend(date: Date): boolean {
  const day = date.getDay();
  return day === 0 || day === 6;
}

function toYYYYMMDD(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function buildAvailableDates(retentionDays: number): DebriefDate[] {
  const dates: DebriefDate[] = [];
  const now = new Date();

  for (let i = 1; i <= retentionDays; i++) {
    const d = new Date(now);
    d.setDate(d.getDate() - i);
    dates.push({
      date: toYYYYMMDD(d),
      label: formatDateLabel(d),
      isWeekend: isWeekend(d),
    });
  }

  return dates;
}

function validateDate(
  date: string,
  availableDates: DebriefDate[],
): string | null {
  const entry = availableDates.find((d) => d.date === date);
  if (!entry) return `Date ${date} is outside the ${DEBRIEF_RETENTION_DAYS}-day retention window`;
  if (entry.isWeekend) return `No market data for ${entry.label}`;
  return null;
}

export function useDebriefMode(): UseDebriefModeResult {
  const [state, setState] = useState<DebriefState>({
    isDebrief: false,
    selectedDate: null,
  });
  const [validationError, setValidationError] = useState<string | null>(null);

  const availableDates = useMemo(
    () => buildAvailableDates(DEBRIEF_RETENTION_DAYS),
    [],
  );

  const enterDebrief = useCallback(
    (date: string) => {
      const error = validateDate(date, availableDates);
      if (error) {
        setValidationError(error);
        return;
      }
      setValidationError(null);
      setState({ isDebrief: true, selectedDate: date });
    },
    [availableDates],
  );

  const exitDebrief = useCallback(() => {
    setValidationError(null);
    setState({ isDebrief: false, selectedDate: null });
  }, []);

  return {
    isDebrief: state.isDebrief,
    selectedDate: state.selectedDate,
    enterDebrief,
    exitDebrief,
    availableDates,
    validationError,
  };
}
