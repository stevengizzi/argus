/**
 * Bottom navigation bar for mobile and tablet (<1024px).
 *
 * Shows 6 tab items with icons and labels, with system status dot overlay.
 */

import { NavLink } from 'react-router-dom';
import { LayoutDashboard, ScrollText, TrendingUp, BookOpen, Gauge, Activity } from 'lucide-react';
import { useLiveStore } from '../stores/live';

// Navigation items in order - must match Sidebar.tsx for consistent keyboard shortcuts (1-6)
const NAV_ITEMS: Array<{
  to: string;
  icon: typeof LayoutDashboard;
  label: string;
  showStatusDot?: boolean;
}> = [
  { to: '/', icon: LayoutDashboard, label: 'Dash' },
  { to: '/trades', icon: ScrollText, label: 'Trades' },
  { to: '/performance', icon: TrendingUp, label: 'Perf' },
  { to: '/patterns', icon: BookOpen, label: 'Patterns' },
  { to: '/orchestrator', icon: Gauge, label: 'Orch' },
  { to: '/system', icon: Activity, label: 'System', showStatusDot: true },
];

interface NavItemProps {
  to: string;
  icon: React.ReactNode;
  label: string;
  showStatusDot?: boolean;
}

function NavItem({ to, icon, label, showStatusDot }: NavItemProps) {
  const status = useLiveStore((state) => state.status);

  const getStatusColor = () => {
    switch (status) {
      case 'connected':
        return 'bg-argus-profit';
      case 'connecting':
        return 'bg-argus-warning';
      case 'error':
        return 'bg-argus-loss';
      default:
        return 'bg-argus-loss';
    }
  };

  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `flex flex-col items-center justify-center flex-1 py-2 transition-all duration-150 active:scale-95 ${
          isActive ? 'text-argus-accent' : 'text-argus-text-dim'
        }`
      }
    >
      {({ isActive }) => (
        <>
          <div className="relative">
            {icon}
            {/* Status dot overlay for System tab */}
            {showStatusDot && (
              <div
                className={`absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full ${getStatusColor()} ${
                  status === 'connected' ? 'pulse' : ''
                }`}
              />
            )}
          </div>
          <span className="text-[9px] mt-1 font-medium">{label}</span>
          {/* Active indicator dot */}
          {isActive && (
            <span className="w-1 h-1 mt-0.5 rounded-full bg-argus-accent" />
          )}
        </>
      )}
    </NavLink>
  );
}

export function MobileNav() {
  return (
    <nav className="min-[1024px]:hidden fixed bottom-0 left-0 right-0 z-50 bg-argus-surface border-t border-argus-border pb-3">
      <div className="flex h-16">
        {NAV_ITEMS.map((item) => (
          <NavItem
            key={item.to}
            to={item.to}
            icon={<item.icon className="w-5 h-5" />}
            label={item.label}
            showStatusDot={item.showStatusDot}
          />
        ))}
      </div>
    </nav>
  );
}
