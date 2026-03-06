/**
 * Chat message component for the AI Copilot.
 *
 * Renders user and assistant messages with appropriate styling.
 * Assistant messages support markdown rendering with XSS protection.
 *
 * Sprint 22, Session 4a.
 */

import { useState, useCallback, memo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeSanitize from 'rehype-sanitize';
import { Copy, Check, Wrench } from 'lucide-react';
import type { ChatMessage as ChatMessageType, ToolUseData } from '../../stores/copilotUI';

interface ChatMessageProps {
  message: ChatMessageType;
}

/**
 * Format a timestamp as relative time (e.g., "2m ago", "1h ago").
 */
function formatRelativeTime(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSeconds < 60) {
    return 'just now';
  } else if (diffMinutes < 60) {
    return `${diffMinutes}m ago`;
  } else if (diffHours < 24) {
    return `${diffHours}h ago`;
  } else {
    return `${diffDays}d ago`;
  }
}

/**
 * User message bubble — right-aligned, accent background.
 */
function UserMessage({ content, createdAt }: { content: string; createdAt: string }) {
  return (
    <div className="flex flex-col items-end gap-1">
      <div className="max-w-[85%] bg-argus-accent/20 text-argus-text rounded-2xl rounded-br-md px-4 py-2">
        <p className="text-sm whitespace-pre-wrap break-words">{content}</p>
      </div>
      <span className="text-xs text-argus-text-dim px-1">
        {formatRelativeTime(createdAt)}
      </span>
    </div>
  );
}

/**
 * Tool use placeholder — shows when assistant used tools.
 * Session 5 will replace with ActionCard.
 */
function ToolUsePlaceholder({ toolUse }: { toolUse: ToolUseData[] }) {
  return (
    <div className="flex items-center gap-2 px-3 py-2 bg-argus-surface-2 rounded-lg border border-argus-border/50 text-sm text-argus-text-dim">
      <Wrench className="w-4 h-4 text-argus-accent" />
      <span>
        {toolUse.length === 1
          ? `Action proposal: ${toolUse[0].toolName}`
          : `${toolUse.length} action proposals`}
      </span>
    </div>
  );
}

/**
 * Assistant message — left-aligned with markdown rendering.
 */
function AssistantMessage({
  content,
  createdAt,
  toolUse,
}: {
  content: string;
  createdAt: string;
  toolUse?: ToolUseData[];
}) {
  const [copied, setCopied] = useState(false);
  const [isHovered, setIsHovered] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  }, [content]);

  return (
    <div className="flex flex-col items-start gap-1">
      <div
        className="relative max-w-[90%] bg-argus-surface-2 text-argus-text rounded-2xl rounded-bl-md px-4 py-2 group"
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      >
        {/* Markdown content */}
        <div className="prose prose-sm prose-invert max-w-none text-sm">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[rehypeSanitize]}
            components={{
              // Custom code block styling
              code: ({ className, children, ...props }) => {
                const isInline = !className;
                if (isInline) {
                  return (
                    <code
                      className="px-1.5 py-0.5 bg-argus-bg rounded text-argus-accent font-mono text-xs"
                      {...props}
                    >
                      {children}
                    </code>
                  );
                }
                // Block code
                return (
                  <code
                    className="block overflow-x-auto p-3 bg-argus-bg rounded-lg font-mono text-xs leading-relaxed"
                    {...props}
                  >
                    {children}
                  </code>
                );
              },
              pre: ({ children }) => (
                <pre className="my-2 overflow-hidden rounded-lg">{children}</pre>
              ),
              // Table styling
              table: ({ children }) => (
                <div className="my-2 overflow-x-auto">
                  <table className="min-w-full border-collapse text-xs">{children}</table>
                </div>
              ),
              th: ({ children }) => (
                <th className="border border-argus-border bg-argus-surface px-2 py-1 text-left font-medium">
                  {children}
                </th>
              ),
              td: ({ children }) => (
                <td className="border border-argus-border px-2 py-1">{children}</td>
              ),
              // Link styling
              a: ({ href, children }) => (
                <a
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-argus-accent hover:underline"
                >
                  {children}
                </a>
              ),
              // List styling
              ul: ({ children }) => (
                <ul className="my-1 ml-4 list-disc space-y-0.5">{children}</ul>
              ),
              ol: ({ children }) => (
                <ol className="my-1 ml-4 list-decimal space-y-0.5">{children}</ol>
              ),
              li: ({ children }) => <li className="text-sm">{children}</li>,
              // Paragraph spacing
              p: ({ children }) => <p className="my-1 leading-relaxed">{children}</p>,
            }}
          >
            {content}
          </ReactMarkdown>
        </div>

        {/* Copy button — appears on hover */}
        {isHovered && content && (
          <button
            onClick={handleCopy}
            className="absolute top-2 right-2 p-1.5 rounded-md bg-argus-bg/80 hover:bg-argus-bg text-argus-text-dim hover:text-argus-text transition-colors"
            aria-label="Copy message"
          >
            {copied ? (
              <Check className="w-3.5 h-3.5 text-green-400" />
            ) : (
              <Copy className="w-3.5 h-3.5" />
            )}
          </button>
        )}
      </div>

      {/* Tool use placeholder */}
      {toolUse && toolUse.length > 0 && (
        <div className="mt-1">
          <ToolUsePlaceholder toolUse={toolUse} />
        </div>
      )}

      {/* Timestamp */}
      <span className="text-xs text-argus-text-dim px-1">
        {formatRelativeTime(createdAt)}
      </span>
    </div>
  );
}

/**
 * Main ChatMessage component.
 */
function ChatMessageComponent({ message }: ChatMessageProps) {
  if (message.role === 'user') {
    return <UserMessage content={message.content} createdAt={message.createdAt} />;
  }

  return (
    <AssistantMessage
      content={message.content}
      createdAt={message.createdAt}
      toolUse={message.toolUse}
    />
  );
}

export const ChatMessage = memo(ChatMessageComponent);
