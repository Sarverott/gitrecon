"""--json / --urls: the output layer, model URLs and shapes, and the commands using them."""

import json
from datetime import datetime, timezone

import pytest
from conftest import FIXTURES, T0, make_event, make_gist, make_repo
from test_links_atlas import workshop  # noqa: F401 - fixture
from test_stars import sarverott_session

from gitrecon.cli.output import Output, dumps
from gitrecon.main import main
from gitrecon.models import Event, Gist, Label, Repository, Star, User
from gitrecon.models.base import url_for_key
from gitrecon.storage import RawBuffer

# --- the output layer ----------------------------------------------------------


def test_listing_text_json_urls(capsys):
    items = [{"n": 1, "u": "https://a"}, {"n": 2, "u": "https://a"}, {"n": 3, "u": None}]
    kwargs = dict(text=lambda i: f"item {i['n']}", data=lambda i: i, url=lambda i: i["u"], summary="-- 3")

    Output().listing(items, **kwargs)
    text = capsys.readouterr()
    assert text.out == "item 1\nitem 2\nitem 3\n-- 3\n" and text.err == ""

    Output(json=True).listing(items, **kwargs)
    machine = capsys.readouterr()
    assert json.loads(machine.out) == items and machine.err == "-- 3\n"  # summary moves to stderr

    Output(urls=True).listing(items, **kwargs)
    assert capsys.readouterr().out == "https://a\n"  # deduplicated, empty skipped


def test_stream_is_json_lines(capsys):
    Output(json=True).stream([{"a": 1}, {"a": 2}], text=str, data=lambda i: i)
    lines = capsys.readouterr().out.splitlines()
    assert [json.loads(line) for line in lines] == [{"a": 1}, {"a": 2}]


def test_dumps_handles_datetimes_and_models():
    data = {"when": datetime(2026, 10, 3, tzinfo=timezone.utc), "user": User(login="x")}
    parsed = json.loads(dumps(data))
    assert parsed["when"] == "2026-10-03T00:00:00+00:00"
    assert parsed["user"]["url"] == "https://github.com/x"


# --- model URLs and JSON shapes -----------------------------------------------------


@pytest.mark.parametrize(
    ("key", "url"),
    [
        ("user:sarverott", "https://github.com/sarverott"),
        ("user:dependabot[bot]", "https://github.com/apps/dependabot"),
        ("org:github", "https://github.com/github"),
        ("repo:sarverott/gitrecon", "https://github.com/sarverott/gitrecon"),
        ("gist:abc123", "https://gist.github.com/abc123"),
        ("star:sarverott->remy/mit-license", "https://github.com/remy/mit-license"),
        ("rfc:RFC2026", "https://www.rfc-editor.org/rfc/rfc2026"),
        ("project:x/1", None),
    ],
)
def test_url_for_key(key, url):
    assert url_for_key(key) == url


def test_model_urls_keep_original_case_and_prefer_api_html_url():
    assert User(login="Sarverott").html_url == "https://github.com/Sarverott"
    assert Repository(full_name="Sarverott/gitrecon").html_url == "https://github.com/Sarverott/gitrecon"
    assert Repository.from_api({"full_name": "a/b", "html_url": "https://example.com/a/b"}).html_url == (
        "https://example.com/a/b"
    )
    assert Event.from_api(make_event(repo="Acme/Lib")).html_url == "https://github.com/Acme/Lib"
    assert Gist.from_api(make_gist()).html_url.startswith("https://gist.github.com/")


def test_star_json_is_flat_and_keeps_repo_name():
    star = Star.from_api("sarverott", {"starred_at": "2026-09-30T10:00:00Z", "repo": make_repo("go-task/task", "Go")})
    assert star.to_json() == {
        "user": "sarverott", "repo": "go-task/task", "url": "https://github.com/go-task/task",
        "starred_at": "2026-09-30T10:00:00+00:00", "language": "Go", "stars": 1, "description": "",
        "topics": [],
    }


def test_to_dict_drops_nested_raw_payloads():
    event = Event.from_api(make_event(org="acme"))
    data = event.to_dict()
    assert "raw" not in data["actor"] and "raw" not in data["repo"] and "raw" not in data["org"]
    assert isinstance(data["created_at"], str)
    assert event.to_json()["actor"] == "alice"


def test_label_json_has_target_url():
    label = Label("star-burst", "repo:x/hyped", 0.9, ["1"])
    assert label.to_json()["url"] == "https://github.com/x/hyped"


# --- commands --------------------------------------------------------------------


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("GITRECON_DATA", str(tmp_path / "data"))
    monkeypatch.setenv("GITRECON_NO_GH_CLI", "1")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    return tmp_path / "data"


@pytest.fixture
def github(monkeypatch):
    session = sarverott_session()
    monkeypatch.setattr("gitrecon.sources.github_api.requests.Session", lambda: session)
    return session


def test_stars_urls_and_json(data_dir, github, capsys):
    assert main(["stars", "sarverott", "--urls"]) == 0
    out = capsys.readouterr()
    assert out.out.splitlines() == [
        "https://github.com/PyGithub/PyGithub",
        "https://github.com/go-task/task",
        "https://github.com/remy/mit-license",
    ]
    assert "-- 3 repositories" in out.err

    assert main(["stars", "sarverott", "--json"]) == 0
    stars = json.loads(capsys.readouterr().out)
    assert [s["repo"] for s in stars][0] == "PyGithub/PyGithub" and stars[0]["url"].startswith("https://")


def test_json_and_urls_are_exclusive(capsys):
    with pytest.raises(SystemExit):
        main(["stars", "sarverott", "--json", "--urls"])


@pytest.fixture
def buffer_with_activity(data_dir):
    buffer = RawBuffer(data_dir / "raw")
    stars = [make_event("WatchEvent", actor=f"u{i}", repo="x/hyped", at=T0) for i in range(60)]
    bot = [make_event(actor="renovate[bot]", repo="x/hyped")]
    buffer.append("events", stars + bot, hour=T0)
    return buffer


def test_label_modes(buffer_with_activity, capsys):
    main(["label", "--json"])
    labels = json.loads(capsys.readouterr().out)
    assert {label["name"] for label in labels} == {"star-burst", "declared-bot"}

    main(["label", "--urls", "--name", "declared-bot"])
    assert capsys.readouterr().out.splitlines() == ["https://github.com/apps/renovate"]


def test_map_modes(buffer_with_activity, capsys):
    main(["map", "--json"])
    summary = json.loads(capsys.readouterr().out)
    assert summary["hubs"][0] == {"key": "repo:x/hyped", "degree": summary["hubs"][0]["degree"],
                                  "url": "https://github.com/x/hyped"}

    main(["map", "--node", "repo:x/hyped", "--urls"])
    urls = capsys.readouterr().out.splitlines()
    assert "https://github.com/u0" in urls and "https://github.com/x" in urls

    main(["map"])
    assert capsys.readouterr().out.startswith("nodes: ")


def test_status_json(buffer_with_activity, capsys):
    main(["status", "--json"])
    status = json.loads(capsys.readouterr().out)
    assert status["sources"] == [{"source": "events", "files": 1, "bytes": status["sources"][0]["bytes"]}]
    assert status["token"] is False


def test_links_urls(data_dir, workshop, capsys):  # noqa: F811
    main(["links", str(workshop), "--kind", "feed", "--urls"])
    assert capsys.readouterr().out.splitlines() == ["https://www.exploit-db.com/rss.xml"]


def test_rfc_json_and_urls(data_dir, monkeypatch, capsys):
    text = (FIXTURES / "rfc-index-sample.txt").read_text(encoding="utf-8")
    monkeypatch.setattr("gitrecon.sources.rfc_index.fetch_index", lambda: text)

    main(["rfc", "--number", "2026", "--json"])
    (rfc,) = json.loads(capsys.readouterr().out)
    assert rfc["status"] == "BEST CURRENT PRACTICE" and rfc["url"] == "https://www.rfc-editor.org/rfc/rfc2026"

    main(["rfc", "--search", "ospf", "--urls"])
    assert capsys.readouterr().out.splitlines() == ["https://www.rfc-editor.org/rfc/rfc10041"]


def test_words_after_options_reach_the_command():
    """Old Pythons (< 3.12.7) reject positionals that follow options; the entry point collects them."""
    from gitrecon import cli

    parser = cli.build_parser()
    args, rest = parser.parse_known_args(["translate", "text", "--to", "pl"])
    cli._late_positionals(parser, args, ["hello", "world"])
    assert args.words == ["hello", "world"]
    args, _ = parser.parse_known_args(["analyze"])
    cli._late_positionals(parser, args, ["a", "b"])
    assert args.path == ["a", "b"]                                  # the default "." is replaced, not kept
    args, _ = parser.parse_known_args(["stars", "sarverott"])
    with pytest.raises(SystemExit):
        cli._late_positionals(parser, args, ["extra"])              # commands without a list argument still refuse
    args, _ = parser.parse_known_args(["translate", "text"])
    with pytest.raises(SystemExit):
        cli._late_positionals(parser, args, ["--nonsense"])         # and unknown options are still errors
