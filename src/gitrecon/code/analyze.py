"""What a cloned repository is made of: languages, structure, frameworks, links.

    analyze_repo("~/__WORKSHOP/forge/rattish/branching-chainer")

Files are found with ``git ls-files`` when the folder is a git repository (so ignored and
vendored-by-gitignore files stay out), else by walking it without the usual heavy folders.
Large and binary files are counted but not read.
"""

from __future__ import annotations

import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

from gitrecon.code import frameworks, lexical, pyast
from gitrecon.code.languages import detect

SKIPPED_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", "vendor", "target",
                ".next", ".nuxt", "site-packages", ".tox", ".mypy_cache", ".pytest_cache"}
MAX_FILE_BYTES = 400_000   # bigger files are generated or data more often than written
MAX_LEXED_FILES = 3_000    # per repository; the rest is counted by size only
TOP = 30


def repo_files(root: Path) -> list[Path]:
    """Tracked files of a git repository, or every file of a plain folder (heavy folders left out)."""
    if (root / ".git").exists():
        done = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], capture_output=True, check=False)
        if done.returncode == 0:
            names = [n for n in done.stdout.decode("utf-8", errors="replace").split("\0") if n]
            return [root / n for n in names if (root / n).is_file()]
    return sorted(p for p in root.rglob("*") if p.is_file() and not SKIPPED_DIRS & set(p.relative_to(root).parts))


def _read(path: Path) -> str | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if b"\0" in data[:8000]:  # binary
        return None
    return data.decode("utf-8", errors="replace")


def analyze_repo(path: str | Path) -> dict[str, Any]:
    """Languages (files, bytes, lines, code, comments), Python structure, frameworks, names, URLs."""
    root = Path(path).expanduser().resolve()
    files = repo_files(root)
    languages: dict[str, dict[str, Any]] = {}
    per_language: dict[str, lexical.LexStats] = {}
    python = pyast.PyStats()
    names: Counter[str] = Counter()
    urls: Counter[str] = Counter()
    unknown: Counter[str] = Counter()
    lexed = skipped_large = 0

    for file in files:
        language = detect(file)
        if language is None:
            unknown[file.suffix.lower() or file.name] += 1
            continue
        try:
            size = file.stat().st_size
        except OSError:
            continue
        entry = languages.setdefault(language.name, {"kind": language.kind, "files": 0, "bytes": 0, "lines": 0,
                                                     "code": 0, "comment": 0, "blank": 0})
        entry["files"] += 1
        entry["bytes"] += size
        if size > MAX_FILE_BYTES:
            skipped_large += 1
            continue
        if not language.family and language.name != "Python" and language.kind not in ("prose", "config"):
            continue
        text = _read(file)
        if text is None:
            continue
        if language.family and lexed < MAX_LEXED_FILES:
            lexed += 1
            stats = lexical.lex(text, language)
            per_language.setdefault(language.name, lexical.LexStats()).add(stats)
            if language.kind == "code":
                names.update(stats.names)
            urls.update(stats.urls)
        else:
            entry["lines"] += text.count("\n") + (1 if text and not text.endswith("\n") else 0)
        if language.name == "Python":
            pyast.add_file(python, text)

    for name, stats in per_language.items():
        languages[name].update(lines=languages[name]["lines"] + stats.lines, code=stats.code,
                               comment=stats.comment, blank=stats.blank, comment_ratio=stats.comment_ratio)
    found_frameworks, deps = frameworks.detect(root, files)
    code_bytes = {n: e["bytes"] for n, e in languages.items() if e["kind"] in ("code", "markup")}
    result: dict[str, Any] = {
        "path": str(root),
        "name": root.name,
        "files": len(files),
        "main_language": max(code_bytes, key=code_bytes.get) if code_bytes else None,
        "languages": dict(sorted(languages.items(), key=lambda kv: -kv[1]["bytes"])),
        "frameworks": found_frameworks,
        "dependencies": deps,
        "names": dict(names.most_common(TOP)),
        "urls": [u for u, _ in urls.most_common(TOP)],
        "url_count": len(urls),
        "unknown_extensions": dict(unknown.most_common(10)),
        "skipped_large_files": skipped_large,
    }
    if python.files:
        result["python"] = {
            "files": python.files, "unparsed": python.unparsed, "functions": python.functions,
            "async_functions": python.async_functions, "classes": python.classes,
            "docstring_ratio": python.docstring_ratio,
            "imports": dict(python.imports.most_common(TOP)),
            "decorators": dict(python.decorators.most_common(10)),
        }
    return result


def find_repos(path: str | Path) -> list[Path]:
    """``path`` itself when it is a repository, else the repositories directly inside it."""
    root = Path(path).expanduser().resolve()
    if (root / ".git").exists():
        return [root]
    return sorted(p for p in root.iterdir() if p.is_dir() and (p / ".git").exists())
