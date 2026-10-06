/**
 * SecureNet — TrafficVerdictCard
 *
 * What the model decided about every flow since the IDS was turned on:
 *  Table 1 — normal vs abnormal (stage 1, Isolation Forest)
 *  Table 2 — which attack the abnormal flows might be (stage 2, XGBoost's guess);
 *            "Benign" there means stage 2 cancelled the alarm
 *  Final verdict — share of normal / abnormal traffic after both stages.
 * Real counts from /api/ids/status only; nothing is shown until flows were scored.
 */

import type { VerdictSummary } from '../../services/idsService';
import { useAuth } from '../../contexts/AuthContext';
import { EmptyState } from '../common/EmptyState';
import { IdsOffNote } from './IdsOffNote';
import styles from './TrafficVerdictCard.module.css';

interface TrafficVerdictCardProps {
  verdicts: VerdictSummary | null | undefined;
  mlLoaded: boolean;
  /** IDS is OFF: no live values on the dashboard */
  idsOff?: boolean;
}

function share(n: number, total: number): string {
  if (total <= 0) return '—';
  const p = (n / total) * 100;
  return `${p >= 99.995 || p === 0 ? p.toFixed(0) : p.toFixed(2)}%`;
}

export function TrafficVerdictCard({ verdicts, mlLoaded, idsOff = false }: TrafficVerdictCardProps) {
  const { isAdmin } = useAuth();
  const title = 'Traffic Verdict';

  if (idsOff) {
    return (
      <div className={styles.card}>
        <h3 className={styles.title}>{title}</h3>
        <IdsOffNote what="verdicts" />
      </div>
    );
  }
  if (!mlLoaded || !verdicts || verdicts.scored === 0) {
    return (
      <div className={styles.card}>
        <h3 className={styles.title}>{title}</h3>
        <EmptyState
          title={mlLoaded ? 'Waiting for traffic' : 'Detection is not set up yet'}
          description={mlLoaded
            ? 'The tables fill in as soon as the first network connections have been checked.'
            : 'Traffic is counted, but nothing can be checked until the detection model is loaded.'}
        />
      </div>
    );
  }

  const { scored, normal, abnormal, guesses, finalNormal, finalAbnormal } = verdicts;
  const anyAbnormal = finalAbnormal > 0;

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <h3 className={styles.title}>{title}</h3>
        <span className={styles.meta}>{scored.toLocaleString()} connections checked since the IDS was turned on</span>
      </div>

      <div className={`${styles.verdict} ${anyAbnormal ? styles.abnormal : styles.normal}`} role="status">
        {anyAbnormal ? 'Abnormal traffic detected' : 'Normal traffic'}
      </div>

      <div className={styles.tables}>
        <table className={styles.table}>
          <caption className={styles.caption}>
            Table 1: Normal or abnormal?
            <span className={styles.stage}>{isAdmin ? 'stage 1 — Isolation Forest' : 'step 1 — is the traffic unusual?'}</span>
          </caption>
          <thead>
            <tr><th scope="col">Verdict</th><th scope="col" className={styles.num}>Flows</th><th scope="col" className={styles.num}>%</th></tr>
          </thead>
          <tbody>
            <tr>
              <td>Normal traffic</td>
              <td className={styles.num}>{normal.toLocaleString()}</td>
              <td className={styles.num}>{share(normal, scored)}</td>
            </tr>
            <tr className={abnormal > 0 ? styles.rowAlert : undefined}>
              <td>Abnormal traffic (flagged)</td>
              <td className={styles.num}>{abnormal.toLocaleString()}</td>
              <td className={styles.num}>{share(abnormal, scored)}</td>
            </tr>
          </tbody>
        </table>

        <table className={styles.table}>
          <caption className={styles.caption}>
            Table 2: Which attack might it be?
            <span className={styles.stage}>
              {isAdmin ? 'stage 2 — XGBoost' : 'step 2 — the model’s guess'}, for all {abnormal.toLocaleString()} flagged flows
            </span>
          </caption>
          <thead>
            <tr><th scope="col">Possible attack</th><th scope="col" className={styles.num}>Flows</th><th scope="col" className={styles.num}>%</th></tr>
          </thead>
          <tbody>
            {guesses.length === 0 ? (
              <tr><td colSpan={3} className={styles.none}>No flagged flows — nothing to guess.</td></tr>
            ) : guesses.map((g) => (
              <tr key={g.label} className={g.cancelled ? undefined : styles.rowAlert}>
                <td>{g.cancelled ? 'Benign (stage 2 cancelled the alarm)' : g.label}</td>
                <td className={styles.num}>{g.flows.toLocaleString()}</td>
                <td className={styles.num}>{share(g.flows, abnormal)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className={styles.final}>
        <strong>Final verdict:</strong> {share(finalNormal, scored)} normal traffic
        {' · '}{share(finalAbnormal, scored)} abnormal traffic
        {anyAbnormal && ` (${finalAbnormal.toLocaleString()} flow${finalAbnormal === 1 ? '' : 's'})`}.
      </p>
      <p className={styles.note}>
        The attack names are the model’s best guess of what the abnormal traffic might be — not a certainty.
      </p>
    </div>
  );
}
