/**
 * System health and monitoring page.
 *
 * Shows overall system status, component health, strategy cards,
 * and WebSocket event log.
 */

import { Activity } from 'lucide-react';
import {
  SystemOverview,
  ComponentStatusList,
  StrategyCards,
  EventsLog,
} from '../features/system';

export function SystemPage() {
  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center gap-3">
        <Activity className="w-6 h-6 text-argus-accent" />
        <h1 className="text-xl font-semibold text-argus-text">System</h1>
      </div>

      {/* Main content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left column: Overview and Components */}
        <div className="space-y-6">
          <SystemOverview />
          <ComponentStatusList />
        </div>

        {/* Right column: Strategies */}
        <div>
          <StrategyCards />
        </div>
      </div>

      {/* Events log - full width at bottom */}
      <EventsLog />
    </div>
  );
}
