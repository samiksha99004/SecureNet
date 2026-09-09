/**
 * SecureNet — Async Data Hook
 *
 * Generic hook for fetching async data with loading/error/success states.
 *
 * Usage:
 *   const { data, status, error, refetch } = useAsyncData(getDashboardSummary);
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import type { ApiError } from '../types/api.types';
import { ApiClientError } from '../services/apiClient';

type AsyncStatus = 'idle' | 'loading' | 'success' | 'error';

interface AsyncState<T> {
  data: T | null;
  status: AsyncStatus;
  error: ApiError | null;
}

interface UseAsyncDataOptions {
  /** Set to false to prevent fetching on mount */
  fetchOnMount?: boolean;
}

export function useAsyncData<T>(
  fetcher: () => Promise<T>,
  options: UseAsyncDataOptions = {}
) {
  const { fetchOnMount = true } = options;
  const [state, setState] = useState<AsyncState<T>>({
    data: null,
    status: 'idle',
    error: null,
  });

  // Prevent state updates on unmounted components
  const isMounted = useRef(true);
  useEffect(() => {
    isMounted.current = true;
    return () => {
      isMounted.current = false;
    };
  }, []);

  const execute = useCallback(async () => {
    if (!isMounted.current) return;
    setState({ data: null, status: 'loading', error: null });

    try {
      const data = await fetcher();
      if (isMounted.current) {
        setState({ data, status: 'success', error: null });
      }
    } catch (err) {
      if (!isMounted.current) return;
      if (err instanceof ApiClientError) {
        setState({
          data: null,
          status: 'error',
          error: {
            status: err.status,
            code: err.code,
            message: err.message,
            details: err.details,
          },
        });
      } else {
        setState({
          data: null,
          status: 'error',
          error: {
            status: 0,
            code: 'NETWORK_ERROR',
            message: err instanceof Error ? err.message : 'An unexpected error occurred.',
          },
        });
      }
    }
  }, [fetcher]);

  useEffect(() => {
    if (fetchOnMount) {
      void execute();
    }
  }, [execute, fetchOnMount]);

  return {
    ...state,
    refetch: execute,
    isLoading: state.status === 'loading',
    isSuccess: state.status === 'success',
    isError: state.status === 'error',
  };
}
