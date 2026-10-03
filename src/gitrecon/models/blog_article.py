"""A blog article captured as markdown."""

from __future__ import annotations

import zlib
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from gitrecon.models.base import Entity


@dataclass
class BlogArticle(Entity):
    kind = "article"

    url: str = ""
    blog: str = ""
    name: str = ""  # "REPORT EMERGENT COLLECTIVE NARRATIVE", from the URL slug
    markdown: str = ""
    fetched_at: datetime | None = None

    @property
    def ident(self) -> str:
        return self.url

    @property
    def html_url(self) -> str:
        return self.url

    def to_json(self) -> dict[str, Any]:
        return self.to_record()

    @property
    def url_checksum(self) -> int:
        """adler32 of the URL, as the original notebook printed it."""
        return zlib.adler32(self.url.encode("utf8"))

    @property
    def name_checksum(self) -> int:
        return zlib.adler32(self.name.encode("utf8"))

    def to_record(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("raw", None)
        data["fetched_at"] = self.fetched_at.isoformat() if self.fetched_at else None
        data["kind"] = self.kind
        data["url_checksum"] = self.url_checksum
        return data

    def to_markdown(self) -> str:
        """The notebook's dump format: one titled, delimited section per article."""
        return "\n".join(
            [
                f"- {self.url_checksum} - {self.name_checksum}",
                f"### ARTICLE FROM [{self.name}]({self.url})",
                "###### BEGIN",
                self.markdown.strip(),
                "###### END",
            ]
        )
