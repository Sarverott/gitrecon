"""Example: refresh the map dataset with gitrecon findings and push it to Hugging Face.

Uses the library directly (no CLI), step by step:

1. load secrets from dotenv files (HF_TOKEN, GH_TOKEN - see gitrecon.config.env_files)
2. make sure the local copy of the map exists; it is pulled only when missing,
   so local edits (like a README drafted by hand) are never overwritten
3. harvest data source links from the gist clones next to this project
4. write findings into the map: dnstrees, ip-address-records, host-unions and
   user-namespace (owners of repositories starred by --stars users)
5. push the map folder to the Hub as one commit (or a Hub pull request with --pr)

    uv run python examples/push_map.py --dry-run
    uv run python examples/push_map.py --stars sarverott -m "map: gist links, github meta, user-namespace"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from gitrecon.atlas import AtlasUpdate
from gitrecon.atlas.namespace import USER_NAMESPACE, UserNamespace, github_owner_identities, link_identities
from gitrecon.atlas.paths import DNSTREES, HOST_UNIONS, IP_RECORDS
from gitrecon.config import PROJECT_ROOT, Config, load_env
from gitrecon.hub.huggingface import DEFAULT_REPO_ID, MapDataset, default_local_dir
from gitrecon.sources import stars
from gitrecon.sources.github_api import GitHubClient
from gitrecon.sources.links import harvest_gists, save_catalog


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", default=DEFAULT_REPO_ID)
    parser.add_argument("--gists", type=Path, default=PROJECT_ROOT.parent, help="dir with gist clones")
    parser.add_argument("--stars", action="append", default=[], metavar="USER")
    parser.add_argument("-m", "--message", default="gitrecon: refresh map")
    parser.add_argument("--pr", action="store_true", help="open a pull request on the Hub instead")
    parser.add_argument("--dry-run", action="store_true", help="update locally, do not push")
    args = parser.parse_args()

    # 1. secrets
    loaded = load_env()
    print(f"env: {', '.join(map(str, loaded)) or 'none'}")
    config = Config()

    # 2. local copy of the map
    dataset = MapDataset(repo_id=args.repo, local_dir=default_local_dir(config))
    if not (dataset.local_dir / "README.md").exists():
        print(f"pulling {dataset.repo_id} -> {dataset.local_dir}")
        dataset.pull()

    # 3. links from gists
    links = harvest_gists(args.gists)
    save_catalog(links, config.data_dir / "catalog" / "links.jsonl")
    print(f"links: {len(links)} from gist clones in {args.gists}")

    # 4. findings into the map
    update = AtlasUpdate(dataset.local_dir)
    update.add_links(links, union="gist-harvest")
    client = GitHubClient(config)
    update.add_github_meta(client.get("/meta").data)

    namespace = UserNamespace(dataset.local_dir)
    for user in args.stars:
        owners = github_owner_identities(stars.starred(client, user))
        for identity in owners:
            namespace.add(identity)
        print(f"user-namespace: {len(owners)} owners of repos starred by {user}")
    for profile, gist_profile in link_identities(links):
        if gist_profile:
            namespace.link(profile, gist_profile)
        else:
            namespace.add(profile)
    namespace.flush()

    update.reindex((DNSTREES, IP_RECORDS, HOST_UNIONS, USER_NAMESPACE))
    changed = update.changed + namespace.changed
    print(f"changed locally: {len(changed)} files")
    for area in dataset.areas():
        print(f"  {area:<22} {sum(1 for f in dataset.files() if f.relative_to(dataset.local_dir).parts[0] == area):>6} files")

    # 5. push
    if args.dry_run:
        print("dry run: nothing pushed")
        return 0
    commit = dataset.push(args.message, create_pr=args.pr)
    print(f"pushed: {commit}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
