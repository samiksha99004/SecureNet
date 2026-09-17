/**
 * SecureNet — Login Page
 */

import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { AuthLayout } from '../components/auth/AuthLayout';
import { LoginForm } from '../components/auth/LoginForm';
import { useAuth } from '../contexts/AuthContext';

export function LoginPage() {
  const { isAuthenticated, status } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [expiredMessage, setExpiredMessage] = useState<string | null>(null);

  // Check if redirected due to expired session
  useEffect(() => {
    if (searchParams.get('expired') === 'true') {
      setExpiredMessage('Your session has expired. Please log in again.');
      // Clear the query parameter after showing the message
      setTimeout(() => setExpiredMessage(null), 5000);
    }
  }, [searchParams]);

  // Redirect already-authenticated users away from login
  useEffect(() => {
    if (status === 'authenticated' && isAuthenticated) {
      navigate('/dashboard', { replace: true });
    }
  }, [isAuthenticated, status, navigate]);

  return (
    <AuthLayout>
      {expiredMessage && (
        <div style={{
          padding: '12px 16px',
          marginBottom: '16px',
          backgroundColor: '#fef3c7',
          border: '1px solid #fbbf24',
          borderRadius: '8px',
          color: '#92400e',
          fontSize: '14px',
          textAlign: 'center'
        }}>
          {expiredMessage}
        </div>
      )}
      <LoginForm />
    </AuthLayout>
  );
}
