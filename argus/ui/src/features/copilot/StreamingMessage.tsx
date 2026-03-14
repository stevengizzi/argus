/**
 * Streaming message component for the AI Copilot.
 *
 * Renders the in-progress streaming response from the AI with a
 * blinking cursor at the end. Uses the same markdown rendering as
 * ChatMessage for consistency.
 *
 * Sprint 22, Session 4a.
 */

import { memo, Children, isValidElement, type ReactNode } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeSanitize from 'rehype-sanitize';
import { useCopilotUIStore } from '../../stores/copilotUI';
import { TickerText } from './TickerText';

/**
 * Recursively process children to apply TickerText formatting to string nodes.
 */
function processTickerChildren(children: ReactNode): ReactNode {
  return Children.map(children, (child) => {
    if (typeof child === 'string') {
      return <TickerText>{child}</TickerText>;
    }
    if (isValidElement<{ children?: ReactNode }>(child) && child.props.children) {
      return { ...child, props: { ...child.props, children: processTickerChildren(child.props.children) } };
    }
    return child;
  });
}

/**
 * Blinking cursor component.
 */
function BlinkingCursor() {
  return (
    <span
      className="inline-block w-2 h-4 bg-argus-accent ml-0.5 animate-pulse"
      aria-hidden="true"
    />
  );
}

/**
 * StreamingMessage displays the AI's in-progress response.
 */
function StreamingMessageComponent() {
  const streamingContent = useCopilotUIStore((state) => state.streamingContent);
  const isStreaming = useCopilotUIStore((state) => state.isStreaming);

  // Don't render if not streaming
  if (!isStreaming) {
    return null;
  }

  // Show loading state if no content yet
  if (!streamingContent) {
    return (
      <div className="flex flex-col items-start gap-1">
        <div className="max-w-[90%] bg-argus-surface-2 text-argus-text rounded-2xl rounded-bl-md px-4 py-3">
          <div className="flex items-center gap-2 text-sm text-argus-text-dim">
            <span className="animate-pulse">Thinking</span>
            <span className="flex gap-1">
              <span className="w-1.5 h-1.5 bg-argus-accent rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-1.5 h-1.5 bg-argus-accent rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-1.5 h-1.5 bg-argus-accent rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-start gap-1">
      <div className="max-w-[90%] bg-argus-surface-2 text-argus-text rounded-2xl rounded-bl-md px-4 py-2">
        {/* Markdown content */}
        <div className="prose prose-sm prose-invert max-w-none text-sm">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[rehypeSanitize]}
            components={{
              // Custom code block styling (same as ChatMessage)
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
              ul: ({ children }) => (
                <ul className="my-1 ml-4 list-disc space-y-0.5">{children}</ul>
              ),
              ol: ({ children }) => (
                <ol className="my-1 ml-4 list-decimal space-y-0.5">{children}</ol>
              ),
              li: ({ children }) => <li className="text-sm">{processTickerChildren(children)}</li>,
              p: ({ children }) => <p className="my-1 leading-relaxed">{processTickerChildren(children)}</p>,
            }}
          >
            {streamingContent}
          </ReactMarkdown>
          <BlinkingCursor />
        </div>
      </div>
      <span className="text-xs text-argus-text-dim px-1">typing...</span>
    </div>
  );
}

export const StreamingMessage = memo(StreamingMessageComponent);
