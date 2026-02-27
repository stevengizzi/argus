/**
 * Reusable confirmation modal dialog.
 *
 * Displays a modal with title, message, and confirm/cancel buttons.
 * Supports three variants: info (blue), warning (amber), danger (red).
 *
 * Uses Framer Motion for entry/exit animations.
 */

import { AlertTriangle, RefreshCcw, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { DURATION, EASE } from '../utils/motion';

export type ModalVariant = 'info' | 'warning' | 'danger';

export interface ConfirmModalProps {
  isOpen: boolean;
  title: string;
  message: string;
  confirmText: string;
  isLoading: boolean;
  variant: ModalVariant;
  onConfirm: () => void;
  onCancel: () => void;
}

const variantStyles = {
  info: {
    iconClass: 'text-argus-accent',
    buttonClass: 'bg-argus-accent hover:bg-argus-accent/80',
    Icon: RefreshCcw,
  },
  warning: {
    iconClass: 'text-amber-500',
    buttonClass: 'bg-amber-500 hover:bg-amber-500/80',
    Icon: AlertTriangle,
  },
  danger: {
    iconClass: 'text-argus-loss',
    buttonClass: 'bg-argus-loss hover:bg-argus-loss/80',
    Icon: AlertTriangle,
  },
};

export function ConfirmModal({
  isOpen,
  title,
  message,
  confirmText,
  isLoading,
  variant,
  onConfirm,
  onCancel,
}: ConfirmModalProps) {
  const { iconClass, buttonClass, Icon } = variantStyles[variant];

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            className="fixed inset-0 bg-black/60 z-50"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: DURATION.fast }}
            onClick={onCancel}
          />

          {/* Modal */}
          <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.div
              className="bg-argus-surface border border-argus-border rounded-lg w-full max-w-md shadow-xl"
              initial={{ scale: 0.95, y: 10 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.95, y: 10 }}
              transition={{ duration: DURATION.normal, ease: EASE.out }}
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div className="flex items-center justify-between p-4 border-b border-argus-border">
                <div className={`flex items-center gap-2 ${iconClass}`}>
                  <Icon className="w-5 h-5" />
                  <h2 className="text-lg font-semibold">{title}</h2>
                </div>
                <button
                  onClick={onCancel}
                  className="p-1 rounded hover:bg-argus-surface-2 transition-colors"
                >
                  <X className="w-5 h-5 text-argus-text-dim" />
                </button>
              </div>

              {/* Content */}
              <div className="p-4">
                <p className="text-argus-text">{message}</p>
              </div>

              {/* Actions */}
              <div className="flex justify-end gap-3 p-4 border-t border-argus-border">
                <button
                  onClick={onCancel}
                  disabled={isLoading}
                  className="px-4 py-2 text-sm rounded-md border border-argus-border bg-argus-surface hover:bg-argus-surface-2 transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={onConfirm}
                  disabled={isLoading}
                  className={`px-4 py-2 text-sm rounded-md text-white transition-colors disabled:opacity-50 ${buttonClass}`}
                >
                  {isLoading ? 'Processing...' : confirmText}
                </button>
              </div>
            </motion.div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
