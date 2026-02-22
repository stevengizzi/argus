/**
 * Connection test page for development.
 *
 * Tests all API endpoints and displays JSON results + WebSocket status.
 */

import { useState, useEffect } from 'react';
import { useAuthStore } from '../stores/auth';
import { useLiveStore } from '../stores/live';
import {
  getAccount,
  getPositions,
  getTrades,
  getPerformance,
  getHealth,
  getStrategies,
} from '../api/client';
import {
  RefreshCw,
  Check,
  X,
  LogOut,
  Wifi,
  WifiOff,
  Activity,
} from 'lucide-react';

interface EndpointResult {
  name: string;
  status: 'pending' | 'loading' | 'success' | 'error';
  data?: unknown;
  error?: string;
  duration?: number;
}

export function ConnectionTest() {
  const logout = useAuthStore((state) => state.logout);
  const { connected, status, recentEvents, connect, disconnect } = useLiveStore();
  const [results, setResults] = useState<EndpointResult[]>([
    { name: 'Account', status: 'pending' },
    { name: 'Positions', status: 'pending' },
    { name: 'Trades', status: 'pending' },
    { name: 'Performance', status: 'pending' },
    { name: 'Health', status: 'pending' },
    { name: 'Strategies', status: 'pending' },
  ]);
  const [selectedResult, setSelectedResult] = useState<number | null>(null);

  const updateResult = (index: number, update: Partial<EndpointResult>) => {
    setResults((prev) =>
      prev.map((r, i) => (i === index ? { ...r, ...update } : r))
    );
  };

  const testEndpoint = async (
    index: number,
    _name: string,
    fetcher: () => Promise<unknown>
  ) => {
    updateResult(index, { status: 'loading' });
    const start = performance.now();
    try {
      const data = await fetcher();
      updateResult(index, {
        status: 'success',
        data,
        error: undefined,
        duration: Math.round(performance.now() - start),
      });
    } catch (err) {
      updateResult(index, {
        status: 'error',
        error: err instanceof Error ? err.message : 'Unknown error',
        data: undefined,
        duration: Math.round(performance.now() - start),
      });
    }
  };

  const runAllTests = async () => {
    // Reset all
    setResults((prev) => prev.map((r) => ({ ...r, status: 'pending' as const })));
    setSelectedResult(null);

    // Run tests in parallel
    await Promise.all([
      testEndpoint(0, 'Account', getAccount),
      testEndpoint(1, 'Positions', getPositions),
      testEndpoint(2, 'Trades', () => getTrades({ limit: 10 })),
      testEndpoint(3, 'Performance', () => getPerformance('today')),
      testEndpoint(4, 'Health', getHealth),
      testEndpoint(5, 'Strategies', getStrategies),
    ]);
  };

  // Run tests on mount
  useEffect(() => {
    runAllTests();
    // Connect to WebSocket
    connect();
    return () => disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const getStatusIcon = (status: EndpointResult['status']) => {
    switch (status) {
      case 'pending':
        return <span className="text-argus-text-dim">-</span>;
      case 'loading':
        return <RefreshCw className="h-4 w-4 text-argus-accent animate-spin" />;
      case 'success':
        return <Check className="h-4 w-4 text-argus-success" />;
      case 'error':
        return <X className="h-4 w-4 text-argus-danger" />;
    }
  };

  const getWsStatusColor = () => {
    switch (status) {
      case 'connected':
        return 'text-argus-success';
      case 'connecting':
        return 'text-argus-warning';
      case 'error':
        return 'text-argus-danger';
      default:
        return 'text-argus-text-dim';
    }
  };

  return (
    <div className="min-h-screen bg-argus-bg p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-argus-text">Connection Test</h1>
            <p className="text-argus-text-dim">
              API and WebSocket endpoint verification
            </p>
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={runAllTests}
              className="flex items-center gap-2 px-4 py-2 bg-argus-accent hover:bg-blue-600 text-white rounded-lg transition-colors"
            >
              <RefreshCw className="h-4 w-4" />
              Re-test All
            </button>
            <button
              onClick={logout}
              className="flex items-center gap-2 px-4 py-2 bg-argus-surface border border-argus-border hover:border-argus-danger text-argus-text rounded-lg transition-colors"
            >
              <LogOut className="h-4 w-4" />
              Logout
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* REST Endpoints */}
          <div className="bg-argus-surface border border-argus-border rounded-lg overflow-hidden">
            <div className="px-4 py-3 border-b border-argus-border">
              <h2 className="font-semibold text-argus-text flex items-center gap-2">
                <Activity className="h-5 w-5" />
                REST Endpoints
              </h2>
            </div>
            <div className="divide-y divide-argus-border">
              {results.map((result, index) => (
                <button
                  key={result.name}
                  onClick={() => setSelectedResult(index)}
                  className={`w-full px-4 py-3 flex items-center justify-between hover:bg-argus-bg/50 transition-colors ${
                    selectedResult === index ? 'bg-argus-bg/50' : ''
                  }`}
                >
                  <div className="flex items-center gap-3">
                    {getStatusIcon(result.status)}
                    <span className="text-argus-text">{result.name}</span>
                  </div>
                  {result.duration !== undefined && (
                    <span className="text-sm text-argus-text-dim">
                      {result.duration}ms
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Selected Result JSON */}
          <div className="bg-argus-surface border border-argus-border rounded-lg overflow-hidden">
            <div className="px-4 py-3 border-b border-argus-border">
              <h2 className="font-semibold text-argus-text">
                {selectedResult !== null
                  ? `${results[selectedResult].name} Response`
                  : 'Select an endpoint'}
              </h2>
            </div>
            <div className="p-4 overflow-auto max-h-96">
              {selectedResult !== null ? (
                results[selectedResult].error ? (
                  <div className="text-argus-danger font-mono text-sm">
                    Error: {results[selectedResult].error}
                  </div>
                ) : (
                  <pre className="text-sm text-argus-text font-mono whitespace-pre-wrap">
                    {JSON.stringify(results[selectedResult].data, null, 2)}
                  </pre>
                )
              ) : (
                <p className="text-argus-text-dim">
                  Click an endpoint to view its response
                </p>
              )}
            </div>
          </div>
        </div>

        {/* WebSocket Status */}
        <div className="mt-6 bg-argus-surface border border-argus-border rounded-lg overflow-hidden">
          <div className="px-4 py-3 border-b border-argus-border flex items-center justify-between">
            <h2 className="font-semibold text-argus-text flex items-center gap-2">
              {connected ? (
                <Wifi className="h-5 w-5 text-argus-success" />
              ) : (
                <WifiOff className="h-5 w-5 text-argus-text-dim" />
              )}
              WebSocket
            </h2>
            <div className="flex items-center gap-4">
              <span className={`text-sm ${getWsStatusColor()}`}>
                {status.charAt(0).toUpperCase() + status.slice(1)}
              </span>
              <button
                onClick={() => (connected ? disconnect() : connect())}
                className="px-3 py-1 text-sm bg-argus-bg border border-argus-border hover:border-argus-accent rounded transition-colors"
              >
                {connected ? 'Disconnect' : 'Connect'}
              </button>
            </div>
          </div>
          <div className="p-4">
            <h3 className="text-sm font-medium text-argus-text-dim mb-2">
              Recent Events ({recentEvents.length})
            </h3>
            {recentEvents.length > 0 ? (
              <div className="space-y-2 max-h-48 overflow-auto">
                {recentEvents.slice(0, 10).map((event, i) => (
                  <div
                    key={`${event.sequence}-${i}`}
                    className="text-xs font-mono p-2 bg-argus-bg rounded border border-argus-border"
                  >
                    <span className="text-argus-accent">{event.type}</span>
                    <span className="text-argus-text-dim"> #{event.sequence}</span>
                    <pre className="mt-1 text-argus-text-dim overflow-hidden">
                      {JSON.stringify(event.data, null, 2).slice(0, 200)}
                      {JSON.stringify(event.data).length > 200 && '...'}
                    </pre>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-argus-text-dim text-sm">
                No events received yet. Connect to start receiving live updates.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
