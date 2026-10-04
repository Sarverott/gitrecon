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
        return "\n".join(lines)

    text = {"summary": summary, "mermaid": diagram, "dot": lambda: render.to_dot(graph)}[args.format]
    if args.save:
        folder = config.data_dir / "networks"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{args.user}-{args.level}.md"
        path.write_text(f"# Network of {args.user} ({args.level})\n\n```mermaid\n{diagram()}\n```\n", encoding="utf-8")
        out.note(f"saved {path}")
    out.result(render.to_json(graph), text=text,
               urls=(node.html_url for node in graph.nodes.values() if node.html_url))
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

    p = sub.add_parser("label", help="conclude labels from the raw buffer")
    p.add_argument("--source")
    p.add_argument("--name", action="append", help="only this label (repeatable), e.g. star-burst")
    p.add_argument("--limit", type=int, default=50, help="how many to print as text (machine output: all)")
    add_output_flags(p)  # --urls: pages of the labeled entities
    p.set_defaults(func=cmd_label)

    p = sub.add_parser("status", help="show raw buffer contents")
    add_output_flags(p, urls=False)
    p.set_defaults(func=cmd_status)
