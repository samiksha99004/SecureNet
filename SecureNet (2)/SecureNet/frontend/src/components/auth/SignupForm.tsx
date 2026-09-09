/**
 * SecureNet — SignupForm
 *
 * Complete registration form with:
 *  - Full name, email, password, confirm password
 *  - Password strength indicator
 *  - Show/hide password toggles
 *  - Full client-side validation
 *  - Loading + error states
 *  - On success: navigates to OTP verify with email in state
 */

import { useState, type FormEvent } from 'react';
import { Eye, EyeOff } from 'lucide-react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import {
  isValidEmail,
  isValidPassword,
  isNonEmpty,
  minLength,
} from '../../utils/validation';
import { FormField } from './FormField';
import { AuthButton } from './AuthButton';
import { AuthDivider } from './AuthDivider';
import { PasswordStrengthBar } from './PasswordStrengthBar';
import styles from './SignupForm.module.css';

interface FormErrors {
  fullName?: string;
  email?: string;
  password?: string;
  confirmPassword?: string;
}

export function SignupForm() {
  const navigate = useNavigate();
  const { signup, status } = useAuth();

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [errors, setErrors] = useState<FormErrors>({});
  const [formError, setFormError] = useState<string | null>(null);

  const isLoading = status === 'loading';

  function clearField(field: keyof FormErrors) {
    setErrors((prev) => ({ ...prev, [field]: undefined }));
  }

  function validate(): boolean {
    const next: FormErrors = {};

    if (!isNonEmpty(fullName)) {
      next.fullName = 'Full name is required.';
    } else if (!minLength(fullName, 2)) {
      next.fullName = 'Full name must be at least 2 characters.';
    }

    if (!isNonEmpty(email)) {
      next.email = 'Email is required.';
    } else if (!isValidEmail(email)) {
      next.email = 'Please enter a valid email address.';
    }

    if (!isNonEmpty(password)) {
      next.password = 'Password is required.';
    } else if (!isValidPassword(password)) {
      next.password =
        'Password must be at least 8 characters and include a letter and a number.';
    }

    if (!isNonEmpty(confirmPassword)) {
      next.confirmPassword = 'Please confirm your password.';
    } else if (password !== confirmPassword) {
      next.confirmPassword = 'Passwords do not match.';
    }

    setErrors(next);
    return Object.keys(next).length === 0;
  }

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setFormError(null);

    if (!validate()) return;

    try {
      await signup({
        fullName: fullName.trim(),
        email: email.trim(),
        password,
        confirmPassword,
      });
      // Navigate to OTP verification, passing the email
      navigate('/otp-verify', { state: { email: email.trim() } });
    } catch (err) {
      setFormError(
        err instanceof Error
          ? err.message
          : 'Registration failed. Please try again.'
      );
    }
  }

  function handleGoogleSignup() {
    setFormError(
      'Google sign-up is not yet available. The backend integration is pending.'
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1 className={styles.title}>Create account</h1>
        <p className={styles.subtitle}>
          Set up your SecureNet account to get started.
        </p>
      </div>

      {formError && (
        <div className={styles.formError} role="alert">
          {formError}
        </div>
      )}

      <form onSubmit={handleSubmit} className={styles.form} noValidate>
        <FormField
          id="signup-name"
          label="Full name"
          type="text"
          value={fullName}
          onChange={(e) => { setFullName(e.target.value); clearField('fullName'); }}
          autoComplete="name"
          placeholder="Jane Smith"
          error={errors.fullName}
          disabled={isLoading}
        />

        <FormField
          id="signup-email"
          label="Email address"
          type="email"
          value={email}
          onChange={(e) => { setEmail(e.target.value); clearField('email'); }}
          autoComplete="email"
          placeholder="you@example.com"
          error={errors.email}
          disabled={isLoading}
        />

        <div>
          <FormField
            id="signup-password"
            label="Password"
            type={showPassword ? 'text' : 'password'}
            value={password}
            onChange={(e) => { setPassword(e.target.value); clearField('password'); }}
            autoComplete="new-password"
            placeholder="Choose a strong password"
            error={errors.password}
            disabled={isLoading}
            hint={!errors.password ? 'At least 8 characters with a letter and number.' : undefined}
            rightElement={
              <button
                type="button"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                onClick={() => setShowPassword((v) => !v)}
                className={styles.eyeButton}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            }
          />
          <PasswordStrengthBar password={password} />
        </div>

        <FormField
          id="signup-confirm"
          label="Confirm password"
          type={showConfirm ? 'text' : 'password'}
          value={confirmPassword}
          onChange={(e) => { setConfirmPassword(e.target.value); clearField('confirmPassword'); }}
          autoComplete="new-password"
          placeholder="Repeat your password"
          error={errors.confirmPassword}
          disabled={isLoading}
          rightElement={
            <button
              type="button"
              aria-label={showConfirm ? 'Hide confirm password' : 'Show confirm password'}
              onClick={() => setShowConfirm((v) => !v)}
              className={styles.eyeButton}
            >
              {showConfirm ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          }
        />

        <AuthButton type="submit" isLoading={isLoading} disabled={isLoading}>
          Create account
        </AuthButton>
      </form>

      <AuthDivider />

      <AuthButton
        type="button"
        variant="secondary"
        onClick={handleGoogleSignup}
        disabled={isLoading}
        leftIcon={
          <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true">
            <path fill="#4285F4" d="M47.5 24.6c0-1.6-.1-3.1-.4-4.6H24v8.7h13.2c-.6 3-2.3 5.5-4.9 7.2v6h7.9c4.6-4.3 7.3-10.6 7.3-17.3z"/>
            <path fill="#34A853" d="M24 48c6.5 0 11.9-2.1 15.9-5.8l-7.9-6c-2.1 1.4-4.9 2.3-8 2.3-6.1 0-11.3-4.1-13.2-9.7H2.7v6.2C6.7 42.9 14.8 48 24 48z"/>
            <path fill="#FBBC05" d="M10.8 28.8c-.5-1.4-.8-2.9-.8-4.4s.3-3 .8-4.4v-6.2H2.7C1 17.1 0 20.4 0 24s1 6.9 2.7 9.9l8.1-6.2-.0 1.1z"/>
            <path fill="#EA4335" d="M24 9.5c3.4 0 6.5 1.2 8.9 3.5l6.6-6.6C35.9 2.5 30.4 0 24 0 14.8 0 6.7 5.1 2.7 12.6l8.1 6.2C12.7 13.6 17.9 9.5 24 9.5z"/>
          </svg>
        }
      >
        Continue with Google
      </AuthButton>

      <p className={styles.switchLink}>
        Already have an account?{' '}
        <Link to="/login" className={styles.link}>
          Sign in
        </Link>
      </p>
    </div>
  );
}
