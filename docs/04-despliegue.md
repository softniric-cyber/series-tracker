# trackmyseries — Despliegue (Sprint 0)

## CI (automático)

`.github/workflows/ci.yml` corre en cada PR y push a `main`:

- **Backend:** `ruff check`, `ruff format --check`, `mypy app`, `pytest`.
- **Frontend:** `oxlint`, `vite build`.

Marca `main` como protegida y exige CI verde + 1 revisión (Settings > Branches).

## CD (autodeploy)

### Backend → Render

1. Neon: crear proyecto Postgres y copiar la connection string (`postgresql+psycopg://...`).
2. Render: **New > Blueprint**, conectar este repo (usa `render.yaml`).
3. En el servicio, pestaña **Environment**, rellenar los secretos (`sync: false`):
   - `DATABASE_URL` (de Neon)
   - `JWT_SECRET` (`python -c "import secrets; print(secrets.token_urlsafe(48))"`)
   - `TMDB_BEARER_TOKEN` (token v4 de https://www.themoviedb.org/settings/api)
   - `CORS_ORIGINS` (URL del frontend en Cloudflare Pages)
4. `autoDeploy: true` ya despliega en cada push a `main`.

### Frontend → Cloudflare Pages

1. Cloudflare Pages: **Create > Connect to Git**, seleccionar este repo.
2. Configuración de build:
   - Root directory: `frontend`
   - Build command: `npm run build`
   - Output directory: `dist`
3. Variable de build `VITE_API_URL` = URL pública del backend en Render.

## Checklist Sprint 0

- [x] S0-1 Monorepo, docker-compose, esqueleto FastAPI + Vite
- [x] S0-2 CI (lint + tests en PR); CD configurado (`render.yaml` + Pages)
- [ ] S0-3 Provisionar Neon / Render / Cloudflare Pages + secretos (manual)
- [x] S0-4 Modelo de datos + migración Alembic inicial
