# Contributing

## Setup

```bash
git clone https://github.com/echoomegaprime/echo-data-pipeline.git
cd echo-data-pipeline
npm install
```

## Development loop

```bash
npm run typecheck                       # tsc --noEmit
npm test                                # vitest run
npx wrangler deploy --dry-run           # verify bindings without deploying
npm run dev                             # local dev server (wrangler dev)
```

## Adding a source or destination type

Add a case to `fetchSourceData()` / `writeDestination()` in `executor.ts`. If it writes to D1,
the table name MUST go through `validateTableName()` (add it to `TABLE_ALLOWLIST`) and every
column name through `validateColumnName()` — never interpolate a client-supplied identifier
into SQL text without both checks.

## Adding a transform type

Add a case to `executeTransformStep()` in `transforms.ts`, following the existing declarative
pattern (`map`/`filter`/`aggregate`/`enrich`). Never add a transform that evaluates a
client-supplied expression as code (`eval`, `new Function`, etc.) — every current transform's
config is data, not code, by design.

## Security-sensitive changes

Anything touching the auth middleware, `timingSafeEqual`, or the D1 source/destination
allowlists needs a test that would fail without the fix — see `SECURITY.md`'s history for why
(this repo has already had one real SQL injection fixed).
