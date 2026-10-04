"""Content and text: digest, posts, text."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from gitrecon.cli.output import Output, add_output_flags, dumps
from gitrecon.config import Config
from gitrecon.storage import RawBuffer


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _digest_lines(spec: str, config: Config):
    from gitrecon.digest import inputs

    kind, _, target = spec.partition(":")
    match kind:
        case "stars":
            from gitrecon.sources import stars
            from gitrecon.sources.github_api import GitHubClient

            return inputs.star_lines(stars.starred(GitHubClient(config), target)), f"stars of {target}"
        case "labels":
            from gitrecon.analysis import Labeler

            labeler = Labeler()
            labeler.ingest(RawBuffer(config.raw_dir).read(target or None))
            return inputs.label_lines(labeler.run()), "activity labels"
        case "links":
            from gitrecon.sources.links import load_catalog

            return inputs.link_lines(load_catalog(config.links_catalog)), "harvested data source links"
        case "file":
            return inputs.file_lines(Path(target)), Path(target).name
    raise SystemExit(f"unknown digest input {spec!r}: stars:USER | labels[:SOURCE] | links | file:PATH")


def cmd_digest(args: argparse.Namespace, config: Config, out: Output) -> int:
    from gitrecon.digest import OllamaClient, Summarizer

    lines, topic = _digest_lines(args.input, config)
    client = OllamaClient(model=args.model) if args.model else OllamaClient()
    summarizer = Summarizer(client, topic=args.topic or topic, max_chars=args.chunk_chars, progress=out.note)
    summary = summarizer.summarize(lines)
    path = config.data_dir / "digests" / f"{_stamp()}-{args.input.replace(':', '-').replace('/', '_')}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"<!-- {topic} | {client.model} -->\n\n{summary}\n", encoding="utf-8")
    out.result({"input": args.input, "topic": args.topic or topic, "model": client.model,
                "path": str(path), "summary": summary}, text=summary)
    out.note(f"-- saved {path}")
    return 0


def cmd_posts(args: argparse.Namespace, config: Config, out: Output) -> int:
    from gitrecon.digest import XaiClient, write_posts

    client = XaiClient(model=args.model) if args.model else XaiClient()
    if args.list_models:
        out.listing(client.models(), text=str, data=str)
        return 0
    posts = write_posts(client, Path(args.summary).read_text(encoding="utf-8"), language=args.language)
    path = posts.save(config.data_dir / "posts" / f"{_stamp()}-{posts.article.slug or 'post'}")

    def text() -> str:
        tweets = [f"[tweet {i}/{len(posts.tweets)} {len(t)}c] {t}" for i, t in enumerate(posts.tweets, start=1)]
        return "\n".join([posts.article.to_markdown(), *tweets])

    out.result({"path": str(path), "posts": posts.to_dict()}, text=text)
    for warning in posts.warnings:
        out.note(f"warning: {warning}")
    out.note(f"-- drafts saved in {path} (nothing was published)")
    return 0


def cmd_text(args: argparse.Namespace, config: Config, out: Output) -> int:
    from gitrecon.text import markdown, tokenizer
    from gitrecon.text.rat import build_rat

    local = Path(args.url).expanduser()
    md_text = local.read_text(encoding="utf-8") if local.is_file() else markdown.fetch_text(args.url)
    match args.action:
        case "toc":
            html = markdown.render_toc(md_text)
            out.result({"url": args.url, "toc_html": html}, text=html)
        case "tokens":
            sentences = tokenizer.text_to_tokenchain_sentences(markdown.md_to_text(md_text))
            out.result(sentences, text=lambda: dumps(sentences))  # data either way
        case "requirements":
            from gitrecon.humanish.requirements import find_requirements, summarize_requirements

            found = find_requirements(md_text if args.raw else markdown.md_to_text(md_text))
            out.listing(found, text=lambda r: f"{r.level:<14} line {r.line:<5} {r.sentence}", data=lambda r: r.to_json(),
                        url=lambda r: None,
                        summary="-- " + (", ".join(f"{n} {level}" for level, n in summarize_requirements(found).items())
                                         or "no requirement keywords (MUST, SHOULD, MAY ... in capitals)"))
        case "rat":
            build = build_rat(markdown.md_to_text(md_text))
            out.result({"url": args.url, "size": len(build.script), "lines": build.lines,
                        "glossary": dict(build.glossary), "script": build.script}, text=build.script)
            out.note(f"-- RAT size {len(build.script)}, lines {build.lines}")
    return 0


def cmd_translate(args: argparse.Namespace, config: Config, out: Output) -> int:
    import sys

    from gitrecon.translate import argos

    try:
        match args.action:
            case "languages":
                if args.available:
                    out.listing(argos.available_packages(), data=lambda p: p, url=lambda p: None,
                                text=lambda p: f"{p['from']:<4} -> {p['to']:<4} {p['from_name']} -> {p['to_name']}",
                                summary=lambda found: f"-- {len(found)} directions in the Argos index; "
                                                      "install one: gitrecon translate install FROM TO")
                else:
                    out.listing(argos.installed_languages(), data=lambda entry: entry, url=lambda entry: None,
                                text=lambda e: f"{e['code']:<4} {e['name']:<22} -> {', '.join(e['to']) or '-'}",
                                summary=lambda found: f"-- {len(found)} languages installed"
                                                      + ("" if found else "; see: gitrecon translate languages --available"))
            case "install":
                if len(args.words) != 2:
                    out.note("usage: gitrecon translate install FROM TO   (language codes, e.g. en pl)")
                    return 2
                out.note(f"installing {args.words[0]} -> {args.words[1]} (a download of about 100 MB the first time)")
                done = argos.install(*args.words)
                out.result(done, text=f"{done['status']}: {done['from_name']} -> {done['to_name']}")
            case "text":
                if not (args.source and args.to):
                    out.note("usage: gitrecon translate text --from CODE --to CODE [WORDS... | - for stdin]")
                    return 2
                text = sys.stdin.read() if args.words in ([], ["-"]) else " ".join(args.words)
                translated = argos.translate(text, args.source, args.to)
                out.result({"from": args.source, "to": args.to, "text": text, "translation": translated},
                           text=translated)
    except (RuntimeError, LookupError) as error:
        out.note(str(error))
        return 1
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("digest", help="summarize big data with a local Ollama model (map-reduce)")
    p.add_argument("input", help="stars:USER | labels[:SOURCE] | links | file:PATH")
    p.add_argument("--model", help="Ollama model (default: $OLLAMA_MODEL or llama3)")
    p.add_argument("--topic")
    p.add_argument("--chunk-chars", type=int, default=16_000)
    add_output_flags(p, urls=False)
    p.set_defaults(func=cmd_digest)

    p = sub.add_parser("posts", help="write SEO article + tweets from a digest with xAI (drafts only)")
    p.add_argument("summary", nargs="?", help="digest markdown file")
    p.add_argument("--model", help="xAI model (default: $XAI_MODEL or grok-4)")
    p.add_argument("--language", default="English")
    p.add_argument("--list-models", action="store_true")
    add_output_flags(p, urls=False)
    p.set_defaults(func=cmd_posts)

    p = sub.add_parser("text", help="markdown/tokenizer/RAT experiments and requirement sentences of a URL or file")
    p.add_argument("action", choices=["toc", "tokens", "rat", "requirements"])
    p.add_argument("url", nargs="?", default="https://taskfile.dev/llms.txt", help="a URL or a local file")
    p.add_argument("--raw", action="store_true", help="requirements: the text is plain (an RFC .txt), not markdown")
    add_output_flags(p, urls=False)
    p.set_defaults(func=cmd_text)

    p = sub.add_parser("translate", help="offline translation with Argos Translate: text, languages, install")
    p.add_argument("action", choices=["text", "languages", "install"])
    p.add_argument("words", nargs="*", help="text: the words (or - for stdin); install: FROM TO language codes")
    p.add_argument("--from", dest="source", help="text: source language code, e.g. en")
    p.add_argument("--to", help="text: target language code, e.g. pl")
    p.add_argument("--available", action="store_true", help="languages: what the Argos index offers, not what is installed")
    add_output_flags(p, urls=False)
    p.set_defaults(func=cmd_translate)
