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

    p = sub.add_parser("label", help="conclude labels from the raw buffer")
    p.add_argument("--source")
    p.add_argument("--name", action="append", help="only this label (repeatable), e.g. star-burst")
    p.add_argument("--limit", type=int, default=50, help="how many to print as text (machine output: all)")
    add_output_flags(p)  # --urls: pages of the labeled entities
    p.set_defaults(func=cmd_label)

    p = sub.add_parser("status", help="show raw buffer contents")
    add_output_flags(p, urls=False)
    p.set_defaults(func=cmd_status)
