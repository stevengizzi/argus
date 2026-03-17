/**
 * Compact date list for entering debrief mode.
 *
 * Shows the last 7 days with market/weekend indicators.
 * Selecting a market day enters debrief mode; clicking "Live" exits.
 *
 * Sprint 25, Session 9.
 */

import { useState, useRef, useEffect } from 'react';
import type { DebriefDate } from '../hooks/useDebriefMode';

interface DebriefDatePickerProps {
  isDebrief: boolean;
  selectedDate: string | null;
  availableDates: DebriefDate[];
  validationError: string | null;
  onSelectDate: (date: string) => void;
  onExitDebrief: () => void;
}

export function DebriefDatePicker({
  isDebrief,
  selectedDate,
  availableDates,
  validationError,
  onSelectDate,
  onExitDebrief,
}: DebriefDatePickerProps) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [open]);

  return (
    <div className="relative" ref={containerRef} data-testid="debrief-date-picker">
      {isDebrief ? (
        <button
          className="px-2 py-0.5 text-[10px] font-medium rounded bg-amber-500/20 text-amber-400 border border-amber-500/30 hover:bg-amber-500/30 transition-colors"
          onClick={onExitDebrief}
          data-testid="debrief-live-button"
        >
          Live
        </button>
      ) : (
        <button
          className="px-2 py-0.5 text-[10px] font-medium rounded bg-argus-surface-2 text-argus-text-dim border border-argus-border hover:text-argus-text hover:border-argus-border-bright transition-colors"
          onClick={() => setOpen((prev) => !prev)}
          data-testid="debrief-toggle-button"
        >
          Debrief
        </button>
      )}

      {open && !isDebrief && (
        <div
          className="absolute top-full left-0 mt-1 z-50 w-48 bg-argus-surface border border-argus-border rounded-md shadow-lg py-1"
          data-testid="debrief-date-list"
        >
          <div className="px-2 py-1 text-[9px] text-argus-text-dim uppercase tracking-wider border-b border-argus-border">
            Select date to review
          </div>
          {availableDates.map((entry) => (
            <button
              key={entry.date}
              className={`w-full text-left px-2 py-1.5 text-[11px] transition-colors ${
                entry.isWeekend
                  ? 'text-argus-text-dim/50 cursor-not-allowed'
                  : 'text-argus-text hover:bg-argus-surface-2 cursor-pointer'
              } ${selectedDate === entry.date ? 'bg-argus-surface-2' : ''}`}
              onClick={() => {
                onSelectDate(entry.date);
                setOpen(false);
              }}
              disabled={entry.isWeekend}
              data-testid={`debrief-date-${entry.date}`}
            >
              <span>{entry.label}</span>
              {entry.isWeekend && (
                <span className="ml-1 text-[9px] text-argus-text-dim/40">(weekend)</span>
              )}
            </button>
          ))}
          {validationError && (
            <div className="px-2 py-1 text-[10px] text-red-400 border-t border-argus-border">
              {validationError}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
