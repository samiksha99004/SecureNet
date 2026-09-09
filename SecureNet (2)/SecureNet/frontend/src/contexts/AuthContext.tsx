/**
 * SecureNet — Authentication Context
 *
 * Provides authentication state and actions throughout the app.
 * Components use the useAuth() hook — never import the context directly.
 *
 * Architecture:
 *   AuthProvider (this file)
 *       ↓
 *   useAuth() hook
 *       ↓
 *   authService.ts
 *       ↓
 *   Future backend
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useReducer,
  type ReactNode,
} from 'react';
import * as authService from '../services/authService';
import type { User, AuthState, LoginRequest, SignupRequest } from '../types/auth.types';
import type { MessageResponse } from '../types/api.types';

// ── State & Reducer ───────────────────────────────────────────────────────────

type AuthAction =
  | { type: 'LOADING' }
  | { type: 'AUTHENTICATED'; user: User }
  | { type: 'UNAUTHENTICATED' }
  | { type: 'ERROR'; error: string }
  | { type: 'CLEAR_ERROR' };

function authReducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case 'LOADING':
      return { ...state, status: 'loading', error: null };
    case 'AUTHENTICATED':
      return { status: 'authenticated', user: action.user, error: null };
    case 'UNAUTHENTICATED':
      return { status: 'unauthenticated', user: null, error: null };
    case 'ERROR':
      return { ...state, status: 'error', error: action.error };
    case 'CLEAR_ERROR':
      return { ...state, error: null };
    default:
      return state;
  }
}

const initialState: AuthState = {
  status: 'idle',
  user: null,
  error: null,
};

// ── Context Shape ─────────────────────────────────────────────────────────────

interface AuthContextValue extends AuthState {
  login: (request: LoginRequest) => Promise<void>;
  signup: (request: SignupRequest) => Promise<MessageResponse>;
  logout: () => Promise<void>;
  clearError: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

// ── Provider ──────────────────────────────────────────────────────────────────

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [state, dispatch] = useReducer(authReducer, initialState);

  // On mount, check if we have a stored user session
  useEffect(() => {
    const storedUser = authService.getStoredUser();
    const token = authService.getAccessToken();

    if (storedUser && token) {
      dispatch({ type: 'AUTHENTICATED', user: storedUser });
    } else {
      dispatch({ type: 'UNAUTHENTICATED' });
    }
  }, []);

  const login = useCallback(async (request: LoginRequest): Promise<void> => {
    dispatch({ type: 'LOADING' });
    try {
      const response = await authService.login(request);
      dispatch({ type: 'AUTHENTICATED', user: response.user });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Login failed.';
      dispatch({ type: 'ERROR', error: message });
      throw err;
    }
  }, []);

  const signup = useCallback(
    async (request: SignupRequest): Promise<MessageResponse> => {
      dispatch({ type: 'LOADING' });
      try {
        const response = await authService.signup(request);
        dispatch({ type: 'UNAUTHENTICATED' }); // Not yet authenticated until OTP
        return response;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Signup failed.';
        dispatch({ type: 'ERROR', error: message });
        throw err;
      }
    },
    []
  );

  const logout = useCallback(async (): Promise<void> => {
    dispatch({ type: 'LOADING' });
    try {
      await authService.logout();
    } finally {
      dispatch({ type: 'UNAUTHENTICATED' });
    }
  }, []);

  const clearError = useCallback((): void => {
    dispatch({ type: 'CLEAR_ERROR' });
  }, []);

  const value: AuthContextValue = {
    ...state,
    login,
    signup,
    logout,
    clearError,
    isAuthenticated: state.status === 'authenticated',
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
