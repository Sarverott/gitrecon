"""MkDocs hook: Obsidian [[links]] in this vault become site links.

[[workshop]] or [[workshop|the workshop]] links to the page whose file is named
workshop.md; a target with no page yet stays as plain text.
"""
import os
import posixpath
import re

WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]+))?\]\]")


def on_page_markdown(markdown, page, config, files):
    pages = {os.path.splitext(os.path.basename(f.src_uri))[0].lower(): f.src_uri for f in files.documentation_pages()}
    here = posixpath.dirname(page.file.src_uri)

    def link(match):
        target, label = match.group(1).strip(), (match.group(2) or match.group(1)).strip()
        found = pages.get(target.lower())
        return f"[{label}]({posixpath.relpath(found, here or '.')})" if found else label

    return WIKILINK.sub(link, markdown)
