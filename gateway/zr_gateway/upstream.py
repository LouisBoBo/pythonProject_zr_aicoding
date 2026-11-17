"""OpenAI-compatible upstream client. Provider keys never reach a client response."""

from __future__ import annotations

import httpx

from .config import DEFAULT_PROVIDER_ID, Provider, Settings


class UpstreamUnavailable(RuntimeError):
    """The upstream could not be reached, or failed twice before any bytes were forwarded."""


class Upstream:
    """Streams chat completions and retries once, but only before the client sees a status."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.upstream_timeout_seconds, connect=10.0),
            follow_redirects=False,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def send_chat(self, payload: dict, request_id: str, provider: Provider | None = None) -> httpx.Response:
        """@returns an open streaming response; callers must `aread()` or `aclose()` it."""
        target = provider if provider is not None else self._settings.provider(DEFAULT_PROVIDER_ID)
        if target is None:
            raise UpstreamUnavailable("upstream provider is not configured")
        url = f"{target.base_url}/chat/completions"
        headers = {
            "authorization": f"Bearer {target.key}",
            "content-type": "application/json",
            "accept": "text/event-stream, application/json",
            "x-request-id": request_id,
        }
        for attempt in (0, 1):
            try:
                request = self._client.build_request("POST", url, json=payload, headers=headers)
                response = await self._client.send(request, stream=True)
            except httpx.HTTPError as error:
                if attempt == 0:
                    continue
                raise UpstreamUnavailable(str(error)) from error
            if response.status_code >= 500:
                await response.aclose()
                if attempt == 1:
                    raise UpstreamUnavailable(f"upstream returned {response.status_code}")
                continue
            return response
        raise UpstreamUnavailable("upstream retry exhausted")
