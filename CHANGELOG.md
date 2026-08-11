# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

### Fixed
- Auth middleware: split the misconfigured-secret case into an explicit 503, and switched the
  API-key comparison to constant-time `timingSafeEqual` (was already fail-closed, but a raw
  `!==` is a timing side-channel on the key).
- `npm audit`: resolved all 7 findings to 0 — `hono` (direct prod dep) and wrangler's dev-only
  toolchain both via `npm audit fix --force`, verified via `wrangler deploy --dry-run`.

### Added
- First test suite: `vitest`, 10 tests covering `timingSafeEqual` and all four auth states.
- `README.md` (none existed previously), `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`,
  `.github/` templates + CI. `LICENSE` added matching the pre-existing `"license": "ISC"`
  declaration in `package.json`.

### Reviewed, not changed
- D1 source/destination SQL injection hardening (table allowlist, column-name validation,
  SELECT-only + keyword-blocklisted source queries) — already solid from a prior fix
  (`c8803d8`), confirmed correct.

## [1.0.0] and earlier

See git history — this file starts tracking from the current consolidation pass forward.
