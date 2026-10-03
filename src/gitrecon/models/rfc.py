"""IETF Request for Comments, as listed in the RFC Editor's index."""

from __future__ import annotations

from dataclasses import dataclass, field

from gitrecon.models.base import Entity


@dataclass
class RFC(Entity):
    kind = "rfc"

    number: int = 0
    title: str = ""
    authors: list[str] = field(default_factory=list)
    date: str | None = None  # "April 1969"
    status: str | None = None  # "PROPOSED STANDARD"
    formats: list[str] = field(default_factory=list)
    doi: str | None = None
    obsoletes: list[str] = field(default_factory=list)
    obsoleted_by: list[str] = field(default_factory=list)
    updates: list[str] = field(default_factory=list)
    updated_by: list[str] = field(default_factory=list)
    also: list[str] = field(default_factory=list)  # e.g. ["BCP9"]
    related: list[str] = field(default_factory=list)  # every RFC mentioned
    not_issued: bool = False
    description: str = ""  # the whole index entry on one line

    @property
    def ident(self) -> str:
        return f"RFC{self.number}"

    @property
    def url(self) -> str:
        return f"https://www.rfc-editor.org/rfc/rfc{self.number}"
