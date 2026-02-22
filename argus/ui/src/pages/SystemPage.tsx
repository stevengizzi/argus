/**
 * System health and monitoring page.
 *
 * Placeholder for Session 7 implementation.
 */

import { Activity } from 'lucide-react';

export function SystemPage() {
  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center gap-3">
        <Activity className="w-6 h-6 text-argus-accent" />
        <h1 className="text-xl font-semibold text-argus-text">System</h1>
      </div>

      {/* Placeholder content */}
      <div className="bg-argus-surface border border-argus-border rounded-lg p-8 text-center">
        <p className="text-argus-text-dim">
          System monitoring coming in Session 7.
        </p>
        <p className="text-argus-text-dim text-sm mt-2">
          Component health, strategy cards, and event log.
        </p>
      </div>
    </div>
  );
}
