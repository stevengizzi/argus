/**
 * Consistent number formatting for financial data.
 * All money values use USD. All percentages show 1-2 decimal places.
 */

const currencyFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const compactCurrencyFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
});

const percentFormatter = new Intl.NumberFormat('en-US', {
  style: 'percent',
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

const decimalFormatter = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

/** Format as currency: $1,234.56 */
export function formatCurrency(value: number): string {
  return currencyFormatter.format(value);
}

/** Format as compact currency (no cents): $1,235 */
export function formatCurrencyCompact(value: number): string {
  return compactCurrencyFormatter.format(value);
}

/** Format as percentage from decimal: 0.125 → 12.5% */
export function formatPercent(value: number): string {
  return percentFormatter.format(value);
}

/** Format as percentage from already-percentage value: 12.5 → 12.5% */
export function formatPercentRaw(value: number): string {
  return `${decimalFormatter.format(value)}%`;
}

/** Format P&L with sign and color class name */
export function formatPnl(value: number): { text: string; className: string } {
  const sign = value >= 0 ? '+' : '';
  return {
    text: `${sign}${currencyFormatter.format(value)}`,
    className: value > 0 ? 'text-argus-profit' : value < 0 ? 'text-argus-loss' : 'text-argus-text-dim',
  };
}

/** Format P&L percentage with sign and color */
export function formatPnlPercent(value: number): { text: string; className: string } {
  const sign = value >= 0 ? '+' : '';
  return {
    text: `${sign}${decimalFormatter.format(value)}%`,
    className: value > 0 ? 'text-argus-profit' : value < 0 ? 'text-argus-loss' : 'text-argus-text-dim',
  };
}

/** Format R-multiple: 1.5 → +1.50R */
export function formatR(value: number): { text: string; className: string } {
  const sign = value >= 0 ? '+' : '';
  return {
    text: `${sign}${decimalFormatter.format(value)}R`,
    className: value > 0 ? 'text-argus-profit' : value < 0 ? 'text-argus-loss' : 'text-argus-text-dim',
  };
}

/** Format duration from seconds: 3725 → "1h 2m" */
export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  const remainMinutes = minutes % 60;
  return remainMinutes > 0 ? `${hours}h ${remainMinutes}m` : `${hours}h`;
}

/** Format timestamp to ET time: "9:45:32 AM" */
export function formatTime(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleTimeString('en-US', {
    timeZone: 'America/New_York',
    hour: 'numeric',
    minute: '2-digit',
    second: '2-digit',
  });
}

/** Format timestamp to ET date: "Feb 23" */
export function formatDate(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleDateString('en-US', {
    timeZone: 'America/New_York',
    month: 'short',
    day: 'numeric',
  });
}

/** Format timestamp to full ET: "Feb 23, 9:45 AM" */
export function formatDateTime(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleDateString('en-US', {
    timeZone: 'America/New_York',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

/** Format price with appropriate decimal places */
export function formatPrice(value: number): string {
  return decimalFormatter.format(value);
}

/** Format large numbers compactly: 1234567 → "1.23M" */
export function formatCompact(value: number): string {
  if (Math.abs(value) >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(2)}M`;
  }
  if (Math.abs(value) >= 1_000) {
    return `${(value / 1_000).toFixed(1)}K`;
  }
  return decimalFormatter.format(value);
}

/** Format a Date as relative time: "2m ago", "1h ago", "3d ago" */
export function formatRelativeTime(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSeconds < 60) {
    return 'just now';
  } else if (diffMinutes < 60) {
    return `${diffMinutes}m ago`;
  } else if (diffHours < 24) {
    return `${diffHours}h ago`;
  } else {
    return `${diffDays}d ago`;
  }
}
