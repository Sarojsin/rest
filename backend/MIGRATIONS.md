# Migrations

The database schema is managed with Alembic. `app/main.py` bootstraps `create_all` +
`seed_if_empty` only in development/tests; in production (`APP_ENV=production`) startup
**fails fast** unless the database is at the latest Alembic head.

Alembic reads the database URL from the app settings (`DATABASE_URL` env var or `.env`),
so the server and migrations always target the same database.

## Common commands (run from `backend/`)

```bash
venv/Scripts/python.exe -m alembic upgrade head      # apply pending migrations
venv/Scripts/python.exe -m alembic current           # show applied revision
venv/Scripts/python.exe -m alembic check             # models vs migrations drift check
venv/Scripts/python.exe -m alembic stamp head        # adopt an existing DB as-is (dev only)
venv/Scripts/python.exe -m alembic revision --autogenerate -m "describe change"
```

## Adding a model/schema change

1. Edit the SQLAlchemy models in `app/models/`.
2. `alembic revision --autogenerate -m "..."`, review the generated script (SQLite-friendly
   alter handling is limited — check it actually works for the DB you target).
3. `alembic upgrade head`, then `alembic check` and run the test suite.

## Current state

- `ed02e9ab12e0_baseline_schema` — full initial schema (includes `menu_item.image_path`,
  `image_emoji`, `model_path`, the `service_calls` table, and payment method config).
- The dev database (`data/restaurant.db`) is stamped at this revision; tests bootstrap
  their own disposable databases via `create_all`.
