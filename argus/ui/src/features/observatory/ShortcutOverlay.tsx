/**
 * Keyboard shortcut reference overlay for the Observatory page.
 *
 * Toggled with the ? key. Shows all available shortcuts grouped by category.
 * Dismissed with Escape, ? again, or clicking the backdrop.
 */

import { AnimatePresence, motion } from 'framer-motion';

const SHORTCUT_GROUPS = [
  {
    title: 'Views',
    shortcuts: [
      { keys: ['1'], description: 'Funnel view' },
      { keys: ['2'], description: 'Matrix view' },
      { keys: ['3'], description: 'Timeline view' },
      { keys: ['4'], description: 'Radar view' },
    ],
  },
  {
    title: 'Navigation',
    shortcuts: [
      { keys: ['['], description: 'Previous tier' },
      { keys: [']'], description: 'Next tier' },
      { keys: ['Tab'], description: 'Next symbol' },
      { keys: ['Shift', 'Tab'], description: 'Previous symbol' },
    ],
  },
  {
    title: 'Selection',
    shortcuts: [
      { keys: ['Enter'], description: 'Open detail panel' },
      { keys: ['Esc'], description: 'Close panel / deselect' },
      { keys: ['/'], description: 'Symbol search' },
    ],
  },
  {
    title: 'Camera',
    shortcuts: [
      { keys: ['R'], description: 'Reset camera' },
      { keys: ['F'], description: 'Fit to view' },
    ],
  },
];

interface ShortcutOverlayProps {
  isOpen: boolean;
  onClose: () => void;
}

export function ShortcutOverlay({ isOpen, onClose }: ShortcutOverlayProps) {
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            key="shortcut-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="fixed inset-0 bg-black/60 z-50"
            onClick={onClose}
            data-testid="shortcut-overlay-backdrop"
          />
          {/* Modal */}
          <motion.div
            key="shortcut-modal"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.15 }}
            className="fixed inset-0 z-50 flex items-center justify-center pointer-events-none"
          >
            <div
              className="bg-argus-surface border border-argus-border rounded-lg shadow-2xl p-6 max-w-md w-full mx-4 pointer-events-auto"
              data-testid="shortcut-overlay"
            >
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-semibold text-argus-text">Keyboard Shortcuts</h2>
                <button
                  onClick={onClose}
                  className="text-argus-text-dim hover:text-argus-text text-xs"
                >
                  ESC
                </button>
              </div>

              <div className="space-y-4">
                {SHORTCUT_GROUPS.map((group) => (
                  <div key={group.title}>
                    <h3 className="text-[10px] font-semibold text-argus-text-dim uppercase tracking-wider mb-2">
                      {group.title}
                    </h3>
                    <div className="space-y-1.5">
                      {group.shortcuts.map((shortcut) => (
                        <div
                          key={shortcut.description}
                          className="flex items-center justify-between"
                        >
                          <span className="text-xs text-argus-text-dim">
                            {shortcut.description}
                          </span>
                          <div className="flex items-center gap-1">
                            {shortcut.keys.map((key) => (
                              <kbd
                                key={key}
                                className="px-1.5 py-0.5 text-[10px] font-mono bg-argus-surface-2 border border-argus-border rounded text-argus-text"
                              >
                                {key}
                              </kbd>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-4 pt-3 border-t border-argus-border">
                <p className="text-[10px] text-argus-text-dim text-center">
                  Press <kbd className="px-1 py-0.5 text-[10px] font-mono bg-argus-surface-2 border border-argus-border rounded">?</kbd> to toggle
                </p>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
