"""Collecting commands: events, gists, stars, archive, links, feeds, rfc, blog."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from gitrecon.cli.output import Output, add_output_flags
from gitrecon.config import Config
from gitrecon.storage import RawBuffer


def _client(config: Config):
    from gitrecon.sources.github_api import GitHubClient

    return GitHubClient(config)


def cmd_events(args: argparse.Namespace, config: Config, out: Output) -> int:
    from gitrecon.models import Event
    from gitrecon.sources.events import EventPoller, Feed

    buffer = RawBuffer(config.raw_dir)
    feed = Feed.parse(args.feed)
    poller = EventPoller(_client(config), feed, state_dir=config.state_dir)
    for batch in poller.listen(max_rounds=None if args.watch else 1):
        stored = buffer.append("events", batch, suffix=feed.name)
        if out.machine:
            out.stream((Event.from_api(record) for record in batch), text=str)
        out.note(f"{feed.name}: +{stored} events (next poll in {poller.state.poll_interval}s)")
    return 0


def cmd_gists(args: argparse.Namespace, config: Config, out: Output) -> int:
    from gitrecon.models import Gist
    from gitrecon.sources import gists

    client = _client(config)
    if args.user:
        raw, suffix = gists.user_gists(client, args.user), f"user-{args.user}"
    else:
        raw, suffix = gists.public_gists(client, since=args.since, max_pages=args.pages), "public"
    stored = RawBuffer(config.raw_dir).append("gists", raw, suffix=suffix)

    def text(gist: Gist) -> str:
        when = f"{gist.created_at:%Y-%m-%d %H:%M}" if gist.created_at else "?"
        names = ", ".join(f.filename for f in gist.files)[:60]
        return f"{when}  {gist.owner or '-':<20} {names:<60} {(gist.description or '')[:50]}"

    out.listing([Gist.from_api(item) for item in raw], text=text,
                summary=f"-- gists ({suffix}): {stored} stored")
    return 0


def cmd_gist_catalog(args: argparse.Namespace, config: Config, out: Output) -> int:
    from gitrecon.sources.gists import gist_catalog

    catalog = gist_catalog(args.user, _client(config), privacy=args.privacy,
                           with_commits=not args.no_commits)

    def text(g: dict) -> str:
        files = ", ".join(g["filelist"])[:48]
        commits = "-" if g["commits"] is None else g["commits"]
        lock = " " if g["public"] else "🔒"
        return (f"{(g['created_at'] or '')[:10]} {lock} {g['gistID']}  *{g['stars']:<3} forks {g['forks']:<3} "
                f"comments {g['comments']:<3} commits {commits!s:<4} {g['size'] / 1024:>8.1f} KiB  {files}")

    def summary(items: list) -> str:
        size = sum(g["size"] for g in items) / 2**20
        return f"-- {len(items)} gists of {args.user} ({args.privacy}), {size:.1f} MiB of files"

    out.listing(catalog, text=text, data=lambda g: g, url=lambda g: g["url"], summary=summary)
    return 0


def cmd_gist_clone(args: argparse.Namespace, config: Config, out: Output) -> int:
    from gitrecon.sources.cloning import default_clone_path
    from gitrecon.sources.gists import GISTS_DIRNAME, clone_gists, gist_catalog

    path = Path(args.path).expanduser() if args.path else default_clone_path(args.user, GISTS_DIRNAME)
    catalog = gist_catalog(args.user, _client(config), privacy=args.privacy, with_commits=False)
    chosen = catalog[: args.limit] if args.limit else catalog
    size = sum(g["size"] for g in chosen) / 2**20
    if args.dry_run:
        out.listing(chosen, text=lambda g: f"would clone {g['gistID']}  {g['size'] / 1024:>8.1f} KiB  "
                                           f"{', '.join(g['filelist'])[:50]}",
                    data=lambda g: g, url=lambda g: g["url"],
                    summary=f"-- {len(chosen)} of {len(catalog)} gists, {size:.1f} MiB of files (plus history) "
                            f"-> {path}")
        return 0
    out.note(f"cloning {len(chosen)} of {len(catalog)} gists ({size:.1f} MiB of files) into {path}")
    results = clone_gists(chosen, path, update=args.update, progress=out.note if not out.machine else None)
    failed = [r for r in results if r["status"] == "failed"]
    out.listing(results, text=lambda r: f"{r['status']:<8} {r['gistID']}" + (f"  {r['error']}" if r["error"] else ""),
                data=lambda r: r, url=lambda r: f"https://gist.github.com/{r['gistID']}",
                summary=f"-- {len(results) - len(failed)} ok, {len(failed)} failed")
    return 1 if failed else 0


def _repo_text(r: dict) -> str:
    flags = " ".join(f for f, on in (("fork", r["fork"]), ("archived", r["archived"]), ("private", r["private"])) if on)
    return (f"{(r['created_at'] or '')[:10]}  {r['full_name']:<50} {r['language'] or '-':<12} *{r['stars']:<5} "
            f"{r['size_kib'] / 1024:>8.1f} MiB  {flags}")


def _repo_summary(what: str):
    def summary(items: list) -> str:
        size = sum(r["size_kib"] for r in items) / 1024
        forks = sum(r["fork"] for r in items)
        return f"-- {len(items)} repositories of {what} ({forks} forks), about {size:,.1f} MiB on GitHub"
    return summary


def cmd_repos(args: argparse.Namespace, config: Config, out: Output) -> int:
    from gitrecon.sources.repos import user_repos

    found = user_repos(args.user, _client(config), privacy=args.privacy, include_forks=not args.no_forks,
                       include_archived=not args.no_archived)
    out.listing(found, text=_repo_text, data=lambda r: r, url=lambda r: r["url"], summary=_repo_summary(args.user))
    return 0


def cmd_orgs(args: argparse.Namespace, config: Config, out: Output) -> int:
    from gitrecon.sources.repos import user_orgs

    found = user_orgs(args.user, _client(config))
    out.listing(found, text=lambda o: f"{o['login']:<28} {o['description'][:80]}", data=lambda o: o,
                url=lambda o: o["url"], summary=f"-- {len(found)} organizations of {args.user}")
    return 0


def cmd_org_repos(args: argparse.Namespace, config: Config, out: Output) -> int:
    from gitrecon.sources.repos import org_repos

    found = org_repos(args.org, _client(config), include_forks=not args.no_forks, include_archived=not args.no_archived)
    out.listing(found, text=_repo_text, data=lambda r: r, url=lambda r: r["url"], summary=_repo_summary(args.org))
    return 0


def _analyse_clones(results: list[dict], repos: list[dict], config: Config, out: Output,
                    map_private: bool = False) -> None:
    """Analyse what was cloned and keep it (raw buffer + map); a short ``analysis`` lands on each result."""
    from gitrecon.code import analyze_repo
    from gitrecon.code.store import save_analysis
    from gitrecon.hub.huggingface import default_local_dir

    analyses = []
    for result in results:
        if result["status"] == "failed":
            continue
        try:
            analysis = analyze_repo(result["path"])
        except Exception as error:  # noqa: BLE001 - analysis never fails a clone
            out.note(f"analysis of {result['full_name']} failed: {error}")
            continue
        analyses.append(analysis)
        result["analysis"] = {"files": analysis["files"], "main_language": analysis["main_language"],
                              "frameworks": analysis["frameworks"]}
    if analyses:
        private = set() if map_private else {r["full_name"].lower() for r in repos if r.get("private")}
        saved = save_analysis(analyses, config.raw_dir, default_local_dir(config), private=private)
        out.note(f"analysed {saved['buffered']} (raw buffer: {config.raw_dir / 'analysis'}; "
                 f"{len(saved['mapped'])} new or changed in the map) - skip with --no-analysis")


def _clone_text(result: dict) -> str:
    line = f"{result['status']:<8} {result['full_name']}" + (f"  {result['error']}" if result["error"] else "")
    if analysis := result.get("analysis"):
        tools = f"; {', '.join(analysis['frameworks'][:6])}" if analysis["frameworks"] else ""
        line += f"  [{analysis['main_language'] or '-'}, {analysis['files']} files{tools}]"
    return line


def _clone_listed(repos: list[dict], args: argparse.Namespace, config: Config, out: Output, what: str) -> int:
    from gitrecon.sources.cloning import default_clone_path
    from gitrecon.sources.repos import clone_repos

    path = Path(args.path).expanduser() if args.path else default_clone_path(what)

    chosen = repos[: args.limit] if args.limit else repos
    size = sum(r["size_kib"] for r in chosen) / 1024
    depth = f", depth {args.depth}" if args.depth else ""
    if args.dry_run:
        out.listing(chosen, text=lambda r: f"would clone {_repo_text(r)}", data=lambda r: r, url=lambda r: r["url"],
                    summary=f"-- {len(chosen)} of {len(repos)} repositories of {what}, about {size:,.1f} MiB on "
                            f"GitHub{depth} -> {path}")
        return 0
    out.note(f"cloning {len(chosen)} of {len(repos)} repositories of {what} (about {size:,.1f} MiB{depth}) "
             f"into {path}")
    results = clone_repos(chosen, path, update=args.update, depth=args.depth,
                          progress=out.note if not out.machine else None)
    failed = [r for r in results if r["status"] == "failed"]
    if not args.no_analysis:
        _analyse_clones(results, chosen, config, out, map_private=args.map_priv_repos)
    out.listing(results, text=_clone_text,
                data=lambda r: r, url=lambda r: f"https://github.com/{r['full_name']}",
                summary=f"-- {len(results) - len(failed)} ok, {len(failed)} failed")
    return 1 if failed else 0


def cmd_repo_clone(args: argparse.Namespace, config: Config, out: Output) -> int:
    from gitrecon.sources.repos import user_repos

    repos = user_repos(args.user, _client(config), privacy=args.privacy, include_forks=not args.no_forks,
                       include_archived=not args.no_archived)
    return _clone_listed(repos, args, config, out, args.user)


def cmd_org_clone(args: argparse.Namespace, config: Config, out: Output) -> int:
    from gitrecon.sources.repos import org_repos

    repos = org_repos(args.org, _client(config), include_forks=not args.no_forks, include_archived=not args.no_archived)
    return _clone_listed(repos, args, config, out, args.org)


def cmd_stars(args: argparse.Namespace, config: Config, out: Output) -> int:
    from gitrecon.sources import stars

    raw = stars.starred_raw(_client(config), args.user)
    if args.save:
        RawBuffer(config.raw_dir).append("stars", raw, suffix=f"user-{args.user}")

    def text(star) -> str:
        when = f"{star.starred_at:%Y-%m-%d}" if star.starred_at else "?"
        return f"{when}  {star.repo.full_name:<50} {star.repo.language or '-':<14} *{star.repo.stargazers_count or 0}"

    out.listing([stars.Star.from_api(args.user, item) for item in raw], text=text,
                summary=lambda found: f"-- {len(found)} repositories starred by {args.user}")
    return 0


def cmd_archive(args: argparse.Namespace, config: Config, out: Output) -> int:
    from gitrecon.sources import gharchive

    buffer = RawBuffer(config.raw_dir)
    start = gharchive.parse_hour(args.start)
    end = gharchive.parse_hour(args.end) if args.end else start
    hours = []
    for hour in gharchive.hour_range(start, end):
        path = gharchive.download_hour(hour, buffer.partition("gharchive", hour), config)
        hours.append({
            "hour": hour.isoformat(),
            "source": f"{config.gharchive_url}/{gharchive.archive_name(hour)}",
            "path": str(path),
            "bytes": path.stat().st_size,
        })
        if not out.machine:
            print(f"{hour:%Y-%m-%d %H}:00 -> {path} ({path.stat().st_size / 2**20:.1f} MiB)")
    if out.machine:
        out.listing(hours, text=str, data=lambda h: h, url=lambda h: h["source"])
    return 0


def cmd_links(args: argparse.Namespace, config: Config, out: Output) -> int:
    from gitrecon.sources import links as harvest

    root = Path(args.root)
    found = harvest.harvest(root, exclude=[config.data_dir]) if args.all else harvest.harvest_gists(root)
    if args.kind:
        found = [link for link in found if link.kind in args.kind]
    if args.save:
        out.note(f"saved {harvest.save_catalog(found, config.links_catalog)}")

    def summary(items) -> str:
        counts = ", ".join(f"{k} {n}" for k, n in Counter(link.kind for link in items).most_common())
        return f"-- {len(items)} links: {counts}"

    out.listing(found, text=lambda link: f"{link.kind:<16} {link.url}", data=lambda link: link.to_dict(),
                url=lambda link: link.url, summary=summary)
    return 0


def cmd_feeds(args: argparse.Namespace, config: Config, out: Output) -> int:
    from gitrecon.sources.feeds import FeedReader, feed_key
    from gitrecon.sources.links import load_catalog

    urls = list(args.url)
    if not urls:
        if not config.links_catalog.exists():
            out.note(f"no feed urls given and no catalog at {config.links_catalog} (run: gitrecon links --save)")
            return 2
        urls = [link.url for link in load_catalog(config.links_catalog) if link.kind == "feed"]
    reader = FeedReader(state_file=config.state_dir / "feeds.json")
    buffer = RawBuffer(config.raw_dir)
    feeds, items = [], []
    for url, result in reader.poll_many(urls).items():
        if isinstance(result, Exception):
            feeds.append({"url": url, "new": 0, "error": str(result)})
            out.note(f"ERROR   {url}: {result}")
            continue
        if args.save and result:
            buffer.append("feeds", (item.to_record() for item in result), suffix=feed_key(url))
        feeds.append({"url": url, "new": len(result), "error": None})
        items += result
        if not out.machine:
            print(f"+{len(result):<5} {url}")
            if args.verbose_items:
                for item in result:
                    when = item.published or item.updated
                    print(f"        {when:%Y-%m-%d} {item.title[:100]}" if when else f"        {item.title[:100]}")
    out.result({"feeds": feeds, "items": [item.to_json() for item in items]},
               text=f"-- {len(items)} new items from {len(urls)} feeds",
               urls=(item.link for item in items if item.link))
    return 0


def cmd_rfc(args: argparse.Namespace, config: Config, out: Output) -> int:
    from gitrecon.sources import rfc_index

    rfcs = rfc_index.parse_index(rfc_index.fetch_index())
    if args.save:
        path = config.data_dir / "catalog" / "rfc-index.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            for rfc in rfcs:
                fh.write(json.dumps(rfc.to_dict(), ensure_ascii=False) + "\n")
        out.note(f"saved {path}")
    words = [w.lower() for w in args.search or []]
    if args.number:
        shown = [r for r in rfcs if r.number in args.number]
    elif words:
        shown = [r for r in rfcs if all(w in r.description.lower() for w in words)]
    else:
        shown = rfcs[-args.limit:]

    def text(rfc) -> str:
        line = f"RFC{rfc.number:<6} {rfc.date or '':<15} {(rfc.status or '-'):<22} {rfc.title[:90]}"
        if not args.number:
            return line
        relations = [f"{name}: {', '.join(getattr(rfc, attr))}" for name, attr in (
            ("obsoletes", "obsoletes"), ("obsoleted by", "obsoleted_by"), ("updates", "updates"),
            ("updated by", "updated_by"), ("also", "also")) if getattr(rfc, attr)]
        return "\n".join([line, f"        {', '.join(rfc.authors)}", f"        {rfc.url}",
                          *(f"        {r}" for r in relations)])

    out.listing(shown, text=text, summary=f"-- {len(shown)} of {len(rfcs)} RFCs")
    return 0


def cmd_blog(args: argparse.Namespace, config: Config, out: Output) -> int:
    from gitrecon.sources import blog

    index_html = blog.fetch_html(args.url)
    feeds = blog.discover_feeds(index_html, args.url)
    links = blog.article_links(index_html, args.url)[: args.limit]
    out.note(f"{len(links)} articles, feeds: {', '.join(feeds) or '-'}")
    articles = [blog.html_to_article(url, blog.fetch_html(url), args.url) for url in links]
    if args.save:
        RawBuffer(config.raw_dir).append("blogs", (a.to_record() for a in articles),
                                         suffix=blog.article_name(args.url).lower().replace(" ", "-") or "blog")
    if args.dump and not out.machine:
        print(f"# {args.url}\n\t-" + "\n\t-".join(links) + "\n\n---\n")
        print("\n\n---\n\n".join(a.to_markdown() for a in articles))
        return 0
    out.listing(articles, text=lambda a: f"{a.url_checksum:>10}  {len(a.markdown):>7}c  {a.name}")
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("events", help="poll an Events API feed into the raw buffer")
    p.add_argument("feed", nargs="?", default="public", help="public | user:X | org:X | repo:owner/name")
    p.add_argument("-w", "--watch", action="store_true", help="keep listening")
    add_output_flags(p)  # --json: JSON Lines, one event per line, as they arrive
    p.set_defaults(func=cmd_events)

    p = sub.add_parser("gists", help="fetch public (or one user's) gists into the raw buffer")
    p.add_argument("--user")
    p.add_argument("--since", help="ISO timestamp")
    p.add_argument("--pages", type=int, default=3)
    add_output_flags(p)
    p.set_defaults(func=cmd_gists)

    p = sub.add_parser("gist-catalog", help="every gist of a user: files, stars, comments, forks, commits, size")
    p.add_argument("user", help="GitHub nickname, e.g. sarverott")
    p.add_argument("--privacy", choices=["public", "all", "secret"], default="public",
                   help="all/secret need that user's own token")
    p.add_argument("--no-commits", action="store_true", help="skip counting commits (one request per gist)")
    add_output_flags(p)
    p.set_defaults(func=cmd_gist_catalog)

    p = sub.add_parser("gist-clone", help="clone a user's gists into PATH/<gistID>, as they are")
    p.add_argument("user", help="GitHub nickname, e.g. sarverott")
    p.add_argument("path", nargs="?", help="where the clones go, PATH/<gistID> (created when missing); "
                                           "default: <forge>/<USER>/my-gists, i.e. ~/__WORKSHOP/forge/<USER>/my-gists")
    p.add_argument("--privacy", choices=["public", "all", "secret"], default="public")
    p.add_argument("--limit", type=int, help="only the first N (oldest first)")
    p.add_argument("--update", action="store_true", help="fast-forward clones that exist already")
    p.add_argument("--dry-run", action="store_true", help="list what would be cloned and its size, clone nothing")
    add_output_flags(p)
    p.set_defaults(func=cmd_gist_clone)

    def repo_filters(p: argparse.ArgumentParser) -> None:
        p.add_argument("--no-forks", action="store_true", help="leave forks out")
        p.add_argument("--no-archived", action="store_true", help="leave archived repositories out")

    def clone_options(p: argparse.ArgumentParser) -> None:
        p.add_argument("path", nargs="?", help="where the clones go, PATH/<name> (created when missing); "
                                               "default: <forge>/<USER or ORG>/, i.e. ~/__WORKSHOP/forge/<name>/")
        p.add_argument("--limit", type=int, help="only the first N (oldest first)")
        p.add_argument("--depth", type=int, help="shallow clones, e.g. 1 = newest commit only (much smaller)")
        p.add_argument("--update", action="store_true", help="fast-forward clones that exist already")
        p.add_argument("--dry-run", action="store_true", help="list what would be cloned and its size, clone nothing")
        p.add_argument("--no-analysis", action="store_true",
                       help="only clone: by default every clone is analysed (languages, frameworks) and the "
                            "result kept in the raw buffer and the map dataset")

        p.add_argument("--map-priv-repos", action="store_true",
                       help="write the analysis of private repositories to the map dataset too")

    p = sub.add_parser("repos", help="repositories a user owns")
    p.add_argument("user", help="GitHub nickname, e.g. sarverott")
    p.add_argument("--privacy", choices=["public", "all"], default="public", help="all: private too (own token)")
    repo_filters(p)
    add_output_flags(p)
    p.set_defaults(func=cmd_repos)

    p = sub.add_parser("orgs", help="organizations a user belongs to (all of them with the user's own token)")
    p.add_argument("user", help="GitHub nickname, e.g. sarverott")
    add_output_flags(p)
    p.set_defaults(func=cmd_orgs)

    p = sub.add_parser("org-repos", help="repositories of an organization")
    p.add_argument("org", help="organization login, e.g. The-Apokryf")
    repo_filters(p)
    add_output_flags(p)
    p.set_defaults(func=cmd_org_repos)

    p = sub.add_parser("repo-clone", help="clone the repositories a user owns into PATH/<name>")
    p.add_argument("user", help="GitHub nickname, e.g. sarverott")
    clone_options(p)
    p.add_argument("--privacy", choices=["public", "all"], default="public", help="all: private too (own token)")
    repo_filters(p)
    add_output_flags(p)
    p.set_defaults(func=cmd_repo_clone)

    p = sub.add_parser("org-clone", help="clone the repositories of an organization into PATH/<name>")
    p.add_argument("org", help="organization login, e.g. The-Apokryf")
    clone_options(p)
    repo_filters(p)
    add_output_flags(p)
    p.set_defaults(func=cmd_org_clone)

    p = sub.add_parser("stars", help="list repositories starred by a user")
    p.add_argument("user", help="GitHub nickname, e.g. sarverott")
    p.add_argument("--save", action="store_true", help="also store them in the raw buffer")
    add_output_flags(p)
    p.set_defaults(func=cmd_stars)

    p = sub.add_parser("archive", help="download GH Archive hours into the raw buffer")
    p.add_argument("start", help="YYYY-MM-DD-H (UTC)")
    p.add_argument("end", nargs="?", help="YYYY-MM-DD-H, inclusive")
    add_output_flags(p)  # --urls: the archive files' source addresses
    p.set_defaults(func=cmd_archive)

    p = sub.add_parser("links", help="harvest data source links from cloned gists (or any notes)")
    p.add_argument("root", nargs="?", default="..", help="directory holding gist clones (default: ..)")
    p.add_argument("--all", action="store_true", help="scan every note file under root, not only gists")
    p.add_argument("--kind", action="append", help="keep only this kind (repeatable), e.g. feed")
    p.add_argument("--save", action="store_true", help="write the catalog to data/catalog/links.jsonl")
    add_output_flags(p)
    p.set_defaults(func=cmd_links)

    p = sub.add_parser("feeds", help="read RSS/Atom feeds (default: feeds in the link catalog)")
    p.add_argument("url", nargs="*")
    p.add_argument("--save", action="store_true", help="store new items in the raw buffer")
    p.add_argument("--items", dest="verbose_items", action="store_true", help="list new items")
    add_output_flags(p)  # --json: {"feeds": [...], "items": [...]}; --urls: item links
    p.set_defaults(func=cmd_feeds)

    p = sub.add_parser("rfc", help="RFC Editor index: list, search, save")
    p.add_argument("--search", nargs="+", help="words that must all appear in the entry")
    p.add_argument("--number", type=int, action="append", help="show one RFC in full (repeatable)")
    p.add_argument("--limit", type=int, default=20, help="newest N when not searching")
    p.add_argument("--save", action="store_true", help="write data/catalog/rfc-index.jsonl")
    add_output_flags(p)
    p.set_defaults(func=cmd_rfc)

    p = sub.add_parser("blog", help="harvest articles of a blog as markdown (default: Apokryf)")
    p.add_argument("url", nargs="?", default="https://blog.apokryf.pl")
    p.add_argument("--limit", type=int)
    p.add_argument("--dump", action="store_true", help="print articles in the notebook's dump format")
    p.add_argument("--save", action="store_true", help="store articles in the raw buffer")
    add_output_flags(p)
    p.set_defaults(func=cmd_blog)
