/**
 * SecureNet — AuthLayout
 *
 * Shared two-column layout used by Login, Signup, and OTP pages.
 * Left panel: branding + tagline.
 * Right panel: the form content (children).
 */

import type { ReactNode } from 'react';
import { ShieldCheck } from 'lucide-react';
import styles from './AuthLayout.module.css';

interface AuthLayoutProps {
  children: ReactNode;
}

export function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <div className={styles.root}>
      {/* ── Left branding panel ── */}
      <aside className={styles.brand} aria-hidden="true">
        <div className={styles.brandInner}>
          <div className={styles.logo}>
            <ShieldCheck size={36} strokeWidth={1.75} />
            <span className={styles.logoText}>SecureNet</span>
          </div>
          <p className={styles.tagline}>
            Network security monitoring and behavioural intrusion detection.
          </p>
          <ul className={styles.featureList}>
            <li>Two-stage ML detection pipeline</li>
            <li>Real-time anomaly scoring</li>
            <li>Attack classification &amp; explanation</li>
            <li>Automated threat response</li>
          </ul>
        </div>
        <p className={styles.brandFooter}>
          University Final Year Project — {new Date().getFullYear()}
        </p>
      </aside>

      {/* ── Right form panel ── */}
      <main className={styles.formPanel}>
        <div className={styles.formInner}>{children}</div>
      </main>
    </div>
  );
}
