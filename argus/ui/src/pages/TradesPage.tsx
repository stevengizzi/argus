/**
 * Trade log page with filtering and pagination.
 *
 * Placeholder for Session 5 implementation.
 */

import { ScrollText } from 'lucide-react';

export function TradesPage() {
  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center gap-3">
        <ScrollText className="w-6 h-6 text-argus-accent" />
        <h1 className="text-xl font-semibold text-argus-text">Trades</h1>
      </div>

      {/* Placeholder content */}
      <div className="bg-argus-surface border border-argus-border rounded-lg p-8 text-center">
        <p className="text-argus-text-dim">
          Trade log coming in Session 5.
        </p>
        <p className="text-argus-text-dim text-sm mt-2">
          Full trade history with filtering, sorting, and pagination.
        </p>
      </div>
    </div>
  );
}
