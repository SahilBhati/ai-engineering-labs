"""Client for an OpenAI-compatible speech endpoint (the Kokoro server, D7)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import httpx
from loguru import logger


class KokoroClient:
    """Adapter over ``POST /v1/audio/speech``; streams raw 16-bit mono PCM."""

    def __init__(
        self,
        url: str,
        *,
        voice: str = "af_sky",
        timeout: float = 30.0,
        restart_wait: float = 30.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.url = url
        self.voice = voice
        # VoiceMode's Kokoro exits after 25 requests and launchd restarts it (~20 s);
        # wait that out instead of failing every 26th reply (backlog H4).
        self.restart_wait = restart_wait
        self._client = client or httpx.AsyncClient(timeout=timeout)

    async def stream(self, text: str) -> AsyncIterator[bytes]:
        """Yield PCM as the server produces it, each chunk a whole number of samples."""
        body = {"model": "kokoro", "input": text, "voice": self.voice, "response_format": "pcm"}
        response = await self._send(self._client.build_request("POST", self.url, json=body))
        try:
            response.raise_for_status()
            carry = b""
            async for chunk in response.aiter_bytes():
                chunk = carry + chunk
                cut = len(chunk) - len(chunk) % 2
                carry = chunk[cut:]
                if cut:
                    yield chunk[:cut]
        finally:
            await response.aclose()

    async def _send(self, request: httpx.Request) -> httpx.Response:
        """Send, retrying connect errors only, for up to ``restart_wait`` seconds."""
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.restart_wait
        while True:
            try:
                return await self._client.send(request, stream=True)
            except httpx.ConnectError:
                if loop.time() >= deadline:
                    raise
                logger.warning("Kokoro unreachable; waiting for it to restart")
                await asyncio.sleep(1.0)

    async def aclose(self) -> None:
        await self._client.aclose()
