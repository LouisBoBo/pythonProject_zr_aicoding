"""Delegate credential checks to the MES login endpoint. MES passwords never touch the gateway store."""

from __future__ import annotations

import httpx

from .config import Settings


class MesUnavailable(RuntimeError):
    """MES login could not be reached or answered abnormally."""


class MesLogin:
    """One-way check: returns whether MES accepted the credentials."""

    def __init__(self, settings: Settings):
        self._client = httpx.AsyncClient(
            base_url=settings.mes_base_url,
            timeout=httpx.Timeout(settings.mes_timeout_seconds, connect=5.0),
            follow_redirects=False,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def verify(self, username: str, password: str, request_id: str) -> bool:
        """@returns whether MES accepted the credentials; 401 is a plain `False`, not an error."""
        try:
            response = await self._client.post(
                "/api/auth/login",
                json={"username": username, "password": password},
                headers={"accept": "application/json", "x-request-id": request_id},
            )
        except httpx.HTTPError as error:
            raise MesUnavailable(str(error)) from error
        if response.status_code == 200:
            return True
        if response.status_code == 401:
            return False
        raise MesUnavailable(f"mes login returned {response.status_code}")
