"""Tests del servicio de email (Resend) — S3-6.

Sin API key el envío es un no-op (log). Con API key, hace POST a Resend con el
Bearer y el destinatario/enlace correctos (mockeado con respx).
"""

import httpx
import pytest
import respx

from app.core.config import get_settings
from app.services.email import send_password_reset


async def test_noop_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "resend_api_key", "")
    # Sin rutas respx registradas: si intentara enviar, fallaría. No debe intentarlo.
    await send_password_reset("u@example.com", "https://x/reset-password?token=abc")


@respx.mock
async def test_posts_to_resend_with_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "resend_api_key", "test-key")
    route = respx.post("https://api.resend.com/emails").mock(
        return_value=httpx.Response(200, json={"id": "abc"})
    )
    await send_password_reset("u@example.com", "https://trackmyseries.com/reset-password?token=xyz")

    assert route.called
    request = route.calls.last.request
    assert request.headers["authorization"] == "Bearer test-key"
    body = request.content.decode()
    assert "u@example.com" in body
    assert "reset-password?token=xyz" in body
