"""A thin async HTTP client used by every scenario.

In dry-run mode no socket is opened: the client simulates a small, jittered
latency and returns success. This keeps a default checkout completely inert
while still exercising the concurrency machinery end to end.
"""

from __future__ import annotations

import asyncio
import random
from types import TracebackType

import aiohttp


class UpstreamError(Exception):
    """Raised when an upstream returns a non-2xx status or the call fails."""


class ProviderClient:
    """Fires JSON POSTs at upstream endpoints, honouring a dry-run switch."""

    def __init__(self, *, dry_run: bool, timeout_seconds: float) -> None:
        self._dry_run = dry_run
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> ProviderClient:
        if not self._dry_run:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None

    async def post_json(self, url: str, payload: dict) -> None:
        """POST ``payload`` as JSON to ``url``, raising :class:`UpstreamError` on failure."""
        if self._dry_run or not url:
            # Simulate a fast internal service without touching the network.
            await asyncio.sleep(random.uniform(0.0005, 0.003))
            return

        assert self._session is not None  # entered via async context manager
        try:
            async with self._session.post(url, json=payload) as resp:
                if resp.status >= 400:
                    raise UpstreamError(f"{url} -> HTTP {resp.status}")
        except aiohttp.ClientError as exc:  # network/timeout/connection errors
            raise UpstreamError(f"{url} -> {exc}") from exc
