/**
 * Chat input component for the AI Copilot.
 *
 * Features:
 * - Auto-growing textarea (max 5 lines, then scrolls)
 * - Send on Enter, Shift+Enter for newline
 * - Cancel button when streaming
 * - Disabled state when AI not configured
 * - Max message length: 10,000 characters
 *
 * Sprint 22, Session 4a.
 */

import { useState, useRef, useCallback, useEffect, memo, type KeyboardEvent, type ChangeEvent } from 'react';
import { Send, X } from 'lucide-react';
import { useCopilotUIStore } from '../../stores/copilotUI';
import { getCopilotWebSocket } from './api';

const MAX_MESSAGE_LENGTH = 10000;
const MAX_LINES = 5;
const LINE_HEIGHT = 20; // Approximate line height in pixels

interface ChatInputProps {
  page: string;
  pageContext: Record<string, unknown>;
}

function ChatInputComponent({ page, pageContext }: ChatInputProps) {
  const [value, setValue] = useState('');
  const [isTruncated, setIsTruncated] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const isOpen = useCopilotUIStore((state) => state.isOpen);
  const isStreaming = useCopilotUIStore((state) => state.isStreaming);
  const aiEnabled = useCopilotUIStore((state) => state.aiEnabled);
  const wsConnected = useCopilotUIStore((state) => state.wsConnected);

  const isDisabled = !aiEnabled || (!wsConnected && !isStreaming);

  // Auto-focus when panel opens
  // ChatInput only mounts when panel is open (inside AnimatePresence), so focus on mount
  useEffect(() => {
    if (isOpen && !isDisabled) {
      // Small delay to ensure panel animation has started and element is visible
      requestAnimationFrame(() => {
        textareaRef.current?.focus();
      });
    }
  }, [isOpen, isDisabled]);

  // Auto-resize textarea
  const adjustHeight = useCallback(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    // Reset height to auto to get the correct scrollHeight
    textarea.style.height = 'auto';

    // Calculate max height (5 lines)
    const maxHeight = LINE_HEIGHT * MAX_LINES;

    // Set new height, capped at max
    const newHeight = Math.min(textarea.scrollHeight, maxHeight);
    textarea.style.height = `${newHeight}px`;
  }, []);

  // Adjust height when value changes
  useEffect(() => {
    adjustHeight();
  }, [value, adjustHeight]);

  const handleChange = useCallback((e: ChangeEvent<HTMLTextAreaElement>) => {
    let newValue = e.target.value;

    // Truncate if over max length
    if (newValue.length > MAX_MESSAGE_LENGTH) {
      newValue = newValue.slice(0, MAX_MESSAGE_LENGTH);
      setIsTruncated(true);
      setTimeout(() => setIsTruncated(false), 3000);
    }

    setValue(newValue);
  }, []);

  const handleSend = useCallback(() => {
    const trimmedValue = value.trim();
    if (!trimmedValue || isDisabled || isStreaming) return;

    // Send message via WebSocket
    const ws = getCopilotWebSocket();
    ws.sendMessage(trimmedValue, page, pageContext);

    // Clear input
    setValue('');

    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [value, isDisabled, isStreaming, page, pageContext]);

  const handleCancel = useCallback(() => {
    const ws = getCopilotWebSocket();
    ws.cancelStream();
  }, []);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      // Enter without Shift sends the message
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (!isStreaming) {
          handleSend();
        }
      }
    },
    [handleSend, isStreaming]
  );

  // Placeholder text based on state
  let placeholder = 'Message ARGUS Copilot...';
  if (!aiEnabled) {
    placeholder = 'AI not configured';
  } else if (!wsConnected && !isStreaming) {
    placeholder = 'Connecting...';
  }

  return (
    <div className="flex flex-col gap-1">
      {/* Truncation notice */}
      {isTruncated && (
        <div className="text-xs text-yellow-400 px-1">
          Message truncated to {MAX_MESSAGE_LENGTH.toLocaleString()} characters
        </div>
      )}

      <div className="flex items-end gap-2">
        {/* Textarea */}
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={isDisabled}
            rows={1}
            className={`
              w-full resize-none rounded-lg border px-3 py-2 text-sm
              bg-argus-surface-2 text-argus-text placeholder:text-argus-text-dim/60
              focus:outline-none focus:ring-1 focus:ring-argus-accent/50
              transition-colors
              ${isDisabled
                ? 'border-argus-border/50 cursor-not-allowed opacity-60'
                : 'border-argus-border hover:border-argus-border-hover'
              }
            `}
            style={{
              minHeight: `${LINE_HEIGHT + 16}px`, // 1 line + padding
              maxHeight: `${LINE_HEIGHT * MAX_LINES + 16}px`,
              lineHeight: `${LINE_HEIGHT}px`,
            }}
            aria-label="Chat message input"
          />
        </div>

        {/* Send / Cancel button */}
        {isStreaming ? (
          <button
            onClick={handleCancel}
            className="flex-shrink-0 p-2 rounded-lg bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors min-w-[40px] min-h-[40px] flex items-center justify-center"
            aria-label="Cancel response"
          >
            <X className="w-4 h-4" />
          </button>
        ) : (
          <button
            onClick={handleSend}
            disabled={isDisabled || !value.trim()}
            className={`
              flex-shrink-0 p-2 rounded-lg transition-colors
              min-w-[40px] min-h-[40px] flex items-center justify-center
              ${isDisabled || !value.trim()
                ? 'bg-argus-surface-2/50 text-argus-text-dim cursor-not-allowed'
                : 'bg-argus-accent/20 text-argus-accent hover:bg-argus-accent/30'
              }
            `}
            aria-label="Send message"
          >
            <Send className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Character count when approaching limit */}
      {value.length > MAX_MESSAGE_LENGTH * 0.8 && (
        <div className="text-xs text-argus-text-dim px-1 text-right">
          {value.length.toLocaleString()} / {MAX_MESSAGE_LENGTH.toLocaleString()}
        </div>
      )}
    </div>
  );
}

export const ChatInput = memo(ChatInputComponent);
