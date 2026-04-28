/**
 * Tests for useAlerts hook (Sprint 31.91 Session 5c).
 *
 * Mirrors the WebSocket-mock pattern in
 * features/arena/useArenaWebSocket.test.ts: a constructor-style mock
 * captures the WS instance so tests can drive onopen/onmessage/onclose
 * directly. JWT auth is mocked via the api/client `getToken` export.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import type { Alert } from '../useAlerts';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock('../../api/client', () => ({
  getToken: () => 'test-token',
}));

interface MockWsInstance {
  onopen: (() => void) | null;
  onmessage: ((event: { data: string }) => void) | null;
  onclose: (() => void) | null;
  onerror: (() => void) | null;
  close: ReturnType<typeof vi.fn>;
  send: ReturnType<typeof vi.fn>;
  readyState: number;
}

let wsInstance: MockWsInstance | null = null;

const MockWebSocket = vi.fn(function MockWebSocketConstructor() {
  wsInstance = {
    onopen: null,
    onmessage: null,
    onclose: null,
    onerror: null,
    close: vi.fn(),
    send: vi.fn(),
    readyState: 1, // OPEN
  };
  return wsInstance;
});
// Static fields read by the hook's cleanup branch.
(MockWebSocket as unknown as { OPEN: number }).OPEN = 1;
(MockWebSocket as unknown as { CONNECTING: number }).CONNECTING = 0;

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function makeAlert(overrides: Partial<Alert> = {}): Alert {
  return {
    alert_id: 'alert-001',
    alert_type: 'phantom_short',
    severity: 'critical',
    source: 'order_manager',
    message: 'Phantom short detected for AAPL',
    metadata: { symbol: 'AAPL', shares: 100 },
    state: 'active',
    created_at_utc: new Date().toISOString(),
    acknowledged_at_utc: null,
    acknowledged_by: null,
    archived_at_utc: null,
    acknowledgment_reason: null,
    ...overrides,
  };
}

function sendMessage(msg: Record<string, unknown>): void {
  wsInstance!.onmessage!({ data: JSON.stringify(msg) });
}

// ---------------------------------------------------------------------------
// Lazy import after mocks
// ---------------------------------------------------------------------------
const { useAlerts } = await import('../useAlerts');

// ---------------------------------------------------------------------------
// Test wrapper
// ---------------------------------------------------------------------------

function makeWrapper(queryClient: QueryClient) {
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useAlerts', () => {
  let queryClient: QueryClient;
  let mockFetch: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.stubGlobal('WebSocket', MockWebSocket);
    vi.clearAllMocks();
    wsInstance = null;
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => [makeAlert()],
    });
    vi.stubGlobal('fetch', mockFetch);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    queryClient.clear();
  });

  it('fetches initial state via REST GET /api/v1/alerts/active', async () => {
    const { result } = renderHook(() => useAlerts(), {
      wrapper: makeWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.alerts.length).toBe(1));
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/v1/alerts/active',
      expect.any(Object),
    );
    expect(result.current.alerts[0].alert_id).toBe('alert-001');
  });

  it('subscribes to WebSocket /ws/v1/alerts on mount and sends auth', () => {
    renderHook(() => useAlerts(), { wrapper: makeWrapper(queryClient) });

    expect(MockWebSocket).toHaveBeenCalledWith(
      expect.stringContaining('/ws/v1/alerts'),
    );
    act(() => {
      wsInstance!.onopen!();
    });
    expect(wsInstance!.send).toHaveBeenCalledWith(
      JSON.stringify({ type: 'auth', token: 'test-token' }),
    );
  });

  it('marks connectionStatus disconnected on ws.onclose and enables REST polling', async () => {
    const { result } = renderHook(() => useAlerts(), {
      wrapper: makeWrapper(queryClient),
    });
    // Initial fetch
    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1));

    act(() => {
      wsInstance!.onclose!();
    });
    expect(result.current.connectionStatus).toBe('disconnected');

    // The query observer should now have refetchInterval=5000.
    const observer = queryClient.getQueryCache().findAll({
      queryKey: ['alerts', 'active'],
    })[0];
    expect(observer.options.refetchInterval).toBe(5000);
  });

  it('refetches REST after WebSocket reconnect (auth_success)', async () => {
    const { result } = renderHook(() => useAlerts(), {
      wrapper: makeWrapper(queryClient),
    });
    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1));

    // Simulate disconnect then reconnect.
    act(() => {
      wsInstance!.onclose!();
    });
    expect(result.current.connectionStatus).toBe('disconnected');

    act(() => {
      wsInstance!.onopen!();
      sendMessage({ type: 'auth_success', timestamp: 'x' });
    });

    expect(result.current.connectionStatus).toBe('connected');
    // refetch() invoked from inside auth_success handler.
    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(2));
  });

  it('replaces query cache from WS snapshot frame', async () => {
    const { result } = renderHook(() => useAlerts(), {
      wrapper: makeWrapper(queryClient),
    });
    await waitFor(() => expect(result.current.alerts.length).toBe(1));

    const snapshotAlerts = [
      makeAlert({ alert_id: 'a', message: 'A' }),
      makeAlert({ alert_id: 'b', message: 'B' }),
      // Archived alert must be filtered out.
      makeAlert({ alert_id: 'c', state: 'archived' }),
    ];

    act(() => {
      wsInstance!.onopen!();
      sendMessage({ type: 'auth_success', timestamp: 'x' });
      sendMessage({
        type: 'snapshot',
        timestamp: 'y',
        alerts: snapshotAlerts,
      });
    });

    expect(result.current.alerts.length).toBe(2);
    expect(result.current.alerts.map((a) => a.alert_id).sort()).toEqual([
      'a',
      'b',
    ]);
  });

  it('appends a new alert on alert_active and removes on alert_auto_resolved', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => [],
    });
    const { result } = renderHook(() => useAlerts(), {
      wrapper: makeWrapper(queryClient),
    });
    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1));

    const newAlert = makeAlert({ alert_id: 'fresh' });

    act(() => {
      wsInstance!.onopen!();
      sendMessage({ type: 'auth_success', timestamp: 'x' });
      sendMessage({ type: 'alert_active', timestamp: 'y', alert: newAlert });
    });

    await waitFor(() =>
      expect(result.current.alerts.map((a) => a.alert_id)).toContain('fresh'),
    );

    act(() => {
      sendMessage({
        type: 'alert_auto_resolved',
        timestamp: 'z',
        alert: { ...newAlert, state: 'archived' },
      });
    });

    await waitFor(() =>
      expect(result.current.alerts.map((a) => a.alert_id)).not.toContain(
        'fresh',
      ),
    );
  });

  it('updates an alert in place on alert_acknowledged', async () => {
    const original = makeAlert({ alert_id: 'ack-target' });
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => [original],
    });
    const { result } = renderHook(() => useAlerts(), {
      wrapper: makeWrapper(queryClient),
    });
    await waitFor(() => expect(result.current.alerts.length).toBe(1));

    act(() => {
      wsInstance!.onopen!();
      sendMessage({ type: 'auth_success', timestamp: 'x' });
      sendMessage({
        type: 'alert_acknowledged',
        timestamp: 'y',
        alert: {
          ...original,
          state: 'acknowledged',
          acknowledged_by: 'operator',
          acknowledgment_reason: 'manual ack',
        },
      });
    });

    expect(result.current.alerts.length).toBe(1);
    expect(result.current.alerts[0].state).toBe('acknowledged');
    expect(result.current.alerts[0].acknowledged_by).toBe('operator');
  });

  it('acknowledge() POSTs to /api/v1/alerts/{id}/acknowledge with reason + operator_id', async () => {
    const ackResult = {
      alert_id: 'a',
      acknowledged_at_utc: 't',
      acknowledged_by: 'operator',
      reason: 'manual',
      audit_id: 1,
      state: 'acknowledged',
    };
    // First call: initial REST list. Second call: ack POST.
    mockFetch
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => [] })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ackResult });

    const { result } = renderHook(() => useAlerts(), {
      wrapper: makeWrapper(queryClient),
    });
    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1));

    let returned: unknown;
    await act(async () => {
      returned = await result.current.acknowledge('a', 'manual ack reason here', 'operator');
    });

    const ackCall = mockFetch.mock.calls[1];
    expect(ackCall[0]).toBe('/api/v1/alerts/a/acknowledge');
    const init = ackCall[1] as RequestInit;
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body as string)).toEqual({
      reason: 'manual ack reason here',
      operator_id: 'operator',
    });
    expect(returned).toEqual(ackResult);
  });

  it('acknowledge() returns null on 404 (alert vanished)', async () => {
    mockFetch
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => [] })
      .mockResolvedValueOnce({ ok: false, status: 404, json: async () => ({}) });

    const { result } = renderHook(() => useAlerts(), {
      wrapper: makeWrapper(queryClient),
    });
    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1));

    let returned: unknown = 'untouched';
    await act(async () => {
      returned = await result.current.acknowledge('gone', 'manual ack reason', 'operator');
    });
    expect(returned).toBeNull();
  });

  it('closes WebSocket on unmount', () => {
    const { unmount } = renderHook(() => useAlerts(), {
      wrapper: makeWrapper(queryClient),
    });
    const handle = wsInstance!;
    unmount();
    expect(handle.close).toHaveBeenCalled();
  });
});
