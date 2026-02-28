/**
 * AI Copilot slide-in panel.
 *
 * Global chat panel that persists across pages. Uses own animation and lifecycle
 * separate from SlideInPanel (different z-index layer, maintains chat state).
 *
 * Sprint 21d — Copilot shell (DEC-212). Content activates Sprint 22.
 */

import { useEffect, useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Bot, Send } from 'lucide-react';
import { useCopilotUIStore } from '../../stores/copilotUI';
import { useMediaQuery } from '../../hooks/useMediaQuery';
import { CopilotPlaceholder } from './CopilotPlaceholder';
import { DURATION, EASE } from '../../utils/motion';

// Map pathname to readable page name
const PAGE_LABELS: Record<string, string> = {
  '/': 'Dashboard',
  '/trades': 'Trade Log',
  '/performance': 'Performance',
  '/orchestrator': 'Orchestrator',
  '/patterns': 'Pattern Library',
  '/debrief': 'The Debrief',
  '/system': 'System',
};

export function CopilotPanel() {
  const { isOpen, close } = useCopilotUIStore();
  const location = useLocation();
  const isDesktop = useMediaQuery('(min-width: 1024px)');

  const pageName = PAGE_LABELS[location.pathname] ?? 'Unknown';

  // Close on Escape key — check isOpen first to not conflict with other panels
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        e.stopPropagation();
        close();
      }
    },
    [isOpen, close]
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

  // Animation variants
  // Damping 35 is critically damped for stiffness 300 — no overshoot/wiggle
  const panelVariants = {
    hidden: isDesktop ? { x: '100%' } : { y: '100%' },
    visible: isDesktop
      ? { x: 0, transition: { type: 'spring' as const, stiffness: 300, damping: 35 } }
      : { y: 0, transition: { type: 'spring' as const, stiffness: 300, damping: 35 } },
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
            className="fixed inset-0 bg-black/40 z-40"
            variants={backdropVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            onClick={close}
          />

          {/* Panel */}
          <motion.div
            className={`fixed z-50 bg-argus-surface flex flex-col ${
              isDesktop
                ? 'right-0 top-0 h-full min-w-[400px] max-w-[560px] border-l border-argus-border'
                : 'inset-x-0 bottom-0 h-[90vh] rounded-t-xl border-t border-argus-border'
            }`}
            style={isDesktop ? { width: '35%' } : undefined}
            variants={panelVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
          >
            {/* Header */}
            <div className="flex-shrink-0 border-b border-argus-border px-4 py-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Bot className="w-5 h-5 text-argus-accent" />
                <div>
                  <h2 className="text-base font-semibold text-argus-text">AI Copilot</h2>
                  <span className="text-xs text-argus-text-dim">Page: {pageName}</span>
                </div>
              </div>
              <button
                onClick={close}
                className="p-2 rounded-md hover:bg-argus-surface-2 transition-colors min-w-[44px] min-h-[44px] flex items-center justify-center"
                aria-label="Close copilot"
              >
                <X className="w-5 h-5 text-argus-text-dim" />
              </button>
            </div>

            {/* Scrollable content area */}
            <div className="flex-1 overflow-y-auto">
              <CopilotPlaceholder />
            </div>

            {/* Footer with disabled input */}
            <div className="flex-shrink-0 border-t border-argus-border px-4 py-3">
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  disabled
                  placeholder="Activating Sprint 22..."
                  className="flex-1 bg-argus-surface-2/50 border border-argus-border rounded-lg px-3 py-2 text-sm text-argus-text-dim placeholder:text-argus-text-dim/60 cursor-not-allowed"
                />
                <button
                  disabled
                  className="p-2 rounded-lg bg-argus-surface-2/50 text-argus-text-dim cursor-not-allowed"
                  aria-label="Send message"
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
