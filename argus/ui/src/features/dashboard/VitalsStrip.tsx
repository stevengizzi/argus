/**
 * VitalsStrip — compact horizontal strip consolidating key dashboard vitals.
 *
 * Four sections in a single row (~80–100px height):
 *   1. Account Equity — large number, cash + buying power beneath
 *   2. Daily P&L — large colored number with sparkline, trade count below
 *   3. Today's Stats — trades count, win rate, avg R, best trade
 *   4. VIX / Regime — VIX close + regime badge
 *
 * Pulls data from existing hooks (no new API calls).
 * Sprint 32.8, Session 2.
 */

import { AnimatedNumber } from '../../components/AnimatedNumber';
import { PnlValue } from '../../components/PnlValue';
import { Sparkline } from '../../components/Sparkline';
import { useAccount } from '../../hooks/useAccount';
import { useLiveEquity } from '../../hooks/useLiveEquity';
import { useSparklineData } from '../../hooks/useSparklineData';
import { useVixData } from '../../hooks/useVixData';
import { formatCurrency } from '../../utils/format';
import type { TodayStatsData } from '../../api/types';

interface VitalsStripProps {
  /** Pre-fetched today's stats from dashboard summary. */
  todayStats?: TodayStatsData;
}

function formatPnlWithSign(value: number): string {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${formatCurrency(value)}`;
}

/** Vertical divider between sections. */
function Divider() {
  return <div className="self-stretch w-px bg-argus-border mx-2 hidden sm:block" />;
}

export function VitalsStrip({ todayStats }: VitalsStripProps) {
  const { data: accountData } = useAccount();
  const liveEquity = useLiveEquity();
  const { pnlTrend } = useSparklineData();
  const { data: vixData } = useVixData();

  const equity = liveEquity?.equity ?? accountData?.equity ?? 0;
  const dailyPnl = liveEquity?.dailyPnl ?? accountData?.daily_pnl ?? 0;
  const dailyPnlPct = liveEquity?.dailyPnlPct ?? accountData?.daily_pnl_pct ?? 0;

  const sparklineColor =
    dailyPnl > 0
      ? 'var(--color-argus-profit)'
      : dailyPnl < 0
        ? 'var(--color-argus-loss)'
        : 'var(--color-argus-text-dim)';

  const trades = todayStats?.trade_count ?? 0;
  const winRate = todayStats?.win_rate ?? 0;
  const avgR = todayStats?.avg_r ?? 0;
  const bestTrade = todayStats?.best_trade ?? null;

  const vixClose = vixData?.vix_close;
  const vrpTier = vixData?.regime?.vrp_tier?.toUpperCase() ?? null;
  const volPhase = vixData?.regime?.vol_regime_phase?.toUpperCase() ?? null;
  const vixAvailable = vixData && vixData.status !== 'unavailable';

  return (
    <div
      className="flex items-stretch bg-argus-surface border border-argus-border rounded-lg px-4 py-3 gap-1 flex-wrap"
      data-testid="VitalsStrip"
    >
      {/* Section 1: Account Equity */}
      <div className="flex-1 min-w-[120px] flex flex-col justify-center">
        <div className="text-[10px] uppercase tracking-wider text-argus-text-dim mb-1">
          Equity
        </div>
        <AnimatedNumber
          value={equity}
          format={formatCurrency}
          className="text-xl font-semibold text-argus-text tabular-nums leading-none"
        />
        {accountData && (
          <div className="flex gap-3 mt-1">
            <span className="text-xs text-argus-text-dim tabular-nums">
              Cash{' '}
              <AnimatedNumber
                value={accountData.cash}
                format={formatCurrency}
                duration={200}
                className="text-argus-text"
              />
            </span>
            <span className="text-xs text-argus-text-dim tabular-nums">
              BP{' '}
              <AnimatedNumber
                value={accountData.buying_power}
                format={formatCurrency}
                duration={200}
                className="text-argus-text"
              />
            </span>
          </div>
        )}
      </div>

      <Divider />

      {/* Section 2: Daily P&L */}
      <div className="flex-[2] min-w-[130px] flex flex-col justify-center">
        <div className="text-[10px] uppercase tracking-wider text-argus-text-dim mb-1">
          Daily P&L
        </div>
        <AnimatedNumber
          value={dailyPnl}
          format={formatPnlWithSign}
          className={`text-xl font-medium tabular-nums leading-none transition-colors duration-300 ${
            dailyPnl > 0
              ? 'text-argus-profit'
              : dailyPnl < 0
                ? 'text-argus-loss'
                : 'text-argus-text-dim'
          }`}
        />
        {pnlTrend.length > 1 && (
          <div className="mt-1 w-24">
            <Sparkline
              data={pnlTrend}
              height={20}
              color={sparklineColor}
              fillOpacity={0.15}
            />
          </div>
        )}
        <div className="mt-0.5">
          <PnlValue value={dailyPnlPct} format="percent" size="sm" />
        </div>
        {accountData && (
          <div className="text-[10px] text-argus-text-dim mt-0.5">
            {trades} trade{trades !== 1 ? 's' : ''} today
          </div>
        )}
      </div>

      <Divider />

      {/* Section 3: Today's Stats */}
      <div className="flex-1 min-w-[160px] flex flex-col justify-center">
        <div className="text-[10px] uppercase tracking-wider text-argus-text-dim mb-1">
          Today's Stats
        </div>
        <div className="grid grid-cols-2 gap-x-4 gap-y-1">
          <div>
            <div className="text-[10px] text-argus-text-dim">Trades</div>
            <div className="text-base font-semibold text-argus-text tabular-nums leading-none">
              {trades}
            </div>
          </div>
          <div>
            <div className="text-[10px] text-argus-text-dim">Win Rate</div>
            <div className={`text-base font-semibold tabular-nums leading-none ${
              winRate * 100 >= 50 ? 'text-argus-profit' : winRate > 0 ? 'text-argus-loss' : 'text-argus-text'
            }`}>
              {trades > 0 ? `${(winRate * 100).toFixed(1)}%` : '—'}
            </div>
          </div>
          <div>
            <div className="text-[10px] text-argus-text-dim">Avg R</div>
            <div className={`text-base font-semibold tabular-nums leading-none ${
              avgR > 0 ? 'text-argus-profit' : avgR < 0 ? 'text-argus-loss' : 'text-argus-text'
            }`}>
              {avgR !== 0 ? `${avgR >= 0 ? '+' : ''}${avgR.toFixed(1)}R` : '—'}
            </div>
          </div>
          <div>
            <div className="text-[10px] text-argus-text-dim">Best</div>
            {bestTrade ? (
              <div className="text-sm font-medium leading-none">
                <span className="text-argus-text">{bestTrade.symbol}</span>
                <span className="text-argus-profit ml-1 text-xs">
                  +{formatCurrency(bestTrade.pnl)}
                </span>
              </div>
            ) : (
              <div className="text-base font-semibold text-argus-text-dim leading-none">—</div>
            )}
          </div>
        </div>
      </div>

      <Divider />

      {/* Section 4: VIX / Regime */}
      {vixAvailable && (
        <div className="flex-1 min-w-[120px] flex flex-col justify-center">
          <div className="text-[10px] uppercase tracking-wider text-argus-text-dim mb-1">
            VIX Regime
          </div>
          <div className="flex items-baseline gap-2 flex-wrap">
            {vixClose != null && (
              <span
                className="text-xl font-semibold text-argus-text tabular-nums leading-none"
                data-testid="vitals-vix-close"
              >
                {vixClose.toFixed(2)}
              </span>
            )}
            {vrpTier && (
              <span className="text-[10px] font-medium uppercase tracking-wider px-1.5 py-0.5 rounded border bg-argus-surface-2 text-argus-text-dim border-argus-border">
                {vrpTier}
              </span>
            )}
          </div>
          {volPhase && (
            <div className="text-xs text-argus-text-dim mt-0.5">
              {volPhase.replace('_', ' ')}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
