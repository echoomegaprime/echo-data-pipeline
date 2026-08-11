# Security Policy

## Supported Versions

Only the latest deployed revision of `echo-data-pipeline` receives security fixes.

## Reporting a Vulnerability

Do not open a public GitHub issue for a suspected vulnerability. Email **security@echo-ept.com**.

## Fixed This Pass

### Auth comparison timing side-channel (hardening, fixed)

The auth middleware (`!c.env.ECHO_API_KEY || apiKey !== c.env.ECHO_API_KEY`) was already
fail-closed by construction — an unconfigured secret correctly denied every request, unlike the
fail-open pattern found elsewhere in this consolidation campaign. The raw `!==` comparison was
still a timing side-channel on the key itself. Fixed by splitting the misconfigured-service case
into an explicit `503` and switching the key comparison to constant-time `timingSafeEqual`.

## Already Solid (reviewed, not changed)

This repo's git history shows a prior real fix: `c8803d8 security: fix SQL injection in D1
source and destination handlers`. Reviewed the current state of that code carefully given that
history:

- **D1 destination writes** (`writeDestination`, `executor.ts`): table names checked against a
  fixed allowlist (`TABLE_ALLOWLIST`); column names validated against
  `^[a-zA-Z_][a-zA-Z0-9_]{0,63}$` before being interpolated into the `INSERT`/`DELETE` statement
  text; all values bound as parameters. Genuinely sound.
- **D1 source queries** (`fetchSourceData`, `executor.ts`): only `SELECT`-prefixed queries
  allowed; a keyword blocklist (`DROP|DELETE|INSERT|UPDATE|ALTER|CREATE|ATTACH|DETACH|PRAGMA`)
  additionally rejects dangerous subquery patterns even within a `SELECT`.
- **Transform pipeline** (`transforms.ts`): every transform (`map`/`filter`/`aggregate`/
  `enrich`) is a fixed declarative operation — no `eval`, `Function`, or dynamic code execution
  of any user-supplied expression.

No further vulnerabilities found in this pass.

## Design Notes

- Single-tenant internal service — `ECHO_API_KEY` gates the whole API, no per-record ownership
  model is needed (unlike multi-tenant services in this fleet).
- `http` source/destination configs let an authenticated caller point this Worker at an
  arbitrary URL — acceptable for an internal orchestration tool behind `ECHO_API_KEY`, not
  exposed to untrusted input.
