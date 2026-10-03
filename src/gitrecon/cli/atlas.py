"""The map dataset on Hugging Face: atlas pull | status | update | push."""

from __future__ import annotations

import argparse
from pathlib import Path

from gitrecon.cli.output import Output, add_output_flags
from gitrecon.config import Config

HUB_DATASETS = "https://huggingface.co/datasets"


def cmd_atlas(args: argparse.Namespace, config: Config, out: Output) -> int:
    from gitrecon.hub.huggingface import MapDataset, default_local_dir

    dataset = MapDataset(repo_id=args.repo, local_dir=default_local_dir(config))
    page = f"{HUB_DATASETS}/{dataset.repo_id}"
    match args.action:
        case "pull":
            path = dataset.pull()
            out.result({"repo": dataset.repo_id, "url": page, "path": str(path)},
                       text=f"pulled {dataset.repo_id} -> {path}", urls=[page])
        case "status":
            files = dataset.files()
            areas = {
                area: sum(1 for f in files if f.relative_to(dataset.local_dir).parts[0] == area)
                for area in dataset.areas()
            }
            text = "\n".join([f"{dataset.repo_id} at {dataset.local_dir}",
                              *(f"  {area:<22} {n:>6} files" for area, n in areas.items())])
            out.result({"repo": dataset.repo_id, "url": page, "path": str(dataset.local_dir), "areas": areas},
                       text=text, urls=[page])
        case "update":
            return _update(args, config, dataset.local_dir, out)
        case "push":
            if not args.message:
                out.note("--message is required for push")
                return 2
            commit = dataset.push(args.message, create_pr=args.pr)
            commit_url = str(getattr(commit, "commit_url", commit))
            out.result({"repo": dataset.repo_id, "commit": commit_url, "pull_request": args.pr},
                       text=f"pushed: {commit_url}", urls=[commit_url])
    return 0


def _update(args: argparse.Namespace, config: Config, root: Path, out: Output) -> int:
    from gitrecon.atlas import AtlasUpdate
    from gitrecon.sources.github_api import GitHubClient
    from gitrecon.sources.links import load_catalog

    update = AtlasUpdate(root)
    if config.links_catalog.exists():
        update.add_links(load_catalog(config.links_catalog), union="gist-harvest")
    else:
        out.note(f"no link catalog at {config.links_catalog} (run: gitrecon links --save)")
    if not args.no_meta:
        update.add_github_meta(GitHubClient(config).get("/meta").data, include_heavy=args.heavy)
    if args.stars:
        update.changed += _fill_namespace(args.stars, config, root, out).changed
    update.reindex()
    changed = [str(path.relative_to(root)) for path in update.changed]
    text = "\n".join([*(f"changed {path}" for path in changed), f"-- {len(changed)} files changed in {root}"])
    out.result({"root": str(root), "changed": changed}, text=text)
    return 0


def _fill_namespace(users: list[str], config: Config, root: Path, out: Output):
    from gitrecon.atlas.namespace import UserNamespace, github_owner_identities, link_identities
    from gitrecon.sources import stars
    from gitrecon.sources.github_api import GitHubClient
    from gitrecon.sources.links import load_catalog

    namespace = UserNamespace(root)
    client = GitHubClient(config)
    for user in users:
        owners = github_owner_identities(stars.starred(client, user))
        for identity in owners:
            namespace.add(identity)
        out.note(f"user-namespace: {len(owners)} owners of repos starred by {user}")
    if config.links_catalog.exists():
        for profile, gist_profile in link_identities(load_catalog(config.links_catalog)):
            if gist_profile:
                namespace.link(profile, gist_profile)
            else:
                namespace.add(profile)
    namespace.flush()
    return namespace


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("atlas", help="the map dataset on Hugging Face (datasets/imperialmap)")
    p.add_argument("action", choices=["pull", "status", "update", "push"])
    p.add_argument("--repo", default="Apokryf/minimap-of-uce")
    p.add_argument("-m", "--message", help="commit message (push)")
    p.add_argument("--pr", action="store_true", help="push as a pull request on the Hub")
    p.add_argument("--no-meta", action="store_true", help="update: skip GitHub /meta networks")
    p.add_argument("--heavy", action="store_true", help="update: include the ~7k GitHub Actions CIDRs")
    p.add_argument("--stars", action="append", metavar="USER",
                   help="update: add owners of repos starred by USER to user-namespace (repeatable)")
    add_output_flags(p)  # --urls: the dataset page (pull, status) or the commit (push)
    p.set_defaults(func=cmd_atlas)
