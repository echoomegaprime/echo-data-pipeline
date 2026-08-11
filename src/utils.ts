import type { ApiResponse } from './types';

export function generateId(): string {
  const ts = Date.now().toString(36);
  const rand = Math.random().toString(36).substring(2, 10);
  return `${ts}-${rand}`;
}

// Constant-time string comparison — runtime must not depend on where (or
// whether) the inputs first differ, including a length mismatch, or an
// attacker can recover the key length/prefix via timing.
export function timingSafeEqual(a: string | undefined | null, b: string | undefined | null): boolean {
  if (!a || !b) return false;
  const encoder = new TextEncoder();
  const bufA = encoder.encode(a);
  const bufB = encoder.encode(b);
  const len = Math.max(bufA.length, bufB.length, 1);
  const padA = new Uint8Array(len);
  const padB = new Uint8Array(len);
  padA.set(bufA);
  padB.set(bufB);
  let mismatch = bufA.length ^ bufB.length;
  for (let i = 0; i < len; i++) {
    mismatch |= (padA[i] ?? 0) ^ (padB[i] ?? 0);
  }
  return mismatch === 0;
}

export function response<T>(data: T, status = 200): Response {
  const body: ApiResponse<T> = {
    success: status >= 200 && status < 300,
    data,
    timestamp: new Date().toISOString(),
  };
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

export function errorResponse(error: string, status = 400): Response {
  const body: ApiResponse = {
    success: false,
    error,
    timestamp: new Date().toISOString(),
  };
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

export function nowISO(): string {
  return new Date().toISOString();
}

/**
 * Exponential backoff delay calculation: 1s, 2s, 4s, 8s (max 3 retries)
 */
export function getRetryDelay(retryCount: number): number {
  const baseMs = 1000;
  return baseMs * Math.pow(2, retryCount);
}

export const MAX_RETRIES = 3;

/**
 * Parse pagination params from URL search params
 */
export function parsePagination(url: URL): { limit: number; offset: number } {
  const limit = Math.min(Math.max(parseInt(url.searchParams.get('limit') || '50', 10), 1), 200);
  const offset = Math.max(parseInt(url.searchParams.get('offset') || '0', 10), 0);
  return { limit, offset };
}
