/**
 * Icon-only sidebar for desktop (≥1024px).
 *
 * Shows 4 navigation items, paper mode badge, status indicator, and logout.
 */

import { NavLink } from 'react-router-dom';
import { LayoutDashboard, ScrollText, TrendingUp, Activity, LogOut } from 'lucide-react';
import { useAuthStore } from '../stores/auth';
import { useLiveStore } from '../stores/live';

interface NavItemProps {
  to: string;
  icon: React.ReactNode;
  label: string;
}

function NavItem({ to, icon, label }: NavItemProps) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `group relative flex items-center justify-center w-12 h-12 rounded-lg transition-colors ${
          isActive
            ? 'bg-argus-surface-2 text-argus-accent'
            : 'text-argus-text-dim hover:text-argus-text hover:bg-argus-surface-2/50'
        }`
      }
    >
      {({ isActive }) => (
        <>
          {/* Active indicator bar */}
          {isActive && (
            <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-6 bg-argus-accent rounded-r" />
          )}
          {/* Icon with hover scale */}
          <span className="transition-transform duration-150 group-hover:scale-105">
            {icon}
          </span>
          {/* Tooltip with 200ms delay */}
          <span className="absolute left-full ml-2 px-2 py-1 bg-argus-surface-2 text-argus-text text-xs rounded opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-opacity duration-150 delay-200 whitespace-nowrap z-50">
            {label}
          </span>
        </>
      )}
    </NavLink>
  );
}

interface SidebarProps {
  paperMode?: boolean;
}

export function Sidebar({ paperMode = false }: SidebarProps) {
  const logout = useAuthStore((state) => state.logout);
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
    <aside className="hidden min-[1024px]:flex fixed left-0 top-0 flex-col w-16 h-dvh bg-argus-surface border-r border-argus-border z-40">
      {/* Logo */}
      <div className="flex items-center justify-center h-16 border-b border-argus-border">
        <img
          src="/argus-logo-sidebar.png"
          srcSet="/argus-logo-sidebar.png 1x, /argus-logo-sidebar@2x.png 2x"
          alt="ARGUS"
          width={32}
          height={32}
        />
      </div>

      {/* Navigation */}
      <nav className="flex-1 flex flex-col items-center py-4 space-y-2">
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
        />
      </nav>

      {/* Bottom section */}
      <div className="flex flex-col items-center py-4 space-y-3 border-t border-argus-border">
        {/* Paper mode badge */}
        {paperMode && (
          <span className="text-[10px] font-semibold text-argus-warning tracking-wider">
            PAPER
          </span>
        )}

        {/* Status indicator */}
        <div className="group relative flex items-center justify-center">
          <div className={`w-2 h-2 rounded-full ${getStatusColor()} ${status === 'connected' ? 'pulse' : ''}`} />
          <span className="absolute left-full ml-2 px-2 py-1 bg-argus-surface-2 text-argus-text text-xs rounded opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-opacity duration-150 delay-200 whitespace-nowrap z-50">
            {status === 'connected' ? 'Connected' : status === 'connecting' ? 'Connecting...' : 'Disconnected'}
          </span>
        </div>

        {/* Logout */}
        <button
          onClick={logout}
          className="group relative flex items-center justify-center w-12 h-12 rounded-lg text-argus-text-dim hover:text-argus-loss hover:bg-argus-surface-2/50 transition-colors"
        >
          <span className="transition-transform duration-150 group-hover:scale-105">
            <LogOut className="w-5 h-5" />
          </span>
          <span className="absolute left-full ml-2 px-2 py-1 bg-argus-surface-2 text-argus-text text-xs rounded opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-opacity duration-150 delay-200 whitespace-nowrap z-50">
            Sign Out
          </span>
        </button>
      </div>
    </aside>
  );
}
