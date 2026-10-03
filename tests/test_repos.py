"""Repositories and organizations of a user, bulk cloning, and the client's fallbacks - offline."""

import subprocess

import pytest
from conftest import FakeResponse, FakeSession, make_repo

from gitrecon.config import Config
from gitrecon.main import main
from gitrecon.sources import repos
from gitrecon.sources.github_api import GitHubClient

API = "https://api.github.com"


def repo(full_name, fork=False, archived=False, private=False, size=1024):
    data = make_repo(full_name)
    data |= {"fork": fork, "archived": archived, "private": private, "size": size,
             "html_url": f"https://github.com/{full_name}", "clone_url": f"https://github.com/{full_name}.git",
             "created_at": "2017-06-24T13:47:30Z", "forks_count": 0}
    return data


def client_with(routes, token="t"):
    session = FakeSession(routes)
    return GitHubClient(Config(github_token=token), session=session), session


MINE = [repo("Sarverott/gitrecon"), repo("Sarverott/old-fork", fork=True), repo("Sarverott/attic", archived=True)]


def test_user_repos_filters_and_shape():
    client, session = client_with({f"{API}/users/sarverott/repos": [FakeResponse(MINE)]})
    found = repos.user_repos("sarverott", client)
    assert [r["full_name"] for r in found] == ["Sarverott/gitrecon", "Sarverott/old-fork", "Sarverott/attic"]
    assert found[0]["clone_url"] == "https://github.com/Sarverott/gitrecon.git" and found[0]["size_kib"] == 1024
    assert session.calls[0][2]["params"]["type"] == "owner"
    only_own = repos.user_repos("sarverott", client, include_forks=False, include_archived=False)
    assert [r["name"] for r in only_own] == ["gitrecon"]


def test_private_repos_need_the_owners_token():
    client, session = client_with({f"{API}/user/repos": [FakeResponse(MINE + [repo("Sarverott/secret", private=True)])],
                                   f"{API}/user": [FakeResponse({"login": "Sarverott"})]})
    assert sum(r["private"] for r in repos.user_repos("sarverott", client, privacy="all")) == 1
    other, _ = client_with({f"{API}/user": [FakeResponse({"login": "someone"})]})
    with pytest.raises(PermissionError):
        repos.user_repos("sarverott", other, privacy="all")


def test_user_orgs_all_memberships_with_own_token_public_otherwise():
    orgs = [{"login": "The-Apokryf", "description": "x"}, {"login": "rattish", "description": None}]
    own, own_session = client_with({f"{API}/user/orgs": [FakeResponse(orgs)],
                                    f"{API}/user": [FakeResponse({"login": "sarverott"})]})
    assert [o["login"] for o in repos.user_orgs("sarverott", own)] == ["The-Apokryf", "rattish"]
    assert repos.user_orgs("sarverott", own)[1] == {"login": "rattish", "url": "https://github.com/rattish",
                                                     "description": ""}
    anonymous, _ = client_with({f"{API}/users/sarverott/orgs": [FakeResponse(orgs[1:])]}, token=None)
    assert [o["login"] for o in repos.user_orgs("sarverott", anonymous)] == ["rattish"]


def test_org_repos():
    client, session = client_with({f"{API}/orgs/rattish/repos": [FakeResponse([repo("rattish/a"), repo("rattish/b", fork=True)])]})
    assert [r["name"] for r in repos.org_repos("rattish", client, include_forks=False)] == ["a"]
    assert session.calls[0][2]["params"]["type"] == "all"


# --- the client's fallbacks ------------------------------------------------------------------


def test_org_refusing_classic_tokens_is_retried_anonymously():
    refused = FakeResponse({"message": "`The-Apokryf` forbids access via a personal access token (classic). "
                                       "Please use a GitHub App, OAuth App, or a personal access token "
                                       "with fine-grained permissions."}, status=403)
    client, session = client_with({f"{API}/orgs/The-Apokryf/repos": [refused, FakeResponse([repo("The-Apokryf/x")])]})
    assert [r["name"] for r in repos.org_repos("The-Apokryf", client)] == ["x"]
    assert session.calls[1][2]["headers"]["Authorization"] is None  # second try without the token
    assert client.anonymous_fallbacks == 1


def test_secondary_rate_limit_waits_and_retries(monkeypatch):
    monkeypatch.setattr("gitrecon.sources.github_api.time.sleep", lambda seconds: None)
    limited = FakeResponse({"message": "You have exceeded a secondary rate limit."}, status=403,
                           headers={"Retry-After": "1"})
    client, session = client_with({f"{API}/orgs/x/repos": [limited, FakeResponse([repo("x/y")])]})
    assert [r["name"] for r in repos.org_repos("x", client)] == ["y"]
    assert len(session.calls) == 2


def test_other_403s_still_fail():
    client, _ = client_with({f"{API}/orgs/x/repos": [FakeResponse({"message": "Bad credentials"}, status=403)]})
    with pytest.raises(RuntimeError):
        repos.org_repos("x", client)


# --- cloning -------------------------------------------------------------------------


@pytest.fixture
def origin(tmp_path):
    path = tmp_path / "origin" / "tool"
    path.mkdir(parents=True)
    run = lambda *a: subprocess.run(["git", *a], cwd=path, check=True, capture_output=True)  # noqa: E731
    run("init", "--quiet")
    for n in range(3):
        (path / "f.txt").write_text(str(n))
        run("add", ".")
        run("-c", "user.name=t", "-c", "user.email=t@t", "commit", "--quiet", "-m", f"c{n}")
    return path


def test_clone_repos_into_path_with_depth(tmp_path, origin):
    listed = [{"name": "tool", "full_name": "me/tool", "clone_url": f"file://{origin}"},
              {"name": "gone", "full_name": "me/gone", "clone_url": f"file://{tmp_path}/nope"}]
    results = repos.clone_repos(listed, tmp_path / "a" / "b", depth=1)
    assert [(r["full_name"], r["status"]) for r in results] == [("me/tool", "cloned"), ("me/gone", "failed")]
    log = subprocess.run(["git", "-C", results[0]["path"], "log", "--oneline"], capture_output=True, text=True).stdout
    assert len(log.splitlines()) == 1  # shallow: the newest commit only
    assert repos.clone_repos(listed[:1], tmp_path / "a" / "b")[0]["status"] == "exists"


def test_org_clone_dry_run(tmp_path, monkeypatch, capsys):
    client, _ = client_with({f"{API}/orgs/rattish/repos": [FakeResponse([repo("rattish/a"), repo("rattish/b", fork=True)])]})
    monkeypatch.setattr("gitrecon.cli.collect._client", lambda config: client)
    target = tmp_path / "never"
    assert main(["org-clone", "rattish", str(target), "--no-forks", "--dry-run", "--urls"]) == 0
    assert capsys.readouterr().out.splitlines() == ["https://github.com/rattish/a"]
    assert not target.exists()
