"""The network around a user: collection (REST listings + GraphQL fork parents) and rendering."""

import json

import pytest
from conftest import FakeResponse, FakeSession
from test_repos import repo

from gitrecon.config import Config
from gitrecon.main import main
from gitrecon.mapping import render
from gitrecon.mapping.network import FORK_OF, MEMBER_OF, collect_network, fork_parents, owner_network
from gitrecon.sources.github_api import GitHubClient

API = "https://api.github.com"


def parents_page(pairs, errors=None):
    nodes = [None if fork is None else {"nameWithOwner": fork, "parent": parent and {
        "nameWithOwner": parent, "owner": {"__typename": kind, "login": parent.split("/")[0]}}}
        for fork, parent, kind in pairs]
    body = {"data": {"repositoryOwner": {"repositories": {
        "pageInfo": {"hasNextPage": False, "endCursor": None}, "nodes": nodes}}}}
    if errors:
        body["errors"] = [{"message": m} for m in errors]
    return FakeResponse(body)


@pytest.fixture
def client():
    session = FakeSession({
        f"{API}/users/sarverott/repos": [FakeResponse([repo("Sarverott/gitrecon"), repo("Sarverott/doc-builder", fork=True),
                                                        repo("Sarverott/mit", fork=True), repo("Sarverott/hidden", fork=True)])],
        f"{API}/users/sarverott": [FakeResponse({"login": "Sarverott", "type": "User"})],
        f"{API}/user/orgs": [FakeResponse([{"login": "rattish", "description": "rats"}, {"login": "bonescraft"}])],
        f"{API}/user": [FakeResponse({"login": "Sarverott"})],
        f"{API}/orgs/rattish/repos": [FakeResponse([repo("rattish/doc-builder"), repo("rattish/gitrecon", fork=True)])],
        f"{API}/orgs/bonescraft/repos": [FakeResponse([])],
        f"{API}/graphql": [
            # the user's forks: one upstream in their own org, one outside, one refused (null)
            parents_page([("Sarverott/doc-builder", "rattish/doc-builder", "Organization"),
                          ("Sarverott/mit", "remy/mit-license", "User"),
                          (None, None, None)], errors=["`X` forbids access via a personal access token (classic)."]),
            parents_page([("rattish/gitrecon", "Sarverott/gitrecon", "User")]),
            parents_page([]),
        ],
    })
    return GitHubClient(Config(github_token="t"), session=session)


def test_collect_network_relations(client):
    graph = collect_network("sarverott", client)
    relations = {(e.source, e.relation, e.target) for e in graph.edges}
    assert ("user:sarverott", MEMBER_OF, "org:rattish") in relations
    assert ("repo:sarverott/doc-builder", FORK_OF, "repo:rattish/doc-builder") in relations
    assert ("repo:rattish/gitrecon", FORK_OF, "repo:sarverott/gitrecon") in relations
    assert ("repo:sarverott/mit", FORK_OF, "repo:remy/mit-license") in relations
    assert ("repo:remy/mit-license", "owned_by", "user:remy") in relations      # the upstream's owner joins
    assert not any(s == "repo:sarverott/hidden" and r == FORK_OF for s, r, _ in relations)  # refused: no edge
    assert graph.nodes["user:sarverott"].login == "Sarverott"


def test_owner_network_counts_flows(client):
    net = owner_network(collect_network("sarverott", client))
    assert net["owners"]["user:sarverott"] == {"repos": 4, "forks": 3, "stars": 4, "kind": "user"}
    assert net["owners"]["org:rattish"]["repos"] == 2
    assert net["owners"]["user:remy"]["repos"] == 0          # an upstream owner: present, nothing listed
    assert net["forks"] == {("user:sarverott", "org:rattish"): 1, ("user:sarverott", "user:remy"): 1,
                            ("org:rattish", "user:sarverott"): 1}


def test_partial_graphql_keeps_data_but_total_refusal_raises():
    refused = FakeResponse({"data": None, "errors": [{"message": "forbidden"}]})
    client = GitHubClient(Config(github_token="t"), session=FakeSession({f"{API}/graphql": [refused]}))
    with pytest.raises(RuntimeError):
        client.graphql("{x}", partial=True)
    assert fork_parents("The-Apokryf", client) == {}          # parents are an enrichment, never fatal
    assert fork_parents("anyone", GitHubClient(Config(github_token=None))) == {}


def test_owners_mermaid(client):
    diagram = render.owners_mermaid(collect_network("sarverott", client))
    lines = diagram.splitlines()
    assert lines[0] == "flowchart LR"
    assert '  user_sarverott(["Sarverott<br/>4 repos · 3 forks · ★4"]):::user' in lines
    assert '  org_bonescraft["bonescraft<br/>0 repos · 0 forks · ★0"]:::org' in lines   # empty org still declared
    assert '  user_remy("remy"):::outside' in lines
    assert "  user_sarverott -->|member| org_rattish" in lines
    assert '  user_sarverott -.->|"1 fork"| org_rattish' in lines
    assert '  click org_rattish "https://github.com/rattish"' in lines
    assert "classDef outside" in diagram


def test_repos_mermaid_groups_by_owner_and_limits(client):
    graph = collect_network("sarverott", client)
    diagram = render.repos_mermaid(graph, forks_only=True)
    assert '  subgraph org_rattish["rattish"]' in diagram
    assert "  repo_sarverott_mit -->|fork of| repo_remy_mit_license" in diagram
    assert 'repo_remy_mit_license["mit-license"]:::outside' in diagram
    assert "repo_sarverott_hidden" not in diagram            # forks_only: no relation, not drawn
    small = render.repos_mermaid(graph, max_nodes=2)
    assert "more repositories not drawn (max_nodes=2)" in small


def test_node_ids_are_mermaid_safe():
    assert render.node_id("repo:cosmos/chain-registry.js") == "repo_cosmos_chain_registry_js"
    assert render.node_id("user:dependabot[bot]") == "user_dependabot_bot_"


def test_dot_and_json(client):
    graph = collect_network("sarverott", client)
    dot = render.to_dot(graph)
    assert dot.startswith("digraph gitrecon {") and '"repo:sarverott/mit" -> "repo:remy/mit-license" [label="fork_of"];' in dot
    data = render.to_json(graph)
    assert {"source": "user:sarverott", "target": "org:rattish", "count": 1} in data["owner_forks"]
    assert next(n for n in data["nodes"] if n["key"] == "org:rattish")["url"] == "https://github.com/rattish"
    json.dumps(data)  # serializable as it is


def test_network_command(tmp_path, monkeypatch, client, capsys):
    monkeypatch.setenv("GITRECON_DATA", str(tmp_path))
    monkeypatch.setattr("gitrecon.sources.github_api.GitHubClient", lambda config: client)
    assert main(["network", "sarverott", "--save"]) == 0
    out = capsys.readouterr().out
    assert "relations around sarverott" in out and "Sarverott" in out and "-> rattish" in out
    saved = (tmp_path / "networks" / "sarverott-owners.md").read_text()
    assert saved.startswith("# Network of sarverott (owners)\n\n```mermaid\nflowchart LR")
