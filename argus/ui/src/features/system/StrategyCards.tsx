/**
 * Strategy info cards.
 *
 * Shows one card per strategy with: name, version, active status,
 * pipeline stage badge, allocated capital, today's P&L, trade count,
 * open positions, config summary, and pause/resume toggle.
 */

import { Card } from '../../components/Card';
import { CardHeader } from '../../components/CardHeader';
import { StatusDot } from '../../components/StatusDot';
import { Badge } from '../../components/Badge';
import { EmptyState } from '../../components/EmptyState';
import { useStrategies } from '../../hooks/useStrategies';
import { usePauseStrategy, useResumeStrategy } from '../../hooks/useControls';
import { formatCurrencyCompact, formatPnl } from '../../utils/format';
import { StrategyCardsSkeleton } from './SystemSkeleton';
import type { StrategyInfo } from '../../api/types';
import { Zap, Pause, Play } from 'lucide-react';

function getPipelineBadgeVariant(stage: string): 'info' | 'success' | 'warning' | 'neutral' {
  const normalized = stage.toLowerCase();
  if (normalized === 'live' || normalized === 'production') return 'success';
  if (normalized === 'paper' || normalized === 'validation') return 'warning';
  if (normalized === 'incubation' || normalized === 'development') return 'info';
  return 'neutral';
}

function formatConfigSummary(config: Record<string, unknown>): string {
  // Format config as compact key=value pairs
  const pairs = Object.entries(config)
    .filter(([, value]) => value !== null && value !== undefined)
    .slice(0, 5) // Limit to 5 most important
    .map(([key, value]) => {
      // Shorten common config keys
      const shortKey = key
        .replace('opening_range_minutes', 'or')
        .replace('hold_minutes', 'hold')
        .replace('gap_threshold', 'gap')
        .replace('target_r_multiple', 'r')
        .replace('stop_buffer_pct', 'stop_buf')
        .replace('max_range_atr_ratio', 'atr');

      // Format value
      let shortValue = String(value);
      if (typeof value === 'number') {
        shortValue = value % 1 === 0 ? String(value) : value.toFixed(1);
      }

      return `${shortKey}=${shortValue}`;
    });

  return pairs.join(', ') || 'No config';
}

interface StrategyCardProps {
  strategy: StrategyInfo;
}

function StrategyCard({ strategy }: StrategyCardProps) {
  const pnl = formatPnl(strategy.daily_pnl);
  const pauseMutation = usePauseStrategy();
  const resumeMutation = useResumeStrategy();

  const isPending = pauseMutation.isPending || resumeMutation.isPending;
  const error = pauseMutation.error || resumeMutation.error;

  const handleToggle = async () => {
    // Reset any previous errors
    pauseMutation.reset();
    resumeMutation.reset();

    try {
      if (strategy.is_active) {
        await pauseMutation.mutateAsync(strategy.strategy_id);
      } else {
        await resumeMutation.mutateAsync(strategy.strategy_id);
      }
    } catch {
      // Error is captured in mutation state
    }
  };

  return (
    <Card className={!strategy.is_active ? 'border-amber-500/30' : undefined}>
      {/* Header with name and badges */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-start gap-2.5">
          <StatusDot
            status={strategy.is_active ? 'healthy' : 'unknown'}
            pulse={strategy.is_active}
            size="sm"
          />
          <div>
            <div className="text-sm font-semibold text-argus-text">
              {strategy.name}
            </div>
            <div className="text-xs text-argus-text-dim">
              v{strategy.version}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {!strategy.is_active && (
            <Badge variant="warning">PAUSED</Badge>
          )}
          <Badge variant={getPipelineBadgeVariant(strategy.pipeline_stage)}>
            {strategy.pipeline_stage.toUpperCase()}
          </Badge>
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-2 mb-4">
        <div className="text-sm">
          <span className="text-argus-text-dim">Capital</span>
          <div className="text-argus-text tabular-nums">
            {formatCurrencyCompact(strategy.allocated_capital)}
          </div>
        </div>
        <div className="text-sm">
          <span className="text-argus-text-dim">Today</span>
          <div className={`tabular-nums ${pnl.className}`}>
            {pnl.text}
          </div>
        </div>
        <div className="text-sm">
          <span className="text-argus-text-dim">Trades</span>
          <div className="text-argus-text tabular-nums">
            {strategy.trade_count_today}
          </div>
        </div>
        <div className="text-sm">
          <span className="text-argus-text-dim">Open</span>
          <div className="text-argus-text tabular-nums">
            {strategy.open_positions}
          </div>
        </div>
      </div>

      {/* Config summary */}
      {strategy.config_summary && Object.keys(strategy.config_summary).length > 0 && (
        <div className="pt-3 border-t border-argus-border">
          <div className="text-xs text-argus-text-dim font-mono">
            {formatConfigSummary(strategy.config_summary)}
          </div>
        </div>
      )}

      {/* Pause/Resume toggle */}
      <div className="pt-3 mt-3 border-t border-argus-border">
        <button
          onClick={handleToggle}
          disabled={isPending}
          className={`w-full flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
            strategy.is_active
              ? 'bg-amber-500/10 text-amber-500 border border-amber-500/30 hover:bg-amber-500/20'
              : 'bg-argus-profit/10 text-argus-profit border border-argus-profit/30 hover:bg-argus-profit/20'
          }`}
        >
          {strategy.is_active ? (
            <>
              <Pause className="w-4 h-4" />
              {isPending ? 'Pausing...' : 'Pause Strategy'}
            </>
          ) : (
            <>
              <Play className="w-4 h-4" />
              {isPending ? 'Resuming...' : 'Resume Strategy'}
            </>
          )}
        </button>
        {error && (
          <div className="mt-2 text-xs text-argus-loss">
            {error instanceof Error ? error.message : 'Operation failed'}
          </div>
        )}
      </div>
    </Card>
  );
}

export function StrategyCards() {
  const { data, isLoading, error } = useStrategies();

  if (isLoading) {
    return <StrategyCardsSkeleton />;
  }

  if (error || !data) {
    return (
      <div>
        <CardHeader title="Strategies" />
        <Card>
          <div className="text-argus-loss text-sm">Failed to load strategies</div>
        </Card>
      </div>
    );
  }

  if (data.strategies.length === 0) {
    return (
      <div>
        <CardHeader title="Strategies" />
        <EmptyState
          icon={Zap}
          message="No strategies are currently configured."
        />
      </div>
    );
  }

  return (
    <div>
      <CardHeader
        title="Strategies"
        subtitle={`${data.strategies.length} configured`}
      />
      <div className="space-y-4">
        {data.strategies.map((strategy) => (
          <StrategyCard key={strategy.strategy_id} strategy={strategy} />
        ))}
      </div>
    </div>
  );
}
