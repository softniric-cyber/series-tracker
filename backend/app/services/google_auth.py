"""Verificación de ID tokens de Google (Sign in with Google).

El frontend obtiene un ID token (JWT firmado por Google) mediante Google Identity
Services y lo envía al backend. Aquí se valida contra las claves públicas de Google
(firma RS256, audiencia = nuestro client ID, emisor y expiración) usando `pyjwt` +
`PyJWKClient` (que descarga y cachea el JWKS con la stdlib, sin dependencias extra).
"""

from dataclasses import dataclass
from urllib.error import URLError

import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientError

# JWKS público de Google y emisores válidos del ID token (OpenID Connect).
_GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
_GOOGLE_ISSUERS = frozenset({"accounts.google.com", "https://accounts.google.com"})

# El cliente cachea las claves de firma entre peticiones.
_jwk_client = PyJWKClient(_GOOGLE_CERTS_URL)


@dataclass(frozen=True)
class GoogleIdentity:
    """Datos de identidad extraídos de un ID token de Google verificado."""

    sub: str
    email: str
    name: str | None


class GoogleTokenError(Exception):
    """El ID token de Google es inválido, ha caducado o no se pudo verificar."""


def verify_google_token(credential: str, client_id: str) -> GoogleIdentity:
    """Valida el ID token de Google y devuelve la identidad; lanza GoogleTokenError si no."""
    if not client_id:
        raise GoogleTokenError("Google auth no está configurado")
    try:
        signing_key = _jwk_client.get_signing_key_from_jwt(credential)
        claims = jwt.decode(
            credential,
            signing_key.key,
            algorithms=["RS256"],
            audience=client_id,
        )
    except (jwt.PyJWTError, PyJWKClientError, URLError) as exc:
        raise GoogleTokenError(str(exc)) from exc

    if claims.get("iss") not in _GOOGLE_ISSUERS:
        raise GoogleTokenError("emisor no válido")
    email = claims.get("email")
    if not email:
        raise GoogleTokenError("el token no incluye email")
    # Exigimos email verificado: la vinculación de cuentas se hace por email, así que
    # un email sin verificar permitiría suplantar una cuenta existente.
    if not claims.get("email_verified"):
        raise GoogleTokenError("email no verificado por Google")

    return GoogleIdentity(
        sub=str(claims["sub"]),
        email=str(email).strip().lower(),
        name=claims.get("name"),
    )
