/**
 * SecureNet — AboutCard
 *
 * Static informational card describing the SecureNet system.
 */

import { Shield } from 'lucide-react';
import { Card } from '../common/Card';
import styles from './AboutCard.module.css';

export function AboutCard() {
  return (
    <Card padding="lg">
      <div className={styles.header}>
        <div className={styles.logoMark} aria-hidden="true">
          <Shield size={22} />
        </div>
        <div>
          <h3 className={styles.title}>SecureNet</h3>
          <p className={styles.subtitle}>AI-Powered Network Intrusion Detection System</p>
        </div>
      </div>

      <div className={styles.body}>
        <p className={styles.description}>
          SecureNet is an AI-powered network intrusion detection system that uses a
          two-stage machine-learning pipeline to identify anomalous traffic and classify
          attack types in real time.
        </p>

        <div className={styles.featureList}>
          <div className={styles.feature}>
            <span className={styles.featureDot} aria-hidden="true" />
            <div>
              <strong>Stage 1 — Isolation Forest:</strong> Unsupervised anomaly
              detection across 78 extracted network-flow features.
            </div>
          </div>
          <div className={styles.feature}>
            <span className={styles.featureDot} aria-hidden="true" />
            <div>
              <strong>Stage 2 — XGBoost:</strong> Supervised classification of
              anomalous flows into specific attack categories.
            </div>
          </div>
          <div className={styles.feature}>
            <span className={styles.featureDot} aria-hidden="true" />
            <div>
              <strong>Live monitoring:</strong> WebSocket-powered real-time anomaly
              scoring stream on the dashboard.
            </div>
          </div>
          <div className={styles.feature}>
            <span className={styles.featureDot} aria-hidden="true" />
            <div>
              <strong>Protection mode:</strong> Optional automatic IP blocking for
              high-severity threats.
            </div>
          </div>
        </div>

        <dl className={styles.metaGrid}>
          <div className={styles.metaRow}>
            <dt className={styles.metaLabel}>Version</dt>
            <dd className={styles.metaValue}>1.0.0</dd>
          </div>
          <div className={styles.metaRow}>
            <dt className={styles.metaLabel}>Pipeline</dt>
            <dd className={styles.metaValue}>Isolation Forest + XGBoost</dd>
          </div>
          <div className={styles.metaRow}>
            <dt className={styles.metaLabel}>Features</dt>
            <dd className={styles.metaValue}>78-feature network flow model</dd>
          </div>
          <div className={styles.metaRow}>
            <dt className={styles.metaLabel}>Protocols</dt>
            <dd className={styles.metaValue}>TCP, UDP, ICMP</dd>
          </div>
        </dl>
      </div>
    </Card>
  );
}
