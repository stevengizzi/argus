/**
 * IntelligenceBriefView - Main component for viewing pre-market intelligence briefs.
 *
 * Features:
 * - Date navigation with prev/next arrows
 * - Markdown rendering of brief content
 * - Metadata bar showing generation info
 * - Generate button for creating new briefs
 * - Empty, loading, and error states
 *
 * Sprint 23.5 Session 6
 */

import { useState, useMemo } from "react";
import { ChevronLeft, ChevronRight, RefreshCw, AlertCircle, FileText } from "lucide-react";
import { MarkdownRenderer } from "./MarkdownRenderer";
import { BriefingCard } from "./BriefingCard";
import {
  useIntelligenceBriefing,
  useIntelligenceBriefingHistory,
  useGenerateIntelligenceBriefing,
} from "../hooks/useIntelligenceBriefings";

/**
 * Get today's date in ET timezone as YYYY-MM-DD.
 */
function getTodayET(): string {
  const now = new Date();
  const etDate = new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/New_York",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(now);
  return etDate;
}

/**
 * Format a date string for display.
 */
function formatDateDisplay(dateStr: string): string {
  const date = new Date(dateStr + "T12:00:00");
  return date.toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

/**
 * Adjust date by a number of days.
 */
function adjustDate(dateStr: string, days: number): string {
  const date = new Date(dateStr + "T12:00:00");
  date.setDate(date.getDate() + days);
  return date.toISOString().split("T")[0];
}

/**
 * Format the generated_at timestamp for display.
 */
function formatGeneratedAt(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
    timeZone: "America/New_York",
  });
}

export function IntelligenceBriefView() {
  const [selectedDate, setSelectedDate] = useState<string>(getTodayET);

  const {
    data: brief,
    isLoading,
    isError,
    error,
    refetch,
  } = useIntelligenceBriefing(selectedDate);

  const { data: history } = useIntelligenceBriefingHistory(10);
  const generateMutation = useGenerateIntelligenceBriefing();

  const todayET = useMemo(() => getTodayET(), []);
  const isToday = selectedDate === todayET;
  const isFuture = selectedDate > todayET;

  const handlePrevDay = () => {
    setSelectedDate((prev) => adjustDate(prev, -1));
  };

  const handleNextDay = () => {
    const next = adjustDate(selectedDate, 1);
    if (next <= todayET) {
      setSelectedDate(next);
    }
  };

  const handleGenerate = () => {
    generateMutation.mutate();
  };

  const handleHistoryClick = (date: string) => {
    setSelectedDate(date);
  };

  const showGenerateButton = isToday && !brief;

  return (
    <div className="flex gap-6">
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-4">
          <button
            onClick={handlePrevDay}
            className="p-2 rounded-lg hover:bg-argus-surface-2 text-argus-text-dim hover:text-argus-text transition-colors"
            aria-label="Previous day"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>

          <div className="text-center">
            <h2 className="text-lg font-semibold text-argus-text">
              {formatDateDisplay(selectedDate)}
            </h2>
            <span className="text-xs text-argus-text-dim">
              {isToday ? "Today" : ""}
            </span>
          </div>

          <button
            onClick={handleNextDay}
            disabled={isToday || isFuture}
            className="p-2 rounded-lg hover:bg-argus-surface-2 text-argus-text-dim hover:text-argus-text transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            aria-label="Next day"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>

        <div className="bg-argus-surface rounded-lg border border-argus-border">
          {isLoading && (
            <div className="p-8 flex flex-col items-center justify-center text-argus-text-dim">
              <RefreshCw className="w-8 h-8 animate-spin mb-3" />
              <span className="text-sm">Loading briefing...</span>
            </div>
          )}

          {isError && !isLoading && (
            <div className="p-8 flex flex-col items-center justify-center">
              <AlertCircle className="w-8 h-8 text-red-400 mb-3" />
              <span className="text-sm text-argus-text mb-3">Failed to load briefing</span>
              <span className="text-xs text-argus-text-dim mb-4">{error?.message ?? "Unknown error"}</span>
              <button
                onClick={() => refetch()}
                className="px-4 py-2 text-sm bg-argus-surface-2 hover:bg-argus-surface-3 text-argus-text rounded-lg transition-colors"
              >
                Retry
              </button>
            </div>
          )}

          {!isLoading && !isError && !brief && (
            <div className="p-8 flex flex-col items-center justify-center">
              <FileText className="w-8 h-8 text-argus-text-dim mb-3" />
              <span className="text-sm text-argus-text mb-4">
                No intelligence brief for {formatDateDisplay(selectedDate)}
              </span>
              {showGenerateButton && (
                <button
                  onClick={handleGenerate}
                  disabled={generateMutation.isPending}
                  className="px-4 py-2 text-sm bg-argus-accent hover:bg-argus-accent-hover text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {generateMutation.isPending && <RefreshCw className="w-4 h-4 animate-spin" />}
                  Generate Brief
                </button>
              )}
            </div>
          )}

          {!isLoading && !isError && brief && (
            <div className="p-6">
              <div className="prose prose-invert max-w-none">
                <MarkdownRenderer content={brief.content} />
              </div>

              <div className="mt-6 pt-4 border-t border-argus-border flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-argus-text-dim">
                <span>Generated at {formatGeneratedAt(brief.generated_at)}</span>
                <span className="text-argus-border">|</span>
                <span>{brief.catalyst_count} catalysts</span>
                <span className="text-argus-border">|</span>
                <span>{brief.symbols_covered.length} symbols</span>
                <span className="text-argus-border">|</span>
                <span>Cost: ${brief.generation_cost_usd.toFixed(4)}</span>
              </div>
            </div>
          )}
        </div>

        {!isLoading && isToday && brief && (
          <div className="mt-4 flex justify-end">
            <button
              onClick={handleGenerate}
              disabled={generateMutation.isPending}
              className="px-3 py-1.5 text-xs bg-argus-surface-2 hover:bg-argus-surface-3 text-argus-text-dim hover:text-argus-text rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {generateMutation.isPending && <RefreshCw className="w-3 h-3 animate-spin" />}
              Regenerate Brief
            </button>
          </div>
        )}
      </div>

      {history && history.length > 0 && (
        <div className="w-64 shrink-0 hidden lg:block">
          <h3 className="text-sm font-medium text-argus-text mb-3">Recent Briefs</h3>
          <div className="space-y-2">
            {history.map((historyBrief) => (
              <BriefingCard
                key={historyBrief.id}
                brief={historyBrief}
                onClick={() => handleHistoryClick(historyBrief.date)}
                isActive={historyBrief.date === selectedDate}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
