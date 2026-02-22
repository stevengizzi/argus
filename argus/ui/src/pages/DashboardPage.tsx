/**
 * Dashboard page - main command post view.
 *
 * Responsive grid layout with three breakpoints:
 * - Phone (<640px): Single column stacked layout
 * - Tablet (640-1023px): Two-column grid
 * - Desktop (>=1024px): Full three-column layout
 */

import {
  AccountSummary,
  DailyPnlCard,
  MarketStatusBadge,
  OpenPositions,
  RecentTrades,
  HealthMini,
} from '../features/dashboard';

export function DashboardPage() {
  return (
    <div className="space-y-4 md:space-y-5 lg:space-y-6">
      {/* Top row: Account, Daily P&L, Market Status */}
      {/* Phone: Stack vertically */}
      {/* Tablet: 2 columns with Market spanning full width below */}
      {/* Desktop: 3 equal columns */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-5 lg:gap-6">
        <AccountSummary />
        <DailyPnlCard />
        {/* On tablet, market badge spans full width in its own row */}
        <div className="md:col-span-2 lg:col-span-1 h-full">
          <MarketStatusBadge />
        </div>
      </div>

      {/* Open positions - full width */}
      <OpenPositions />

      {/* Bottom row: Recent Trades and Health Status */}
      {/* Phone: Stack vertically */}
      {/* Tablet: 2 columns */}
      {/* Desktop: 2 columns */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-5 lg:gap-6">
        <RecentTrades />
        <HealthMini />
      </div>
    </div>
  );
}
