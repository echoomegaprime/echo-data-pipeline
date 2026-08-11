## What

## Why

## Testing

- [ ] `npm run typecheck` passes
- [ ] `npm test` passes
- [ ] `npx wrangler deploy --dry-run` succeeds
- [ ] If adding a D1 destination/source: table name added to the allowlist, column names go
      through `validateColumnName()`
- [ ] If touching auth/`timingSafeEqual`: added a test that would fail without the fix
