/**
 * IDS Application — Dashboard Page
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

import { useCallback, useState, useEffect } from 'react';
import {
  Activity,
  AlertTriangle,
  ShieldAlert,
  Ban,
  BarChart2,
} from 'lucide-react';
import { MainLayout } from '../components/layout/MainLayout';
import { IDSControlWidget } from '../components/dashboard/IDSControlWidget';
import { KPICard } from '../components/common/KPICard';
import { HostStatusCard } from '../components/dashboard/HostStatusCard';
import { SecuritySummaryCard } from '../components/dashboard/SecuritySummaryCard';
import { LiveAnomalyChart } from '../components/dashboard/LiveAnomalyChart';
import { DetectionReasonCard } from '../components/dashboard/DetectionReasonCard';
import { ProtocolDistributionCard } from '../components/dashboard/ProtocolDistributionCard';
import { TopSourcesCard } from '../components/dashboard/TopSourcesCard';
import { RecentEventsTable } from '../components/dashboard/RecentEventsTable';
import { useAsyncData } from '../hooks/useAsyncData';
import {
  getDashboardSummary,
  getHostStatus,
  getProtocolDistribution,
  getTopSources,
} from '../services/dashboardService';
import { getIDSStatus } from '../services/idsService';
import { formatScore, formatNumber } from '../utils/format';
import styles from './DashboardPage.module.css';

export function DashboardPage() {
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  // ── Data fetching ───────────────────────────────────────────────────────────
  const summary = useAsyncData(useCallback(() => getDashboardSummary(), [refreshTrigger]));
  const host = useAsyncData(useCallback(() => getHostStatus(), [refreshTrigger]));
  const protocol = useAsyncData(useCallback(() => getProtocolDistribution(), [refreshTrigger]));
  const sources = useAsyncData(useCallback(() => getTopSources(5), [refreshTrigger]));
  const idsStatus = useAsyncData(useCallback(() => getIDSStatus(), [refreshTrigger]));

  // Refresh IDS status periodically when enabled
  useEffect(() => {
    if (idsStatus.data?.enabled) {
      const interval = setInterval(() => {
        void idsStatus.refetch();
      }, 5000); // Poll every 5 seconds
      return () => clearInterval(interval);
    }
  }, [idsStatus.data?.enabled, idsStatus]);

  const s = summary.data;

  // Wire DetectionReasonCard to the highest-scoring event in the recent-events
  // list that the backend already returns in the dashboard summary.
  // This is real data — no values are fabricated.
  const topRecentEvent = s?.recentEvents.length
    ? s.recentEvents.reduce((best, e) =>
        e.anomalyScore > best.anomalyScore ? e : best
      )
    : null;

  // Get latest abnormal event for IDS widget
  const latestAbnormalEvent = s?.recentEvents.find(
    (e) => e.severity === 'high' || e.severity === 'medium'
  ) ?? null;

  function handleIDSStatusChange() {
    setRefreshTrigger((prev) => prev + 1);
  }

  return (
    <MainLayout title="Dashboard">
      <div className={styles.page}>

        {/* ── IDS Control Widget ──────────────────────────────────────────── */}
        <IDSControlWidget
          idsStatus={idsStatus.data}
          latestEvent={latestAbnormalEvent}
          isLoading={idsStatus.isLoading}
          onStatusChange={handleIDSStatusChange}
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
            title="Blocked"
            value={s ? formatNumber(s.blockedCount) : null}
            icon={<Ban size={16} />}
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
          <LiveAnomalyChart />
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
