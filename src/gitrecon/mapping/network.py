"""The network around a user: their repositories, organizations, and where forks come from.

    graph = collect_network("sarverott")

Relations (edges of an ``ActivityGraph``):

- ``user  -member_of-> org``
- ``repo  -owned_by->  user | org``
- ``repo  -fork_of->   repo``       (the upstream; its owner becomes a node too)

Listings come from ``sources.repos`` (REST). Fork parents are not in those listings: they
come from GraphQL, one query per 100 forks of an owner. Where GraphQL is refused (an
organization that blocks classic tokens), that owner's forks simply have no ``fork_of`` edge.
"""

from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Callable
from typing import Any

from gitrecon.mapping.graph import ActivityGraph
from gitrecon.models import Organization, Repository, User
from gitrecon.sources import repos
from gitrecon.sources.github_api import GitHubClient

log = logging.getLogger(__name__)

MEMBER_OF, OWNED_BY, FORK_OF = "member_of", "owned_by", "fork_of"

FORK_PARENTS = """query($login: String!, $after: String) {
  repositoryOwner(login: $login) {
    repositories(first: 100, after: $after, isFork: true, ownerAffiliations: OWNER) {
      pageInfo { hasNextPage endCursor }
      nodes { nameWithOwner parent { nameWithOwner owner { __typename login } } }
    }
  }
}"""


def fork_parents(owner: str, client: GitHubClient) -> dict[str, dict[str, str]]:
    """``{fork full name (lowercase): {"parent": full name, "owner": login, "owner_type": ...}}``.

    Empty when there is no token or GitHub refuses the query for this owner.
    """
    if not client.config.github_token:
        return {}
    found: dict[str, dict[str, str]] = {}
    after = None
    try:
        while True:
            # partial: a fork whose upstream sits in an organization refusing the token comes back
            # as null - keep the others
            data = client.graphql(FORK_PARENTS, {"login": owner, "after": after}, partial=True)["repositoryOwner"]
            if data is None:
                break
            page = data["repositories"]
            for node in page["nodes"]:
                if node is None:  # the fork itself was refused
                    continue
                parent = node.get("parent")  # None: the upstream is private, gone or refused
                if parent:
                    found[node["nameWithOwner"].lower()] = {
                        "parent": parent["nameWithOwner"],
                        "owner": parent["owner"]["login"],
                        "owner_type": parent["owner"]["__typename"],
                    }
            if not page["pageInfo"]["hasNextPage"]:
                break
            after = page["pageInfo"]["endCursor"]
    except Exception as error:  # noqa: BLE001 - parents are an enrichment, never fatal
        log.warning("no fork parents for %s: %s", owner, error)
    return found


def _owner_entity(login: str, kind: str | None) -> User | Organization:
    return Organization(login=login) if kind == "Organization" else User(login=login)


def _add_owner_repos(graph: ActivityGraph, owner: User | Organization, listing: list[dict[str, Any]],
                     parents: dict[str, dict[str, str]]) -> None:
    for entry in listing:
        repo = Repository(full_name=entry["full_name"], raw=entry, fork=entry["fork"], language=entry["language"],
                          stargazers_count=entry["stars"], archived=entry["archived"], topics=entry["topics"])
        graph.link(repo, OWNED_BY, owner, entry["full_name"])
        parent = parents.get(entry["full_name"].lower())
        if parent:
            upstream = Repository(full_name=parent["parent"])
            graph.link(repo, FORK_OF, upstream, entry["full_name"])
            graph.link(upstream, OWNED_BY, _owner_entity(parent["owner"], parent["owner_type"]), parent["parent"])


def collect_network(
    username: str,
    client: GitHubClient | None = None,
    include_orgs: bool = True,
    privacy: str = "public",
    progress: Callable[[str], None] | None = None,
) -> ActivityGraph:
    """Repositories of ``username`` and of their organizations, with membership and fork relations."""
    client = client or GitHubClient()
    say = progress or (lambda message: None)
    graph = ActivityGraph()
    user = User.from_api(client.get(f"/users/{username}").data)  # the name as GitHub spells it
    graph.add_node(user)

    say(f"repositories of {username}")
    _add_owner_repos(graph, user, repos.user_repos(username, client, privacy=privacy), fork_parents(username, client))

    if include_orgs:
        for org in repos.user_orgs(username, client):
            say(f"organization {org['login']}")
            entity = Organization(login=org["login"], description=org["description"], raw=org)
            graph.link(user, MEMBER_OF, entity, org["login"])
            _add_owner_repos(graph, entity, repos.org_repos(org["login"], client), fork_parents(org["login"], client))
    return graph


def owner_of(graph: ActivityGraph, repo_key: str) -> str | None:
    """Key of the user or organization owning a repository node."""
    return next((e.target for e in graph.edges if e.source == repo_key and e.relation == OWNED_BY), None)


def owner_network(graph: ActivityGraph) -> dict[str, Any]:
    """The graph collapsed to owners: who forks from whom (and how often), who belongs where.

    ``{"owners": {key: {"repos", "forks", "stars", "kind"}}, "forks": {(from, to): n},
    "members": [(user, org)]}``
    """
    owners: dict[str, dict[str, Any]] = {}

    def owner(key: str) -> dict[str, Any]:
        return owners.setdefault(key, {"repos": 0, "forks": 0, "stars": 0, "kind": key.split(":", 1)[0]})

    owned = {e.source: e.target for e in graph.edges if e.relation == OWNED_BY}
    forks: Counter[tuple[str, str]] = Counter()
    for repo_key, owner_key in owned.items():
        node = graph.nodes[repo_key]
        stats = owner(owner_key)
        if node.raw:  # listed repositories; bare upstream stubs only mark their owner as present
            stats["repos"] += 1
            stats["forks"] += bool(node.fork)
            stats["stars"] += node.stargazers_count or 0
    for edge in graph.edges:
        if edge.relation == FORK_OF and edge.source in owned and edge.target in owned:
            forks[(owned[edge.source], owned[edge.target])] += 1
    members = [(e.source, e.target) for e in graph.edges if e.relation == MEMBER_OF]
    for user_key, org_key in members:
        owner(user_key), owner(org_key)
    return {"owners": owners, "forks": dict(forks), "members": members}
