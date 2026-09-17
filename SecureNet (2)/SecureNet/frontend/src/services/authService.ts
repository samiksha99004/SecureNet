/**
 * SecureNet — Authentication Service
 *
 * All auth interactions go through this service.
 * Components call these functions; the service communicates
 * with the backend via the API client.
 *
 * Token storage is handled here so components never touch
 * localStorage or token headers directly.
 *
 * TODO (backend): Replace placeholder endpoint paths with
 * actual backend routes once the API is ready.
 */

import { apiClient } from './apiClient';
import type {
  LoginRequest,
  SignupRequest,
  OtpVerifyRequest,
  OtpResendRequest,
  OtpVerifyResponse,
  AuthResponse,
  ChangePasswordRequest,
  ForgotPasswordRequest,
  ResetPasswordRequest,
  User,
} from '../types/auth.types';
import type { MessageResponse } from '../types/api.types';

// ── Token Storage Keys ────────────────────────────────────────────────────────

const ACCESS_TOKEN_KEY = 'sn_access_token';
const REFRESH_TOKEN_KEY = 'sn_refresh_token';
const USER_KEY = 'sn_user';

// ── Token Helpers ─────────────────────────────────────────────────────────────

export function storeTokens(accessToken: string, refreshToken: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function storeUser(user: User): void {
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function getStoredUser(): User | null {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as User;
  } catch {
    return null;
  }
}

export function isAuthenticated(): boolean {
  return getAccessToken() !== null;
}

// ── Auth API Calls ────────────────────────────────────────────────────────────

/**
 * Log in with email + password.
 * TODO (backend): POST /auth/login
 */
export async function login(request: LoginRequest): Promise<AuthResponse> {
  const response = await apiClient.post<any>('/auth/login', request, {
    skipAuth: true,
  });
  
  // Transform snake_case to camelCase
  const transformedResponse: AuthResponse = {
    user: {
      id: response.user.id,
      email: response.user.email,
      fullName: response.user.full_name,
      role: response.user.role,
      accountStatus: response.user.account_status,
      authProvider: response.user.auth_provider,
      createdAt: response.user.created_at,
      lastLoginAt: response.user.last_login_at,
      avatarUrl: response.user.avatar_url
    },
    tokens: response.tokens
  };
  
  storeTokens(transformedResponse.tokens.accessToken, transformedResponse.tokens.refreshToken);
  storeUser(transformedResponse.user);
  return transformedResponse;
}

/**
 * Register a new user account.
 * TODO (backend): POST /auth/signup
 */
export async function signup(request: SignupRequest): Promise<MessageResponse> {
  return apiClient.post<MessageResponse>('/auth/signup', request, {
    skipAuth: true,
  });
}

/**
 * Verify the OTP sent to the user's email.
 * TODO (backend): POST /auth/otp/verify
 */
export async function verifyOtp(request: OtpVerifyRequest): Promise<OtpVerifyResponse> {
  const response = await apiClient.post<any>(
    '/auth/otp/verify',
    request,
    { skipAuth: true }
  );
  
  if (response.authResponse && response.authResponse.user) {
    // Transform snake_case to camelCase
    const transformedUser: User = {
      id: response.authResponse.user.id,
      email: response.authResponse.user.email,
      fullName: response.authResponse.user.full_name,
      role: response.authResponse.user.role,
      accountStatus: response.authResponse.user.account_status,
      authProvider: response.authResponse.user.auth_provider,
      createdAt: response.authResponse.user.created_at,
      lastLoginAt: response.authResponse.user.last_login_at,
      avatarUrl: response.authResponse.user.avatar_url
    };
    
    storeTokens(
      response.authResponse.tokens.accessToken,
      response.authResponse.tokens.refreshToken
    );
    storeUser(transformedUser);
    
    return {
      verified: response.verified,
      authResponse: {
        user: transformedUser,
        tokens: response.authResponse.tokens
      }
    };
  }
  
  return response;
}

/**
 * Resend OTP to the given email.
 * TODO (backend): POST /auth/otp/resend
 */
export async function resendOtp(request: OtpResendRequest): Promise<MessageResponse> {
  return apiClient.post<MessageResponse>('/auth/otp/resend', request, {
    skipAuth: true,
  });
}

/**
 * Log out — clears local tokens.
 * TODO (backend): POST /auth/logout (optional server-side session invalidation)
 */
export async function logout(): Promise<void> {
  try {
    await apiClient.post<MessageResponse>('/auth/logout', {});
  } catch {
    // Always clear local state even if server call fails
  } finally {
    clearTokens();
  }
}

/**
 * Fetch the currently authenticated user's profile.
 * TODO (backend): GET /auth/me
 */
export async function getCurrentUser(): Promise<User> {
  const response = await apiClient.get<any>('/auth/me');
  
  // Transform snake_case to camelCase
  return {
    id: response.id,
    email: response.email,
    fullName: response.full_name,
    role: response.role,
    accountStatus: response.account_status,
    authProvider: response.auth_provider,
    createdAt: response.created_at,
    lastLoginAt: response.last_login_at,
    avatarUrl: response.avatar_url
  };
}

/**
 * Request a password-reset email.
 * TODO (backend): POST /auth/forgot-password
 */
export async function forgotPassword(
  request: ForgotPasswordRequest
): Promise<MessageResponse> {
  return apiClient.post<MessageResponse>('/auth/forgot-password', request, {
    skipAuth: true,
  });
}

/**
 * Reset password using a token from the reset email.
 * TODO (backend): POST /auth/reset-password
 */
export async function resetPassword(
  request: ResetPasswordRequest
): Promise<MessageResponse> {
  return apiClient.post<MessageResponse>('/auth/reset-password', request, {
    skipAuth: true,
  });
}

/**
 * Change password for an authenticated user.
 * TODO (backend): POST /auth/change-password
 */
export async function changePassword(
  request: ChangePasswordRequest
): Promise<MessageResponse> {
  return apiClient.post<MessageResponse>('/auth/change-password', request);
}

/**
 * Initiate Google OAuth login flow.
 * TODO (backend): GET /auth/google — redirect to Google consent screen.
 * The frontend navigates to this URL; OAuth callback is handled server-side.
 */
export function getGoogleOAuthUrl(): string {
  return `${import.meta.env.VITE_API_BASE_URL ?? ''}/auth/google`;
}
