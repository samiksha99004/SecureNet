/**
 * SecureNet — Authentication Types
 *
 * These interfaces define the shape of auth-related data.
 * All fields reflect what the backend will eventually provide.
 */

// ── User ──────────────────────────────────────────────────────────────────────

export type AuthProvider = 'local' | 'google';

export type AccountStatus = 'active' | 'suspended' | 'pending_verification';

export type UserRole = 'admin' | 'analyst' | 'viewer';

export interface User {
  id: string;
  email: string;
  fullName: string;
  role: UserRole;
  accountStatus: AccountStatus;
  authProvider: AuthProvider;
  createdAt: string;      // ISO 8601
  lastLoginAt: string | null;
  avatarUrl: string | null;
}

// ── Auth Requests ─────────────────────────────────────────────────────────────

export interface LoginRequest {
  email: string;
  password: string;
}

export interface SignupRequest {
  fullName: string;
  email: string;
  password: string;
  confirmPassword: string;
}

export interface OtpVerifyRequest {
  email: string;
  otp: string;
}

export interface OtpResendRequest {
  email: string;
}

export interface ChangePasswordRequest {
  currentPassword: string;
  newPassword: string;
  confirmNewPassword: string;
}

export interface ForgotPasswordRequest {
  email: string;
}

export interface ResetPasswordRequest {
  token: string;
  newPassword: string;
  confirmNewPassword: string;
}

// ── Auth Responses ────────────────────────────────────────────────────────────

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
  expiresIn: number; // seconds
}

export interface AuthResponse {
  user: User;
  tokens: AuthTokens;
}

export interface OtpVerifyResponse {
  verified: boolean;
  authResponse: AuthResponse | null;
}

// ── Auth State ────────────────────────────────────────────────────────────────

export type AuthStatus =
  | 'idle'
  | 'loading'
  | 'authenticated'
  | 'unauthenticated'
  | 'error';

export interface AuthState {
  status: AuthStatus;
  user: User | null;
  error: string | null;
}
