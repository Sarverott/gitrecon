#!/usr/bin/env python3
"""Start a scrapnote: docs/devlog/scrapnote-<UNIXUSAT>.md, named by the current moment in milliseconds.

    task scrapnote                      an empty note with its heading
    task scrapnote -- "the title"       with a title

Prints the path, so an editor can open it: $EDITOR "$(task scrapnote)".
"""

import sys
import time
from datetime import datetime
from pathlib import Path

DEVLOG = Path(__file__).resolve().parent.parent / "docs" / "devlog"


def main() -> int:
    stamp = time.time_ns() // 1_000_000
    title = " ".join(sys.argv[1:]).strip() or "Scrapnote"
    path = DEVLOG / f"scrapnote-{stamp}.md"
    DEVLOG.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# {title}\n\n> {datetime.now().date().isoformat()} · [UNIXUSAT={stamp}]\n\n", encoding="utf-8")
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
