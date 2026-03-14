/**
 * Chat message component for the AI Copilot.
 *
 * Renders user and assistant messages with appropriate styling.
 * Assistant messages support markdown rendering with XSS protection.
 *
 * Sprint 22, Session 4a.
 */

import { useState, useCallback, useEffect, memo, Children, isValidElement, type ReactNode } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeSanitize from 'rehype-sanitize';
import { Copy, Check } from 'lucide-react';
import { useCopilotUIStore } from '../../stores/copilotUI';
import type { ChatMessage as ChatMessageType, ToolUseData, ProposalState } from '../../stores/copilotUI';
import { ActionCard } from './ActionCard';
import { approveProposal, rejectProposal } from './api';
import { TickerText } from './TickerText';

interface ChatMessageProps {
  message: ChatMessageType;
}

/**
 * Recursively process children to apply TickerText formatting to string nodes.
 */
function processTickerChildren(children: ReactNode): ReactNode {
  return Children.map(children, (child) => {
    if (typeof child === 'string') {
      return <TickerText>{child}</TickerText>;
    }
    if (isValidElement<{ children?: ReactNode }>(child) && child.props.children) {
      // Clone element with processed children
      return { ...child, props: { ...child.props, children: processTickerChildren(child.props.children) } };
    }
    return child;
  });
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
 * Action card list — renders ActionCards for tool_use blocks.
 */
function ActionCardList({ toolUse }: { toolUse: ToolUseData[] }) {
  const { proposals, setProposal, updateProposal } = useCopilotUIStore();

  // Initialize proposals in the store for any that have proposalIds
  useEffect(() => {
    toolUse.forEach((tu) => {
      if (tu.proposalId && !proposals[tu.proposalId]) {
        // Create a default pending proposal state
        // The expiresAt will be overridden if we fetch from the server
        const now = new Date();
        const defaultExpiry = new Date(now.getTime() + 5 * 60 * 1000); // 5 min default

        const proposal: ProposalState = {
          id: tu.proposalId,
          toolName: tu.toolName,
          toolInput: tu.toolInput,
          status: 'pending',
          expiresAt: defaultExpiry.toISOString(),
        };
        setProposal(proposal);
      }
    });
  }, [toolUse, proposals, setProposal]);

  const handleApprove = useCallback(async (proposalId: string) => {
    try {
      const response = await approveProposal(proposalId);
      updateProposal(proposalId, {
        status: response.proposal.status as ProposalState['status'],
        result: response.proposal.result ?? undefined,
      });

      // If approved, the server may start execution. Poll for executed/failed status.
      // For now, just set to approved. Session 3b handles execution.
      if (response.proposal.status === 'approved') {
        // Simulate execution completion after a short delay (for demo purposes)
        // In production, WebSocket would push the executed/failed status
        setTimeout(() => {
          updateProposal(proposalId, { status: 'executed' });
        }, 1500);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to approve';

      // Check for specific error codes
      if (message.includes('expired') || message.includes('410')) {
        updateProposal(proposalId, { status: 'expired' });
      } else if (message.includes('409')) {
        // Already resolved — the message contains the current status
        // For now, just mark as failed with the message
        updateProposal(proposalId, { status: 'failed', failureReason: message });
      } else {
        updateProposal(proposalId, { status: 'failed', failureReason: message });
      }
      throw error;
    }
  }, [updateProposal]);

  const handleReject = useCallback(async (proposalId: string, reason?: string) => {
    try {
      const response = await rejectProposal(proposalId, reason);
      updateProposal(proposalId, {
        status: response.proposal.status as ProposalState['status'],
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to reject';
      updateProposal(proposalId, { status: 'failed', failureReason: message });
      throw error;
    }
  }, [updateProposal]);

  // Filter to only render proposals that have a proposalId
  const proposalsToRender = toolUse
    .filter((tu) => tu.proposalId)
    .map((tu) => {
      const proposal = proposals[tu.proposalId!];
      if (!proposal) return null;
      return (
        <ActionCard
          key={proposal.id}
          proposal={proposal}
          onApprove={handleApprove}
          onReject={handleReject}
        />
      );
    })
    .filter(Boolean);

  // Also render generate_report tool uses (no approval needed)
  const reportToolUses = toolUse.filter(
    (tu) => tu.toolName === 'generate_report' && !tu.proposalId
  );

  if (proposalsToRender.length === 0 && reportToolUses.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-col gap-2">
      {proposalsToRender}
      {reportToolUses.map((tu, idx) => (
        <ActionCard
          key={`report-${idx}`}
          proposal={{
            id: `report-${idx}`,
            toolName: tu.toolName,
            toolInput: tu.toolInput,
            status: 'executed',
            expiresAt: new Date().toISOString(),
            result: { message: 'Report generated' },
          }}
          onApprove={async () => {}}
          onReject={async () => {}}
        />
      ))}
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
              li: ({ children }) => <li className="text-sm">{processTickerChildren(children)}</li>,
              // Paragraph spacing with ticker formatting
              p: ({ children }) => <p className="my-1 leading-relaxed">{processTickerChildren(children)}</p>,
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

      {/* Action cards for tool use */}
      {toolUse && toolUse.length > 0 && (
        <div className="mt-2">
          <ActionCardList toolUse={toolUse} />
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
