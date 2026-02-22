/**
 * Bottom navigation bar for mobile and tablet (<1024px).
 *
 * Shows 4 tab items with icons and labels, with system status dot overlay.
 */

import { NavLink } from 'react-router-dom';
import { LayoutDashboard, ScrollText, TrendingUp, Activity } from 'lucide-react';
import { useLiveStore } from '../stores/live';

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
        `flex flex-col items-center justify-center flex-1 py-2 transition-colors ${
          isActive ? 'text-argus-accent' : 'text-argus-text-dim'
        }`
      }
    >
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
      <span className="text-[10px] mt-1 font-medium">{label}</span>
    </NavLink>
  );
}

export function MobileNav() {
  return (
    <nav className="min-[1024px]:hidden fixed bottom-0 left-0 right-0 z-50 bg-argus-surface border-t border-argus-border pb-[env(safe-area-inset-bottom)]">
      <div className="flex h-16">
        <NavItem
          to="/"
          icon={<LayoutDashboard className="w-5 h-5" />}
          label="Dashboard"
        />
        <NavItem
          to="/trades"
          icon={<ScrollText className="w-5 h-5" />}
          label="Trades"
        />
        <NavItem
          to="/performance"
          icon={<TrendingUp className="w-5 h-5" />}
          label="Performance"
        />
        <NavItem
          to="/system"
          icon={<Activity className="w-5 h-5" />}
          label="System"
          showStatusDot
        />
      </div>
    </nav>
  );
}
