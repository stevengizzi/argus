/**
 * Performance analytics page with charts and metrics.
 *
 * Placeholder for Session 6 implementation.
 */

import { TrendingUp } from 'lucide-react';

export function PerformancePage() {
  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center gap-3">
        <TrendingUp className="w-6 h-6 text-argus-accent" />
        <h1 className="text-xl font-semibold text-argus-text">Performance</h1>
      </div>

      {/* Placeholder content */}
      <div className="bg-argus-surface border border-argus-border rounded-lg p-8 text-center">
        <p className="text-argus-text-dim">
          Performance analytics coming in Session 6.
        </p>
        <p className="text-argus-text-dim text-sm mt-2">
          Equity curve, daily P&L histogram, metrics grid, and strategy breakdown.
        </p>
      </div>
    </div>
  );
}
