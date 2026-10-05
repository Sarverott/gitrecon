"""PARKED (2026-10-05): the Ollama interface. Nothing imports this module.

The approach - a local model filling in the commit form - is set aside until it is
reconsidered. The code is kept below, commented out, as it last worked: an ``Ollama``
object with ``chat``, ``structured`` (answers as a pydantic model), ``embed``, ``models``,
``pull``, and ``find_host``. What it measured is in docs/devlog/scrapnote-1791187496508.md.

To bring it back: uncomment, restore the exports in ``gitrecon/llm/__init__.py`` and the
``llm`` command in ``gitrecon/cli/content.py``.
"""

# """The Ollama interface: one object for chat, answers in a given shape, embeddings, model listing.
#
#     llm = Ollama()                                   # host and model from the environment
#     llm.models()                                     # what the server has
#     form = llm.structured(Pet, "I have a cat named Luna ...")     # a pydantic model, filled in
#
# Where the server is (first that applies): ``OLLAMA_HOST``; else whichever answers of
# ``http://localhost:11434`` (a host install) and ``http://localhost:11435`` (the ``ollama``
# service of ``services/``). Which model: the ``model=`` given, else ``OLLAMA_MODEL``, else
# the first model the server has. A key for a remote server (``OLLAMA_API_KEY``) is sent
# only over https.
#
# Needs the ``llm`` extra (the ``ollama`` package, which brings pydantic).
# """
#
# from __future__ import annotations
#
# import os
# from dataclasses import dataclass, field
# from typing import Any, TypeVar
#
# import requests
#
# T = TypeVar("T")
# LOCAL_HOSTS = ("http://localhost:11434", "http://localhost:11435")
#
#
# def _normal(host: str) -> str:
#     return (host if host.startswith("http") else f"http://{host}").rstrip("/")
#
#
# def find_host(session: Any = None) -> str:
#     """``OLLAMA_HOST`` when set; else the first local address that answers; else the usual default."""
#     if os.environ.get("OLLAMA_HOST"):
#         return _normal(os.environ["OLLAMA_HOST"])
#     for host in LOCAL_HOSTS:
#         try:
#             if (session or requests).get(f"{host}/api/version", timeout=1.5).ok:
#                 return host
#         except Exception:  # noqa: BLE001 - nobody there: try the next address
#             continue
#     return LOCAL_HOSTS[0]
#
#
# @dataclass
# class Ollama:
#     host: str = field(default_factory=find_host)
#     model: str | None = field(default_factory=lambda: os.environ.get("OLLAMA_MODEL") or None)
#     temperature: float = 0.0
#     num_ctx: int = 8192
#     timeout: float = 600
#     _client: Any = field(default=None, repr=False)
#
#     @property
#     def client(self) -> Any:
#         if self._client is None:
#             try:
#                 import ollama
#             except ImportError as error:
#                 raise RuntimeError("the Ollama interface needs the llm extra: uv sync --extra llm") from error
#             headers = {}
#             key = os.environ.get("OLLAMA_API_KEY")
#             if key and self.host.startswith("https://"):
#                 headers["Authorization"] = f"Bearer {key}"
#             self._client = ollama.Client(host=self.host, timeout=self.timeout, headers=headers)
#         return self._client
#
#     def models(self) -> list[str]:
#         """Names of the models the server has, as it lists them."""
#         try:
#             listed = self.client.list()
#         except Exception as error:  # noqa: BLE001
#             raise RuntimeError(f"no Ollama server at {self.host} ({error}); start one (ollama serve, or "
#                                "task services:up -- ollama) or set OLLAMA_HOST") from error
#         entries = listed.models if hasattr(listed, "models") else listed["models"]
#         return [m.model if hasattr(m, "model") else m["model"] for m in entries]
#
#     def pick_model(self, model: str | None = None) -> str:
#         """The model to use: the one asked for, the configured one, else the server's first that can chat."""
#         chosen = model or self.model
#         if chosen:
#             return chosen
#         available = self.models()
#         if not available:
#             raise RuntimeError(f"the Ollama server at {self.host} has no models: gitrecon llm pull MODEL "
#                                "(e.g. deepseek-r1:1.5b), or ollama pull MODEL")
#         talking = [name for name in available if "embed" not in name.lower()]  # an embedding model cannot chat
#         self.model = (talking or available)[0]
#         return self.model
#
#     def pull(self, model: str) -> str:
#         """Download a model into the server; returns its final status."""
#         return str(getattr(self.client.pull(model), "status", "done"))
#
#     def _options(self, options: dict[str, Any] | None) -> dict[str, Any]:
#         return {"temperature": self.temperature, "num_ctx": self.num_ctx} | (options or {})
#
#     def chat(self, prompt: str | list[dict[str, Any]], model: str | None = None, system: str | None = None,
#              images: list[str] | None = None, options: dict[str, Any] | None = None, **more: Any) -> str:
#         """A plain answer to a prompt (or to a list of messages)."""
#         call = {"model": self.pick_model(model), "messages": self._messages(prompt, system, images),
#                 "options": self._options(options)} | more
#         try:
#             response = self.client.chat(**call)
#         except Exception as error:  # noqa: BLE001
#             if "think" not in call or "think" not in str(error).lower():
#                 raise
#             call.pop("think")  # a model without a thinking mode refuses the switch: ask again without it
#             response = self.client.chat(**call)
#         return response.message.content if hasattr(response, "message") else response["message"]["content"]
#
#     def structured(self, shape: type[T], prompt: str | list[dict[str, Any]], model: str | None = None,
#                    system: str | None = None, images: list[str] | None = None,
#                    options: dict[str, Any] | None = None, retries: int = 1, think: bool | None = False) -> T:
#         """The answer as an instance of ``shape`` (a pydantic model): the server is given its JSON
#         schema and may only answer in it. An answer that still does not validate is asked for again
#         ``retries`` times, then the validation error is raised.
#
#         ``think=False`` (default) tells reasoning models (deepseek-r1, qwen3 ...) to answer
#         straight away: filling a form needs no essay first, and on a CPU the essay costs minutes.
#         ``think=None`` leaves the model's own default.
#         """
#         more = {} if think is None else {"think": think}
#         error: Exception | None = None
#         for _ in range(retries + 1):
#             content = self.chat(prompt, model=model, system=system, images=images, options=options,
#                                 format=shape.model_json_schema(), **more)
#             try:
#                 return shape.model_validate_json(content)
#             except Exception as problem:  # noqa: BLE001 - pydantic's ValidationError
#                 error = problem
#         raise ValueError(f"{self.model} did not answer in the shape of {shape.__name__}: {error}")
#
#     def embed(self, texts: str | list[str], model: str | None = None) -> list[list[float]]:
#         """Embedding vectors of texts (for a vector database); needs an embedding model on the server."""
#         response = self.client.embed(model=self.pick_model(model), input=texts)
#         return list(response.embeddings if hasattr(response, "embeddings") else response["embeddings"])
#
#     @staticmethod
#     def _messages(prompt: str | list[dict[str, Any]], system: str | None, images: list[str] | None) -> list[dict[str, Any]]:
#         if isinstance(prompt, list):
#             return prompt
#         user: dict[str, Any] = {"role": "user", "content": prompt}
#         if images:
#             user["images"] = images
#         return ([{"role": "system", "content": system}] if system else []) + [user]
