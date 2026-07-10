"""Envío de email transaccional vía Resend (S3-6).

Se usa para el enlace de recuperación de contraseña. Si no hay `RESEND_API_KEY`
configurada (dev/tests), no se envía nada: el enlace se registra en el log, de
modo que el flujo completo es probable en local sin proveedor de email.
"""

import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger("app.email")

_RESEND_URL = "https://api.resend.com/emails"


def _reset_html(reset_link: str, minutes: int) -> str:
    return (
        f"<p>Has solicitado restablecer tu contraseña en SeriesTracker.</p>"
        f'<p><a href="{reset_link}">Pulsa aquí para elegir una nueva contraseña</a> '
        f"(el enlace caduca en {minutes} minutos).</p>"
        f"<p>Si no has sido tú, ignora este correo: tu contraseña no cambiará.</p>"
    )


async def send_password_reset(to_email: str, reset_link: str) -> None:
    settings = get_settings()
    if not settings.resend_api_key:
        # Degradado para dev/tests: no se envía, se registra el enlace.
        logger.warning(
            "RESEND_API_KEY sin configurar. Enlace de reset para %s: %s", to_email, reset_link
        )
        return
    payload = {
        "from": settings.email_from,
        "to": [to_email],
        "subject": "Restablece tu contraseña — SeriesTracker",
        "html": _reset_html(reset_link, settings.reset_token_minutes),
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                _RESEND_URL,
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json=payload,
            )
            resp.raise_for_status()
    except httpx.HTTPError:
        # No propagamos: el endpoint responde igual (anti-enumeración) y el fallo se registra.
        logger.exception("Fallo enviando el email de reset a %s", to_email)
