/**
 * Bottom sheet for mobile navigation overflow.
 *
 * Shows Performance, Debrief, and System navigation items
 * when the mobile nav uses the 5+More pattern.
 *
 * Features:
 * - Framer Motion slide-up animation
 * - Backdrop tap to dismiss
 * - Drag handle for visual affordance
 * - Escape key to close
 *
 * Sprint 21d — Navigation restructure (DEC-211).
 */

import { useEffect, useCallback } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { TrendingUp, GraduationCap, Activity } from 'lucide-react';
import { DURATION, EASE } from '../utils/motion';

interface MoreSheetProps {
  isOpen: boolean;
  onClose: () => void;
}

const MORE_ITEMS = [
  { to: '/performance', icon: TrendingUp, label: 'Performance' },
  { to: '/debrief', icon: GraduationCap, label: 'The Debrief' },
  { to: '/system', icon: Activity, label: 'System' },
] as const;

export function MoreSheet({ isOpen, onClose }: MoreSheetProps) {
  const location = useLocation();

  // Close on Escape key
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    },
    [isOpen, onClose]
  );

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  // Prevent body scroll when sheet is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  const backdropVariants = {
    hidden: { opacity: 0 },
    visible: { opacity: 1, transition: { duration: DURATION.fast } },
    exit: { opacity: 0, transition: { duration: DURATION.fast } },
  };

  const sheetVariants = {
    hidden: { y: '100%' },
    visible: {
      y: 0,
      transition: { type: 'spring' as const, stiffness: 300, damping: 30 },
    },
    exit: {
      y: '100%',
      transition: { duration: DURATION.normal, ease: EASE.inOut },
    },
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop overlay */}
          <motion.div
            className="fixed inset-0 bg-black/60 z-50"
            variants={backdropVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            onClick={onClose}
          />

          {/* Sheet */}
          <motion.div
            className="fixed inset-x-0 bottom-0 z-50 bg-argus-surface rounded-t-xl border-t border-argus-border"
            variants={sheetVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
          >
            {/* Drag handle */}
            <div className="flex justify-center pt-3 pb-2">
              <div className="w-10 h-1 rounded-full bg-argus-text-dim/30" />
            </div>

            {/* Navigation items */}
            <nav className="px-4 pb-6">
              {MORE_ITEMS.map((item) => {
                const isActive = location.pathname === item.to;
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    onClick={onClose}
                    className={`flex items-center gap-4 py-4 px-3 rounded-lg transition-colors ${
                      isActive
                        ? 'bg-argus-surface-2 text-argus-accent'
                        : 'text-argus-text hover:bg-argus-surface-2/50'
                    }`}
                  >
                    <item.icon className="w-5 h-5" />
                    <span className="text-base font-medium">{item.label}</span>
                  </NavLink>
                );
              })}
            </nav>

            {/* Safe area padding for iOS */}
            <div className="safe-bottom" />
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
