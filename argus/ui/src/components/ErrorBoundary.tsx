/**
 * Error Boundary component to catch and display JavaScript runtime errors.
 *
 * Prevents the entire app from crashing when a component throws an error.
 */

import { Component, type ReactNode, type ErrorInfo } from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface ErrorBoundaryProps {
  children: ReactNode;
  /** Optional name for identifying which boundary caught the error */
  name?: string;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    this.setState({ errorInfo });
    console.error(`[ErrorBoundary${this.props.name ? `: ${this.props.name}` : ''}] Caught error:`, error, errorInfo);
  }

  handleRetry = (): void => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      const { error, errorInfo } = this.state;

      return (
        <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
          <AlertCircle className="w-12 h-12 text-argus-loss mb-4" />
          <h3 className="text-lg font-semibold text-argus-text mb-2">
            Something went wrong
          </h3>
          <p className="text-sm text-argus-text-dim mb-4 max-w-md">
            {error?.message || 'An unexpected error occurred'}
          </p>

          {/* Show component stack in development */}
          {import.meta.env.DEV && errorInfo?.componentStack && (
            <details className="mb-4 w-full max-w-xl text-left">
              <summary className="text-xs text-argus-text-dim cursor-pointer hover:text-argus-text">
                Show error details
              </summary>
              <pre className="mt-2 p-3 bg-argus-surface-2 rounded-md text-xs text-argus-text-dim overflow-x-auto whitespace-pre-wrap">
                {error?.stack}
                {'\n\nComponent Stack:'}
                {errorInfo.componentStack}
              </pre>
            </details>
          )}

          <button
            onClick={this.handleRetry}
            className="flex items-center gap-2 px-4 py-2 text-sm rounded-md bg-argus-accent hover:bg-argus-accent/80 text-white font-medium transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Try Again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
