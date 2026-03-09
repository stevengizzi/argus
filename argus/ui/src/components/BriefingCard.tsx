/**
 * BriefingCard - Compact card for briefing history display.
 *
 * Shows date, catalyst count, symbol count, and truncated content preview.
 * Used in the history sidebar of IntelligenceBriefView.
 *
 * Sprint 23.5 Session 6
 */

import type { IntelligenceBrief } from "../hooks/useIntelligenceBriefings";

interface BriefingCardProps {
  brief: IntelligenceBrief;
  onClick: () => void;
  isActive?: boolean;
}

/**
 * Format date for compact display (e.g., "Mar 10").
 */
function formatShortDate(dateStr: string): string {
  const date = new Date(dateStr + "T12:00:00");
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

/**
 * Get the first line of content, truncated if needed.
 */
function getContentPreview(content: string, maxLength: number = 60): string {
  // Remove markdown headers and get first meaningful line
  const lines = content.split("\n").filter((line) => {
    const trimmed = line.trim();
    return trimmed && !trimmed.startsWith("#");
  });

  const firstLine = lines[0] || "";
  // Remove markdown formatting
  const cleaned = firstLine
    .replace(/\*\*/g, "")
    .replace(/\*/g, "")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .trim();

  if (cleaned.length <= maxLength) {
    return cleaned;
  }
  return cleaned.substring(0, maxLength - 3) + "...";
}

export function BriefingCard({ brief, onClick, isActive = false }: BriefingCardProps) {
  const preview = getContentPreview(brief.content);

  return (
    <button
      onClick={onClick}
      className={`w-full text-left p-3 rounded-lg border transition-colors ${
        isActive
          ? "bg-argus-accent/10 border-argus-accent/30"
          : "bg-argus-surface border-argus-border hover:bg-argus-surface-2"
      }`}
    >
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm font-medium text-argus-text">
          {formatShortDate(brief.date)}
        </span>
        <div className="flex items-center gap-2 text-xs text-argus-text-dim">
          <span>{brief.catalyst_count} catalysts</span>
          <span>•</span>
          <span>{brief.symbols_covered.length} symbols</span>
        </div>
      </div>
      {preview && (
        <p className="text-xs text-argus-text-dim line-clamp-2">{preview}</p>
      )}
    </button>
  );
}
