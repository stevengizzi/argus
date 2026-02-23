/**
 * Strategy breakdown table showing per-strategy performance metrics.
 * Card container is stable; only table content dims during period transitions.
 */

import { Card } from '../../components/Card';
import { CardHeader } from '../../components/CardHeader';
import { DataTable, type Column } from '../../components/DataTable';
import { PnlValue } from '../../components/PnlValue';
import type { StrategyMetrics } from '../../api/types';
import { formatPercentRaw } from '../../utils/format';

interface StrategyRow {
  strategyId: string;
  metrics: StrategyMetrics;
}

interface StrategyBreakdownProps {
  byStrategy: Record<string, StrategyMetrics>;
  isTransitioning?: boolean;
  className?: string;
}

export function StrategyBreakdown({ byStrategy, isTransitioning = false, className = '' }: StrategyBreakdownProps) {
  // Convert record to array for DataTable
  const data: StrategyRow[] = Object.entries(byStrategy).map(([strategyId, metrics]) => ({
    strategyId,
    metrics,
  }));

  const columns: Column<StrategyRow>[] = [
    {
      key: 'strategy',
      header: 'Strategy',
      render: (row) => (
        <span className="font-medium text-argus-text">{row.strategyId}</span>
      ),
    },
    {
      key: 'trades',
      header: 'Trades',
      align: 'right',
      render: (row) => row.metrics.total_trades,
    },
    {
      key: 'winRate',
      header: 'Win Rate',
      align: 'right',
      render: (row) => formatPercentRaw(row.metrics.win_rate * 100),
    },
    {
      key: 'pf',
      header: 'PF',
      align: 'right',
      hideBelow: 'md',
      render: (row) => row.metrics.profit_factor.toFixed(2),
    },
    {
      key: 'pnl',
      header: 'Net P&L',
      align: 'right',
      render: (row) => <PnlValue value={row.metrics.net_pnl} format="currency" size="sm" />,
    },
  ];

  // Card and CardHeader always persist
  return (
    <Card className={className} noPadding>
      <div className="p-4 pb-0">
        <CardHeader title="By Strategy" />
      </div>
      <div
        className={`transition-opacity duration-200 ${isTransitioning ? 'opacity-40' : 'opacity-100'}`}
      >
        {data.length === 0 ? (
          <div className="text-center py-6 text-argus-text-dim text-sm p-4">
            No strategy data available
          </div>
        ) : (
          <DataTable
            columns={columns}
            data={data}
            keyExtractor={(row) => row.strategyId}
            emptyMessage="No strategy data"
          />
        )}
      </div>
    </Card>
  );
}
