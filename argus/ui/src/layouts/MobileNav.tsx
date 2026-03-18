/**
 * Bottom navigation bar for mobile and tablet (<1024px).
 *
 * Shows 5 primary tabs + More bottom sheet.
 * Primary: Dashboard, Trades, Orchestrator, Patterns, More
 * More sheet: Performance, Debrief, System
 *
 * Sprint 21d — Navigation restructure (DEC-211, DEC-216).
 */

import { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { LayoutDashboard, ScrollText, Gauge, BookOpen, MoreHorizontal } from 'lucide-react';
import { MoreSheet } from './MoreSheet';

// Routes that live in the More sheet
const MORE_ROUTES = ['/performance', '/observatory', '/debrief', '/system'];

// Primary navigation items (5 tabs)
const NAV_ITEMS: Array<{
  to: string;
  icon: typeof LayoutDashboard;
  label: string;
}> = [
  { to: '/', icon: LayoutDashboard, label: 'Dash' },
  { to: '/trades', icon: ScrollText, label: 'Trades' },
  { to: '/orchestrator', icon: Gauge, label: 'Orch' },
  { to: '/patterns', icon: BookOpen, label: 'Patterns' },
];

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
        `flex flex-col items-center justify-center flex-1 py-2 transition-all duration-150 active:scale-95 ${
          isActive ? 'text-argus-accent' : 'text-argus-text-dim'
        }`
      }
    >
      {({ isActive }) => (
        <>
          <div className="relative">{icon}</div>
          <span className="text-[8px] mt-1 font-medium">{label}</span>
          {/* Active indicator dot */}
          {isActive && (
            <span className="w-1 h-1 mt-0.5 rounded-full bg-argus-accent" />
          )}
        </>
      )}
    </NavLink>
  );
}

interface MoreTabProps {
  isActive: boolean;
  onClick: () => void;
}

function MoreTab({ isActive, onClick }: MoreTabProps) {
  return (
    <button
      onClick={onClick}
      className={`flex flex-col items-center justify-center flex-1 py-2 transition-all duration-150 active:scale-95 ${
        isActive ? 'text-argus-accent' : 'text-argus-text-dim'
      }`}
    >
      <div className="relative">
        <MoreHorizontal className="w-5 h-5" />
      </div>
      <span className="text-[8px] mt-1 font-medium">More</span>
      {/* Active indicator dot when on a More route */}
      {isActive && (
        <span className="w-1 h-1 mt-0.5 rounded-full bg-argus-accent" />
      )}
    </button>
  );
}

export function MobileNav() {
  const [isMoreOpen, setIsMoreOpen] = useState(false);
  const location = useLocation();

  // More tab is active if current route is in MORE_ROUTES
  const isMoreActive = MORE_ROUTES.includes(location.pathname);

  return (
    <>
      <nav className="min-[1024px]:hidden fixed bottom-0 left-0 right-0 z-40 bg-argus-surface border-t border-argus-border pb-3">
        <div className="flex h-16">
          {NAV_ITEMS.map((item) => (
            <NavItem
              key={item.to}
              to={item.to}
              icon={<item.icon className="w-5 h-5" />}
              label={item.label}
            />
          ))}
          <MoreTab
            isActive={isMoreActive}
            onClick={() => setIsMoreOpen(true)}
          />
        </div>
      </nav>

      <MoreSheet
        isOpen={isMoreOpen}
        onClose={() => setIsMoreOpen(false)}
      />
    </>
  );
}
