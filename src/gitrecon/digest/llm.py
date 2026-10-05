"""Chat clients: local Ollama (bulk summarizing) and xAI (writing posts).

Both speak plain HTTP, so they need no SDKs and are easy to fake in tests.

The Ollama side is decided: ``gitrecon.llm.Ollama`` is the interface (structured answers,
embeddings, model management); this plain-HTTP client stays for the digest's bulk
summarizing and finds the server the same way.

TODO(llm-interfaces): the OpenAI-compatible enterprise endpoints are still open. Expected:
one OpenAI-compatible client configured per provider (base URL, key, model) replacing the
xAI-only client.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Protocol

import requests

Messages = list[dict[str, str]]


class ChatClient(Protocol):
    model: str

    def chat(self, messages: Messages, json_mode: bool = False) -> str: ...


def _ollama_host() -> str:
    from gitrecon.llm.ollama import find_host

    return find_host()


@dataclass
class OllamaClient:
    model: str = field(default_factory=lambda: os.environ.get("OLLAMA_MODEL", "llama3"))
    host: str = field(default_factory=_ollama_host)
    num_ctx: int = 8192
    timeout: float = 600
    session: requests.Session = field(default_factory=lambda: requests.Session())

    def chat(self, messages: Messages, json_mode: bool = False) -> str:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"num_ctx": self.num_ctx, "temperature": 0.2},
        }
        if json_mode:
            body["format"] = "json"
        r = self.session.post(f"{self.host}/api/chat", json=body, timeout=self.timeout)
        r.raise_for_status()
        return r.json()["message"]["content"]

    def models(self) -> list[str]:
        r = self.session.get(f"{self.host}/api/tags", timeout=10)
        r.raise_for_status()
        return [m["name"] for m in r.json().get("models", [])]


@dataclass
class XaiClient:
    """xAI (Grok) through its OpenAI-compatible chat completions endpoint."""

    model: str = field(default_factory=lambda: os.environ.get("XAI_MODEL", "grok-4"))
    api_key: str | None = field(default_factory=lambda: os.environ.get("XAI_API_KEY"))
    base_url: str = field(default_factory=lambda: os.environ.get("XAI_BASE_URL", "https://api.x.ai/v1"))
    timeout: float = 300
    session: requests.Session = field(default_factory=lambda: requests.Session())

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise RuntimeError("XAI_API_KEY is not set")
        return {"Authorization": f"Bearer {self.api_key}"}

    def chat(self, messages: Messages, json_mode: bool = False) -> str:
        body: dict[str, Any] = {"model": self.model, "messages": messages, "temperature": 0.7}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        r = self.session.post(
            f"{self.base_url}/chat/completions", json=body, headers=self._headers(), timeout=self.timeout
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    def models(self) -> list[str]:
        r = self.session.get(f"{self.base_url}/models", headers=self._headers(), timeout=30)
        r.raise_for_status()
        return [m["id"] for m in r.json().get("data", [])]


def parse_json_reply(text: str) -> Any:
    """Parse a model's JSON answer, tolerating code fences or chatter around it."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    fenced = re.search(r"```(?:json)?\s*(.+?)```", text, re.DOTALL)
    if fenced:
        return json.loads(fenced.group(1))
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        return json.loads(text[start : end + 1])
    raise ValueError("no JSON object in model reply")
