/**
 * IDS Control Widget
 *
 * ON / OFF control plus live IDS status:
 *  - power toggle (every signed-in user). ON = capture, detect, alert + email.
 *  - capture + detector state (clearly says when no model is loaded)
 *  - current status: IDS IS OFF while stopped; when running NORMAL TRAFFIC or
 *    ABNORMAL TRAFFIC DETECTED (the attack is only shown as the model's guess)
 *  - live counters from the backend
 */

import { useState } from 'react';
import { Power, Shield, ShieldOff, AlertTriangle, Info } from 'lucide-react';
import { useToast } from '../common/Toast';
import { useAuth } from '../../contexts/AuthContext';
import { useNotifications } from '../../contexts/NotificationContext';
import {
  DETECTOR_LABELS,
  startIDS,
  stopIDS,
  type IDSStatus,
} from '../../services/idsService';
import { requestDesktopNotifications } from '../../utils/alertChannels';
import { formatTimestamp, formatDuration } from '../../utils/format';
import type { SecurityEvent } from '../../types/security.types';
import { possibleAttack } from '../../utils/verdict';
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
  const { isAdmin } = useAuth();
  const { prefs } = useNotifications();
  const [isBusy, setIsBusy] = useState(false);

  const isEnabled = idsStatus?.enabled ?? false;
  const hasAbnormalEvent = !!latestEvent && latestEvent.state === 'active';

  async function run(action: () => Promise<unknown>, success: string) {
    setIsBusy(true);
    try {
      await action();
      showToast({ message: success, variant: 'success' });
      onStatusChange();
    } catch (err) {
      showToast({
        message: err instanceof Error && err.message ? err.message : 'The IDS request failed.',
        variant: 'error',
      });
    } finally {
      setIsBusy(false);
    }
  }

  function handleToggle() {
    if (isEnabled) {
      void run(stopIDS, 'IDS stopped');
    } else {
      if (prefs.desktop) void requestDesktopNotifications();   // only asks the browser once
      void run(() => startIDS('monitor'), 'IDS started');
    }
  }

  // "Normal" is only claimed while the IDS is actually watching
  const isOff = !isEnabled;
  const statusLabel = !idsStatus
    ? (isLoading ? 'CHECKING…' : 'STATUS UNKNOWN')
    : isOff
      ? 'IDS IS OFF'
      : hasAbnormalEvent
        ? 'ABNORMAL TRAFFIC DETECTED'
        : 'NORMAL TRAFFIC';
  const cardStyle = isOff ? styles.statusOff : hasAbnormalEvent ? styles.statusAbnormal : styles.statusNormal;

  return (
    <div className={styles.widget}>
      {/* ── Power ─────────────────────────────────────────────────────── */}
      <div className={styles.powerSection}>
        <div className={styles.powerHeader}>
          <div>
            <h2 className={styles.title}>Intrusion Detection System</h2>
            <p className={styles.subtitle}>
              {isEnabled
                ? 'Running' + (idsStatus?.uptimeSeconds ? ` · up ${formatDuration(idsStatus.uptimeSeconds)}` : '')
                : 'Stopped'}
            </p>
          </div>

          <div className={styles.controls}>
            <button
              type="button"
              className={`${styles.powerButton} ${isEnabled ? styles.powerOn : styles.powerOff}`}
              onClick={handleToggle}
              disabled={isBusy || isLoading}
              aria-label={isEnabled ? 'Stop IDS' : 'Start IDS'}
            >
              <Power size={18} aria-hidden="true" />
              <span className={styles.powerLabel}>{isEnabled ? 'ON' : 'OFF'}</span>
            </button>
          </div>
        </div>

        {idsStatus?.captureError && (
          <p className={`${styles.notice} ${styles.noticeError}`} role="alert">
            <AlertTriangle size={14} aria-hidden="true" /> {idsStatus.captureError}
          </p>
        )}
        {idsStatus && !idsStatus.mlLoaded && (
          <p className={styles.notice}>
            <Info size={14} aria-hidden="true" />{' '}
            {isAdmin
              ? 'No detection model is loaded — the IDS captures and counts traffic but does not score it. Load Isolation Forest and/or XGBoost from Settings → Model.'
              : 'Attack detection is not set up yet — your SecureNet admin needs to finish the setup. Traffic is still counted while the IDS is on.'}
          </p>
        )}
      </div>

      {/* ── Current status ────────────────────────────────────────────────── */}
      <div className={styles.statusSection}>
        <div className={`${styles.statusCard} ${cardStyle}`}>
          <div className={styles.statusIcon}>
            {isOff ? <ShieldOff size={22} /> : hasAbnormalEvent ? <AlertTriangle size={22} /> : <Shield size={22} />}
          </div>
          <div className={styles.statusContent}>
            <span className={styles.statusLabel}>Current Status</span>
            <span className={styles.statusValue}>{statusLabel}</span>
            {idsStatus && isOff && (
              <span className={styles.statusHint}>Your network is not being watched. Press ON to start monitoring.</span>
            )}
            {!isOff && hasAbnormalEvent && latestEvent && (
              <span className={styles.statusHint}>
                Possible attack: {possibleAttack(latestEvent)} — the model’s best guess, see the tables below.
              </span>
            )}
          </div>
          <div className={styles.detectorInfo}>
            <span className={styles.statusLabel}>{isAdmin ? 'Detector' : 'Detection'}</span>
            <span className={styles.detectorValue}>
              {isAdmin
                ? DETECTOR_LABELS[idsStatus?.detector ?? 'none'] ?? idsStatus?.detector
                : idsStatus?.mlLoaded ? 'Active' : 'Not set up yet'}
            </span>
          </div>
        </div>

        {!isOff && hasAbnormalEvent && latestEvent && (
          <div className={styles.incidentDetails}>
            <h3 className={styles.incidentTitle}>Latest Unresolved Incident</h3>
            <div className={styles.incidentGrid}>
              <DetailRow label="Verdict" value="Abnormal traffic" highlight />
              <DetailRow label="Possible attack" value={possibleAttack(latestEvent)} />
              <DetailRow label="Severity" value={latestEvent.severity.toUpperCase()} />
              <DetailRow label="Anomaly Score" value={latestEvent.anomalyScore.toFixed(4)} />
              <DetailRow label="Source" value={`${latestEvent.sourceIp}:${latestEvent.sourcePort}`} />
              <DetailRow label="Destination" value={`${latestEvent.destinationIp}:${latestEvent.destinationPort}`} />
              <DetailRow label="Protocol" value={latestEvent.protocol} />
              <DetailRow label="Time" value={formatTimestamp(latestEvent.timestamp)} />
              <DetailRow
                label="Action"
                value={latestEvent.actionTaken.toUpperCase()}
                highlight={latestEvent.actionTaken === 'blocked'}
              />
            </div>
            {latestEvent.detectionReason && (
              <div className={styles.reasonBox}>
                <span className={styles.reasonLabel}>Detection Reason</span>
                <p className={styles.reasonText}>{latestEvent.detectionReason}</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Live counters (only while the IDS runs) ─────────────────────────── */}
      {idsStatus && !isOff && (
        <div className={styles.statsRow}>
          <Stat label="Packets" value={idsStatus.packetsProcessed} />
          <Stat label="Flows Analyzed" value={idsStatus.flowsAnalyzed} />
          <Stat label="Active Flows" value={idsStatus.activeFlows} />
          <Stat label="Normal Traffic" value={idsStatus.verdicts?.finalNormal ?? 0} />
          <Stat label="Abnormal Traffic" value={idsStatus.verdicts?.finalAbnormal ?? idsStatus.anomaliesDetected} />
        </div>
      )}
    </div>
  );
}

function DetailRow({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className={styles.detailRow}>
      <span className={styles.detailLabel}>{label}</span>
      <span className={`${styles.detailValue} ${highlight ? styles.detailHighlight : ''}`}>{value}</span>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className={styles.stat}>
      <span className={styles.statValue}>{value.toLocaleString()}</span>
      <span className={styles.statLabel}>{label}</span>
    </div>
  );
}
