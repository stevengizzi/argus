/**
 * ArenaStatsBar — top stats strip for The Arena page.
 *
 * Displays five real-time session metrics: open position count,
 * total P&L (color-coded), net R-multiple, entries in last 5 min,
 * exits in last 5 min.
 *
 * Props are static placeholders in S8; wired to live data in S11.
 *
 * Sprint 32.75, Session 8.
 */

interface StatItemProps {
  label: string;
  children: React.ReactNode;
}

function StatItem({ label, children }: StatItemProps) {
  return (
    <div className="flex items-center gap-2 px-4 border-r border-argus-border last:border-r-0">
      <span className="text-[10px] text-argus-text-dim uppercase tracking-widest whitespace-nowrap">
        {label}
      </span>
      <span className="text-sm font-mono font-semibold">{children}</span>
    </div>
  );
}

export interface ArenaStatsBarProps {
  positionCount?: number;
  totalPnl?: number;
  netR?: number;
  entries5m?: number;
  exits5m?: number;
}

export function ArenaStatsBar({
  positionCount = 0,
  totalPnl = 0,
  netR = 0,
  entries5m = 0,
  exits5m = 0,
}: ArenaStatsBarProps) {
  const pnlPositive = totalPnl > 0;
  const pnlNegative = totalPnl < 0;
  const pnlClass = pnlPositive
    ? 'text-argus-profit'
    : pnlNegative
    ? 'text-argus-loss'
    : 'text-argus-text';

  const rPositive = netR >= 0;
  const rClass = rPositive ? 'text-argus-profit' : 'text-argus-loss';

  const pnlSign = pnlPositive ? '+' : pnlNegative ? '-' : '';
  const rSign = rPositive ? '+' : '';

  return (
    <div
      className="flex items-center h-12 bg-argus-surface border-b border-argus-border px-2 flex-none"
      data-testid="arena-stats-bar"
    >
      <StatItem label="Positions">
        <span className="text-argus-text" data-testid="stat-position-count">
          {positionCount}
        </span>
      </StatItem>

      <StatItem label="Total P&amp;L">
        <span className={pnlClass} data-testid="stat-total-pnl">
          {pnlSign}${Math.abs(totalPnl).toFixed(2)}
        </span>
      </StatItem>

      <StatItem label="Net R">
        <span className={rClass} data-testid="stat-net-r">
          {rSign}
          {netR.toFixed(2)}R
        </span>
      </StatItem>

      <StatItem label="Entries 5m">
        <span className="text-argus-text" data-testid="stat-entries-5m">
          {entries5m}
        </span>
      </StatItem>

      <StatItem label="Exits 5m">
        <span className="text-argus-text" data-testid="stat-exits-5m">
          {exits5m}
        </span>
      </StatItem>
    </div>
  );
}
