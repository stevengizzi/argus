/**
 * AI Copilot slide-in panel.
 *
 * Global chat panel that persists across pages. Uses own animation and lifecycle
 * separate from SlideInPanel (different z-index layer, maintains chat state).
 *
 * Sprint 21d — Copilot shell (DEC-212).
 * Sprint 22, Session 4a — Live chat integration.
 */

import { useEffect, useCallback, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Bot, AlertCircle, WifiOff } from 'lucide-react';
import { useCopilotUIStore } from '../../stores/copilotUI';
import { useMediaQuery } from '../../hooks/useMediaQuery';
import { ChatMessage } from './ChatMessage';
import { StreamingMessage } from './StreamingMessage';
import { ChatInput } from './ChatInput';
import {
  getCopilotWebSocket,
  checkAIStatus,
  loadTodayConversation,
} from './api';
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

// Map pathname to API page context key
const PAGE_KEYS: Record<string, string> = {
  '/': 'Dashboard',
  '/trades': 'Trades',
  '/performance': 'Performance',
  '/orchestrator': 'Orchestrator',
  '/patterns': 'PatternLibrary',
  '/debrief': 'Debrief',
  '/system': 'System',
};

/**
 * Connection status indicator.
 */
function ConnectionStatus() {
  const wsConnected = useCopilotUIStore((state) => state.wsConnected);
  const aiEnabled = useCopilotUIStore((state) => state.aiEnabled);
  const error = useCopilotUIStore((state) => state.error);

  if (error) {
    return (
      <span className="flex items-center gap-1 text-xs text-red-400">
        <span className="w-2 h-2 rounded-full bg-red-400" />
        Error
      </span>
    );
  }

  if (!aiEnabled) {
    return (
      <span className="flex items-center gap-1 text-xs text-argus-text-dim">
        <WifiOff className="w-3 h-3" />
        Offline
      </span>
    );
  }

  if (wsConnected) {
    return (
      <span className="flex items-center gap-1 text-xs text-green-400">
        <span className="w-2 h-2 rounded-full bg-green-400" />
        Connected
      </span>
    );
  }

  return (
    <span className="flex items-center gap-1 text-xs text-argus-text-dim">
      <span className="w-2 h-2 rounded-full bg-gray-400 animate-pulse" />
      Connecting...
    </span>
  );
}

/**
 * Error banner component.
 */
function ErrorBanner() {
  const error = useCopilotUIStore((state) => state.error);
  const clearError = useCopilotUIStore((state) => state.clearError);

  if (!error) return null;

  return (
    <div className="flex items-center gap-2 px-4 py-2 bg-red-500/10 border-b border-red-500/20 text-sm">
      <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
      <span className="flex-1 text-red-400">{error}</span>
      <button
        onClick={clearError}
        className="p-1 hover:bg-red-500/20 rounded transition-colors"
        aria-label="Dismiss error"
      >
        <X className="w-4 h-4 text-red-400" />
      </button>
    </div>
  );
}

/**
 * Loading skeleton for conversation.
 */
function LoadingSkeleton() {
  return (
    <div className="flex flex-col gap-4 p-4 animate-pulse">
      {/* User message skeleton */}
      <div className="flex justify-end">
        <div className="w-2/3 h-12 bg-argus-surface-2 rounded-2xl rounded-br-md" />
      </div>
      {/* Assistant message skeleton */}
      <div className="flex justify-start">
        <div className="w-3/4 h-20 bg-argus-surface-2 rounded-2xl rounded-bl-md" />
      </div>
      {/* Another pair */}
      <div className="flex justify-end">
        <div className="w-1/2 h-10 bg-argus-surface-2 rounded-2xl rounded-br-md" />
      </div>
      <div className="flex justify-start">
        <div className="w-2/3 h-16 bg-argus-surface-2 rounded-2xl rounded-bl-md" />
      </div>
    </div>
  );
}

/**
 * Empty state when no conversation exists.
 */
function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full px-6 py-8 text-center">
      <div className="p-4 rounded-full bg-argus-accent/10 mb-4">
        <Bot className="w-10 h-10 text-argus-accent" />
      </div>
      <h3 className="text-lg font-medium text-argus-text mb-2">
        Start a conversation
      </h3>
      <p className="text-sm text-argus-text-dim max-w-xs">
        Ask questions about your trading data, request analysis, or get insights
        about your strategies.
      </p>
    </div>
  );
}

/**
 * AI Not Configured state.
 */
function AINotConfiguredState() {
  return (
    <div className="flex flex-col items-center justify-center h-full px-6 py-8 text-center">
      <div className="p-4 rounded-full bg-argus-surface-2 mb-4">
        <WifiOff className="w-10 h-10 text-argus-text-dim" />
      </div>
      <h3 className="text-lg font-medium text-argus-text mb-2">
        AI Not Configured
      </h3>
      <p className="text-sm text-argus-text-dim max-w-xs">
        The AI Copilot requires an API key to be configured. Check your system
        settings to enable AI features.
      </p>
    </div>
  );
}

/**
 * Message list container.
 */
function MessageList() {
  const messages = useCopilotUIStore((state) => state.messages);
  const isStreaming = useCopilotUIStore((state) => state.isStreaming);
  const streamingContent = useCopilotUIStore((state) => state.streamingContent);
  const isLoading = useCopilotUIStore((state) => state.isLoading);
  const aiEnabled = useCopilotUIStore((state) => state.aiEnabled);

  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const isNearBottomRef = useRef(true);

  // Track if user is near the bottom of the scroll container
  const handleScroll = useCallback(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const threshold = 50; // pixels from bottom
    const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
    isNearBottomRef.current = distanceFromBottom <= threshold;
  }, []);

  // Auto-scroll to bottom on new messages (always scroll for new messages)
  useEffect(() => {
    const container = scrollContainerRef.current;
    if (container) {
      container.scrollTop = container.scrollHeight;
      isNearBottomRef.current = true;
    }
  }, [messages]);

  // Auto-scroll during streaming only if user is near the bottom
  useEffect(() => {
    const container = scrollContainerRef.current;
    if (container && isStreaming && isNearBottomRef.current) {
      container.scrollTop = container.scrollHeight;
    }
  }, [streamingContent, isStreaming]);

  if (!aiEnabled) {
    return <AINotConfiguredState />;
  }

  if (isLoading) {
    return <LoadingSkeleton />;
  }

  if (messages.length === 0 && !isStreaming) {
    return <EmptyState />;
  }

  return (
    <div
      ref={scrollContainerRef}
      onScroll={handleScroll}
      className="flex-1 overflow-y-auto px-4 py-4 space-y-4"
    >
      {/* Render messages oldest-first */}
      {messages.map((message) => (
        <ChatMessage key={message.id} message={message} />
      ))}

      {/* Streaming message */}
      <StreamingMessage />
    </div>
  );
}

export function CopilotPanel() {
  const { isOpen, close } = useCopilotUIStore();
  const aiEnabled = useCopilotUIStore((state) => state.aiEnabled);
  const location = useLocation();
  const isDesktop = useMediaQuery('(min-width: 1024px)');
  const initializedRef = useRef(false);

  const pageName = PAGE_LABELS[location.pathname] ?? 'Unknown';
  const pageKey = PAGE_KEYS[location.pathname] ?? 'Dashboard';

  // Initialize AI status and WebSocket on panel open
  useEffect(() => {
    if (isOpen && !initializedRef.current) {
      initializedRef.current = true;

      // Check AI status first
      checkAIStatus().then((enabled) => {
        if (enabled) {
          // Connect WebSocket
          const ws = getCopilotWebSocket();
          ws.connect();

          // Load today's conversation
          loadTodayConversation();
        }
      });
    }
  }, [isOpen]);

  // Reconnect WebSocket if disconnected while panel is open
  useEffect(() => {
    if (isOpen && aiEnabled) {
      const ws = getCopilotWebSocket();
      if (ws.getState() === 'disconnected') {
        ws.connect();
      }
    }
  }, [isOpen, aiEnabled]);

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
                  <div className="flex items-center gap-2">
                    <h2 className="text-base font-semibold text-argus-text">ARGUS Copilot</h2>
                    <ConnectionStatus />
                  </div>
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

            {/* Error banner */}
            <ErrorBanner />

            {/* Message list */}
            <div className="flex-1 overflow-hidden flex flex-col">
              <MessageList />
            </div>

            {/* Chat input */}
            <div className="flex-shrink-0 border-t border-argus-border px-4 py-3">
              <ChatInput page={pageKey} pageContext={{}} />
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
