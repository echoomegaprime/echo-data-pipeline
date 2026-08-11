import { describe, it, expect } from 'vitest';
import { app } from '../src/index.js';
import { timingSafeEqual } from '../src/utils.js';

describe('timingSafeEqual', () => {
  it('returns true for identical strings', () => {
    expect(timingSafeEqual('secret-value', 'secret-value')).toBe(true);
  });
  it('returns false for different strings of the same length', () => {
    expect(timingSafeEqual('secret-value', 'secret-vlaue')).toBe(false);
  });
  it('returns false for strings of different length', () => {
    expect(timingSafeEqual('short', 'a-much-longer-string')).toBe(false);
  });
  it('returns false when either side is missing', () => {
    expect(timingSafeEqual(undefined, 'x')).toBe(false);
    expect(timingSafeEqual('x', null)).toBe(false);
  });
});

// A trivial "always empty" fake D1 -- enough to let an authenticated route
// reach a 200 without needing real data (the auth gate is what's under test).
function fakeDB() {
  const stmt = {
    bind: () => stmt,
    first: async () => null,
    run: async () => ({ success: true }),
    all: async () => ({ results: [] }),
  };
  return { prepare: () => stmt } as any;
}

function fakeEnv(overrides: Record<string, unknown> = {}) {
  return {
    DB: fakeDB(),
    CACHE: { get: async () => null, put: async () => undefined },
    SHARED_BRAIN: { fetch: async () => new Response('{}') },
    ALERT_ROUTER: { fetch: async () => new Response('{}') },
    KNOWLEDGE_FORGE: { fetch: async () => new Response('{}') },
    ECHO_API_KEY: 'correct-horse-battery-staple',
    ...overrides,
  } as any;
}

describe('auth gate', () => {
  it('allows "/" and "/health" with no key', async () => {
    const rootRes = await app.fetch(new Request('https://worker/'), fakeEnv());
    expect(rootRes.status).toBe(200);
    const healthRes = await app.fetch(new Request('https://worker/health'), fakeEnv());
    expect(healthRes.status).toBe(200);
  });

  it('rejects a protected route with no key (401)', async () => {
    const res = await app.fetch(new Request('https://worker/pipelines'), fakeEnv());
    expect(res.status).toBe(401);
  });

  it('rejects a protected route with a wrong key (401)', async () => {
    const res = await app.fetch(
      new Request('https://worker/pipelines', { headers: { 'X-Echo-API-Key': 'garbage' } }),
      fakeEnv()
    );
    expect(res.status).toBe(401);
  });

  it('fails closed (503) when ECHO_API_KEY is not configured', async () => {
    const res = await app.fetch(
      new Request('https://worker/pipelines', { headers: { 'X-Echo-API-Key': 'anything' } }),
      fakeEnv({ ECHO_API_KEY: '' })
    );
    expect(res.status).toBe(503);
  });

  it('allows a protected route with the correct key (positive control)', async () => {
    const res = await app.fetch(
      new Request('https://worker/pipelines', {
        headers: { 'X-Echo-API-Key': 'correct-horse-battery-staple' },
      }),
      fakeEnv()
    );
    expect(res.status).toBe(200);
  });

  it('blocks pipeline creation without a key', async () => {
    const res = await app.fetch(
      new Request('https://worker/pipelines', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: 'test', source_type: 'static', destination_type: 'log' }),
      }),
      fakeEnv()
    );
    expect(res.status).toBe(401);
  });
});
