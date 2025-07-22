"""Moonshot API client wrapper using OpenAI-compatible SDK.

Provides synchronous and asynchronous chat completion helpers
configured for the Kimi-K2-Instruct model. All agent code should
import this client instead of talking to `openai` directly so that
any future API changes can be handled in one place.

Environment variables recognised:
- MOONSHOT_API_KEY         (required)
- MOONSHOT_BASE_URL        (optional, default https://api.moonshot.ai/v1)
- MOONSHOT_DEFAULT_MODEL   (optional, default kimi-k2-0711-preview)
"""
from __future__ import annotations

import os
from typing import List, Dict, Any, Optional

from openai import OpenAI, AsyncOpenAI  # OpenAI-compatible SDK works for Moonshot

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_URL: str = os.getenv("MOONSHOT_BASE_URL", "https://api.moonshot.ai/v1")
DEFAULT_MODEL: str = os.getenv("MOONSHOT_DEFAULT_MODEL", "kimi-k2-0711-preview")


class MoonshotClient:
    """Thin wrapper around the OpenAI-compatible Moonshot endpoints."""

    def __init__(self,
                 api_key: Optional[str] = None,
                 model: str = DEFAULT_MODEL,
                 base_url: str = BASE_URL) -> None:
        self.api_key: str | None = api_key or os.getenv("MOONSHOT_API_KEY")
        if not self.api_key:
            raise EnvironmentError(
                "MOONSHOT_API_KEY environment variable is not set.")

        self.model = model
        self.base_url = base_url.rstrip("/")

        # -----------------------------------------------------------------
        # Work around httpx>=1.0 where the `proxies` argument was removed.
        # OpenAI SDK <2.0 passes `proxies` when constructing its own internal
        # httpx.Client, which raises TypeError. We detect this and create our
        # own http_client compatible with the current httpx version.
        # -----------------------------------------------------------------
        import httpx  # local import to avoid mandatory dependency if unused

        def _supports_proxies() -> bool:
            try:
                httpx.Client(proxies=None)
                return True
            except TypeError:
                return False

        if _supports_proxies():
            # Standard path – httpx still supports the parameter
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            self._aclient = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        else:
            # Create custom http_client without unsupported kwargs
            sync_http_client = httpx.Client(follow_redirects=False, timeout=60)
            async_http_client = httpx.AsyncClient(follow_redirects=False, timeout=60)
            self._client = OpenAI(api_key=self.api_key,
                                  base_url=self.base_url,
                                  http_client=sync_http_client)
            self._aclient = AsyncOpenAI(api_key=self.api_key,
                                         base_url=self.base_url,
                                         http_client=async_http_client)

    # ---------------------------------------------------------------------
    # Helper methods
    # ---------------------------------------------------------------------
    def chat_completion(self, messages: List[Dict[str, str]], **kwargs: Any) -> Dict[str, Any]:
        """Synchronous chat completion call with built-in retry/back-off.

        Automatically adds a generous default timeout (120 s) and retries
        transient errors such as RateLimit or APITimeout up to 3 times with
        exponential back-off.
        """
        import time
        from openai import RateLimitError, APITimeoutError, APIError
        
        # Apply default request timeout if caller didn't specify one
        kwargs.setdefault("timeout", 120)
        max_attempts = 3
        backoff = 1.0

        for attempt in range(1, max_attempts + 1):
            try:
                resp = self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    **kwargs
                )
                return resp.model_dump()
            except (RateLimitError, APITimeoutError, APIError) as exc:
                if attempt == max_attempts:
                    raise  # Bubble up after final attempt
                time.sleep(backoff)
                backoff *= 2

        """Synchronous chat completion call.

        Example:
            messages = [
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "Hello"}
            ]
            response = client.chat_completion(messages, temperature=0.3)
        """
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            **kwargs
        )
        return resp.model_dump()

    async def a_chat_completion(self, messages: List[Dict[str, str]], **kwargs: Any) -> Dict[str, Any]:
        """Asynchronous chat completion with retry/back-off."""
        import asyncio
        from openai import RateLimitError, APITimeoutError, APIError

        kwargs.setdefault("timeout", 120)
        max_attempts = 3
        backoff = 1.0

        for attempt in range(1, max_attempts + 1):
            try:
                resp = await self._aclient.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    **kwargs
                )
                return resp.model_dump()
            except (RateLimitError, APITimeoutError, APIError):
                if attempt == max_attempts:
                    raise
                await asyncio.sleep(backoff)
                backoff *= 2

        """Asynchronous chat completion call."""
        resp = await self._aclient.chat.completions.create(
            model=self.model,
            messages=messages,
            **kwargs
        )
        return resp.model_dump()

    # Convenience wrapper returning just the string content
    def chat_completion_text(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        resp = self.chat_completion(messages, **kwargs)
        return resp.choices[0].message.content  # type: ignore[attr-defined]

    async def a_chat_completion_text(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        resp_dict = await self.a_chat_completion(messages, **kwargs)
        return resp_dict['choices'][0]['message']['content']


__all__ = ["MoonshotClient"]
