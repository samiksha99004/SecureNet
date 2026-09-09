/**
 * SecureNet — SupportInfoCard
 *
 * Shows documentation links, quick-start guidance, and
 * backend integration status information.
 */

import { BookOpen, GitBranch, Wifi } from 'lucide-react';
import { Card } from '../common/Card';
import styles from './SupportInfoCard.module.css';

export function SupportInfoCard() {
  const backendUrl = import.meta.env.VITE_API_BASE_URL ?? '';
  const wsUrl = import.meta.env.VITE_WS_URL ?? '';
  const backendConfigured = backendUrl !== '';
  const wsConfigured = wsUrl !== '';

  return (
    <Card padding="lg">
      <h3 className={styles.heading}>Support &amp; Documentation</h3>

      <div className={styles.sections}>
        {/* Getting started */}
        <section>
          <div className={styles.sectionHeader}>
            <BookOpen size={15} className={styles.sectionIcon} aria-hidden="true" />
            <h4 className={styles.sectionTitle}>Getting Started</h4>
          </div>
          <ul className={styles.list}>
            <li>Configure <code className={styles.code}>VITE_API_BASE_URL</code> in <code className={styles.code}>.env.local</code> once the backend is ready.</li>
            <li>Configure <code className={styles.code}>VITE_WS_URL</code> for live anomaly streaming on the dashboard.</li>
            <li>Use the Settings page to tune detection sensitivity, protection mode, and notification preferences.</li>
            <li>Add trusted IPs or CIDR ranges to the Whitelist to exclude them from detection.</li>
          </ul>
        </section>

        {/* Backend integration status */}
        <section>
          <div className={styles.sectionHeader}>
            <GitBranch size={15} className={styles.sectionIcon} aria-hidden="true" />
            <h4 className={styles.sectionTitle}>Backend Integration Status</h4>
          </div>
          <div className={styles.statusList}>
            <div className={styles.statusRow}>
              <span className={backendConfigured ? styles.dotGreen : styles.dotAmber} aria-hidden="true" />
              <span className={styles.statusLabel}>REST API</span>
              <span className={styles.statusValue}>
                {backendConfigured ? backendUrl : 'Not configured — set VITE_API_BASE_URL'}
              </span>
            </div>
            <div className={styles.statusRow}>
              <span className={wsConfigured ? styles.dotGreen : styles.dotAmber} aria-hidden="true" />
              <span className={styles.statusLabel}>WebSocket</span>
              <span className={styles.statusValue}>
                {wsConfigured ? wsUrl : 'Not configured — set VITE_WS_URL'}
              </span>
            </div>
          </div>
        </section>

        {/* Live monitoring */}
        <section>
          <div className={styles.sectionHeader}>
            <Wifi size={15} className={styles.sectionIcon} aria-hidden="true" />
            <h4 className={styles.sectionTitle}>Live Monitoring</h4>
          </div>
          <p className={styles.prose}>
            The Dashboard streams real-time anomaly scores via WebSocket. When the
            WebSocket URL is not configured, the chart shows a "Not connected" state.
            Connection status is visible in the top bar.
          </p>
        </section>
      </div>
    </Card>
  );
}
