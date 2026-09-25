/**
 * SecureNet — ChangePasswordCard
 *
 * Password change form for local-auth users.
 * Hidden entirely for Google OAuth users (password change is not
 * supported for federated accounts).
 *
 * Calls authService.changePassword → backend API.
 * Shows backend-pending notice instead of silently faking success.
 */

import { useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';
import type { User } from '../../types/auth.types';
import { changePassword } from '../../services/authService';
import { useToast } from '../common/Toast';
import { Card } from '../common/Card';
import { isValidPassword } from '../../utils/validation';
import styles from './ChangePasswordCard.module.css';
import { errorMessage } from '../../utils/errors';

interface ChangePasswordCardProps {
  user: User;
}

export function ChangePasswordCard({ user }: ChangePasswordCardProps) {
  const { showToast } = useToast();

  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNext, setShowNext] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSaving, setIsSaving] = useState(false);

  // Google OAuth users cannot change their password through SecureNet
  if (user.authProvider === 'google') {
    return (
      <Card padding="lg">
        <h3 className={styles.heading}>Security</h3>
        <div className={styles.oauthNotice} role="note">
          <p className={styles.oauthTitle}>Password change not available</p>
          <p className={styles.oauthDesc}>
            Your account is authenticated via Google OAuth. Password management
            is handled by your Google account settings.
          </p>
        </div>
      </Card>
    );
  }

  function validate(): boolean {
    const errs: Record<string, string> = {};
    if (!current.trim()) errs.current = 'Current password is required.';
    if (!isValidPassword(next)) {
      errs.next = 'New password must be at least 8 characters and include a letter and a number.';
    }
    if (next !== confirm) errs.confirm = 'Passwords do not match.';
    if (next === current && next !== '') errs.next = 'New password must differ from your current password.';
    setErrors(errs);
    return Object.keys(errs).length === 0;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;
    setIsSaving(true);
    try {
      await changePassword({
        currentPassword: current,
        newPassword: next,
        confirmNewPassword: confirm,
      });
      showToast({ message: 'Password changed successfully.', variant: 'success' });
      setCurrent(''); setNext(''); setConfirm('');
      setErrors({});
    } catch (err) {
      showToast({ message: errorMessage(err, 'Could not change password.'), variant: 'error' });
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <Card padding="lg">
      <h3 className={styles.heading}>Change Password</h3>

      <form onSubmit={handleSubmit} className={styles.form} noValidate>
        {/* Current password */}
        <div className={styles.fieldGroup}>
          <label htmlFor="pwd-current" className={styles.label}>Current Password</label>
          <div className={styles.inputWrap}>
            <input
              id="pwd-current"
              type={showCurrent ? 'text' : 'password'}
              className={styles.input}
              value={current}
              onChange={(e) => { setCurrent(e.target.value); setErrors((p) => ({ ...p, current: '' })); }}
              autoComplete="current-password"
            />
            <button
              type="button"
              className={styles.eyeBtn}
              onClick={() => setShowCurrent((p) => !p)}
              aria-label={showCurrent ? 'Hide password' : 'Show password'}
            >
              {showCurrent ? <EyeOff size={15} /> : <Eye size={15} />}
            </button>
          </div>
          {errors.current && <p className={styles.error}>{errors.current}</p>}
        </div>

        {/* New password */}
        <div className={styles.fieldGroup}>
          <label htmlFor="pwd-new" className={styles.label}>New Password</label>
          <div className={styles.inputWrap}>
            <input
              id="pwd-new"
              type={showNext ? 'text' : 'password'}
              className={styles.input}
              value={next}
              onChange={(e) => { setNext(e.target.value); setErrors((p) => ({ ...p, next: '' })); }}
              autoComplete="new-password"
            />
            <button
              type="button"
              className={styles.eyeBtn}
              onClick={() => setShowNext((p) => !p)}
              aria-label={showNext ? 'Hide password' : 'Show password'}
            >
              {showNext ? <EyeOff size={15} /> : <Eye size={15} />}
            </button>
          </div>
          {errors.next && <p className={styles.error}>{errors.next}</p>}
        </div>

        {/* Confirm */}
        <div className={styles.fieldGroup}>
          <label htmlFor="pwd-confirm" className={styles.label}>Confirm New Password</label>
          <div className={styles.inputWrap}>
            <input
              id="pwd-confirm"
              type={showConfirm ? 'text' : 'password'}
              className={styles.input}
              value={confirm}
              onChange={(e) => { setConfirm(e.target.value); setErrors((p) => ({ ...p, confirm: '' })); }}
              autoComplete="new-password"
            />
            <button
              type="button"
              className={styles.eyeBtn}
              onClick={() => setShowConfirm((p) => !p)}
              aria-label={showConfirm ? 'Hide password' : 'Show password'}
            >
              {showConfirm ? <EyeOff size={15} /> : <Eye size={15} />}
            </button>
          </div>
          {errors.confirm && <p className={styles.error}>{errors.confirm}</p>}
        </div>

        <div className={styles.actions}>
          <button
            type="submit"
            className={styles.submitBtn}
            disabled={isSaving}
            aria-busy={isSaving}
          >
            {isSaving ? 'Saving…' : 'Update Password'}
          </button>
        </div>
      </form>
    </Card>
  );
}
