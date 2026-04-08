from __future__ import annotations

import time
from typing import Any

import httpx

from ..config import BrainSettings, load_settings
from .types import ProviderStatus


class OpenAICompatibleProvider:
    def __init__(self, settings: BrainSettings | None = None) -> None:
        self._settings = settings or load_settings()
        self._last_probe_at = 0.0
        self._last_status: ProviderStatus = {
            "configured": self.is_configured(),
            "mode": "openai_compatible",
            "model": self._settings.model_name,
            "reachable": False,
        }

    def is_configured(self) -> bool:
        return bool(self._settings.model_base_url and self._settings.model_name)

    def snapshot(self, *, force: bool = False) -> ProviderStatus:
        configured = self.is_configured()
        if not configured:
            self._last_status = {
                "configured": False,
                "mode": "openai_compatible",
                "model": self._settings.model_name,
                "reachable": False,
            }
            return self._last_status

        now = time.time()
        if not force and now - self._last_probe_at < 15:
            return self._last_status

        reachable = False
        try:
            headers = self._headers()
            with httpx.Client(base_url=self._settings.model_base_url, timeout=2.0, headers=headers) as client:
                response = client.get("/models")
                reachable = response.status_code < 500
        except Exception:
            reachable = False

        self._last_probe_at = now
        self._last_status = {
            "configured": True,
            "mode": "openai_compatible",
            "model": self._settings.model_name,
            "reachable": reachable,
        }
        return self._last_status

    async def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        if not self.is_configured():
            raise RuntimeError("External provider is not configured")

        payload = {
            "model": self._settings.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.3,
        }
        async with httpx.AsyncClient(
            base_url=self._settings.model_base_url,
            timeout=self._settings.http_timeout_sec,
            headers=self._headers(),
        ) as client:
            response = await client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
        content = self._extract_content(data)
        if not content.strip():
            raise RuntimeError("External provider returned an empty response")
        self._last_status = {
            "configured": True,
            "mode": "openai_compatible",
            "model": self._settings.model_name,
            "reachable": True,
        }
        self._last_probe_at = time.time()
        return content.strip()

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._settings.model_api_key:
            headers["Authorization"] = f"Bearer {self._settings.model_api_key}"
        return headers

    def _extract_content(self, payload: Any) -> str:
        if not isinstance(payload, dict):
            return ""
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            return ""
        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            return ""
        message = first_choice.get("message")
        if not isinstance(message, dict):
            return ""
        content = message.get("content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and isinstance(item.get("text"), str):
                    parts.append(item["text"])
            return "\n".join(parts)
        return ""
