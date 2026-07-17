# Tend - todos & recurring maintenance

A self-hosted todo service built for the stuff that comes back: house maintenance, car oil changes, filter swaps.
Every task carries its own details (oil type, filter model, part numbers) so you never look them up twice, and your phone gets a ping when something is coming due.

## Features

* Tasks with details, a category, a due date, and an optional step-by-step checklist.
* Recurring tasks: every N days/weeks/months/years, either on a fixed schedule ("gutters every April") or re-anchored on completion ("oil change 6 months after the last one").
  Completing an occurrence automatically schedules the next one and keeps the full history per task.
* Phone notifications through [ntfy](https://ntfy.sh): one ping when a task enters its reminder window and a high-priority one on the due date, only during waking hours.
  Reminders missed while the server was off are sent on the next pass, never twice.
* Installable as an iOS home-screen app (web manifest + icons included).

## Architecture

| Piece | Tech | Image |
| --- | --- | --- |
| frontend | React + Vite SPA served by unprivileged nginx, which proxies `/api` | `ghcr.io/<owner>/todo-frontend` |
| backend | FastAPI + SQLAlchemy (async), uvicorn, background reminder loop | `ghcr.io/<owner>/todo-backend` |
| database | Postgres 16 (SQLite fallback for bare local dev) | `postgres:16-alpine` |

### Backend configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | SQLite in `./data` | Async SQLAlchemy URL |
| `NTFY_TOPIC` | *(empty = reminders off)* | ntfy topic to publish reminders to; treat it like a password |
| `NTFY_URL` | `https://ntfy.sh` | ntfy server |
| `NTFY_TOKEN` | *(empty)* | Bearer token for protected ntfy servers |
| `TIMEZONE` | `America/New_York` | Decides "today" and the notification window |
| `NOTIFY_FROM_HOUR` / `NOTIFY_UNTIL_HOUR` | `8` / `21` | Local hours when reminders may fire |
| `APP_URL` | *(empty)* | Absolute app URL; makes notifications tappable |

## Local development

Full stack (what production runs, built from source):

```sh
docker compose -f compose.dev.yaml up --build
# app on http://localhost:8086
```

Hot-reload loop:

```sh
cd backend && uv sync && uv run uvicorn app.main:app --reload   # API on :8000
cd frontend && npm install && npm run dev                        # UI on :5173, proxies /api
```

Tests:

```sh
cd backend && uv run pytest
cd frontend && npm run build   # includes typecheck
```

## Deployment

Pushes to `main` (and `v*` tags) run tests, then build and push multi-arch images to GHCR via `.github/workflows/build-images.yml`.
The home server deploys them with the stack in the sister repo: `home-server/stacks/todo/compose.yaml`, reachable over the tailnet at `https://todo.<tailnet>.ts.net`.

## Phone notifications setup

1. Generate a private topic name: `openssl rand -hex 12`.
2. Set `NTFY_TOPIC` in the stack's `.env` and restart the backend.
3. Install the ntfy app on your iPhone and subscribe to the same topic.
4. Open Settings in the web app and hit "Send test notification".
