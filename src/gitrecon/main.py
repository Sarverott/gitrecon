"""gitrecon command line: collect -> buffer -> map -> label."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone

from gitrecon.config import Config
from gitrecon.storage import RawBuffer


def _dump(data) -> None:
    print(json.dumps(data, indent=2, default=str, ensure_ascii=False))


# --- collect ---------------------------------------------------------------


def cmd_events(args: argparse.Namespace, config: Config) -> int:
    from gitrecon.sources.events import EventPoller, Feed
    from gitrecon.sources.github_api import GitHubClient

    buffer = RawBuffer(config.raw_dir)
    feed = Feed.parse(args.feed)
    poller = EventPoller(GitHubClient(config), feed, state_dir=config.state_dir)
    rounds = None if args.watch else 1
    for batch in poller.listen(max_rounds=rounds):
        stored = buffer.append("events", batch, suffix=feed.name)
        print(f"{feed.name}: +{stored} events (next poll in {poller.state.poll_interval}s)")
    return 0


def cmd_gists(args: argparse.Namespace, config: Config) -> int:
    from gitrecon.sources import gists
    from gitrecon.sources.github_api import GitHubClient

    client = GitHubClient(config)
    if args.user:
        found, suffix = gists.user_gists(client, args.user), f"user-{args.user}"
    else:
        found, suffix = gists.public_gists(client, since=args.since, max_pages=args.pages), "public"
    stored = RawBuffer(config.raw_dir).append("gists", found, suffix=suffix)
    print(f"gists ({suffix}): +{stored}")
    return 0


def cmd_stars(args: argparse.Namespace, config: Config) -> int:
    from gitrecon.sources import stars
    from gitrecon.sources.github_api import GitHubClient

    raw = stars.starred_raw(GitHubClient(config), args.user)
    if args.save:
        RawBuffer(config.raw_dir).append("stars", raw, suffix=f"user-{args.user}")
    found = [stars.Star.from_api(args.user, item) for item in raw]
    if args.json:
        _dump([
            {"repo": s.repo.full_name, "starred_at": s.starred_at, "language": s.repo.language,
             "stars": s.repo.stargazers_count, "description": s.repo.description}
            for s in found
        ])
        return 0
    for star in found:
        when = f"{star.starred_at:%Y-%m-%d}" if star.starred_at else "?"
        lang = star.repo.language or "-"
        print(f"{when}  {star.repo.full_name:<50} {lang:<14} *{star.repo.stargazers_count or 0}")
    print(f"-- {len(found)} repositories starred by {args.user}")
    return 0


def cmd_archive(args: argparse.Namespace, config: Config) -> int:
    from gitrecon.sources import gharchive

    buffer = RawBuffer(config.raw_dir)
    start = gharchive.parse_hour(args.start)
    end = gharchive.parse_hour(args.end) if args.end else start
    for hour in gharchive.hour_range(start, end):
        path = gharchive.download_hour(hour, buffer.partition("gharchive", hour), config)
        print(f"{hour:%Y-%m-%d %H}:00 -> {path} ({path.stat().st_size / 2**20:.1f} MiB)")
    return 0


# --- analyze ---------------------------------------------------------------


def cmd_map(args: argparse.Namespace, config: Config) -> int:
    from gitrecon.mapping import ActivityGraph

    graph = ActivityGraph()
    graph.ingest(RawBuffer(config.raw_dir).read(args.source))
    if args.node:
        _dump(graph.neighbors(args.node))
    elif args.full:
        _dump(graph.to_dict())
    else:
        _dump(graph.summary())
    return 0


def cmd_label(args: argparse.Namespace, config: Config) -> int:
    from gitrecon.analysis import Labeler

    labeler = Labeler()
    labeler.ingest(RawBuffer(config.raw_dir).read(args.source))
    labels = labeler.run()
    if args.json:
        _dump([label.to_dict() for label in labels])
    else:
        for label in labels[: args.limit]:
            print(label)
        print(f"-- {len(labels)} labels")
    return 0


def cmd_status(args: argparse.Namespace, config: Config) -> int:
    buffer = RawBuffer(config.raw_dir)
    print(f"data dir: {config.data_dir.resolve()}")
    print(f"token:    {'set' if config.github_token else 'not set (60 req/h)'}")
    for source in buffer.sources():
        files = buffer.files(source)
        size = sum(f.stat().st_size for f in files)
        print(f"  {source:<10} {len(files):>5} files {size / 2**20:>10.1f} MiB")
    return 0


# --- sources catalog, map dataset, digests -----------------------------------


def _catalog_path(config: Config):
    return config.data_dir / "catalog" / "links.jsonl"


def cmd_links(args: argparse.Namespace, config: Config) -> int:
    from collections import Counter
    from pathlib import Path

    from gitrecon.sources import links as harvest

    root = Path(args.root)
    found = harvest.harvest(root, exclude=[config.data_dir]) if args.all else harvest.harvest_gists(root)
    if args.kind:
        found = [link for link in found if link.kind in args.kind]
    if args.save:
        print(f"saved {harvest.save_catalog(found, _catalog_path(config))}", file=sys.stderr)
    if args.json:
        _dump([link.to_dict() for link in found])
    else:
        for link in found:
            print(f"{link.kind:<16} {link.url}")
        counts = ", ".join(f"{k} {n}" for k, n in Counter(link.kind for link in found).most_common())
        print(f"-- {len(found)} links: {counts}")
    return 0


def cmd_atlas(args: argparse.Namespace, config: Config) -> int:
    from gitrecon.hub.huggingface import MapDataset, default_local_dir

    dataset = MapDataset(repo_id=args.repo, local_dir=default_local_dir(config))
    match args.action:
        case "pull":
            print(f"pulled {dataset.repo_id} -> {dataset.pull()}")
        case "status":
            print(f"{dataset.repo_id} at {dataset.local_dir}")
            for area in dataset.areas():
                files = [f for f in dataset.files() if f.relative_to(dataset.local_dir).parts[0] == area]
                print(f"  {area:<22} {len(files):>6} files")
        case "update":
            return _atlas_update(args, config, dataset.local_dir)
        case "push":
            if not args.message:
                print("--message is required for push", file=sys.stderr)
                return 2
            result = dataset.push(args.message, create_pr=args.pr)
            print(f"pushed: {result}")
    return 0


def _atlas_update(args: argparse.Namespace, config: Config, root) -> int:
    from gitrecon.atlas import AtlasUpdate
    from gitrecon.sources.github_api import GitHubClient
    from gitrecon.sources.links import load_catalog

    update = AtlasUpdate(root)
    catalog = _catalog_path(config)
    if catalog.exists():
        update.add_links(load_catalog(catalog), union="gist-harvest")
    else:
        print(f"no link catalog at {catalog} (run: gitrecon links --save)", file=sys.stderr)
    if not args.no_meta:
        update.add_github_meta(GitHubClient(config).get("/meta").data, include_heavy=args.heavy)
    update.reindex()
    for path in update.changed:
        print(f"changed {path.relative_to(root)}")
    print(f"-- {len(update.changed)} files changed in {root}")
    return 0


def _digest_lines(spec: str, config: Config):
    from pathlib import Path

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

            return inputs.link_lines(load_catalog(_catalog_path(config))), "harvested data source links"
        case "file":
            return inputs.file_lines(Path(target)), Path(target).name
    raise SystemExit(f"unknown digest input {spec!r}: stars:USER | labels[:SOURCE] | links | file:PATH")


def cmd_digest(args: argparse.Namespace, config: Config) -> int:
    from gitrecon.digest import OllamaClient, Summarizer

    lines, topic = _digest_lines(args.input, config)
    client = OllamaClient(model=args.model) if args.model else OllamaClient()
    summarizer = Summarizer(client, topic=args.topic or topic, max_chars=args.chunk_chars,
                            progress=lambda m: print(m, file=sys.stderr))
    summary = summarizer.summarize(lines)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = args.input.replace(":", "-").replace("/", "_")
    out = config.data_dir / "digests" / f"{stamp}-{name}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(f"<!-- {topic} | {client.model} -->\n\n{summary}\n", encoding="utf-8")
    print(summary)
    print(f"-- saved {out}", file=sys.stderr)
    return 0


def cmd_posts(args: argparse.Namespace, config: Config) -> int:
    from pathlib import Path

    from gitrecon.digest import XaiClient, write_posts

    client = XaiClient(model=args.model) if args.model else XaiClient()
    if args.list_models:
        print("\n".join(client.models()))
        return 0
    summary = Path(args.summary).read_text(encoding="utf-8")
    posts = write_posts(client, summary, language=args.language)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = posts.save(config.data_dir / "posts" / f"{stamp}-{posts.article.slug or 'post'}")
    print(posts.article.to_markdown())
    for i, tweet in enumerate(posts.tweets, start=1):
        print(f"[tweet {i}/{len(posts.tweets)} {len(tweet)}c] {tweet}")
    for warning in posts.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    print(f"-- drafts saved in {out} (nothing was published)", file=sys.stderr)
    return 0


# --- text experiments ------------------------------------------------------


def cmd_text(args: argparse.Namespace, config: Config) -> int:
    from gitrecon.text import markdown, tokenizer
    from gitrecon.text.rat import build_rat

    md_text = markdown.fetch_text(args.url)
    match args.action:
        case "toc":
            print(markdown.render_toc(md_text))
        case "tokens":
            _dump(tokenizer.text_to_tokenchain_sentences(markdown.md_to_text(md_text)))
        case "rat":
            build = build_rat(markdown.md_to_text(md_text))
            print(build.script)
            print(f"-- RAT size {len(build.script)}, lines {build.lines}", file=sys.stderr)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gitrecon", description=__doc__)
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("events", help="poll an Events API feed into the raw buffer")
    p.add_argument("feed", nargs="?", default="public", help="public | user:X | org:X | repo:owner/name")
    p.add_argument("-w", "--watch", action="store_true", help="keep listening")
    p.set_defaults(func=cmd_events)

    p = sub.add_parser("gists", help="fetch public (or one user's) gists into the raw buffer")
    p.add_argument("--user")
    p.add_argument("--since", help="ISO timestamp")
    p.add_argument("--pages", type=int, default=3)
    p.set_defaults(func=cmd_gists)

    p = sub.add_parser("stars", help="list repositories starred by a user")
    p.add_argument("user", help="GitHub nickname, e.g. sarverott")
    p.add_argument("--json", action="store_true")
    p.add_argument("--save", action="store_true", help="also store them in the raw buffer")
    p.set_defaults(func=cmd_stars)

    p = sub.add_parser("archive", help="download GH Archive hours into the raw buffer")
    p.add_argument("start", help="YYYY-MM-DD-H (UTC)")
    p.add_argument("end", nargs="?", help="YYYY-MM-DD-H, inclusive")
    p.set_defaults(func=cmd_archive)

    p = sub.add_parser("map", help="build the activity graph from the raw buffer")
    p.add_argument("--source", help="events | gists | gharchive (default: all)")
    p.add_argument("--node", help="show neighbors of a key, e.g. user:octocat")
    p.add_argument("--full", action="store_true", help="dump all nodes and edges")
    p.set_defaults(func=cmd_map)

    p = sub.add_parser("label", help="conclude labels from the raw buffer")
    p.add_argument("--source")
    p.add_argument("--json", action="store_true")
    p.add_argument("--limit", type=int, default=50)
    p.set_defaults(func=cmd_label)

    p = sub.add_parser("status", help="show raw buffer contents")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("links", help="harvest data source links from cloned gists (or any notes)")
    p.add_argument("root", nargs="?", default="..", help="directory holding gist clones (default: ..)")
    p.add_argument("--all", action="store_true", help="scan every note file under root, not only gists")
    p.add_argument("--kind", action="append", help="keep only this kind (repeatable), e.g. feed")
    p.add_argument("--save", action="store_true", help="write the catalog to data/catalog/links.jsonl")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_links)

    p = sub.add_parser("atlas", help="the map dataset on Hugging Face (datasets/imperialmap)")
    p.add_argument("action", choices=["pull", "status", "update", "push"])
    p.add_argument("--repo", default="Apokryf/minimap-of-uce")
    p.add_argument("-m", "--message", help="commit message (push)")
    p.add_argument("--pr", action="store_true", help="push as a pull request on the Hub")
    p.add_argument("--no-meta", action="store_true", help="update: skip GitHub /meta networks")
    p.add_argument("--heavy", action="store_true", help="update: include the ~7k GitHub Actions CIDRs")
    p.set_defaults(func=cmd_atlas)

    p = sub.add_parser("digest", help="summarize big data with a local Ollama model (map-reduce)")
    p.add_argument("input", help="stars:USER | labels[:SOURCE] | links | file:PATH")
    p.add_argument("--model", help="Ollama model (default: $OLLAMA_MODEL or llama3)")
    p.add_argument("--topic")
    p.add_argument("--chunk-chars", type=int, default=16_000)
    p.set_defaults(func=cmd_digest)

    p = sub.add_parser("posts", help="write SEO article + tweets from a digest with xAI (drafts only)")
    p.add_argument("summary", nargs="?", help="digest markdown file")
    p.add_argument("--model", help="xAI model (default: $XAI_MODEL or grok-4)")
    p.add_argument("--language", default="English")
    p.add_argument("--list-models", action="store_true")
    p.set_defaults(func=cmd_posts)

    p = sub.add_parser("text", help="markdown/tokenizer/RAT experiments on a URL")
    p.add_argument("action", choices=["toc", "tokens", "rat"])
    p.add_argument("url", nargs="?", default="https://taskfile.dev/llms.txt")
    p.set_defaults(func=cmd_text)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    return args.func(args, Config())


if __name__ == "__main__":
    sys.exit(main())
