from __future__ import annotations

import json
import math
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass
class ModelResponse:
    text: str
    logprobs: dict[str, float] | None = None


class Backend:
    supports_logprobs = False

    def complete(self, *, messages, temperature=0.0, max_tokens=1, logprobs=False, top_logprobs=0, json_mode=False) -> ModelResponse:
        raise NotImplementedError


class OpenAICompatibleBackend(Backend):
    supports_logprobs = True

    def __init__(self, model: str, api_key: str | None = None, base_url: str | None = None, supports_logprobs: bool = True):
        self.model = model
        self.api_key = api_key
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self.supports_logprobs = supports_logprobs

    def complete(self, *, messages, temperature=0.0, max_tokens=1, logprobs=False, top_logprobs=0, json_mode=False) -> ModelResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if logprobs:
            payload["logprobs"] = True
            payload["top_logprobs"] = top_logprobs
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode(),
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
        choice = data["choices"][0]
        text = (choice.get("message") or {}).get("content") or ""
        lp = None
        if logprobs and choice.get("logprobs"):
            top = (choice["logprobs"].get("content") or [{}])[0]
            lp = {}
            for item in top.get("top_logprobs") or []:
                token = item["token"]
                if isinstance(token, bytes):
                    continue
                lp[token] = math.exp(item.get("logprob") or 0.0)
        return ModelResponse(text=text, logprobs=lp)


class OpenAIBackend(OpenAICompatibleBackend):
    supports_logprobs = True

    def __init__(self, model: str = "gpt-4o-mini", api_key: str | None = None, base_url: str | None = None):
        super().__init__(model=model, api_key=api_key, base_url=base_url, supports_logprobs=True)


class OllamaBackend(Backend):
    supports_logprobs = False

    def __init__(self, model: str = "llama3.1:8b", base_url: str = "http://localhost:11434", num_ctx: int | None = None):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.num_ctx = num_ctx

    def complete(self, *, messages, temperature=0.0, max_tokens=1, logprobs=False, top_logprobs=0, json_mode=False) -> ModelResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if self.num_ctx:
            payload["options"]["num_ctx"] = self.num_ctx
        if json_mode:
            payload["format"] = "json"
        req = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
        return ModelResponse(text=data["message"]["content"] or "")


class LocalOpenAIBackend(OpenAICompatibleBackend):
    def __init__(self, model: str, base_url: str, api_key: str = "not-needed", supports_logprobs: bool = True):
        super().__init__(model=model, base_url=base_url, api_key=api_key, supports_logprobs=supports_logprobs)


class AnthropicCompatibleBackend(Backend):
    supports_logprobs = False

    def __init__(self, model: str = "claude-3-5-haiku-latest", api_key: str | None = None, base_url: str = "https://api.anthropic.com", anthropic_version: str = "2023-06-01"):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.anthropic_version = anthropic_version

    def complete(self, *, messages, temperature=0.0, max_tokens=1, logprobs=False, top_logprobs=0, json_mode=False) -> ModelResponse:
        system_parts: list[str] = []
        convo: list[dict[str, str]] = []
        for msg in messages:
            content = msg.get("content") or ""
            if msg.get("role") == "system":
                system_parts.append(content)
            else:
                convo.append({"role": msg.get("role", "user"), "content": content})
        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": convo,
        }
        if system_parts:
            payload["system"] = "\n".join(system_parts)
        headers = {
            "Content-Type": "application/json",
            "anthropic-version": self.anthropic_version,
        }
        if self.api_key:
            headers["x-api-key"] = self.api_key
        req = urllib.request.Request(
            f"{self.base_url}/v1/messages",
            data=json.dumps(payload).encode(),
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
        text = ""
        for block in data.get("content") or []:
            if block.get("type") == "text":
                text += block.get("text") or ""
        return ModelResponse(text=text)


class MockBackend(Backend):
    supports_logprobs = True

    def __init__(self, logprobs: dict[str, float] | None = None):
        self._logprobs = logprobs or {"0": 0.6, "1": 0.3, "2": 0.1, "Yes": 0.7, "No": 0.3}

    def complete(self, *, messages, temperature=0.0, max_tokens=1, logprobs=False, top_logprobs=0, json_mode=False) -> ModelResponse:
        text = max(self._logprobs, key=self._logprobs.get)
        return ModelResponse(text=text, logprobs=dict(self._logprobs))