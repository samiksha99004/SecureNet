/**
 * SecureNet — Dashboard Page
 *
 * Primary monitoring screen.
 *
 * Layout:
 *   Row 1: IDS Control Widget (ON/OFF, monitoring status, incident details)
 *   Row 2: 5 KPI cards
 *   Row 3: Host Status | Security Summary | Protocol Distribution
 *   Row 4: Live Anomaly Chart (full width)
 *   Row 5: Detection Reason | Top Sources
 *   Row 6: Recent Events table (full width)
 *
 * All data fetched from services — no hardcoded values.
 * Components show loading/empty/error states appropriately.
 */

import { useCallback, useEffect, useRef, Suspense, lazy } from 'react';
import {
  Activity,
  AlertTriangle,
  ShieldAlert,
  BarChart2,
} from 'lucide-react';
import { MainLayout } from '../components/layout/MainLayout';
import { IDSControlWidget } from '../components/dashboard/IDSControlWidget';
import { KPICard } from '../components/common/KPICard';
import { HostStatusCard } from '../components/dashboard/HostStatusCard';
import { SecuritySummaryCard } from '../components/dashboard/SecuritySummaryCard';
import { LoadingState } from '../components/common/LoadingState';
import { DetectionReasonCard } from '../components/dashboard/DetectionReasonCard';
import { ProtocolDistributionCard } from '../components/dashboard/ProtocolDistributionCard';
import { TopSourcesCard } from '../components/dashboard/TopSourcesCard';
import { RecentEventsTable } from '../components/dashboard/RecentEventsTable';
import { useAsyncData } from '../hooks/useAsyncData';
import { useWebSocketMessage } from '../hooks/useLiveMonitoring';
import {
  getDashboardSummary,
  getHostStatus,
  getProtocolDistribution,
  getTopSources,
} from '../services/dashboardService';
import { getIDSStatus } from '../services/idsService';
import { getDetectionSettings } from '../services/settingsService';
import { formatScore, formatNumber } from '../utils/format';
import styles from './DashboardPage.module.css';

const LiveAnomalyChart = lazy(() =>
  import('../components/dashboard/LiveAnomalyChart').then((m) => ({ default: m.LiveAnomalyChart }))
);

const POLL_INTERVAL_MS = 15_000;

export function DashboardPage() {
  // ── Data fetching ───────────────────────────────────────────────────────────
  const summary = useAsyncData(useCallback(() => getDashboardSummary(), []));
  const host = useAsyncData(useCallback(() => getHostStatus(), []));
  const protocol = useAsyncData(useCallback(() => getProtocolDistribution(), []));
  const sources = useAsyncData(useCallback(() => getTopSources(5), []));
  const idsStatus = useAsyncData(useCallback(() => getIDSStatus(), []));
  const detection = useAsyncData(useCallback(() => getDetectionSettings(), []));

  // Latest "refresh everything" callback, kept in a ref for timers / socket events
  const refetchAll = useRef<() => void>(() => {});
  useEffect(() => {
    refetchAll.current = () => {
      void summary.refetch();
      void host.refetch();
      void protocol.refetch();
      void sources.refetch();
      void idsStatus.refetch();
    };
  });

  // Periodic refresh (keeps host metrics and counters current)
  useEffect(() => {
    const interval = setInterval(() => refetchAll.current(), POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, []);

  // Refresh immediately when the backend reports a new alert / status change
  // (debounced so an attack burst does not flood the API).
  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const scheduleRefresh = useCallback(() => {
    if (debounceTimer.current) return;
    debounceTimer.current = setTimeout(() => {
      debounceTimer.current = null;
      refetchAll.current();
    }, 1000);
  }, []);
  useEffect(() => () => {
    if (debounceTimer.current) clearTimeout(debounceTimer.current);
  }, []);
  useWebSocketMessage('alert', scheduleRefresh);
  const refetchIds = idsStatus.refetch;
  useWebSocketMessage('system_status', useCallback(() => void refetchIds(), [refetchIds]));

  const s = summary.data;

  // The highest-scoring recent event drives the Detection Reason card.
  const topRecentEvent = s?.recentEvents.length
    ? s.recentEvents.reduce((best, e) => (e.anomalyScore > best.anomalyScore ? e : best))
    : null;

  // Latest unresolved medium/high event for the IDS widget
  const latestAbnormalEvent =
    s?.recentEvents.find(
      (e) => e.state === 'active' && (e.severity === 'high' || e.severity === 'medium')
    ) ?? null;

  return (
    <MainLayout title="Dashboard">
      <div className={styles.page}>

        {/* ── IDS Control Widget ──────────────────────────────────────────── */}
        <IDSControlWidget
          idsStatus={idsStatus.data}
          latestEvent={latestAbnormalEvent}
          isLoading={idsStatus.isLoading}
          onStatusChange={() => refetchAll.current()}
        />

        {/* ── Row 1: KPI Cards ─────────────────────────────────────────────── */}
        <section
          className={styles.kpiGrid}
          aria-label="Key security metrics"
        >
          <KPICard
            title="Active Flows"
            value={s ? formatNumber(s.activeFlows) : null}
            icon={<Activity size={16} />}
            accent="info"
            isLoading={summary.isLoading}
          />
          <KPICard
            title="Anomalies — Last 1 Hour"
            value={s ? formatNumber(s.anomaliesLastHour) : null}
            icon={<AlertTriangle size={16} />}
            accent="medium"
            isLoading={summary.isLoading}
          />
          <KPICard
            title="High Severity"
            value={s ? formatNumber(s.highSeverityCount) : null}
            icon={<ShieldAlert size={16} />}
            accent="high"
            isLoading={summary.isLoading}
          />
          <KPICard
            title="Avg Anomaly Score"
            value={s ? formatScore(s.averageAnomalyScore) : null}
            icon={<BarChart2 size={16} />}
            accent="default"
            isLoading={summary.isLoading}
          />
        </section>

        {/* ── Row 2: Status cards ──────────────────────────────────────────── */}
        <section className={styles.statusGrid} aria-label="System status">
          <HostStatusCard
            data={host.data}
            isLoading={host.isLoading}
            isError={host.isError}
            onRetry={host.refetch}
          />
          <SecuritySummaryCard
            data={summary.data}
            isLoading={summary.isLoading}
            isError={summary.isError}
            onRetry={summary.refetch}
          />
          <ProtocolDistributionCard
            data={protocol.data}
            isLoading={protocol.isLoading}
            isError={protocol.isError}
            onRetry={protocol.refetch}
          />
        </section>

        {/* ── Row 3: Live chart ────────────────────────────────────────────── */}
        <section aria-label="Live anomaly monitoring">
          <Suspense fallback={<LoadingState message="Loading live chart..." />}>
            <LiveAnomalyChart threshold={detection.data?.anomalyThreshold ?? 0.5} />
          </Suspense>
        </section>

        {/* ── Row 4: Detection reason + Top sources ────────────────────────── */}
        <section className={styles.detailGrid} aria-label="Detection details">
          <DetectionReasonCard
            reason={topRecentEvent?.detectionReason ?? null}
            features={topRecentEvent?.contributingFeatures ?? []}
            attackType={topRecentEvent?.attackType ?? null}
            confidence={topRecentEvent?.confidence ?? null}
          />
          <TopSourcesCard
            data={sources.data ?? []}
            isLoading={sources.isLoading}
            isError={sources.isError}
            onRetry={sources.refetch}
          />
        </section>

        {/* ── Row 5: Recent events ─────────────────────────────────────────── */}
        <section aria-label="Recent security events">
          <RecentEventsTable
            events={s?.recentEvents ?? []}
            isLoading={summary.isLoading}
          />
        </section>

      </div>
    </MainLayout>
  );
}
