/**
 * Dashboard page - main command post view.
 *
 * Placeholder for Session 4 implementation.
 */

import { LayoutDashboard } from 'lucide-react';

export function DashboardPage() {
  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center gap-3">
        <LayoutDashboard className="w-6 h-6 text-argus-accent" />
        <h1 className="text-xl font-semibold text-argus-text">Dashboard</h1>
      </div>

      {/* Placeholder content */}
      <div className="bg-argus-surface border border-argus-border rounded-lg p-8 text-center">
        <p className="text-argus-text-dim">
          Dashboard content coming in Session 4.
        </p>
        <p className="text-argus-text-dim text-sm mt-2">
          Account summary, positions, recent trades, and system health.
        </p>
      </div>
    </div>
  );
}
