/**
 * Floating action button to toggle the AI Copilot panel.
 *
 * Desktop: Fixed bottom-right, 24px from edges.
 * Mobile: Fixed bottom-right, stacked above WatchlistSidebar FAB.
 *   - WatchlistSidebar FAB: bottom-20 (80px)
 *   - CopilotButton: bottom-36 (144px) = 80px + 48px button + 16px gap
 *
 * Hides when panel is open (panel has its own close button).
 *
 * Sprint 21d — Copilot shell (DEC-212, DEC-217).
 */

import { useRef, useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MessageCircle } from 'lucide-react';
import { useCopilotUIStore } from '../../stores/copilotUI';

export function CopilotButton() {
  const { isOpen, open } = useCopilotUIStore();
  const [hasAnimated, setHasAnimated] = useState(false);
  const mountedRef = useRef(false);

  // Track first mount to trigger entrance animation only once
  useEffect(() => {
    if (!mountedRef.current) {
      mountedRef.current = true;
      // Small delay to ensure smooth entrance after page load
      const timer = setTimeout(() => setHasAnimated(true), 100);
      return () => clearTimeout(timer);
    }
  }, []);

  // Don't render button when panel is open
  if (isOpen) {
    return null;
  }

  return (
    <AnimatePresence>
      <motion.button
        onClick={open}
        className="
          fixed z-30
          min-[1024px]:bottom-6 min-[1024px]:right-6
          bottom-36 right-4
          w-12 h-12
          bg-argus-accent text-white
          rounded-full
          flex items-center justify-center
          shadow-lg
          hover:scale-105
          active:scale-95
          transition-transform duration-150
        "
        initial={!hasAnimated ? { scale: 0, opacity: 0 } : false}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0, opacity: 0 }}
        transition={{ type: 'spring', stiffness: 400, damping: 25 }}
        aria-label="Open AI Copilot"
      >
        <MessageCircle className="w-5 h-5" />
      </motion.button>
    </AnimatePresence>
  );
}
