"""Looking and concluding: map, label, status."""

from __future__ import annotations

import argparse

from gitrecon.cli.output import Output, add_output_flags
from gitrecon.config import Config
from gitrecon.models.base import url_for_key
from gitrecon.storage import RawBuffer


def cmd_map(args: argparse.Namespace, config: Config, out: Output) -> int:
    from gitrecon.mapping import ActivityGraph

    graph = ActivityGraph()
    graph.ingest(RawBuffer(config.raw_dir).read(args.source))

    if args.node:
        neighbors = [{"relation": rel, "key": key, "url": url_for_key(key)} for rel, key in graph.neighbors(args.node)]
        out.listing(neighbors, text=lambda n: f"{n['relation']:<30} {n['key']}", data=lambda n: n,
                    url=lambda n: n["url"], summary=f"-- {len(neighbors)} relations of {args.node}")
    elif args.full:
        nodes = list(graph.nodes.values())
        if out.machine:
            out.result(graph.to_dict(), text="", urls=(n.html_url for n in nodes if n.html_url))
        else:
            for edge, evidence in graph.edges.items():
                print(f"{edge.source} -[{edge.relation}]-> {edge.target}  ({len(evidence)})")
            print(f"-- {len(nodes)} nodes, {len(graph.edges)} edges")
    else:
        summary = graph.summary()
        text = _summary_text(summary)
        summary["hubs"] = [{"key": key, "degree": n, "url": url_for_key(key)} for key, n in summary["hubs"]]
        out.result(summary, text=text, urls=(h["url"] for h in summary["hubs"] if h["url"]))
    return 0


def _summary_text(summary: dict) -> str:
    nodes = ", ".join(f"{kind} {n}" for kind, n in summary["nodes"].items())
    relations = ", ".join(f"{rel} {n}" for rel, n in list(summary["relations"].items())[:12])
    hubs = "\n".join(f"  {n:>6}  {key}" for key, n in summary["hubs"])
    return f"nodes: {nodes}\nedges: {summary['edges']}\nrelations: {relations}\nhubs:\n{hubs}"


def cmd_network(args: argparse.Namespace, config: Config, out: Output) -> int:
    from gitrecon.mapping import render
    from gitrecon.mapping.network import collect_network, owner_network
    from gitrecon.sources.github_api import GitHubClient

    graph = collect_network(args.user, GitHubClient(config), include_orgs=not args.no_orgs,
                            privacy=args.privacy, progress=out.note if args.verbose_progress else None)
    net = owner_network(graph)
    name = lambda key: render._name(key, graph)  # noqa: E731

    def diagram() -> str:
        if args.level == "repos":
            return render.repos_mermaid(graph, max_nodes=args.max_nodes, forks_only=args.forks_only)
        return render.owners_mermaid(graph, min_forks=args.min_forks)

    def summary() -> str:
        listed = sorted((k for k, s in net["owners"].items() if s["repos"]), key=lambda k: -net["owners"][k]["repos"])
        lines = [f"{len(graph.nodes)} nodes, {len(graph.edges)} relations around {args.user}", "", "owners:"]
        for key in listed:
            s = net["owners"][key]
            lines.append(f"  {s['kind']:<5} {name(key):<26} {s['repos']:>4} repos {s['forks']:>4} forks  ★{s['stars']}")
        lines += ["", "forks from (owner -> upstream owner):"]
        flows = sorted(((n, s, t) for (s, t), n in net["forks"].items() if s != t), key=lambda f: -f[0])
        lines += [f"  {n:>3}  {name(s):<26} -> {name(t)}" for n, s, t in flows[: args.limit]]
        if len(flows) > args.limit:
            lines.append(f"  ... {len(flows) - args.limit} more (--limit)")
        if graph.notes:
            lines += ["", "not seen:"] + [f"  {note}" for note in graph.notes]
        return "\n".join(lines)

    text = {"summary": summary, "mermaid": diagram, "dot": lambda: render.to_dot(graph)}[args.format]
    if args.save:
        folder = config.data_dir / "networks"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{args.user}-{args.level}.md"
        path.write_text(f"# Network of {args.user} ({args.level})\n\n```mermaid\n{diagram()}\n```\n", encoding="utf-8")
        out.note(f"saved {path}")
    if graph.notes and args.format != "summary":
        for note in graph.notes:
            out.note(f"note: {note}")
    out.result(render.to_json(graph) | {"notes": graph.notes}, text=text,
               urls=(node.html_url for node in graph.nodes.values() if node.html_url))
    return 0


def cmd_analyze(args: argparse.Namespace, config: Config, out: Output) -> int:
    from gitrecon.code import analyze_repo, find_repos

    if args.deep:
        from gitrecon.code import structure

        if not structure.available():
            out.note("--deep needs the code extra (uv sync --extra code); continuing with the quick reading only")
    repos = [repo for path in args.path for repo in find_repos(path)]
    if not repos:
        out.note(f"no repository in {', '.join(args.path)} (a folder with .git, or a folder of such folders)")
        return 2
    results = []
    for repo in repos:
        if len(repos) > 1:
            out.note(f"analysing {repo.name}")
        results.append(analyze_repo(repo, deep=args.deep))

    def text(r: dict) -> str:
        lines = [f"{r['name']}  ({r['files']} files, main language: {r['main_language'] or '-'})"]
        for name, e in list(r["languages"].items())[: args.limit]:
            detail = f"code {e['code']:>6}  comments {e['comment']:>5}" if e.get("code") else f"lines {e['lines']:>6}"
            lines.append(f"  {name:<18} {e['files']:>5} files {e['bytes'] / 1024:>9.1f} KiB  {detail}")
        if r["frameworks"]:
            lines.append("  frameworks & tools: " + ", ".join(r["frameworks"]))
        if py := r.get("python"):
            lines.append(f"  python: {py['functions']} functions, {py['classes']} classes, docstrings "
                         f"{py['docstring_ratio']:.0%}; imports: {', '.join(list(py['imports'])[:10])}")
        for name, s in (r.get("structure") or {}).items():
            counts = ", ".join(f"{v} {k}" for k, v in s["defined_kinds"].items())
            lines.append(f"  structure {name}: {counts or 'nothing defined'}"
                         + (f" ({s['unread']} of {s['files']} files unread)" if s["unread"] else ""))
        if r["names"]:
            lines.append("  names: " + ", ".join(list(r["names"])[:15]))
        if r["url_count"]:
            lines.append(f"  links in code: {r['url_count']}")
        return "\n".join(lines)

    from gitrecon.code.store import describe, save_analysis

    for result in results:
        describe(result)
    if args.format == "pie" and not out.machine:
        from gitrecon.mapping.contributors import pie

        shares: dict[str, float] = {}
        for r in results:
            for name, e in r["languages"].items():
                if e["kind"] in ("code", "markup"):
                    shares[name] = shares.get(name, 0) + round(e["bytes"] / 1024, 1)
        title = results[0]["name"] if len(results) == 1 else f"{len(results)} repositories"
        print(pie(shares, f"Languages of {title} (KiB of code)", top=args.limit), end="")
    else:
        out.listing(results, text=text, data=lambda r: r, url=lambda r: None,
                    summary=f"-- {len(results)} repositories analysed" if len(results) > 1 else None)
    if not args.no_save:
        from gitrecon.hub.huggingface import default_local_dir

        private: set[str] = set()
        if not args.map_priv_repos:
            from gitrecon.code.store import not_public
            from gitrecon.sources.github_api import GitHubClient

            private = not_public(results, GitHubClient(config))
        saved = save_analysis(results, config.raw_dir, default_local_dir(config), private=private)
        out.note(f"saved: {saved['buffered']} to the raw buffer ({config.raw_dir / 'analysis'}), "
                 f"{len(saved['mapped'])} new or changed in the map"
                 + (f"; kept out of the map (no origin, private or not shown public - --map-priv-repos "
                    f"writes them too): {', '.join(saved['unmapped'])}" if saved["unmapped"] else ""))
    if out.urls:
        for url in dict.fromkeys(u for r in results for u in r["urls"]):
            print(url)
    return 0


def cmd_commits(args: argparse.Namespace, config: Config, out: Output) -> int:
    from pathlib import Path

    from gitrecon.code.store import origin
    from gitrecon.humanish import commit_labels, read_commits, summarize_commits

    path = Path(args.path).expanduser().resolve()
    commits = read_commits(path, args.max_commits or None)
    source = origin(path)
    target = f"repo:{source['owner']}/{source['name']}".lower() if source else f"repo:{path.name}"
    summary = summarize_commits(commits)
    labels = commit_labels(target, commits)

    def text() -> str:
        counts = lambda d: ", ".join(f"{k} {v}" for k, v in d.items()) or "-"  # noqa: E731
        lines = [f"{path.name}: {summary['commits']} commits ({counts(summary['forms'])})",
                 f"  conventional form: {summary['conventional_share']:.0%} of {summary['own']} own commits",
                 f"  types:  {counts(summary['types'])}",
                 f"  work:   {counts(summary['work'])}",
                 f"  scopes: {counts(dict(list(summary['scopes'].items())[:8]))}",
                 f"  breaking: {summary['breaking']}"]
        if summary["unknown_types"]:
            lines.append(f"  types without a meaning in resources/humanish.yml: {', '.join(summary['unknown_types'])}")
        lines += [f"  {label}" for label in labels] or ["  no labels"]
        return "\n".join(lines)

    out.result({"repository": path.name, "target": target, "summary": summary,
                "labels": [label.to_json() for label in labels],
                "commits": [c.to_json() for c in commits] if args.list else None}, text=text)
    if args.list and not out.machine:
        for c in commits:
            mark = "!" if c.breaking else " "
            print(f"  {(c.sha or '')[:7]} {c.form:<12} {(c.type or '-'):<9}{mark} {c.subject[:70]}")
    return 0


def cmd_imports(args: argparse.Namespace, config: Config, out: Output) -> int:
    from pathlib import Path

    from gitrecon.code.imports import folder_edges, import_graph, imports_mermaid

    graph = import_graph(Path(args.path).expanduser())
    mermaid = imports_mermaid(graph, level=args.level, depth=args.depth, max_nodes=args.max_nodes)

    def summary() -> str:
        lines = [f"{graph['name']}: {len(graph['files'])} files read "
                 f"({', '.join(f'{n} {name}' for name, n in graph['languages'].items()) or 'none'}), "
                 f"{len(graph['edges'])} imports between them",
                 "  most used:"]
        lines += [f"    {m['used_by']:>4}  {m['file']}" for m in graph["most_used"][: args.limit]] or ["    -"]
        lines.append("  uses most:")
        lines += [f"    {m['uses']:>4}  {m['file']}" for m in graph["uses_most"][: args.limit]] or ["    -"]
        between = sorted(folder_edges(graph, args.depth).items(), key=lambda kv: (-kv[1], kv[0]))
        if between:
            lines.append(f"  between folders ({args.depth} levels deep):")
            lines += [f"    {n:>4}  {source} -> {target}" for (source, target), n in between[: args.limit]]
        lines.append(f"  cycles: {len(graph['cycles'])}")
        lines += [f"    {' <-> '.join(group[:6])}{' ...' if len(group) > 6 else ''}" for group in graph["cycles"][:5]]
        lines.append(f"  unconnected files: {len(graph['unconnected'])}")
        outside = list(graph["external"].items())[: args.limit]
        lines.append("  external: " + (", ".join(f"{name} ({n})" for name, n in outside) or "-"))
        return "\n".join(lines)

    out.result(graph | {"mermaid": mermaid}, text=mermaid.rstrip("\n") if args.format == "mermaid" else summary)
    if args.save:
        folder = config.data_dir / "imports"
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / f"{graph['name']}-{args.level}.md"
        target.write_text(f"# Imports inside {graph['name']} ({args.level} level)\n\n```mermaid\n{mermaid}```\n",
                          encoding="utf-8")
        out.note(f"saved {target}")
    return 0


def add_ignorelist_flag(p: argparse.ArgumentParser, effect: str) -> None:
    p.add_argument("--ignorelist", nargs="?", const="", metavar="FILE",
                   help=f"skip the identities listed in FILE (default list: resources/ignorelist.txt - bots): {effect}")


def _ignorelist(args: argparse.Namespace, out: Output) -> list[str] | None:
    if args.ignorelist is None:
        return None
    from gitrecon.mapping.contributors import read_ignorelist

    return read_ignorelist(args.ignorelist or None)


def cmd_contributors(args: argparse.Namespace, config: Config, out: Output) -> int:
    from pathlib import Path

    from gitrecon.mapping import contributors as who

    path = Path(args.path).expanduser().resolve()
    people = who.contributors(path, args.max_commits or None, ignore=_ignorelist(args, out))
    if args.format == "authors":
        text = who.authors_text(people, path.name)
    elif args.format == "pie":
        text = who.contributors_pie(people, path.name, by=args.by, top=args.top)
    else:
        text = None
    if text is None:
        out.listing(people, data=lambda c: c.to_json(), url=lambda c: None,
                    text=lambda c: f"{c.commits + c.merges:>6} commits ({c.merges} merges)  +{c.added:<8} -{c.deleted:<8} "
                                   f"{c.to_json()['first']} .. {c.to_json()['last']}  {c.name}"
                                   + (f" <{c.emails[0]}>" if c.emails else "")
                                   + (f"  (also: {', '.join(c.names[:3])})" if c.names else ""),
                    summary=lambda found: f"-- {len(found)} contributors of {path.name}")
    else:
        out.result({"repository": path.name, "format": args.format, "text": text,
                    "contributors": [c.to_json() for c in people]}, text=text.rstrip("\n"))
    if args.save:
        folder = config.data_dir / "contributors"
        folder.mkdir(parents=True, exist_ok=True)
        if args.format == "pie":
            target = folder / f"{path.name}-{args.by}.md"
            target.write_text(f"# Contributors of {path.name}\n\n```mermaid\n{text}```\n", encoding="utf-8")
        else:
            target = folder / f"{path.name}.AUTHORS"
            target.write_text(who.authors_text(people, path.name), encoding="utf-8")
        out.note(f"saved {target}")
    return 0


def _outward(args: argparse.Namespace, config: Config, out: Output) -> int:
    """`relations` on one repository: what it holds on to outside itself (the third circle)."""
    from gitrecon.code.relations import OUTWARD_ORDER, outward_ties
    from gitrecon.mapping.contributors import pie

    client = None
    if not args.offline:
        from gitrecon.sources.github_api import GitHubClient

        client = GitHubClient(config)
    found = outward_ties(args.path, client)
    diagram = pie({kind: count for kind, count in found["counts"].items()},
                  f"What {found['name']} holds on to, by kind of tie")

    def summary() -> str:
        lines = [f"{found['name']}: " + ", ".join(f"{found['counts'][kind]} {kind}" for kind in OUTWARD_ORDER)]
        for kind in OUTWARD_ORDER:
            ties = [t for t in found["ties"] if t["kind"] == kind]
            if not ties:
                continue
            if kind == "registry":  # the long, ordinary part: names only
                by_ecosystem: dict[str, list[str]] = {}
                for tie in ties:
                    by_ecosystem.setdefault(tie["ecosystem"], []).append(tie["name"])
                lines += [f"  registry   {eco}: {', '.join(names)}" for eco, names in by_ecosystem.items()]
            else:
                lines += [f"  {kind:<10} {t['ecosystem']}: {t['name']}" + (f"  <- {t['detail']}" if t["detail"] else "")
                          for t in ties]
        lines += [f"  note: {note}" for note in found["notes"]]
        return "\n".join(lines)

    out.result(found | {"mermaid": diagram}, text=diagram.rstrip("\n") if args.format == "mermaid" else summary)
    return 0


def cmd_relations(args: argparse.Namespace, config: Config, out: Output) -> int:
    from gitrecon.code.relations import owner_relations, relations_mermaid

    from pathlib import Path

    if (Path(args.path).expanduser() / ".git").exists():
        return _outward(args, config, out)
    relations = owner_relations(args.path)
    if not relations["repositories"]:
        out.note(f"no repositories directly inside {relations['folder']} (expected: a folder of clones, "
                 "such as ~/__WORKSHOP/forge/<owner>)")
        return 2
    mermaid = relations_mermaid(relations, show_untied=args.all)

    def summary() -> str:
        edges = relations["edges"]
        lines = [f"{relations['name']}: {len(relations['repositories'])} repositories, "
                 f"{sum(e['kind'] == 'submodule' for e in edges)} submodule ties, "
                 f"{sum(e['kind'] == 'dependency' for e in edges)} dependency ties between them"]
        lines += [f"  {e['kind']:<10} {e['from']} -> {e['to']}  ({e['detail']})" for e in edges]
        outside = relations["outside_submodules"]
        if outside:
            lines.append(f"  submodules from outside the folder: {len(outside)}")
            lines += [f"    {m['from']}: {m['path']} <- {m['url']}" for m in outside[:20]]
        lines.append(f"  untied: {len(relations['untied'])}"
                     + (f" ({', '.join(relations['untied'][:12])}{' ...' if len(relations['untied']) > 12 else ''})"
                        if relations["untied"] else ""))
        return "\n".join(lines)

    out.result(relations | {"mermaid": mermaid}, text=mermaid.rstrip("\n") if args.format == "mermaid" else summary)
    if args.save:
        folder = config.data_dir / "relations"
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / f"{relations['name']}.md"
        target.write_text(f"# Ties between the repositories in {relations['name']}\n\n```mermaid\n{mermaid}```\n",
                          encoding="utf-8")
        out.note(f"saved {target}")
    return 0


def cmd_score(args: argparse.Namespace, config: Config, out: Output) -> int:
    from pathlib import Path

    from gitrecon.mapping import score
    from gitrecon.mapping.gitgraph import assign_lanes, branch_tips, read_history

    path = Path(args.path).expanduser().resolve()
    commits = read_history(path, args.max_commits or None)
    lanes = assign_lanes(commits, branch_tips(path))
    notes = score.score_notes(commits, ignore=_ignorelist(args, out))
    folder = config.data_dir / "scores"
    band = args.contributors_band_mode
    members = score.band(notes) if band else None
    suffix = "-band" if band else ""
    if args.format == "midi":
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / f"{path.name}{suffix}.mid"
        target.write_bytes(score.to_midi(notes, tempo=args.tempo, band_mode=band))
        played = (f"{len(members)} contributors: " + ", ".join(f"{m['author']} ({m['instrument']})" for m in members[:8])
                  if band else f"{min(len(lanes), 6)} strings")
        out.result({"repository": path.name, "notes": len(notes), "file": str(target), "band": members},
                   text=f"{path.name}: {len(notes)} notes, {played} -> {target}")
        return 0
    text = (score.to_tab(notes, band_mode=band) if args.format == "tab"
            else score.to_abc(notes, title=path.name, band_mode=band))
    out.result({"repository": path.name, "format": args.format, "lanes": lanes, "band": members, "score": text,
                "notes": [{"sha": n.sha, "lane": n.lane, "string": n.string, "frets": n.frets, "eighths": n.eighths,
                           "pitches": n.pitches, "tag": n.tag, "author": n.author} for n in notes]}, text=text.rstrip("\n"))
    if args.save:
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / f"{path.name}{suffix}.{'abc' if args.format == 'abc' else 'tab.txt'}"
        target.write_text(text, encoding="utf-8")
        out.note(f"saved {target}")
    return 0


def cmd_gitgraph(args: argparse.Namespace, config: Config, out: Output) -> int:
    from collections import Counter
    from pathlib import Path

    from gitrecon.mapping import gitgraph

    path = Path(args.path).expanduser().resolve()
    commits = gitgraph.read_history(path, args.max_commits or None)
    lanes = gitgraph.assign_lanes(commits, gitgraph.branch_tips(path))
    diagram = gitgraph.git_graph(path, max_commits=args.max_commits or None, labels=args.labels)
    per_lane = Counter(c.lane for c in commits)

    def summary() -> str:
        merges = sum(len(c.parents) > 1 for c in commits)
        lines = [f"{path.name}: {len(commits)} commits, {merges} merges, {len(lanes)} lanes", ""]
        lines += [f"  {per_lane[lane]:>5}  {lane}" for lane in lanes]
        tagged = [f"{t} ({c.short})" for c in commits for t in c.tags]
        if tagged:
            lines += ["", "tags: " + ", ".join(tagged[-12:])]
        return "\n".join(lines)

    if args.save:
        folder = config.data_dir / "gitgraphs"
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / f"{path.name}.md"
        target.write_text(f"# Git graph of {path.name}\n\n```mermaid\n{diagram}```\n", encoding="utf-8")
        out.note(f"saved {target}")
    data = {"repository": str(path), "lanes": {lane: per_lane[lane] for lane in lanes},
            "commits": [{"sha": c.sha, "parents": c.parents, "lane": c.lane, "time": c.time, "author": c.author,
                         "subject": c.subject, "tags": c.tags} for c in commits]}
    out.result(data, text=summary if args.format == "summary" else diagram.rstrip("\n"))
    return 0


def cmd_label(args: argparse.Namespace, config: Config, out: Output) -> int:
    from gitrecon.analysis import Labeler

    labeler = Labeler()
    labeler.ingest(RawBuffer(config.raw_dir).read(args.source))
    labels = labeler.run()
    if args.name:
        labels = [label for label in labels if label.name in args.name]
    # --limit trims the readable list; --json and --urls hand over everything
    shown = labels if out.machine else labels[: args.limit]
    out.listing(shown, text=str, summary=f"-- {len(labels)} labels")
    return 0


def cmd_status(args: argparse.Namespace, config: Config, out: Output) -> int:
    buffer = RawBuffer(config.raw_dir)
    sources = []
    for source in buffer.sources():
        files = buffer.files(source)
        sources.append({"source": source, "files": len(files), "bytes": sum(f.stat().st_size for f in files)})
    data = {
        "data_dir": str(config.data_dir.resolve()),
        "datasets_dir": str(config.datasets_dir.resolve()),
        "token": bool(config.github_token),
        "sources": sources,
    }

    def text() -> str:
        lines = [f"data dir: {data['data_dir']}",
                 f"token:    {'set' if data['token'] else 'not set (60 req/h)'}"]
        lines += [f"  {s['source']:<10} {s['files']:>5} files {s['bytes'] / 2**20:>10.1f} MiB" for s in sources]
        return "\n".join(lines)

    out.result(data, text=text)
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("map", help="build the activity graph from the raw buffer")
    p.add_argument("--source", help="events | gists | gharchive (default: all)")
    p.add_argument("--node", help="show neighbors of a key, e.g. user:octocat")
    p.add_argument("--full", action="store_true", help="every edge (with --json: all nodes and edges)")
    add_output_flags(p)  # --urls: hubs, neighbors (--node) or every node (--full)
    p.set_defaults(func=cmd_map)

    p = sub.add_parser("network", help="relations around a user: repositories, organizations, where forks come from")
    p.add_argument("user", help="GitHub nickname, e.g. sarverott")
    p.add_argument("--format", choices=["summary", "mermaid", "dot"], default="summary",
                   help="summary (default), a Mermaid diagram, or Graphviz DOT of everything")
    p.add_argument("--level", choices=["owners", "repos"], default="owners",
                   help="diagram zoom: owners (who forks from whom) or repositories grouped by owner")
    p.add_argument("--min-forks", type=int, default=1, help="owners level: draw fork flows of at least N")
    p.add_argument("--max-nodes", type=int, default=150, help="repos level: most connected N repositories")
    p.add_argument("--forks-only", action="store_true", help="repos level: only repositories in a fork relation")
    p.add_argument("--no-orgs", action="store_true", help="only the user's own repositories")
    p.add_argument("--privacy", choices=["public", "all"], default="public", help="all: private too (own token)")
    p.add_argument("--limit", type=int, default=25, help="summary: how many fork flows to list")
    p.add_argument("--save", action="store_true", help="write the diagram to data/networks/<user>-<level>.md")
    p.add_argument("--progress", dest="verbose_progress", action="store_true", help="say what is being collected")
    add_output_flags(p)  # --json: nodes, edges and the owner overview; --urls: every node's page
    p.set_defaults(func=cmd_network)

    p = sub.add_parser("analyze", help="what cloned repositories are made of: languages, structure, frameworks")
    p.add_argument("path", nargs="*", default=["."],
                   help="repositories, or folders of repositories such as ~/__WORKSHOP/forge/rattish (default: .)")
    p.add_argument("--limit", type=int, default=8, help="languages listed per repository (pie: slices)")
    p.add_argument("--format", choices=["summary", "pie"], default="summary",
                   help="summary (default) or a Mermaid pie of the languages, all given repositories together")
    p.add_argument("--deep", action="store_true",
                   help="CaptorLex step 1: also functions, methods, classes per language (tree-sitter; code extra)")
    p.add_argument("--map-priv-repos", action="store_true",
                   help="write private repositories to the map dataset too (by default only public ones; "
                        "the map gets published)")
    p.add_argument("--no-save", action="store_true",
                   help="only print: by default results go to the raw buffer and the map dataset")
    add_output_flags(p)  # --json: the full analysis; --urls: links found in code and comments
    p.set_defaults(func=cmd_analyze, rest="path", rest_default=["."])

    p = sub.add_parser("commits", help="a cloned repository's commit messages read as records: types, scopes, labels")
    p.add_argument("path", nargs="?", default=".", help="the repository (default: the current folder)")
    p.add_argument("--max-commits", type=int, default=0, help="only the newest N (default: all)")
    p.add_argument("--list", action="store_true", help="also every commit with its form and type")
    add_output_flags(p, urls=False)
    p.set_defaults(func=cmd_commits)

    p = sub.add_parser("imports", help="which file uses which inside a cloned repository (CaptorLex step 2)")
    p.add_argument("path", nargs="?", default=".", help="the repository (default: the current folder)")
    p.add_argument("--format", choices=["summary", "mermaid"], default="summary")
    p.add_argument("--level", choices=["folder", "file"], default="folder", help="mermaid: folders (default) or files")
    p.add_argument("--depth", type=int, default=3, help="folder level: how many path parts make a folder")
    p.add_argument("--max-nodes", type=int, default=80, help="file level: draw the N most connected files")
    p.add_argument("--limit", type=int, default=8, help="summary: rows per list")
    p.add_argument("--save", action="store_true", help="write the diagram to data/imports/<repository>-<level>.md")
    add_output_flags(p, urls=False)  # --json: files, edges, most_used, cycles, external, mermaid
    p.set_defaults(func=cmd_imports)

    p = sub.add_parser("contributors", help="who made a cloned repository: commits, lines, dates; AUTHORS text; pie")
    p.add_argument("path", nargs="?", default=".", help="the repository (default: the current folder)")
    p.add_argument("--format", choices=["list", "authors", "pie"], default="list",
                   help="list (default), the text of an AUTHORS file, or a Mermaid pie")
    p.add_argument("--by", choices=["commits", "lines", "added"], default="commits", help="pie: what a slice measures")
    p.add_argument("--top", type=int, default=12, help="pie: slices before the rest becomes 'others'")
    p.add_argument("--max-commits", type=int, default=0, help="only the newest N commits (default: all)")
    add_ignorelist_flag(p, "they are not listed, credited or drawn")
    p.add_argument("--save", action="store_true",
                   help="write data/contributors/<repository>.AUTHORS (pie: <repository>-<by>.md)")
    add_output_flags(p, urls=False)
    p.set_defaults(func=cmd_contributors)

    p = sub.add_parser("relations", help="ties between an owner's cloned repositories (a folder of clones), or what "
                                         "one repository holds on to outside itself (a clone)")
    p.add_argument("path", help="a folder of clones, e.g. ~/__WORKSHOP/forge/rattish - or one repository")
    p.add_argument("--offline", action="store_true", help="one repository: do not ask GitHub whether it is a fork")
    p.add_argument("--format", choices=["summary", "mermaid"], default="summary")
    p.add_argument("--all", action="store_true", help="mermaid: draw repositories without ties too")
    p.add_argument("--save", action="store_true", help="write the diagram to data/relations/<folder>.md")
    add_output_flags(p, urls=False)  # --json: repositories, edges, outside_submodules, untied, mermaid
    p.set_defaults(func=cmd_relations)

    p = sub.add_parser("score", help="a cloned repository's history as music: guitar tab, ABC notation or MIDI")
    p.add_argument("path", nargs="?", default=".", help="the repository (default: the current folder)")
    p.add_argument("--format", choices=["tab", "abc", "midi"], default="tab",
                   help="tab (default), abc, or midi - written to data/scores/<repository>.mid")
    p.add_argument("--max-commits", type=int, default=64, help="play the newest N commits (0: all)")
    p.add_argument("--tempo", type=int, default=96, help="midi: quarter notes per minute")
    p.add_argument("--contributors-band-mode", action="store_true",
                   help="an instrument per contributor: the busiest plays guitar, then bass, piano, violin ...")
    add_ignorelist_flag(p, "their commits are silent and they get no instrument")
    p.add_argument("--save", action="store_true", help="tab, abc: also write data/scores/<repository>.abc | .tab.txt")
    add_output_flags(p, urls=False)
    p.set_defaults(func=cmd_score)

    p = sub.add_parser("gitgraph", help="a cloned repository's history across all branches, as a Mermaid gitGraph")
    p.add_argument("path", nargs="?", default=".", help="the repository (default: the current folder)")
    p.add_argument("--format", choices=["summary", "mermaid"], default="summary",
                   help="summary of lanes (default) or the Mermaid script")
    p.add_argument("--max-commits", type=int, default=150, help="draw the newest N commits (0: all)")
    p.add_argument("--labels", action="store_true", help="show commit subjects next to the commits")
    p.add_argument("--save", action="store_true", help="write the diagram to data/gitgraphs/<repository>.md")
    add_output_flags(p, urls=False)  # --json: commits with their lanes
    p.set_defaults(func=cmd_gitgraph)

    p = sub.add_parser("label", help="conclude labels from the raw buffer")
    p.add_argument("--source")
    p.add_argument("--name", action="append", help="only this label (repeatable), e.g. star-burst")
    p.add_argument("--limit", type=int, default=50, help="how many to print as text (machine output: all)")
    add_output_flags(p)  # --urls: pages of the labeled entities
    p.set_defaults(func=cmd_label)

    p = sub.add_parser("status", help="show raw buffer contents")
    add_output_flags(p, urls=False)
    p.set_defaults(func=cmd_status)
