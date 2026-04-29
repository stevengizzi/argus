/**
 * AlertsPanel: Observatory-page browsing surface for active + historical
 * alerts.
 *
 * Sprint 31.91 Session 5e — D13 alert observability frontend.
 *
 * Layout:
 *   - Filters (severity / source / symbol).
 *   - Active alerts table (sortable).
 *   - History date-range picker + table (defaults to last 7 days).
 *   - Detail modal with metadata + acknowledgment audit trail.
 *
 * Sources:
 *   - Active alerts: `useAlerts` (the same WebSocket-backed hook the
 *     banner + toast consume — single source of truth in-session).
 *   - Historical alerts: `useAlertHistory` → REST `/api/v1/alerts/history`.
 *   - Audit trail: `useAlertAuditTrail` → REST `/api/v1/alerts/{id}/audit`.
 */

import { useMemo, useState } from 'react';
import {
  useAlerts,
  useAlertHistory,
  useAlertAuditTrail,
  type Alert,
  type AlertSeverity,
  type AlertHistoryRange,
} from '../hooks/useAlerts';

type SortKey = 'severity' | 'source' | 'symbol' | 'created_at_utc';

const SEVERITY_RANK: Record<AlertSeverity, number> = {
  critical: 0,
  warning: 1,
  info: 2,
};

const DEFAULT_HISTORY_DAYS = 7;

function isoDayStart(d: Date): string {
  // YYYY-MM-DDT00:00:00Z — ISO-8601 UTC, day boundary.
  const yyyy = d.getUTCFullYear();
  const mm = String(d.getUTCMonth() + 1).padStart(2, '0');
  const dd = String(d.getUTCDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}T00:00:00Z`;
}

function isoDayEnd(d: Date): string {
  const yyyy = d.getUTCFullYear();
  const mm = String(d.getUTCMonth() + 1).padStart(2, '0');
  const dd = String(d.getUTCDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}T23:59:59Z`;
}

function defaultHistoryRange(): AlertHistoryRange {
  const now = new Date();
  const from = new Date(now);
  from.setUTCDate(from.getUTCDate() - DEFAULT_HISTORY_DAYS);
  return { from: isoDayStart(from), to: isoDayEnd(now) };
}

function symbolOf(a: Alert): string {
  const sym = a.metadata?.symbol;
  return typeof sym === 'string' ? sym : '';
}

function applyFilters(
  list: Alert[],
  filters: { severity: string; source: string; symbol: string },
): Alert[] {
  return list.filter((a) => {
    if (filters.severity !== 'all' && a.severity !== filters.severity) {
      return false;
    }
    if (filters.source !== 'all' && a.source !== filters.source) {
      return false;
    }
    if (filters.symbol.trim()) {
      const needle = filters.symbol.trim().toUpperCase();
      if (!symbolOf(a).toUpperCase().includes(needle)) {
        return false;
      }
    }
    return true;
  });
}

function sortAlerts(list: Alert[], key: SortKey): Alert[] {
  const copy = [...list];
  copy.sort((a, b) => {
    switch (key) {
      case 'severity':
        return SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity];
      case 'source':
        return a.source.localeCompare(b.source);
      case 'symbol':
        return symbolOf(a).localeCompare(symbolOf(b));
      case 'created_at_utc':
      default:
        // Newest first.
        return a.created_at_utc < b.created_at_utc ? 1 : -1;
    }
  });
  return copy;
}

interface AlertsTableProps {
  alerts: Alert[];
  onSelectAlert: (alert: Alert) => void;
  sortKey: SortKey;
  onSortChange: (key: SortKey) => void;
  emptyMessage: string;
  testId: string;
}

function AlertsTable({
  alerts,
  onSelectAlert,
  sortKey,
  onSortChange,
  emptyMessage,
  testId,
}: AlertsTableProps) {
  if (alerts.length === 0) {
    return (
      <div
        data-testid={`${testId}-empty`}
        className="text-sm text-argus-text-dim py-4"
      >
        {emptyMessage}
      </div>
    );
  }

  const headerBtnClass = (active: boolean) =>
    `text-left px-2 py-1 text-xs uppercase tracking-wide ${
      active
        ? 'text-argus-accent font-semibold'
        : 'text-argus-text-dim hover:text-argus-text'
    }`;

  return (
    <div className="overflow-auto" data-testid={testId}>
      <table className="w-full text-sm">
        <thead className="border-b border-argus-border bg-argus-surface-2">
          <tr>
            <th>
              <button
                type="button"
                className={headerBtnClass(sortKey === 'severity')}
                onClick={() => onSortChange('severity')}
                data-testid={`${testId}-sort-severity`}
              >
                Severity
              </button>
            </th>
            <th>
              <button
                type="button"
                className={headerBtnClass(sortKey === 'source')}
                onClick={() => onSortChange('source')}
                data-testid={`${testId}-sort-source`}
              >
                Source
              </button>
            </th>
            <th>
              <button
                type="button"
                className={headerBtnClass(sortKey === 'symbol')}
                onClick={() => onSortChange('symbol')}
                data-testid={`${testId}-sort-symbol`}
              >
                Symbol
              </button>
            </th>
            <th className="px-2 py-1 text-left text-xs uppercase tracking-wide text-argus-text-dim">
              Type
            </th>
            <th className="px-2 py-1 text-left text-xs uppercase tracking-wide text-argus-text-dim">
              Message
            </th>
            <th>
              <button
                type="button"
                className={headerBtnClass(sortKey === 'created_at_utc')}
                onClick={() => onSortChange('created_at_utc')}
                data-testid={`${testId}-sort-time`}
              >
                Emitted
              </button>
            </th>
            <th className="px-2 py-1 text-left text-xs uppercase tracking-wide text-argus-text-dim">
              State
            </th>
          </tr>
        </thead>
        <tbody>
          {alerts.map((a) => (
            <tr
              key={a.alert_id}
              role="button"
              tabIndex={0}
              data-testid={`${testId}-row-${a.alert_id}`}
              className="border-b border-argus-border hover:bg-argus-surface-2 cursor-pointer"
              onClick={() => onSelectAlert(a)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  onSelectAlert(a);
                }
              }}
            >
              <td className="px-2 py-1.5">
                <span
                  className={
                    a.severity === 'critical'
                      ? 'text-red-400 font-semibold'
                      : a.severity === 'warning'
                        ? 'text-yellow-400'
                        : 'text-argus-text-dim'
                  }
                >
                  {a.severity}
                </span>
              </td>
              <td className="px-2 py-1.5 text-argus-text-dim">{a.source}</td>
              <td className="px-2 py-1.5 font-mono">{symbolOf(a) || '—'}</td>
              <td className="px-2 py-1.5 font-mono text-xs">{a.alert_type}</td>
              <td className="px-2 py-1.5 truncate max-w-md" title={a.message}>
                {a.message}
              </td>
              <td className="px-2 py-1.5 font-mono text-xs text-argus-text-dim">
                {a.created_at_utc}
              </td>
              <td className="px-2 py-1.5 text-xs uppercase">{a.state}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface AlertDetailViewProps {
  alert: Alert;
  onClose: () => void;
}

export function AlertDetailView({ alert, onClose }: AlertDetailViewProps) {
  const { data: auditTrail = [], isLoading } = useAlertAuditTrail(
    alert.alert_id,
  );

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="alert-detail-title"
      data-testid="alert-detail-view"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
    >
      <div
        className="bg-argus-surface border border-argus-border rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-4 py-3 border-b border-argus-border flex items-center justify-between">
          <h3
            id="alert-detail-title"
            className="font-semibold text-argus-text"
          >
            {alert.alert_type}
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="text-argus-text-dim hover:text-argus-text text-sm"
            aria-label="Close"
          >
            Close
          </button>
        </div>

        <div className="px-4 py-3 space-y-3">
          <div>
            <div className="text-xs uppercase text-argus-text-dim mb-1">
              Message
            </div>
            <div className="text-sm">{alert.message}</div>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs">
            <div>
              <span className="text-argus-text-dim">Severity:</span>{' '}
              <span className="font-mono">{alert.severity}</span>
            </div>
            <div>
              <span className="text-argus-text-dim">State:</span>{' '}
              <span className="font-mono">{alert.state}</span>
            </div>
            <div>
              <span className="text-argus-text-dim">Source:</span>{' '}
              <span className="font-mono">{alert.source}</span>
            </div>
            <div>
              <span className="text-argus-text-dim">Created:</span>{' '}
              <span className="font-mono">{alert.created_at_utc}</span>
            </div>
          </div>

          <div>
            <div className="text-xs uppercase text-argus-text-dim mb-1">
              Metadata
            </div>
            <pre
              data-testid="alert-detail-metadata"
              className="text-xs bg-argus-surface-2 border border-argus-border rounded p-2 overflow-auto whitespace-pre-wrap"
            >
              {JSON.stringify(alert.metadata, null, 2)}
            </pre>
          </div>

          <div>
            <div className="text-xs uppercase text-argus-text-dim mb-1">
              Audit Trail
            </div>
            {isLoading ? (
              <div
                data-testid="alert-detail-audit-loading"
                className="text-xs text-argus-text-dim"
              >
                Loading audit trail…
              </div>
            ) : auditTrail.length === 0 ? (
              <div
                data-testid="alert-detail-audit-empty"
                className="text-xs text-argus-text-dim"
              >
                No acknowledgment audit entries.
              </div>
            ) : (
              <ul
                data-testid="alert-detail-audit"
                className="space-y-1 text-xs"
              >
                {auditTrail.map((entry) => (
                  <li
                    key={entry.audit_id}
                    data-testid={`audit-entry-${entry.audit_id}`}
                    className="border border-argus-border rounded p-2"
                  >
                    <div className="font-mono text-argus-text-dim">
                      {entry.timestamp_utc} · {entry.audit_kind} ·{' '}
                      {entry.operator_id}
                    </div>
                    <div className="mt-0.5">{entry.reason}</div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export function AlertsPanel() {
  const { alerts: activeAlerts } = useAlerts();
  const [historyRange, setHistoryRange] = useState<AlertHistoryRange>(
    defaultHistoryRange,
  );
  const { data: historyAlerts = [] } = useAlertHistory(historyRange);

  const [sortKey, setSortKey] = useState<SortKey>('created_at_utc');
  const [filterSeverity, setFilterSeverity] = useState<string>('all');
  const [filterSource, setFilterSource] = useState<string>('all');
  const [filterSymbol, setFilterSymbol] = useState<string>('');
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);

  const sourceOptions = useMemo(() => {
    const sources = new Set<string>();
    for (const a of activeAlerts) sources.add(a.source);
    for (const a of historyAlerts) sources.add(a.source);
    return Array.from(sources).sort();
  }, [activeAlerts, historyAlerts]);

  const filters = {
    severity: filterSeverity,
    source: filterSource,
    symbol: filterSymbol,
  };

  const filteredActive = applyFilters(activeAlerts, filters);
  const sortedActive = sortAlerts(filteredActive, sortKey);
  const filteredHistory = applyFilters(historyAlerts, filters);
  const sortedHistory = sortAlerts(filteredHistory, sortKey);

  const fromInput = historyRange.from.slice(0, 10);
  const toInput = historyRange.to.slice(0, 10);

  return (
    <div
      data-testid="alerts-panel"
      className="bg-argus-surface border border-argus-border rounded-lg p-4 space-y-4"
    >
      <h2 className="text-lg font-semibold">Alerts</h2>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <label className="text-xs text-argus-text-dim flex items-center gap-2">
          Severity
          <select
            data-testid="filter-severity"
            value={filterSeverity}
            onChange={(e) => setFilterSeverity(e.target.value)}
            className="h-8 bg-argus-surface-2 border border-argus-border rounded px-2 text-sm text-argus-text"
          >
            <option value="all">All</option>
            <option value="critical">Critical</option>
            <option value="warning">Warning</option>
            <option value="info">Info</option>
          </select>
        </label>
        <label className="text-xs text-argus-text-dim flex items-center gap-2">
          Source
          <select
            data-testid="filter-source"
            value={filterSource}
            onChange={(e) => setFilterSource(e.target.value)}
            className="h-8 bg-argus-surface-2 border border-argus-border rounded px-2 text-sm text-argus-text"
          >
            <option value="all">All</option>
            {sourceOptions.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs text-argus-text-dim flex items-center gap-2">
          Symbol
          <input
            data-testid="filter-symbol"
            type="text"
            value={filterSymbol}
            onChange={(e) => setFilterSymbol(e.target.value)}
            placeholder="e.g. AAPL"
            className="h-8 bg-argus-surface-2 border border-argus-border rounded px-2 text-sm text-argus-text"
          />
        </label>
      </div>

      {/* Active alerts */}
      <section className="space-y-2" data-testid="alerts-panel-active-section">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-argus-text-dim">
          Active ({sortedActive.length})
        </h3>
        <AlertsTable
          alerts={sortedActive}
          onSelectAlert={setSelectedAlert}
          sortKey={sortKey}
          onSortChange={setSortKey}
          emptyMessage="No active alerts."
          testId="alerts-table-active"
        />
      </section>

      {/* History */}
      <section className="space-y-2" data-testid="alerts-panel-history-section">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-argus-text-dim">
            History ({sortedHistory.length})
          </h3>
          <div className="flex items-center gap-2 text-xs">
            <input
              type="date"
              aria-label="History from date"
              data-testid="history-from"
              value={fromInput}
              onChange={(e) => {
                const v = e.target.value;
                if (v) {
                  setHistoryRange((prev) => ({
                    ...prev,
                    from: `${v}T00:00:00Z`,
                  }));
                }
              }}
              className="h-8 bg-argus-surface-2 border border-argus-border rounded px-2"
            />
            <span className="text-argus-text-dim">→</span>
            <input
              type="date"
              aria-label="History to date"
              data-testid="history-to"
              value={toInput}
              min={fromInput}
              onChange={(e) => {
                const v = e.target.value;
                if (v) {
                  setHistoryRange((prev) => ({
                    ...prev,
                    to: `${v}T23:59:59Z`,
                  }));
                }
              }}
              className="h-8 bg-argus-surface-2 border border-argus-border rounded px-2"
            />
          </div>
        </div>
        <AlertsTable
          alerts={sortedHistory}
          onSelectAlert={setSelectedAlert}
          sortKey={sortKey}
          onSortChange={setSortKey}
          emptyMessage="No historical alerts in selected range."
          testId="alerts-table-history"
        />
      </section>

      {selectedAlert && (
        <AlertDetailView
          alert={selectedAlert}
          onClose={() => setSelectedAlert(null)}
        />
      )}
    </div>
  );
}
