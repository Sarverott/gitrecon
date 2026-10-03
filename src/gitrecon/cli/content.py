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

    md_text = markdown.fetch_text(args.url)
    match args.action:
        case "toc":
            html = markdown.render_toc(md_text)
            out.result({"url": args.url, "toc_html": html}, text=html)
        case "tokens":
            sentences = tokenizer.text_to_tokenchain_sentences(markdown.md_to_text(md_text))
            out.result(sentences, text=lambda: dumps(sentences))  # data either way
        case "rat":
            build = build_rat(markdown.md_to_text(md_text))
            out.result({"url": args.url, "size": len(build.script), "lines": build.lines,
                        "glossary": dict(build.glossary), "script": build.script}, text=build.script)
            out.note(f"-- RAT size {len(build.script)}, lines {build.lines}")
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

    p = sub.add_parser("text", help="markdown/tokenizer/RAT experiments on a URL")
    p.add_argument("action", choices=["toc", "tokens", "rat"])
    p.add_argument("url", nargs="?", default="https://taskfile.dev/llms.txt")
    add_output_flags(p, urls=False)
    p.set_defaults(func=cmd_text)
