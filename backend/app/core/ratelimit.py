"""Limitador de tasa por IP para los endpoints de auth (slowapi) — S3-4.

Protege registro/login/refresh contra fuerza bruta. Se desactiva en los tests
(`limiter.enabled = False` en conftest) para no interferir con los muchos
registros/logins que hacen. Los límites concretos viven en la config.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings

limiter = Limiter(key_func=get_remote_address, enabled=get_settings().rate_limit_enabled)
