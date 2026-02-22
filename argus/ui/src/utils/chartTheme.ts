/**
 * Shared chart theming for both TradingView Lightweight Charts and Recharts.
 *
 * Lightweight Charts: equity curve, daily P&L histogram, future price charts
 * Recharts: sparklines, distributions, heatmaps (Sprint 21+)
 */

import type { DeepPartial, ChartOptions, LineStyle } from 'lightweight-charts';

/** Shared color constants used by both chart libraries */
export const chartColors = {
  primary: '#3b82f6',
  profit: '#22c55e',
  loss: '#ef4444',
  grid: '#2a2d3a',
  text: '#8b8fa3',
  bg: '#0f1117',
  surface: '#1a1d27',
  border: '#2a2d3a',
  series: ['#3b82f6', '#8b5cf6', '#06b6d4', '#f59e0b', '#ec4899', '#10b981'],
};

/** TradingView Lightweight Charts default options */
export const lwcDefaultOptions: DeepPartial<ChartOptions> = {
  layout: {
    background: { color: chartColors.bg },
    textColor: chartColors.text,
    fontSize: 11,
  },
  watermark: {
    visible: false,
  },
  grid: {
    vertLines: { color: chartColors.border },
    horzLines: { color: chartColors.border },
  },
  crosshair: {
    vertLine: {
      color: chartColors.text,
      width: 1,
      style: 3 as LineStyle,
      labelBackgroundColor: chartColors.surface,
    },
    horzLine: {
      color: chartColors.text,
      width: 1,
      style: 3 as LineStyle,
      labelBackgroundColor: chartColors.surface,
    },
  },
  timeScale: {
    borderColor: chartColors.border,
    timeVisible: false,
  },
  rightPriceScale: {
    borderColor: chartColors.border,
  },
};

/** Recharts shared props (for non-time-series charts in future sprints) */
export const rechartsAxisStyle = {
  fontSize: 11,
  fill: chartColors.text,
};

export const rechartsGridStyle = {
  strokeDasharray: '3 3',
  stroke: chartColors.grid,
};

export const rechartsTooltipStyle = {
  contentStyle: {
    backgroundColor: chartColors.surface,
    borderColor: chartColors.border,
    color: chartColors.text,
    borderRadius: '6px',
    fontSize: '12px',
  },
};
