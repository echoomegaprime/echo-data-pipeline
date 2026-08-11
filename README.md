# Echo Data Pipeline

> ETL/data pipeline orchestration Worker for the ECHO ecosystem.

## Overview

Define pipelines with a source, a chain of declarative transforms, and a destination. Runs on
demand or on a schedule, with per-step tracking, retries with exponential backoff, and a
priority queue processed every 10 minutes.

**Sources:** `http`, `d1` (SELECT-only, keyword-blocklisted, no destructive SQL), `kv`,
`shared_brain`, `knowledge_forge`, `static`.
**Transforms:** `map` (field rename/default), `filter` (eq/ne/gt/lt/gte/lte/contains/exists),
`aggregate` (group-by + count/sum/avg/min/max), `enrich` (static fields + concat/uppercase/
lowercase/timestamp computed fields). All declarative — no `eval`/`Function` execution.
**Destinations:** `kv`, `d1` (table allowlisted, column names validated against
`^[a-zA-Z_][a-zA-Z0-9_]{0,63}$`), `http`, `shared_brain`, `log`.

## Authentication

Every route except `GET /` and `GET /health` requires an `X-Echo-API-Key` header matching the
`ECHO_API_KEY` secret. An unconfigured key fails closed (503), never open.

```bash
npx wrangler secret put ECHO_API_KEY
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/`, `/health` | Liveness + dependency status (no auth) |
| `GET` | `/stats` | Fleet-wide pipeline/run stats (KV-cached 300s) |
| `GET` | `/pipelines` | List pipelines, filter by `status`/`source_type` |
| `GET` | `/pipelines/:id` | Full detail + last 10 runs |
| `POST` | `/pipelines` | Create a pipeline |
| `PUT` | `/pipelines/:id` | Update a pipeline |
| `DELETE` | `/pipelines/:id` | Delete a pipeline + its runs/steps/queue entries |
| `POST` | `/pipelines/:id/run` | Trigger a manual run |
| `POST` | `/pipelines/:id/pause` / `/resume` | Pause/resume |
| `GET` | `/pipelines/:id/runs` | Run history |
| `GET` | `/pipelines/:id/metrics` | Duration/throughput/retry metrics (KV-cached 300s) |
| `GET` | `/runs/:id` | Step-level run detail |
| `POST` | `/runs/:id/retry` | Retry a failed run |
| `GET` | `/queue` | View the pending queue |
| `POST` | `/queue/flush` | Process the queue immediately |

## Deployment

```bash
npm install
npx wrangler secret put ECHO_API_KEY
npx wrangler deploy
```

## Testing

```bash
npm run typecheck   # tsc --noEmit
npm test             # vitest run
npx wrangler deploy --dry-run
```

## Architecture

Hono on Cloudflare Workers. D1 (`DB`) stores pipeline definitions, runs, per-step tracking, and
the retry queue; KV (`CACHE`) caches stats/metrics. Three cron triggers: queue processing
(`*/10 * * * *`), hourly stats aggregation (`0 * * * *`), and daily cleanup of runs older than
30 days (`0 0 * * *`). Failed runs retry up to 3 times with exponential backoff (1s/2s/4s/8s)
before the pipeline is marked `error`.
