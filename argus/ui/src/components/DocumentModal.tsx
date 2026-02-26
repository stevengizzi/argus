/**
 * Document Modal for reading strategy documentation.
 *
 * Full-screen (mobile) or large centered modal (desktop) for reading
 * long-form documentation. Scrollable content area with sticky header.
 */

import { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import { MarkdownRenderer } from './MarkdownRenderer';
import type { StrategyDocument } from '../api/types';

interface DocumentModalProps {
  document: StrategyDocument | null;
  isOpen: boolean;
  onClose: () => void;
}

/**
 * Format ISO date string to readable format (MMM DD, YYYY).
 */
function formatDate(isoDate: string): string {
  const date = new Date(isoDate);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

export function DocumentModal({ document: doc, isOpen, onClose }: DocumentModalProps) {
  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        e.preventDefault();
        e.stopPropagation();
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown, { capture: true });
    return () => window.removeEventListener('keydown', handleKeyDown, { capture: true });
  }, [isOpen, onClose]);

  // Prevent body scroll when modal is open
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

  return (
    <AnimatePresence>
      {isOpen && doc && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 bg-black/60 z-50"
            onClick={onClose}
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-4 md:inset-[5%] lg:inset-[10%] bg-argus-surface border border-argus-border rounded-lg z-50 flex flex-col overflow-hidden"
          >
            {/* Header - sticky */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-argus-border bg-argus-surface flex-shrink-0">
              <div>
                <h2 className="text-lg font-semibold text-argus-text">{doc.title}</h2>
                <p className="text-xs text-argus-text-dim">
                  {doc.word_count.toLocaleString()} words · {doc.reading_time_min} min read · Updated {formatDate(doc.last_modified)}
                </p>
              </div>
              <button
                onClick={onClose}
                className="p-2 rounded-lg text-argus-text-dim hover:text-argus-text hover:bg-argus-surface-2 transition-colors"
                aria-label="Close"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Content - scrollable */}
            <div className="flex-1 overflow-y-auto p-4 md:p-6">
              <MarkdownRenderer content={doc.content} />
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
