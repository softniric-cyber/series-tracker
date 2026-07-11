# trackmyseries — Checklist de seguridad (§7)

Revisión de seguridad del MVP (S3-4). Cada punto del §7 de la arquitectura, con su
estado y dónde vive en el código.

| # | Control | Estado | Dónde |
|---|---------|--------|-------|
| 1 | **JWT** access 30 min + refresh 30 días, refresh rotado | ✅ | `services/security.py`, `api/auth.py` (cada `/auth/refresh` emite un par nuevo) |
| 2 | Hash de contraseñas con **argon2** | ✅ | `services/security.py` (passlib/argon2) |
| 3 | **CORS** restringido al dominio del frontend | ✅ | `main.py` + `CORS_ORIGINS` (Render) |
| 4 | **HTTPS** forzado | ✅ | lo proveen Render (backend) y Cloudflare Pages (frontend) |
| 5 | **Rate limiting** por IP en auth (slowapi) contra fuerza bruta | ✅ | `core/ratelimit.py`, decoradores en `api/auth.py` (login 10/min, register 10/h, refresh 30/min) → 429 |
| 6 | Secreto JWT y token TMDB **solo en variables de entorno** del backend | ✅ | `core/config.py`; `.env` en `.gitignore`; nunca en el frontend |
| 7 | **RGPD**: borrado en cascada + export JSON | ✅ | `api/users.py` (`DELETE /users/me`, `GET /users/me/export`), `services/account.py` |
| 8 | **Atribución TMDB** visible | ✅ | `components/Footer.tsx` (texto + enlace, "no avalado ni certificado por TMDB") |

## Notas y limitaciones asumidas (MVP)

- **Rotación de refresh sin invalidación:** al refrescar se emite un refresh token
  nuevo, pero el anterior sigue siendo válido hasta su expiración (JWT stateless, sin
  denylist/tabla de tokens). Aceptable para el MVP; una denylist o `jti` en BD sería
  la mejora natural post-MVP.
- **Rate limiting en memoria:** el almacenamiento de slowapi es en proceso. Con el
  plan free de Render (una sola instancia) es suficiente; si se escala a varias
  instancias haría falta un backend compartido (Redis).
- **Validación de entrada:** Pydantic valida todos los cuerpos; los `tmdb_id`/paths
  llevan restricciones (`ge=1`, etc.). El acceso a datos ajenos está acotado por
  `current_user` en cada consulta (no hay IDOR: las queries filtran por `user_id`).
