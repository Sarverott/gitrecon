"""A user's gist catalog (GraphQL + commit counts) and cloning gists - offline."""

import json
import subprocess

import pytest
from conftest import FakeResponse, FakeSession

from gitrecon.config import Config
from gitrecon.main import main
from gitrecon.sources.gists import clone_gists, gist_catalog
from gitrecon.sources.github_api import GitHubClient

API = "https://api.github.com"


def node(gist_id, files, stars=0, public=True, created="2017-10-28T14:02:04Z"):
    return {"name": gist_id, "description": f"gist {gist_id}", "isPublic": public, "stargazerCount": stars,
            "createdAt": created, "updatedAt": created,
            "files": [{"name": n, "size": s} for n, s in files],
            "forks": {"totalCount": 1}, "comments": {"totalCount": 2}}


def page(nodes, next_cursor=None, root="user", login="sarverott"):
    gists = {"totalCount": 3, "nodes": nodes,
             "pageInfo": {"hasNextPage": next_cursor is not None, "endCursor": next_cursor}}
    body = {root: {"gists": gists} | ({"login": login} if root == "viewer" else {})}
    return FakeResponse({"data": body})


def commits(count, rel):
    """GET /gists/<id>/commits?per_page=1 - with rel=last, or only rel=next (as GitHub does for gists)."""
    response = FakeResponse([{"version": "x"}])
    if rel == "last":
        response.links = {"last": {"url": f"{API}/gists/a/commits?per_page=1&page={count}"}}
    elif rel == "next":
        response.links = {"next": {"url": f"{API}/gists/b/commits?per_page=1&page=2"}}
    return response


@pytest.fixture
def github():
    session = FakeSession({
        f"{API}/graphql": [page([node("a", [("x.py", 100)], stars=2), node("b", [("r.md", 50), ("s.md", 25)])], "c1"),
                           page([node("c", [("old.php", 10)])])],
        f"{API}/gists/a/commits": [commits(7, "last")],
        # only rel=next: counted by paging 100 at a time
        f"{API}/gists/b/commits": [commits(0, "next"), FakeResponse([{}] * 83)],
        f"{API}/gists/c/commits": [commits(1, None)],
    })
    return GitHubClient(Config(github_token="t"), session=session), session


def test_catalog_shape_and_paging(github):
    client, session = github
    catalog = gist_catalog("sarverott", client)
    assert [g["gistID"] for g in catalog] == ["a", "b", "c"]
    assert catalog[0] == {
        "gistID": "a", "filelist": ["x.py"], "description": "gist a", "stars": 2, "comments": 2, "forks": 1,
        "commits": 7, "size": 100, "public": True, "created_at": "2017-10-28T14:02:04Z",
        "url": "https://gist.github.com/a",
    }
    assert catalog[1]["commits"] == 83 and catalog[1]["filelist"] == ["r.md", "s.md"] and catalog[1]["size"] == 75
    assert catalog[2]["commits"] == 1
    second_query = [c for c in session.calls if c[1].endswith("/graphql")][1]
    assert second_query[2]["json"]["variables"] == {"login": "sarverott", "after": "c1"}


def test_catalog_without_commits_makes_no_rest_calls(github):
    client, session = github
    catalog = gist_catalog("sarverott", client, with_commits=False)
    assert all(g["commits"] is None for g in catalog)
    assert all(c[1].endswith("/graphql") for c in session.calls)


def test_secret_gists_need_the_owners_token():
    session = FakeSession({f"{API}/graphql": [page([node("s", [("x", 1)], public=False)], root="viewer", login="someone")]})
    client = GitHubClient(Config(github_token="t"), session=session)
    with pytest.raises(PermissionError):
        gist_catalog("sarverott", client, privacy="all")
    with pytest.raises(ValueError):
        gist_catalog("sarverott", client, privacy="hidden")


def test_graphql_needs_a_token():
    with pytest.raises(RuntimeError):
        GitHubClient(Config(github_token=None)).graphql("{viewer{login}}")


# --- cloning, against local repositories -------------------------------------------


@pytest.fixture
def origins(tmp_path):
    """Two local repositories standing in for gists: <tmp>/origins/<id>."""
    root = tmp_path / "origins"
    for gist_id in ("aaa", "bbb"):
        repo = root / gist_id
        repo.mkdir(parents=True)
        run = lambda *a, cwd=repo: subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True)  # noqa: E731
        run("init", "--quiet")
        (repo / "note.md").write_text(gist_id)
        run("add", ".")
        run("-c", "user.name=t", "-c", "user.email=t@t", "commit", "--quiet", "-m", "first")
    return root


def test_clone_creates_path_skips_existing_and_reports_failures(tmp_path, origins):
    pattern = f"file://{origins}/{{gist_id}}"
    target = tmp_path / "deep" / "my-gists"
    results = clone_gists([{"gistID": "aaa"}, "bbb", "missing"], target, pattern=pattern)
    assert [(r["gistID"], r["status"]) for r in results] == [("aaa", "cloned"), ("bbb", "cloned"), ("missing", "failed")]
    assert (target / "aaa" / "note.md").read_text() == "aaa"
    assert results[2]["error"]

    again = clone_gists(["aaa"], target, pattern=pattern)
    assert again[0]["status"] == "exists"
    assert clone_gists(["aaa"], target, pattern=pattern, update=True)[0]["status"] == "updated"

    (target / "bbb-copy").mkdir()
    (target / "bbb-copy" / "stray").write_text("x")
    blocked = clone_gists(["bbb-copy"], target, pattern=pattern)
    assert blocked[0]["status"] == "failed" and "not a git clone" in blocked[0]["error"]


def test_gist_clone_dry_run_clones_nothing(tmp_path, monkeypatch, github, capsys):
    client, session = github
    monkeypatch.setattr("gitrecon.cli.collect._client", lambda config: client)
    target = tmp_path / "never-created"
    assert main(["gist-clone", "sarverott", str(target), "--limit", "2", "--dry-run", "--urls"]) == 0
    assert capsys.readouterr().out.splitlines() == ["https://gist.github.com/a", "https://gist.github.com/b"]
    assert not target.exists()


def test_gist_catalog_json(monkeypatch, github, capsys):
    client, _ = github
    monkeypatch.setattr("gitrecon.cli.collect._client", lambda config: client)
    assert main(["gist-catalog", "sarverott", "--json", "--no-commits"]) == 0
    assert [g["gistID"] for g in json.loads(capsys.readouterr().out)] == ["a", "b", "c"]
