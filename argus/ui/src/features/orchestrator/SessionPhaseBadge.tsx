/**
 * Session phase badge - shows current trading session phase.
 *
 * Extracted from RegimePanel for use in page header.
 * Displays colored pill badge with phase name.
 */

// Session phase colors and labels
const SESSION_PHASE_CONFIG: Record<string, { label: string; className: string }> = {
  pre_market: {
    label: 'Pre-Market',
    className: 'text-argus-accent bg-argus-accent/15',
  },
  market_open: {
    label: 'Market Open',
    className: 'text-argus-profit bg-argus-profit-dim',
  },
  midday: {
    label: 'Midday',
    className: 'text-argus-warning bg-argus-warning-dim',
  },
  power_hour: {
    label: 'Power Hour',
    className: 'text-orange-400 bg-orange-400/15',
  },
  after_hours: {
    label: 'After Hours',
    className: 'text-argus-text-dim bg-argus-surface-2',
  },
  market_closed: {
    label: 'Market Closed',
    className: 'text-argus-text-dim bg-argus-surface-2',
  },
};

interface SessionPhaseBadgeProps {
  phase: string;
}

export function SessionPhaseBadge({ phase }: SessionPhaseBadgeProps) {
  const config = SESSION_PHASE_CONFIG[phase] ?? SESSION_PHASE_CONFIG.market_closed;

  return (
    <span
      className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${config.className}`}
    >
      {config.label}
    </span>
  );
}
