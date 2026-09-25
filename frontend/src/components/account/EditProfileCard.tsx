/**
 * SecureNet — EditProfileCard
 *
 * Every user can change their own name, phone number and email. Each change
 * is confirmed with a 6-digit code sent by email (to the NEW address when the
 * email changes). Nothing changes until the code is entered.
 */

import { useState, type FormEvent } from 'react';
import { Card } from '../common/Card';
import { useToast } from '../common/Toast';
import { useAuth } from '../../contexts/AuthContext';
import * as authService from '../../services/authService';
import type { ProfileChangeRequest, User } from '../../types/auth.types';
import { isValidEmail, isValidOtp, isValidPhone } from '../../utils/validation';
import styles from './ChangePasswordCard.module.css';
import local from './EditProfileCard.module.css';

export function EditProfileCard({ user }: { user: User }) {
  const { completeLogin } = useAuth();
  const { showToast } = useToast();

  const [fullName, setFullName] = useState(user.fullName);
  const [phone, setPhone] = useState(user.phoneNumber ?? '');
  const [email, setEmail] = useState(user.email);
  const [pending, setPending] = useState<{ token: string; message: string } | null>(null);
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const changes: ProfileChangeRequest = {};
  if (fullName.trim() !== user.fullName) changes.fullName = fullName.trim();
  if (phone.trim() !== (user.phoneNumber ?? '')) changes.phoneNumber = phone.trim();
  if (email.trim().toLowerCase() !== user.email.toLowerCase()) changes.email = email.trim();
  const hasChanges = Object.keys(changes).length > 0;

  function validate(): string | null {
    if (fullName.trim().length < 2) return 'Full name must be at least 2 characters.';
    if (!isValidPhone(phone)) return 'Enter a valid phone number (7–15 digits, e.g. +91 98765 43210).';
    if (!isValidEmail(email)) return 'Please enter a valid email address.';
    return null;
  }

  async function sendCode(e?: FormEvent<HTMLFormElement>) {
    e?.preventDefault();
    setError(null);
    const invalid = validate();
    if (invalid) { setError(invalid); return; }
    if (!hasChanges) { setError('Nothing to change — your details are the same.'); return; }
    setBusy(true);
    try {
      const started = await authService.requestProfileChange(changes);
      setPending({ token: started.changeToken, message: started.message });
      setCode('');
    } catch (err) {
      setError(err instanceof Error && err.message ? err.message : 'Could not send the code. Please try again.');
    } finally {
      setBusy(false);
    }
  }

  async function confirm(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!pending) return;
    setError(null);
    if (!isValidOtp(code)) { setError('Enter the 6-digit code from the email.'); return; }
    setBusy(true);
    try {
      const updated = await authService.confirmProfileChange(pending.token, code.trim());
      completeLogin(updated);
      setPending(null);
      setFullName(updated.fullName);
      setPhone(updated.phoneNumber ?? '');
      setEmail(updated.email);
      showToast({ message: 'Your details have been updated.', variant: 'success' });
    } catch (err) {
      setError(err instanceof Error && err.message ? err.message : 'Could not confirm the change. Please try again.');
    } finally {
      setBusy(false);
    }
  }

  function cancel() {
    setPending(null);
    setCode('');
    setError(null);
    setFullName(user.fullName);
    setPhone(user.phoneNumber ?? '');
    setEmail(user.email);
  }

  return (
    <Card padding="lg">
      <h3 className={styles.heading}>Edit Details</h3>
      <p className={local.intro}>
        Change your name, phone number or email. We&apos;ll email you a code to confirm each change.
      </p>

      {!pending && (
        <form onSubmit={sendCode} className={styles.form} noValidate>
          <div className={styles.fieldGroup}>
            <label htmlFor="edit-name" className={styles.label}>Full Name</label>
            <input id="edit-name" className={styles.input} value={fullName} disabled={busy}
                   autoComplete="name" onChange={(e) => { setFullName(e.target.value); setError(null); }} />
          </div>
          <div className={styles.fieldGroup}>
            <label htmlFor="edit-phone" className={styles.label}>Phone Number</label>
            <input id="edit-phone" className={styles.input} value={phone} disabled={busy} type="tel" inputMode="tel"
                   autoComplete="tel" onChange={(e) => { setPhone(e.target.value); setError(null); }} />
          </div>
          <div className={styles.fieldGroup}>
            <label htmlFor="edit-email" className={styles.label}>Email</label>
            <input id="edit-email" className={styles.input} value={email} disabled={busy} type="email"
                   autoComplete="email" onChange={(e) => { setEmail(e.target.value); setError(null); }} />
            {changes.email && <p className={local.hint}>The code will be sent to your new email address.</p>}
          </div>

          {error && <p className={styles.error} role="alert">{error}</p>}

          <div className={styles.actions}>
            <button type="submit" className={styles.submitBtn} disabled={busy || !hasChanges}>
              {busy ? 'Sending…' : 'Send code'}
            </button>
          </div>
        </form>
      )}

      {pending && (
        <form onSubmit={confirm} className={styles.form} noValidate>
          <p className={local.sent} role="status">{pending.message}</p>
          <div className={styles.fieldGroup}>
            <label htmlFor="edit-code" className={styles.label}>Verification Code</label>
            <input id="edit-code" className={styles.input} value={code} disabled={busy} inputMode="numeric"
                   autoComplete="one-time-code" maxLength={6} placeholder="6-digit code"
                   onChange={(e) => { setCode(e.target.value.replace(/\D/g, '').slice(0, 6)); setError(null); }} />
          </div>

          {error && <p className={styles.error} role="alert">{error}</p>}

          <div className={local.buttons}>
            <button type="submit" className={styles.submitBtn} disabled={busy || code.length < 6}>
              {busy ? 'Confirming…' : 'Confirm change'}
            </button>
            <button type="button" className={local.secondary} onClick={() => void sendCode()} disabled={busy}>
              Resend code
            </button>
            <button type="button" className={local.secondary} onClick={cancel} disabled={busy}>
              Cancel
            </button>
          </div>
        </form>
      )}
    </Card>
  );
}
