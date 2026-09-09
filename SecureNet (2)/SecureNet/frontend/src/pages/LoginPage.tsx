/**
 * SecureNet — Login Page
 */

import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthLayout } from '../components/auth/AuthLayout';
import { LoginForm } from '../components/auth/LoginForm';
import { useAuth } from '../contexts/AuthContext';

export function LoginPage() {
  const { isAuthenticated, status } = useAuth();
  const navigate = useNavigate();

  // Redirect already-authenticated users away from login
  useEffect(() => {
    if (status === 'authenticated' && isAuthenticated) {
      navigate('/dashboard', { replace: true });
    }
  }, [isAuthenticated, status, navigate]);

  return (
    <AuthLayout>
      <LoginForm />
    </AuthLayout>
  );
}
