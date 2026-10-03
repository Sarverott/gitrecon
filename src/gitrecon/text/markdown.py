"""Markdown fetching and rendering.

Deconstructed from the first notebook, ``docs/tests-with-md-parsing-and-rattish-implementations.ipynb``
(removed, see git history; demo: ``examples/text-experiments``)
(cells 1-5 and 11).
"""

from __future__ import annotations

import bs4
import marko
import requests

# as example the llm info briefing about task tool
EXAMPLE_MD_URL = "https://taskfile.dev/llms.txt"


def fetch_text(url: str, timeout: float = 30) -> str:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.text


def md_to_html(md_text: str) -> str:
    return marko.convert(md_text)


def html_to_text(html: str) -> str:
    return bs4.BeautifulSoup(html, "html.parser").text


def md_to_text(md_text: str) -> str:
    return html_to_text(md_to_html(md_text))


def render_toc(md_text: str) -> str:
    """Render the table of contents (HTML ``<ul>``) of a markdown document."""
    md = marko.Markdown()
    md.use("footnote")
    md.use("toc")
    md.use("codehilite")
    md(md_text)
    return md.renderer.render_toc()
