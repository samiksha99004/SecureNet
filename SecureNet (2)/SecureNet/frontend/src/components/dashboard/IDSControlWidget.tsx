/**
 * IDS Control Widget
 *
 * Prominent IDS ON/OFF control with current monitoring status.
 * Shows:
 * - IDS ON/OFF state
 * - Current monitoring status: NORMAL / ABNORMAL / attack type
 * - Latest incident details when abnormal detected
 */

import { useState } from 'react';
import { Power, Shield, AlertTriangle } from 'lucide-react';
import { useToast } from '../common/Toast';
import { startIDS, stopIDS, type IDSStatus } from '../../services/idsService';
import type { SecurityEvent } from '../../types/security.types';
import styles from './IDSControlWidget.module.css';

interface IDSControlWidgetProps {
  idsStatus: IDSStatus | null;
  latestEvent: SecurityEvent | null;
  isLoading: boolean;
  onStatusChange: () => void;
}

export function IDSControlWidget({
  idsStatus,
  latestEvent,
  isLoading,
  onStatusChange,
}: IDSControlWidgetProps) {
  const { showToast } = useToast();
  const [isToggling, setIsToggling] = useState(false);

  const isEnabled = idsStatus?.enabled ?? false;
  const hasAbnormalEvent = latestEvent && latestEvent.severity !== 'low';

  async function handleToggle() {
    setIsToggling(true);
    try {
      if (isEnabled) {
        await stopIDS();
        showToast({ message: 'IDS stopped', variant: 'success' });
      } else {
        await startIDS();
        showToast({ message: 'IDS started — monitoring and protection active', variant: 'success' });
      }
      onStatusChange();
    } catch (err: any) {
      // Check if it's an authentication error
      const isAuthError = err?.status === 401 || err?.code === 'UNAUTHORIZED';
      const message = isAuthError 
        ? 'Session expired — please log in again'
        : `Failed to ${isEnabled ? 'stop' : 'start'} IDS — ${err?.message || 'backend not connected'}`;
      
      showToast({
        message,
        variant: 'error',
      });
      
      // If auth error, redirect to login after a short delay
      if (isAuthError) {
        setTimeout(() => {
          window.location.href = '/login';
        }, 2000);
      }
    } finally {
      setIsToggling(false);
    }
  }

  // Determine monitoring status
  let statusLabel = 'NORMAL';
  let statusIcon = <Shield size={20} />;
  let statusClass = styles.statusNormal;

  if (hasAbnormalEvent) {
    const attackType = latestEvent.attackType;
    if (attackType && attackType !== 'Unknown') {
      statusLabel = attackType.toUpperCase();
    } else {
      statusLabel = 'UNKNOWN ATTACK TYPE';
    }
    statusIcon = <AlertTriangle size={20} />;
    statusClass = styles.statusAbnormal;
  }

  return (
    <div className={styles.widget}>
      {/* IDS Power Control */}
      <div className={styles.powerSection}>
        <div className={styles.powerHeader}>
          <h2 className={styles.title}>Intrusion Detection System</h2>
          <button
            type="button"
            className={`${styles.powerButton} ${isEnabled ? styles.powerOn : styles.powerOff}`}
            onClick={handleToggle}
            disabled={isToggling || isLoading}
            aria-label={isEnabled ? 'Stop IDS' : 'Start IDS'}
          >
            <Power size={20} aria-hidden="true" />
            <span className={styles.powerLabel}>{isEnabled ? 'ON' : 'OFF'}</span>
          </button>
        </div>

        {!isEnabled && (
          <p className={styles.offMessage}>
            Network monitoring, detection, and protection are currently disabled.
          </p>
        )}
      </div>

      {/* Monitoring Status */}
      {isEnabled && (
        <div className={styles.statusSection}>
          <div className={`${styles.statusCard} ${statusClass}`}>
            <div className={styles.statusIcon}>{statusIcon}</div>
            <div className={styles.statusContent}>
              <span className={styles.statusLabel}>Current Status</span>
              <span className={styles.statusValue}>{statusLabel}</span>
            </div>
          </div>

          {/* Latest Incident Details */}
          {hasAbnormalEvent && latestEvent && (
            <div className={styles.incidentDetails}>
              <h3 className={styles.incidentTitle}>Latest Incident</h3>
              <div className={styles.incidentGrid}>
                <DetailRow label="Severity" value={latestEvent.severity.toUpperCase()} />
                <DetailRow label="Anomaly Score" value={latestEvent.anomalyScore.toFixed(4)} />
                {latestEvent.confidence && (
                  <DetailRow label="Confidence" value={`${(latestEvent.confidence * 100).toFixed(1)}%`} />
                )}
                <DetailRow label="Source IP" value={latestEvent.sourceIp} />
                <DetailRow label="Destination IP" value={latestEvent.destinationIp} />
                <DetailRow label="Protocol" value={latestEvent.protocol} />
                <DetailRow
                  label="Time"
                  value={new Date(latestEvent.timestamp).toLocaleString()}
                />
                {latestEvent.actionTaken && (
                  <DetailRow
                    label="Action"
                    value={latestEvent.actionTaken.toUpperCase()}
                    highlight={latestEvent.actionTaken === 'blocked'}
                  />
                )}
              </div>
              {latestEvent.detectionReason && (
                <div className={styles.reasonBox}>
                  <span className={styles.reasonLabel}>Detection Reason:</span>
                  <p className={styles.reasonText}>{latestEvent.detectionReason}</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Stats */}
      {isEnabled && idsStatus && (
        <div className={styles.statsRow}>
          <Stat label="Packets Processed" value={idsStatus.packetsProcessed.toLocaleString()} />
          <Stat label="Flows Analyzed" value={idsStatus.flowsAnalyzed.toLocaleString()} />
          <Stat label="Anomalies" value={idsStatus.anomaliesDetected.toLocaleString()} />
          <Stat label="Attacks" value={idsStatus.attacksDetected.toLocaleString()} />
        </div>
      )}
    </div>
  );
}

function DetailRow({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div className={styles.detailRow}>
      <span className={styles.detailLabel}>{label}:</span>
      <span className={`${styles.detailValue} ${highlight ? styles.detailHighlight : ''}`}>
        {value}
      </span>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className={styles.stat}>
      <span className={styles.statValue}>{value}</span>
      <span className={styles.statLabel}>{label}</span>
    </div>
  );
}
