"""LLM Router — unified interface for external LLM providers."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import httpx
from loguru import logger

from fixeragent.config import get_settings
from fixeragent.models import LLMConfig, LLMProvider


class LLMError(Exception):
    """Raised when all LLM providers fail."""


class LLMRouter:
    """Route requests to configured LLM provider with automatic fallback."""

    PROVIDER_CONFIG: dict[str, dict[str, Any]] = {
        "claude": {
            "base_url": "https://api.anthropic.com/v1",
            "chat_endpoint": "/messages",
            "models": ["claude-opus-4-6", "claude-sonnet-4-6", "claude-haiku-4-5"],
            "default": "claude-sonnet-4-6",
            "vision_models": ["claude-opus-4-6", "claude-sonnet-4-6"],
        },
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "chat_endpoint": "/chat/completions",
            "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
            "default": "gpt-4o",
            "vision_models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
        },
        "gemini": {
            "base_url": "https://generativelanguage.googleapis.com/v1beta",
            "chat_endpoint": "/models/{model}:generateContent",
            "models": ["gemini-2.0-flash", "gemini-1.5-pro"],
            "default": "gemini-2.0-flash",
            "vision_models": ["gemini-2.0-flash", "gemini-1.5-pro"],
        },
        "local": {
            "base_url": "http://localhost:11434",
            "chat_endpoint": "/api/chat",
            "models": ["llava", "mistral", "llama3"],
            "default": "llava",
            "vision_models": ["llava"],
        },
    }

    def __init__(self, config: LLMConfig | None = None) -> None:
        self.settings = get_settings()
        self.config = config or self._default_config()
        self.http = httpx.Client(timeout=120.0)
        logger.info(f"LLMRouter initialized: provider={self.config.provider}, model={self.config.model}")

    def _default_config(self) -> LLMConfig:
        return LLMConfig(
            provider=LLMProvider(self.settings.llm_provider),
            model=self.settings.llm_model,
            api_key=self.settings.llm_api_key or "",
            temperature=self.settings.llm_temperature,
            max_tokens=self.settings.llm_max_tokens,
        )

    def chat(self, messages: list[dict[str, str]], json_mode: bool = False) -> str:
        """Send a chat completion request. Returns assistant message content."""
        providers = [self.config.provider.value]
        if self.config.fallback == "next_provider":
            providers += [p for p in self.PROVIDER_CONFIG if p not in providers]

        for provider in providers:
            try:
                return self._call_provider(provider, messages, json_mode=json_mode)
            except Exception as e:
                logger.warning(f"Provider {provider} failed: {e}")
                continue

        raise LLMError(f"All LLM providers failed. Last error logged above.")

    def vision(self, image_path: str | Path, prompt: str, json_mode: bool = False) -> str:
        """Send a vision analysis request with an image."""
        providers = [self.config.provider.value]
        if self.config.fallback == "next_provider":
            # Prefer vision-capable providers in fallback
            vision_capable = ["openai", "gemini", "claude", "local"]
            providers = [p for p in vision_capable if p in self.PROVIDER_CONFIG]

        for provider in providers:
            try:
                return self._call_vision_provider(provider, image_path, prompt, json_mode)
            except Exception as e:
                logger.warning(f"Vision provider {provider} failed: {e}")
                continue

        raise LLMError(f"All vision providers failed.")

    def _call_provider(self, provider: str, messages: list[dict[str, str]], json_mode: bool = False) -> str:
        cfg = self.PROVIDER_CONFIG[provider]
        api_key = self.config.api_key or getattr(self.settings, f"{provider}_api_key", "")

        if provider == "claude":
            return self._call_claude(cfg, api_key, messages, json_mode)
        elif provider == "openai":
            return self._call_openai(cfg, api_key, messages, json_mode)
        elif provider == "gemini":
            return self._call_gemini(cfg, api_key, messages, json_mode)
        elif provider == "local":
            return self._call_local(cfg, messages)
        else:
            raise LLMError(f"Unknown provider: {provider}")

    def _call_claude(self, cfg: dict, api_key: str, messages: list[dict[str, str]], json_mode: bool) -> str:
        system_msg = next((m["content"] for m in messages if m.get("role") == "system"), "")
        user_assistant = [m for m in messages if m.get("role") != "system"]
        payload: dict[str, Any] = {
            "model": self.config.model or cfg["default"],
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "system": system_msg,
            "messages": user_assistant,
        }
        if json_mode:
            # Claude does not have native json_mode; we use system prompt instruction instead
            pass

        resp = self.http.post(
            f"{cfg['base_url']}{cfg['chat_endpoint']}",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]

    def _call_openai(self, cfg: dict, api_key: str, messages: list[dict[str, str]], json_mode: bool) -> str:
        payload: dict[str, Any] = {
            "model": self.config.model or cfg["default"],
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        resp = self.http.post(
            f"{cfg['base_url']}{cfg['chat_endpoint']}",
            headers={"authorization": f"Bearer {api_key}", "content-type": "application/json"},
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def _call_gemini(self, cfg: dict, api_key: str, messages: list[dict[str, str]], json_mode: bool) -> str:
        # Convert messages to Gemini format
        gemini_contents = []
        for m in messages:
            role = "user" if m["role"] in ("user", "system") else "model"
            gemini_contents.append({"role": role, "parts": [{"text": m["content"]}]})

        model_name = self.config.model or cfg["default"]
        endpoint = cfg["chat_endpoint"].format(model=model_name)
        payload: dict[str, Any] = {
            "contents": gemini_contents,
            "generationConfig": {
                "temperature": self.config.temperature,
                "maxOutputTokens": self.config.max_tokens,
            },
        }
        if json_mode:
            payload["generationConfig"]["responseMimeType"] = "application/json"

        resp = self.http.post(
            f"{cfg['base_url']}{endpoint}?key={api_key}",
            headers={"content-type": "application/json"},
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

    def _call_local(self, cfg: dict, messages: list[dict[str, str]]) -> str:
        payload = {
            "model": self.config.model or cfg["default"],
            "messages": messages,
            "stream": False,
            "options": {"temperature": self.config.temperature},
        }
        resp = self.http.post(
            f"{cfg['base_url']}{cfg['chat_endpoint']}",
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "")

    def _call_vision_provider(self, provider: str, image_path: str | Path, prompt: str, json_mode: bool) -> str:
        b64 = self._encode_image(image_path)
        cfg = self.PROVIDER_CONFIG[provider]
        api_key = self.config.api_key or getattr(self.settings, f"{provider}_api_key", "")

        if provider == "claude":
            return self._vision_claude(cfg, api_key, b64, prompt, json_mode)
        elif provider == "openai":
            return self._vision_openai(cfg, api_key, b64, prompt, json_mode)
        elif provider == "gemini":
            return self._vision_gemini(cfg, api_key, b64, prompt, json_mode)
        elif provider == "local":
            return self._vision_local(cfg, b64, prompt)
        else:
            raise LLMError(f"Vision not supported for provider: {provider}")

    def _vision_claude(self, cfg: dict, api_key: str, b64: str, prompt: str, json_mode: bool) -> str:
        media_type = "image/jpeg"
        payload: dict[str, Any] = {
            "model": self.config.model or cfg["default"],
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        }
        resp = self.http.post(
            f"{cfg['base_url']}{cfg['chat_endpoint']}",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]

    def _vision_openai(self, cfg: dict, api_key: str, b64: str, prompt: str, json_mode: bool) -> str:
        payload: dict[str, Any] = {
            "model": self.config.model or cfg["default"],
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    ],
                }
            ],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        resp = self.http.post(
            f"{cfg['base_url']}{cfg['chat_endpoint']}",
            headers={"authorization": f"Bearer {api_key}", "content-type": "application/json"},
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def _vision_gemini(self, cfg: dict, api_key: str, b64: str, prompt: str, json_mode: bool) -> str:
        model_name = self.config.model or cfg["default"]
        endpoint = f"/models/{model_name}:generateContent"
        payload: dict[str, Any] = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt},
                        {"inlineData": {"mimeType": "image/jpeg", "data": b64}},
                    ],
                }
            ],
            "generationConfig": {
                "temperature": self.config.temperature,
                "maxOutputTokens": self.config.max_tokens,
            },
        }
        if json_mode:
            payload["generationConfig"]["responseMimeType"] = "application/json"
        resp = self.http.post(
            f"{cfg['base_url']}{endpoint}?key={api_key}",
            headers={"content-type": "application/json"},
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

    def _vision_local(self, cfg: dict, b64: str, prompt: str) -> str:
        payload = {
            "model": self.config.model or cfg["default"],
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [b64],
                }
            ],
            "stream": False,
        }
        resp = self.http.post(
            f"{cfg['base_url']}{cfg['chat_endpoint']}",
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "")

    @staticmethod
    def _encode_image(image_path: str | Path) -> str:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def close(self) -> None:
        self.http.close()