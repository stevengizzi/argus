/**
 * Shared slide-in panel component.
 *
 * Provides consistent slide-in behavior across the app:
 * - Desktop (≥1024px): Slides in from right, configurable width
 * - Mobile (<1024px): Slides up from bottom, 90vh height
 *
 * Features: backdrop overlay, escape to close, body scroll lock.
 */

import { useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import { useMediaQuery } from '../hooks/useMediaQuery';
import { DURATION, EASE } from '../utils/motion';

interface SlideInPanelProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  width?: string; // Desktop width, default "40%"
}

export function SlideInPanel({
  isOpen,
  onClose,
  title,
  subtitle,
  children,
  width = '40%',
}: SlideInPanelProps) {
  const isDesktop = useMediaQuery('(min-width: 1024px)');

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

  // Prevent body scroll when panel is open
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

  // Desktop: slide from right
  // Mobile: slide from bottom
  const panelVariants = {
    hidden: isDesktop ? { x: '100%' } : { y: '100%' },
    visible: isDesktop
      ? { x: 0, transition: { type: 'spring' as const, stiffness: 300, damping: 30 } }
      : { y: 0, transition: { type: 'spring' as const, stiffness: 300, damping: 30 } },
    exit: isDesktop
      ? { x: '100%', transition: { duration: DURATION.normal, ease: EASE.inOut } }
      : { y: '100%', transition: { duration: DURATION.normal, ease: EASE.inOut } },
  };

  const backdropVariants = {
    hidden: { opacity: 0 },
    visible: { opacity: 1, transition: { duration: DURATION.fast } },
    exit: { opacity: 0, transition: { duration: DURATION.fast } },
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop overlay */}
          <motion.div
            className="fixed inset-0 bg-black/60 z-40"
            variants={backdropVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            onClick={onClose}
          />

          {/* Panel */}
          <motion.div
            className={`fixed z-50 bg-argus-surface border-argus-border overflow-y-auto ${
              isDesktop
                ? 'right-0 top-0 h-full min-w-[400px] max-w-[600px] border-l'
                : 'inset-x-0 bottom-0 h-[90vh] rounded-t-xl border-t'
            }`}
            style={isDesktop ? { width } : undefined}
            variants={panelVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
          >
            {/* Header */}
            <div className="sticky top-0 z-10 bg-argus-surface border-b border-argus-border px-4 py-3 flex items-center justify-between">
              <div className="flex flex-col">
                <span className="text-xl font-semibold text-argus-text">{title}</span>
                {subtitle && (
                  <span className="text-sm text-argus-text-dim">{subtitle}</span>
                )}
              </div>
              <button
                onClick={onClose}
                className="p-2 rounded-md hover:bg-argus-surface-2 transition-colors min-w-[44px] min-h-[44px] flex items-center justify-center"
                aria-label="Close panel"
              >
                <X className="w-5 h-5 text-argus-text-dim" />
              </button>
            </div>

            {/* Content */}
            <div className="p-4">
              {children}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
