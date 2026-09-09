/**
 * SecureNet — HostStatusCard
 *
 * Displays monitored host resource metrics: CPU, Memory, Network, Uptime.
 * All values come from the backend. Shows "Not available" until connected.
 */

import { Cpu, MemoryStick, Network, Clock, Monitor } from 'lucide-react';
import type { HostStatus } from '../../types/security.types';
import { formatPercent, formatBytes, formatDuration } from '../../utils/format';
import { LoadingState } from '../common/LoadingState';
import { ErrorState } from '../common/ErrorState';
import styles from './HostStatusCard.module.css';

interface HostStatusCardProps {
  data: HostStatus | null;
  isLoading: boolean;
  isError: boolean;
  onRetry?: () => void;
}

interface MetricRowProps {
  icon: React.ReactNode;
  label: string;
  value: string | null | undefined;
}

function MetricRow({ icon, label, value }: MetricRowProps) {
  return (
    <div className={styles.metricRow}>
      <span className={styles.metricIcon} aria-hidden="true">{icon}</span>
      <span className={styles.metricLabel}>{label}</span>
      <span className={styles.metricValue}>
        {value ?? <span className={styles.na}>Not available</span>}
      </span>
    </div>
  );
}

function UsageBar({ value }: { value: number | null }) {
  if (value === null) return null;
  const pct = Math.min(100, Math.max(0, value));
  const color =
    pct >= 90 ? 'var(--color-severity-high)'
    : pct >= 70 ? 'var(--color-severity-medium)'
    : 'var(--color-severity-low)';
  return (
    <div className={styles.usageBarTrack} role="img" aria-label={`${pct.toFixed(0)}%`}>
      <div
        className={styles.usageBarFill}
        style={{ width: `${pct}%`, backgroundColor: color }}
      />
    </div>
  );
}

export function HostStatusCard({
  data,
  isLoading,
  isError,
  onRetry,
}: HostStatusCardProps) {
  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <Monitor size={16} className={styles.headerIcon} aria-hidden="true" />
        <h3 className={styles.title}>Host Status</h3>
        {data?.hostname && (
          <span className={styles.hostname}>{data.hostname}</span>
        )}
      </div>

      {isLoading && <LoadingState message="Loading host status…" />}

      {isError && !isLoading && (
        <ErrorState
          title="Unable to load host status"
          message="Backend not connected."
          onRetry={onRetry}
        />
      )}

      {!isLoading && !isError && (
        <div className={styles.metrics}>
          {/* CPU */}
          <div className={styles.metricBlock}>
            <MetricRow
              icon={<Cpu size={14} />}
              label="CPU"
              value={data?.cpuPercent !== null && data?.cpuPercent !== undefined
                ? `${data.cpuPercent.toFixed(1)}%`
                : null}
            />
            <UsageBar value={data?.cpuPercent ?? null} />
          </div>

          {/* Memory */}
          <div className={styles.metricBlock}>
            <MetricRow
              icon={<MemoryStick size={14} />}
              label="Memory"
              value={data?.memoryPercent !== null && data?.memoryPercent !== undefined
                ? formatPercent(data.memoryPercent / 100)
                : null}
            />
            <UsageBar value={data?.memoryPercent ?? null} />
          </div>

          {/* Network */}
          <MetricRow
            icon={<Network size={14} />}
            label="Network"
            value={data?.networkBytesPerSec !== null && data?.networkBytesPerSec !== undefined
              ? `${formatBytes(data.networkBytesPerSec)}/s`
              : null}
          />

          {/* Uptime */}
          <MetricRow
            icon={<Clock size={14} />}
            label="Uptime"
            value={data?.uptime !== null && data?.uptime !== undefined
              ? formatDuration(data.uptime)
              : null}
          />

          {/* OS */}
          {data?.os && (
            <MetricRow
              icon={<Monitor size={14} />}
              label="OS"
              value={data.os}
            />
          )}

          {!data && (
            <p className={styles.noData}>
              Waiting for backend connection.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
