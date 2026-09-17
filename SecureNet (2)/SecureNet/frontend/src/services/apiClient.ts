/**
 * SecureNet — API Client
 *
 * Centralised HTTP client. Reads base URL from environment.
 * The backend developer sets VITE_API_BASE_URL in .env.local
 * once the backend is ready.
 *
 * All service files use this client — never raw fetch/axios calls
 * in components.
 */

import type { ApiError } from '../types/api.types';

// ── Configuration ─────────────────────────────────────────────────────────────

const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? '';

// ── Error Handling ────────────────────────────────────────────────────────────

export class ApiClientError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details?: Record<string, string[]>;

  constructor(error: ApiError) {
    super(error.message);
    this.name = 'ApiClientError';
    this.status = error.status;
    this.code = error.code;
    this.details = error.details;
  }
}

async function parseErrorResponse(response: Response): Promise<ApiClientError> {
  try {
    const body = (await response.json()) as ApiError;
    return new ApiClientError(body);
  } catch {
    return new ApiClientError({
      status: response.status,
      code: 'UNKNOWN_ERROR',
      message: `HTTP ${response.status}: ${response.statusText}`,
    });
  }
}

// ── Token Retrieval ───────────────────────────────────────────────────────────
// The auth service stores the access token; we read it here to attach
// to every outgoing request. Replaced by the backend developer when
// the actual auth flow is connected.

function getStoredAccessToken(): string | null {
  return localStorage.getItem('sn_access_token');
}

// ── Request Builder ───────────────────────────────────────────────────────────

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  body?: unknown;
  headers?: Record<string, string>;
  /** Skip Authorization header (e.g. for login/signup) */
  skipAuth?: boolean;
}

async function request<T>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const { method = 'GET', body, headers = {}, skipAuth = false } = options;

  const resolvedHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    ...headers,
  };

  if (!skipAuth) {
    const token = getStoredAccessToken();
    if (token) {
      resolvedHeaders['Authorization'] = `Bearer ${token}`;
    }
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: resolvedHeaders,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    // Handle 401 Unauthorized - session expired
    if (response.status === 401 && !skipAuth) {
      // Clear stored tokens
      localStorage.removeItem('sn_access_token');
      localStorage.removeItem('sn_refresh_token');
      localStorage.removeItem('sn_user');
      
      // Redirect to login if not already on login/signup pages
      if (!window.location.pathname.includes('/login') && 
          !window.location.pathname.includes('/signup')) {
        window.location.href = '/login?expired=true';
      }
    }
    
    throw await parseErrorResponse(response);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

// ── Public API ────────────────────────────────────────────────────────────────

export const apiClient = {
  get: <T>(path: string, opts?: Omit<RequestOptions, 'method' | 'body'>) =>
    request<T>(path, { ...opts, method: 'GET' }),

  post: <T>(path: string, body: unknown, opts?: Omit<RequestOptions, 'method' | 'body'>) =>
    request<T>(path, { ...opts, method: 'POST', body }),

  put: <T>(path: string, body: unknown, opts?: Omit<RequestOptions, 'method' | 'body'>) =>
    request<T>(path, { ...opts, method: 'PUT', body }),

  patch: <T>(path: string, body: unknown, opts?: Omit<RequestOptions, 'method' | 'body'>) =>
    request<T>(path, { ...opts, method: 'PATCH', body }),

  delete: <T>(path: string, opts?: Omit<RequestOptions, 'method' | 'body'>) =>
    request<T>(path, { ...opts, method: 'DELETE' }),
};
