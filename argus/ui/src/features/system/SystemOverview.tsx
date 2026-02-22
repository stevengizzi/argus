/**
 * System overview card showing overall health status and key metadata.
 *
 * Displays: status dot, uptime, mode (paper/live), broker/data sources,
 * and key timestamps (last heartbeat, last trade, last data received).
 */

import { Card } from '../../components/Card';
import { StatusDot } from '../../components/StatusDot';
import { Badge } from '../../components/Badge';
import { LoadingState } from '../../components/LoadingState';
import { useHealth } from '../../hooks/useHealth';
import { formatDuration, formatTime } from '../../utils/format';

type StatusLevel = 'healthy' | 'degraded' | 'error' | 'unknown';

function mapOverallStatus(status: string): StatusLevel {
  const normalized = status.toLowerCase();
  if (normalized === 'healthy' || normalized === 'ok') return 'healthy';
  if (normalized === 'degraded' || normalized === 'warning') return 'degraded';
  if (normalized === 'error' || normalized === 'unhealthy') return 'error';
  return 'unknown';
}

function getStatusText(status: StatusLevel): string {
  switch (status) {
    case 'healthy':
      return 'Healthy';
    case 'degraded':
      return 'Degraded';
    case 'error':
      return 'Error';
    default:
      return 'Unknown';
  }
}

function getBorderClass(status: StatusLevel): string {
  if (status === 'error') return 'border-argus-loss';
  if (status === 'degraded') return 'border-argus-warning';
  return '';
}

interface MetaRowProps {
  label: string;
  value: string | null;
  dim?: boolean;
}

function MetaRow({ label, value, dim = false }: MetaRowProps) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-argus-text-dim">{label}</span>
      <span className={`tabular-nums ${dim ? 'text-argus-text-dim' : 'text-argus-text'}`}>
        {value ?? '—'}
      </span>
    </div>
  );
}

export function SystemOverview() {
  const { data, isLoading, error } = useHealth();

  if (isLoading) {
    return (
      <Card>
        <LoadingState message="Loading system status..." />
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card>
        <div className="text-argus-loss text-sm">Failed to load system status</div>
      </Card>
    );
  }

  const overallStatus = mapOverallStatus(data.status);
  const borderClass = getBorderClass(overallStatus);
  const statusText = getStatusText(overallStatus);

  // Format timestamps - only show time if available
  const lastHeartbeat = data.last_heartbeat ? formatTime(data.last_heartbeat) : null;
  const lastTrade = data.last_trade ? formatTime(data.last_trade) : null;
  const lastDataReceived = data.last_data_received ? formatTime(data.last_data_received) : null;

  return (
    <Card className={borderClass}>
      {/* Status header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <StatusDot
            status={overallStatus}
            pulse={overallStatus === 'healthy'}
            size="md"
          />
          <div>
            <div className="flex items-center gap-2">
              <span className="text-lg font-semibold text-argus-text">
                Status: {statusText}
              </span>
            </div>
          </div>
        </div>
        {data.paper_mode && (
          <Badge variant="warning">PAPER</Badge>
        )}
      </div>

      {/* Key metadata grid */}
      <div className="space-y-2">
        <MetaRow
          label="Uptime"
          value={formatDuration(data.uptime_seconds)}
        />
        <MetaRow
          label="Mode"
          value={data.paper_mode ? 'Paper Trading' : 'Live Trading'}
        />

        {/* Divider */}
        <div className="border-t border-argus-border my-3" />

        {/* Sources */}
        <div className="text-xs uppercase tracking-wider text-argus-text-dim mb-2">
          Sources
        </div>
        <MetaRow label="Broker" value="SimulatedBroker" />
        <MetaRow label="Data" value="Mock Data" />

        {/* Divider */}
        <div className="border-t border-argus-border my-3" />

        {/* Timestamps */}
        <div className="text-xs uppercase tracking-wider text-argus-text-dim mb-2">
          Timestamps (ET)
        </div>
        <MetaRow
          label="Last Heartbeat"
          value={lastHeartbeat}
          dim={!lastHeartbeat}
        />
        <MetaRow
          label="Last Trade"
          value={lastTrade}
          dim={!lastTrade}
        />
        <MetaRow
          label="Last Data"
          value={lastDataReceived}
          dim={!lastDataReceived}
        />
      </div>
    </Card>
  );
}
