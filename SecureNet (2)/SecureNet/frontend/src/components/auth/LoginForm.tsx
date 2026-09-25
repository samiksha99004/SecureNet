/**
 * SecureNet — LoginForm
 *
 * Complete login form with:
 *  - Email + password fields
 *  - Show/hide password toggle
 *  - Validation (client-side)
 *  - Loading state
 *  - Error display
 *  - Unverified accounts are sent to OTP verification
 *  - Link to signup
 */

import { useState, type FormEvent } from 'react';
import { Eye, EyeOff } from 'lucide-react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { isValidEmail, isNonEmpty } from '../../utils/validation';
import { FormField } from './FormField';
import { AuthButton } from './AuthButton';
import styles from './LoginForm.module.css';

interface FormErrors {
  email?: string;
  password?: string;
  form?: string;
}

export function LoginForm() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, status } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState<FormErrors>({});
  const [formError, setFormError] = useState<string | null>(null);

  const isLoading = status === 'loading';

  // Message handed over by another page (e.g. "password changed")
  const notice = (location.state as { notice?: string } | null)?.notice ?? null;

  // Where to redirect after login
  const from =
    (location.state as { from?: { pathname: string } })?.from?.pathname ??
    '/dashboard';

  function validate(): boolean {
    const next: FormErrors = {};
    if (!isNonEmpty(email)) {
      next.email = 'Email is required.';
    } else if (!isValidEmail(email)) {
      next.email = 'Please enter a valid email address.';
    }
    if (!isNonEmpty(password)) {
      next.password = 'Password is required.';
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setFormError(null);

    if (!validate()) return;

    try {
      await login({ email: email.trim(), password });
      navigate(from, { replace: true });
    } catch (err) {
      setFormError(
        err instanceof Error && err.message
          ? err.message
          : 'Login failed. Please check your credentials.'
      );
    }
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1 className={styles.title}>Welcome back</h1>
        <p className={styles.subtitle}>Sign in to your SecureNet account.</p>
      </div>

      {notice && !formError && (
        <div className={styles.notice} role="status">
          {notice}
        </div>
      )}

      {/* ── Global form error ── */}
      {formError && (
        <div className={styles.formError} role="alert">
          {formError}
        </div>
      )}

      <form onSubmit={handleSubmit} className={styles.form} noValidate>
        <FormField
          id="login-email"
          label="Email address"
          type="email"
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
            if (errors.email) setErrors((prev) => ({ ...prev, email: undefined }));
          }}
          autoComplete="email"
          placeholder="you@example.com"
          error={errors.email}
          disabled={isLoading}
        />

        <FormField
          id="login-password"
          label="Password"
          type={showPassword ? 'text' : 'password'}
          value={password}
          onChange={(e) => {
            setPassword(e.target.value);
            if (errors.password) setErrors((prev) => ({ ...prev, password: undefined }));
          }}
          autoComplete="current-password"
          placeholder="Enter your password"
          error={errors.password}
          disabled={isLoading}
          rightElement={
            <button
              type="button"
              aria-label={showPassword ? 'Hide password' : 'Show password'}
              onClick={() => setShowPassword((v) => !v)}
              className={styles.eyeButton}
              tabIndex={0}
            >
              {showPassword
                ? <EyeOff size={16} />
                : <Eye size={16} />}
            </button>
          }
        />

        <p className={styles.forgotRow}>
          <Link to="/forgot-password" className={styles.forgotLink}>
            Forgot password?
          </Link>
        </p>

        <AuthButton type="submit" isLoading={isLoading} disabled={isLoading}>
          Sign in
        </AuthButton>
      </form>

      <p className={styles.switchLink}>
        Don&apos;t have an account?{' '}
        <Link to="/signup" className={styles.link}>
          Create account
        </Link>
      </p>
    </div>
  );
}
