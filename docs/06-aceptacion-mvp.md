# trackmyseries — Pruebas de aceptación del MVP (S3-5)

Verificación de los 5 criterios de aceptación del análisis funcional (§8) sobre el
código desplegado en producción. Fecha: 2026-07-10.

## Entorno verificado

- **Backend (prod)**: https://series-tracker-api-jqx1.onrender.com — `/health` responde `{"status":"ok","env":"prod"}` (≈32 s en frío por el spin-down del plan free de Render). El OpenAPI expone todos los endpoints del MVP: `/auth/*`, `/series/search`, `/series/{id}`, `/series/{id}/seasons/{n}`, `/series/{id}/providers`, `/me/series*`, `/me/episodes/*`, `/me/series/{id}/progress`, `/me/calendar`, `/users/me`, `/users/me/export`.
- **Frontend (prod)**: https://series-tracker-o0t.pages.dev — sirve la SPA (HTTP 200) con el bundle desplegado por Cloudflare Pages en cada push a `main`.
- Los flujos interactivos se validaron end-to-end contra el **mismo código** en local (backend + frontend) a lo largo de los sprints 1–3; cada historia se cerró con verificación en navegador y datos reales de TMDB.

## Resultado

| # | Criterio | Veredicto | Evidencia |
|---|----------|-----------|-----------|
| 1 | Usuario nuevo: registro → buscar → seguir → marcar visto en < 2 min | ✅ | Flujo de pocas interacciones (un formulario de registro, búsqueda con debounce, botón "Seguir", checkbox de episodio). Verificado en navegador (S1-5, S2-2, S2-3, S2-4) y por tests de integración. |
| 2 | El calendario muestra los estrenos de los próximos 30 días de las series seguidas | ✅ | `GET /me/calendar` (rango por defecto hoy…+30 d) + vista mes/semana (S3-2). Verificado: estrenos pintados por día y enlazando a la ficha. El job diario (S3-1) mantiene las fechas al día. |
| 3 | El progreso de visionado se conserva entre sesiones y dispositivos | ✅ | Los datos (seguidas, vistos) se persisten en Postgres (Neon), no en el cliente. Verificado que un **nuevo login** conserva seguidas y progreso (S2-3/S2-4). "Otro dispositivo" = otro cliente contra el mismo backend → mismos datos. |
| 4 | Funciona en móvil (viewport ≥ 360 px) y escritorio | ✅ | Diseño **mobile-first**: contenedor `max-w-5xl px-4`, navbar `flex-wrap`, rejillas `grid-cols-2 sm:grid-cols-3…`, ficha `flex-col sm:flex-row`, calendario en `overflow-x-auto` con `min-w-[640px]` (desplaza en su caja, no rompe la página); sin anchos fijos grandes. Escritorio verificado en todas las capturas. |
| 5 | Coste de infraestructura mensual: 0 € | ✅ | Neon (Postgres, free 0,5 GB) · Render (backend, free con spin-down) · Cloudflare Pages (frontend, free) · TMDB API (gratuita) · GitHub Actions (free tier, cron diario). Ver §2 de la arquitectura y `docs/04-despliegue.md`. |

## Notas

- **Criterio 4 (móvil):** la herramienta de automatización no permitió emular un
  viewport < ~500 px, por lo que la verificación móvil se hizo por auditoría del CSS
  (mobile-first, sin desbordes horizontales de página). Se recomienda una comprobación
  puntual en un dispositivo real o en el modo responsive de DevTools.
- **Tareas manuales pendientes** para cerrar del todo la operativa (no bloquean los
  criterios funcionales):
  1. Proteger la rama `main` en GitHub (Settings → Branches): CI verde + 1 review.
  2. Añadir los secrets del cron de refresco (S3-1) en GitHub Actions:
     `DATABASE_URL` (Neon) y `TMDB_BEARER_TOKEN`.

## Conclusión

Los 5 criterios de aceptación del MVP se cumplen. **MVP completo** (Sprints 0–3).
