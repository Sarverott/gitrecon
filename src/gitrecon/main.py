"""gitrecon command line: collect -> buffer -> map -> label."""

from __future__ import annotations

import argparse
import json
import logging
import sys

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
