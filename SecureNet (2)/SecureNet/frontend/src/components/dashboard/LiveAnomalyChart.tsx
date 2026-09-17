/**
 * SecureNet — LiveAnomalyChart
 *
 * Real-time anomaly score line chart powered by Recharts.
 * Data comes exclusively from the WebSocket feed via useLiveMonitoring().
 *
 * States:
 *  - Idle / connecting / reconnecting: spinner + status message
 *  - Connected but no data yet: "Waiting for data…"
 *  - Connected with data: renders live chart
 *  - Disconnected / error: "Live monitoring unavailable"
 *
 * No fake data points are ever generated.
 */

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { useLiveMonitoring } from '../../hooks/useLiveMonitoring';
import { StatusBadge } from '../common/StatusBadge';
import { Spinner } from '../common/LoadingState';
import type { LiveChartPoint } from '../../types/security.types';
import styles from './LiveAnomalyChart.module.css';

// Anomaly threshold reference line (0.5 is a typical default)
const THRESHOLD_REFERENCE = 0.5;

interface TooltipEntry {
  value?: number;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: TooltipEntry[];
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;
  const score = payload[0]?.value;
  return (
    <div className={styles.tooltip}>
      <p className={styles.tooltipTime}>{label}</p>
      <p className={styles.tooltipScore}>
        Score: <span className={styles.tooltipValue}>{score?.toFixed(4)}</span>
      </p>
    </div>
  );
}

function scoreToColor(score: number): string {
  if (score >= 0.7) return 'var(--color-severity-high)';
  if (score >= 0.5) return 'var(--color-severity-medium)';
  return 'var(--color-severity-low)';
}

// Derive a single stroke colour from the latest point
function getLineColor(data: LiveChartPoint[]): string {
  if (!data.length) return 'var(--color-peach-accent)';
  const last = data[data.length - 1];
  return scoreToColor(last.score);
}

export function LiveAnomalyChart() {
  const { status, chartData, lastScore, isConnecting } = useLiveMonitoring();

  const isUnavailable =
    status === 'disconnected' || status === 'error';
  const isWaiting =
    status === 'idle' || isConnecting;
  const isConnected = status === 'connected';

  return (
    <div className={styles.card}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <h3 className={styles.title}>Live Anomaly Score</h3>
          {lastScore !== null && isConnected && (
            <span
              className={styles.liveScore}
              style={{ color: scoreToColor(lastScore) }}
              aria-label={`Current anomaly score: ${lastScore.toFixed(4)}`}
            >
              {lastScore.toFixed(4)}
            </span>
          )}
        </div>
        <StatusBadge
          status={
            isConnected
              ? 'connected'
              : isConnecting
              ? 'connecting'
              : isUnavailable
              ? 'disconnected'
              : 'connecting'
          }
        />
      </div>

      {/* Chart area */}
      <div className={styles.chartArea} role="img" aria-label="Live anomaly score chart">
        {/* Unavailable */}
        {isUnavailable && (
          <div className={styles.overlayMessage}>
            <p className={styles.unavailableText}>Live monitoring unavailable</p>
            <p className={styles.unavailableSubtext}>
              Connect the backend WebSocket to enable real-time monitoring.
            </p>
          </div>
        )}

        {/* Waiting / connecting */}
        {isWaiting && !isUnavailable && (
          <div className={styles.overlayMessage}>
            <Spinner size="md" />
            <p className={styles.waitingText}>
              {status === 'idle' ? 'Initialising…' : 'Connecting to live feed…'}
            </p>
          </div>
        )}

        {/* Connected, no data yet */}
        {isConnected && chartData.length === 0 && (
          <div className={styles.overlayMessage}>
            <p className={styles.waitingText}>No anomalies detected yet</p>
            <p className={styles.unavailableSubtext}>
              Turn IDS ON and generate network traffic to see live scores
            </p>
          </div>
        )}

        {/* Chart */}
        {isConnected && chartData.length > 0 && (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={chartData}
              margin={{ top: 8, right: 16, bottom: 4, left: 0 }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="var(--color-border)"
                vertical={false}
              />
              <XAxis
                dataKey="time"
                tick={{ fontFamily: 'var(--font-mono)', fontSize: 11, fill: 'var(--color-text-muted)' }}
                tickLine={false}
                axisLine={false}
                interval="preserveStartEnd"
              />
              <YAxis
                domain={[0, 1]}
                tick={{ fontFamily: 'var(--font-mono)', fontSize: 11, fill: 'var(--color-text-muted)' }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v: number) => v.toFixed(1)}
                width={36}
              />
              <Tooltip content={<CustomTooltip />} />
              <ReferenceLine
                y={THRESHOLD_REFERENCE}
                stroke="var(--color-severity-medium)"
                strokeDasharray="4 2"
                label={{
                  value: 'threshold',
                  position: 'right',
                  fontSize: 10,
                  fill: 'var(--color-text-muted)',
                  fontFamily: 'var(--font-mono)',
                }}
              />
              <Line
                type="monotone"
                dataKey="score"
                stroke={getLineColor(chartData)}
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
