"""Map-reduce summarizing of arbitrarily large data with a small-context local model.

Lines are packed into chunks that fit the model's context, each chunk is
summarized, and the summaries are summarized again until one remains.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field

from gitrecon.digest.llm import ChatClient

log = logging.getLogger(__name__)

# ~4 chars per token; leaves room for the prompt and the answer in an 8k context.
DEFAULT_CHUNK_CHARS = 16_000

MAP_PROMPT = (
    "You analyse data mined from GitHub ({topic}). Below is one slice of it. "
    "Summarise what is happening in this slice: main themes, notable projects, "
    "technologies, patterns, anomalies and numbers worth keeping. Be factual and dense; "
    "use short bullet points; do not invent anything that is not in the data."
)
REDUCE_PROMPT = (
    "Below are partial summaries of data mined from GitHub ({topic}). Merge them into one "
    "summary: deduplicate, keep the strongest themes, concrete names and numbers, and note "
    "trends across parts. Use short sections with bullet points. Do not invent facts."
)


def chunk_lines(lines: Iterable[str], max_chars: int = DEFAULT_CHUNK_CHARS) -> Iterator[str]:
    """Pack lines into chunks of at most ``max_chars`` (an over-long line is cut)."""
    chunk: list[str] = []
    size = 0
    for line in lines:
        line = line[:max_chars]
        if chunk and size + len(line) + 1 > max_chars:
            yield "\n".join(chunk)
            chunk, size = [], 0
        chunk.append(line)
        size += len(line) + 1
    if chunk:
        yield "\n".join(chunk)


@dataclass
class Summarizer:
    client: ChatClient
    topic: str = "GitHub activity"
    max_chars: int = DEFAULT_CHUNK_CHARS
    progress: Callable[[str], None] = field(default=lambda message: log.info(message))

    def _ask(self, prompt: str, text: str) -> str:
        return self.client.chat(
            [
                {"role": "system", "content": prompt.format(topic=self.topic)},
                {"role": "user", "content": text},
            ]
        ).strip()

    def summarize(self, lines: Iterable[str]) -> str:
        parts = []
        for index, chunk in enumerate(chunk_lines(lines, self.max_chars), start=1):
            parts.append(self._ask(MAP_PROMPT, chunk))
            self.progress(f"summarized chunk {index}")
        level = 1
        while len(parts) > 1:
            level += 1
            chunks = list(chunk_lines(parts, self.max_chars))
            if len(chunks) == len(parts):
                # every summary fills a chunk alone: pair them so each level shrinks
                chunks = ["\n\n".join(parts[i : i + 2]) for i in range(0, len(parts), 2)]
            self.progress(f"reduce level {level}: {len(parts)} summaries -> {len(chunks)}")
            parts = [self._ask(REDUCE_PROMPT, chunk) for chunk in chunks]
        return parts[0] if parts else ""
