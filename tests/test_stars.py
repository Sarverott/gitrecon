from conftest import FakeResponse, FakeSession, make_repo

from gitrecon.config import Config
from gitrecon.main import main
from gitrecon.models import Star
from gitrecon.sources import stars
from gitrecon.sources.github_api import GitHubClient

API = "https://api.github.com"
PAGE_2 = f"{API}/user/29676193/starred?per_page=100&page=2"


def sarverott_session():
    page_1 = [
        {"starred_at": "2026-09-30T10:00:00Z", "repo": make_repo("PyGithub/PyGithub", stars=7787)},
        {"starred_at": "2025-01-02T08:00:00Z", "repo": make_repo("go-task/task", language="Go", stars=13000)},
    ]
    page_2 = [{"starred_at": "2018-12-11T00:00:00Z", "repo": make_repo("remy/mit-license", language="HTML")}]
    return FakeSession({
        f"{API}/users/sarverott/starred": [FakeResponse(page_1, next_url=PAGE_2)],
        f"{API}/user/29676193/starred": [FakeResponse(page_2)],
    })


def client_for(session):
    return GitHubClient(Config(github_token=None), session=session)


def test_starred_follows_pages_and_asks_for_star_dates():
    session = sarverott_session()
    found = stars.starred(client_for(session), "sarverott")

    assert [s.repo.full_name for s in found] == ["PyGithub/PyGithub", "go-task/task", "remy/mit-license"]
    assert found[0].starred_at.year == 2026
    assert found[1].repo.language == "Go"
    first_call = session.calls[0]
    assert first_call[1] == f"{API}/users/sarverott/starred"
    assert first_call[2]["headers"]["Accept"] == stars.STAR_MEDIA_TYPE
    assert session.calls[1][1] == PAGE_2


def test_star_model_accepts_plain_repo_payload():
    star = Star.from_api("sarverott", make_repo("Sarverott/gitrecon"))
    assert star.key == "star:sarverott->sarverott/gitrecon"
    assert star.starred_at is None


def test_stars_cli_lists_repositories(monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("GITRECON_DATA", str(tmp_path))
    monkeypatch.setenv("GITRECON_NO_GH_CLI", "1")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    session = sarverott_session()
    monkeypatch.setattr("gitrecon.sources.github_api.requests.Session", lambda: session)

    assert main(["stars", "sarverott", "--save"]) == 0

    out = capsys.readouterr().out
    assert "2026-09-30  PyGithub/PyGithub" in out
    assert "-- 3 repositories starred by sarverott" in out
    assert list((tmp_path / "raw" / "stars").rglob("*-user-sarverott.json.gz"))
