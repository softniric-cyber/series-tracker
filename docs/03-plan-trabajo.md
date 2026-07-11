# trackmyseries — Instrucciones de trabajo para el equipo

## 1. Organización

- **Monorepo** `series-tracker`: `/backend` (FastAPI), `/frontend` (React), `/docs` (estos documentos), `/.github/workflows`.
- **Git flow simplificado:** `main` protegida; ramas `feat/...`, `fix/...`; PR obligatoria con CI verde y 1 revisión.
- **Commits:** Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `test:`).
- **Gestión:** GitHub Projects con las historias de abajo como issues. Sprints de 2 semanas.

## 2. Convenciones de código

**Backend:** Python 3.12, `ruff` (lint + format), tipado obligatorio (mypy en CI), pytest con cobertura mínima 80 % en `services/`. Toda llamada externa (TMDB) mockeada en tests (`respx`).

**Frontend:** TypeScript estricto, ESLint + Prettier, componentes funcionales, TanStack Query para todo acceso a API (nada de fetch suelto), vitest + Testing Library para componentes con lógica.

**API:** cualquier cambio de contrato se refleja primero en el esquema OpenAPI (FastAPI lo genera) y se comunica en la PR.

## 3. Definición de Hecho (DoD)

Una historia está terminada cuando: código revisado y mergeado, tests pasando en CI, migración Alembic incluida si toca BD, desplegado en prod y probado manualmente, sin secretos en el repo.

## 4. Backlog por sprints

### Sprint 0 — Fundaciones (1 semana)
| ID | Tarea | Área |
|---|---|---|
| S0-1 | Crear monorepo, docker-compose local (Postgres), esqueleto FastAPI y Vite | Full |
| S0-2 | CI: lint + tests en PR; CD: autodeploy Render + Cloudflare Pages | DevOps |
| S0-3 | Provisionar Neon, Render, Cloudflare Pages; variables de entorno; API key TMDB | DevOps |
| S0-4 | Modelo de datos inicial + Alembic (tablas del doc de arquitectura §6) | Back |

### Sprint 1 — Usuarios y búsqueda
| ID | Historia | Criterio de aceptación |
|---|---|---|
| S1-1 | Registro y login con JWT (access+refresh) | Usuario se registra, entra y su sesión sobrevive a recargar |
| S1-2 | Perfil: país e idioma editables | PATCH /users/me funciona y afecta a llamadas TMDB |
| S1-3 | Cliente TMDB (`tmdb_client.py`) con retry y rate limit | Tests con mocks; búsqueda real en dev |
| S1-4 | Búsqueda de series (API + página de resultados) | Buscar "Severance" muestra resultados con póster en < 3 s |
| S1-5 | Frontend: layout base, rutas, login/registro | Navegación completa en móvil y escritorio |

### Sprint 2 — Ficha y seguimiento
| ID | Historia | Criterio de aceptación |
|---|---|---|
| S2-1 | Caché de series/episodios (caché-first, TTL 24 h / 7 d) | Segunda visita a una ficha no llama a TMDB |
| S2-2 | Ficha de serie con temporadas, episodios y "dónde verla" | Providers correctos según país del perfil |
| S2-3 | Seguir / dejar de seguir; página "Mis series" | Lista persiste entre sesiones |
| S2-4 | Marcar episodio/temporada como visto; progreso y "siguiente por ver" | Marcar T1 completa actualiza progreso al instante |

### Sprint 3 — Calendario y cierre MVP
| ID | Historia | Criterio de aceptación |
|---|---|---|
| S3-1 | Endpoint calendario + job diario de refresco (GitHub Actions cron) | Estrenos de próximos 30 días correctos tras el job |
| S3-2 | Vista calendario mes/semana en frontend | Entrada de estreno enlaza a la ficha |
| S3-3 | RGPD: baja con borrado y export de datos | DELETE /users/me elimina todo rastro |
| S3-4 | Rate limiting en auth, atribución TMDB, revisión de seguridad | Checklist de seguridad (§7 arquitectura) completa |
| S3-5 | Pruebas de aceptación del MVP (criterios del análisis funcional §8) | Los 5 criterios se cumplen en prod |

## 5. Reparto orientativo (equipo de 2-3)

- **Dev backend:** S0-4, S1-1..S1-3, S2-1, S3-1, S3-3.
- **Dev frontend:** S1-4, S1-5, S2-2..S2-4 (UI), S3-2.
- **Compartido/DevOps:** S0-1..S0-3, S3-4, S3-5.

Si es una sola persona (proyecto personal): mismo orden, ~6-8 semanas a tiempo parcial.

## 6. Primeros pasos (día 1)

1. Crear cuenta TMDB y solicitar API key (inmediato): https://www.themoviedb.org/settings/api
2. Crear proyectos en Neon, Render y Cloudflare Pages (todas con login GitHub).
3. `git init` del monorepo con el esqueleto y docker-compose.
4. Abrir los issues del Sprint 0 en GitHub Projects.

## 7. Referencias

- Análisis funcional: `01-analisis-funcional.md`
- Arquitectura técnica: `02-arquitectura-tecnica.md`
- TMDB API: https://developer.themoviedb.org/docs
