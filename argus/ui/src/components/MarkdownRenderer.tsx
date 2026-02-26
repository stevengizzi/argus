/**
 * Styled markdown renderer for strategy documentation.
 *
 * Uses react-markdown with remark-gfm for table support.
 * Styled to match the dark Argus theme.
 */

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MarkdownRendererProps {
  content: string;
}

export function MarkdownRenderer({ content }: MarkdownRendererProps) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        h1: ({ children }) => (
          <h1 className="text-xl font-bold text-argus-text mt-6 mb-3">{children}</h1>
        ),
        h2: ({ children }) => (
          <h2 className="text-lg font-semibold text-argus-text mt-5 mb-2 border-b border-argus-border pb-1">
            {children}
          </h2>
        ),
        h3: ({ children }) => (
          <h3 className="text-base font-semibold text-argus-text mt-4 mb-1">{children}</h3>
        ),
        p: ({ children }) => (
          <p className="text-sm text-argus-text leading-relaxed mb-3">{children}</p>
        ),
        ul: ({ children }) => (
          <ul className="text-sm text-argus-text list-disc list-inside mb-3 space-y-1">
            {children}
          </ul>
        ),
        ol: ({ children }) => (
          <ol className="text-sm text-argus-text list-decimal list-inside mb-3 space-y-1">
            {children}
          </ol>
        ),
        li: ({ children }) => <li className="text-sm text-argus-text">{children}</li>,
        table: ({ children }) => (
          <div className="overflow-x-auto mb-4">
            <table className="w-full text-sm border-collapse">{children}</table>
          </div>
        ),
        thead: ({ children }) => (
          <thead className="border-b border-argus-border">{children}</thead>
        ),
        th: ({ children }) => (
          <th className="text-left text-argus-text-dim font-medium py-2 px-3">{children}</th>
        ),
        td: ({ children }) => (
          <td className="text-argus-text py-2 px-3 border-b border-argus-border/50">{children}</td>
        ),
        code: ({ children, className }) => {
          const isBlock = className?.includes('language-');
          if (isBlock) {
            return (
              <code className="block bg-argus-surface-2 rounded-md p-3 text-xs font-mono overflow-x-auto mb-3">
                {children}
              </code>
            );
          }
          return (
            <code className="bg-argus-surface-2 px-1.5 py-0.5 rounded text-xs font-mono">
              {children}
            </code>
          );
        },
        pre: ({ children }) => <pre className="mb-3">{children}</pre>,
        blockquote: ({ children }) => (
          <blockquote className="border-l-2 border-argus-accent/50 pl-4 italic text-argus-text-dim mb-3">
            {children}
          </blockquote>
        ),
        a: ({ href, children }) => (
          <a
            href={href}
            className="text-argus-accent hover:underline"
            target="_blank"
            rel="noopener noreferrer"
          >
            {children}
          </a>
        ),
        hr: () => <hr className="border-argus-border my-4" />,
        strong: ({ children }) => (
          <strong className="font-semibold text-argus-text">{children}</strong>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  );
}
