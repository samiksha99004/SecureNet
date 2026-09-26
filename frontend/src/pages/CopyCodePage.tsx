/**
 * SecureNet — Copy code page (/code#123456)
 *
 * Opened by the "Copy code" button in a verification-code email. Copies the
 * code to the clipboard and fills it into the SecureNet tab that asked for it
 * (utils/codeHandoff). The code travels in the #fragment, so it never reaches
 * a server. Public page: works before signing in.
 */

import { useEffect, useState } from 'react';
import { Check, Copy, ShieldCheck } from 'lucide-react';
import { handOffCode } from '../utils/codeHandoff';
import styles from './CopyCodePage.module.css';

function codeFromHash(): string | null {
  const value = window.location.hash.replace(/^#/, '').trim();
  return /^\d{6}$/.test(value) ? value : null;
}

async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    // older browsers / no permission: select-and-copy fallback
    try {
      const area = document.createElement('textarea');
      area.value = text;
      area.setAttribute('readonly', '');
      area.style.position = 'fixed';
      area.style.opacity = '0';
      document.body.appendChild(area);
      area.select();
      const ok = document.execCommand('copy');
      area.remove();
      return ok;
    } catch {
      return false;
    }
  }
}

export function CopyCodePage() {
  const [code] = useState(codeFromHash);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!code) return;
    handOffCode(code);                       // fill it into the waiting SecureNet tab
    void copyText(code).then(setCopied);     // and put it on the clipboard
  }, [code]);

  async function copyAgain() {
    if (code) setCopied(await copyText(code));
  }

  return (
    <main className={styles.page}>
      <div className={styles.card}>
        <div className={styles.brand}>
          <ShieldCheck size={22} aria-hidden="true" /> SecureNet
        </div>

        {!code ? (
          <>
            <h1 className={styles.title}>No code in this link</h1>
            <p className={styles.text}>Open the “Copy code” button from your SecureNet email again, or type the code shown in the email.</p>
          </>
        ) : (
          <>
            <h1 className={styles.title}>Your verification code</h1>
            <div className={styles.digits} aria-label={`Code ${code.split('').join(' ')}`}>
              {code.split('').map((digit, i) => (
                <span key={i} className={styles.digit}>{digit}</span>
              ))}
            </div>
            <button type="button" className={styles.copyButton} onClick={() => void copyAgain()}>
              {copied ? <Check size={18} aria-hidden="true" /> : <Copy size={18} aria-hidden="true" />}
              {copied ? 'Copied' : 'Copy code'}
            </button>
            <p className={styles.status} role="status">
              {copied ? 'The code is copied. ' : ''}
              It has also been filled in on your SecureNet page — switch back to that tab and continue.
              You can close this tab.
            </p>
          </>
        )}
      </div>
    </main>
  );
}
