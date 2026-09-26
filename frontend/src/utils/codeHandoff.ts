/**
 * SecureNet — hand a verification code from the email's "Copy code" button
 * to the SecureNet tab that is waiting for it.
 *
 * The email button opens /code#123456 (CopyCodePage). That page copies the code
 * and calls handOffCode(); every open SecureNet page with a code field uses
 * useCodeHandoff() and fills the code in. Same browser only (BroadcastChannel,
 * plus a localStorage event as a fallback); codes older than 5 minutes are ignored.
 */

import { useEffect, useRef } from 'react';
import { storageSet } from './storage';

const STORAGE_KEY = 'sn_code_handoff';
const CHANNEL = 'securenet-code';
const MAX_AGE_MS = 5 * 60 * 1000;

interface Handoff {
  code: string;
  at: number;
}

export function handOffCode(code: string): void {
  const message: Handoff = { code, at: Date.now() };
  storageSet(STORAGE_KEY, JSON.stringify(message));
  try {
    const channel = new BroadcastChannel(CHANNEL);
    channel.postMessage(message);
    channel.close();
  } catch {
    /* BroadcastChannel unavailable: the storage event still reaches other tabs */
  }
}

/** Call `onCode(code)` when a code arrives from the email's "Copy code" button (while `active`). */
export function useCodeHandoff(onCode: (code: string) => void, active = true): void {
  const handler = useRef(onCode);
  useEffect(() => {
    handler.current = onCode;
  });

  useEffect(() => {
    if (!active) return;
    const accept = (message: unknown) => {
      const m = message as Partial<Handoff> | null;
      if (m && typeof m.code === 'string' && /^\d{6}$/.test(m.code)
          && typeof m.at === 'number' && Date.now() - m.at < MAX_AGE_MS) {
        handler.current(m.code);
      }
    };
    const onStorage = (event: StorageEvent) => {
      if (event.key !== STORAGE_KEY || !event.newValue) return;
      try {
        accept(JSON.parse(event.newValue));
      } catch {
        /* ignore malformed values */
      }
    };
    window.addEventListener('storage', onStorage);
    let channel: BroadcastChannel | null = null;
    try {
      channel = new BroadcastChannel(CHANNEL);
      channel.onmessage = (event) => accept(event.data);
    } catch {
      channel = null;
    }
    return () => {
      window.removeEventListener('storage', onStorage);
      channel?.close();
    };
  }, [active]);
}
