/**
 * Icon-only sidebar for desktop (≥1024px).
 *
 * Shows 6 navigation items, paper mode badge, status indicator, and logout.
 */

import { useEffect } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { LayoutDashboard, ScrollText, TrendingUp, BookOpen, Gauge, Activity, LogOut } from 'lucide-react';
import { useAuthStore } from '../stores/auth';
import { useLiveStore } from '../stores/live';

// Navigation items in sidebar order - keyboard shortcuts use this order (1, 2, 3, 4, 5, 6)
const NAV_ITEMS = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/trades', icon: ScrollText, label: 'Trades' },
  { to: '/performance', icon: TrendingUp, label: 'Performance' },
  { to: '/patterns', icon: BookOpen, label: 'Pattern Library' },
  { to: '/orchestrator', icon: Gauge, label: 'Orchestrator' },
  { to: '/system', icon: Activity, label: 'System' },
] as const;

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
  const navigate = useNavigate();

  // Keyboard shortcuts: 1-6 for navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if typing in an input or textarea
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
        return;
      }

      const keyNum = parseInt(e.key, 10);
      if (keyNum >= 1 && keyNum <= NAV_ITEMS.length) {
        navigate(NAV_ITEMS[keyNum - 1].to);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [navigate]);

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
      {/* Safe area spacer for PWA/iOS */}
      <div className="safe-top" />
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

      {/* Navigation - items are numbered 1-6 for keyboard shortcuts */}
      <nav className="flex-1 flex flex-col items-center py-4 space-y-2">
        {NAV_ITEMS.map((item) => (
          <NavItem
            key={item.to}
            to={item.to}
            icon={<item.icon className="w-5 h-5" />}
            label={item.label}
          />
        ))}
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
