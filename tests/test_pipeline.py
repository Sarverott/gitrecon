from datetime import timedelta

from conftest import T0, make_event, make_gist

from gitrecon.analysis import Labeler, Thresholds
from gitrecon.analysis.timeline import densest_window, gap_variation
from gitrecon.mapping import ActivityGraph
from gitrecon.sources.events import Feed
from gitrecon.sources.gharchive import archive_name, hour_range, parse_hour
from gitrecon.storage import RawBuffer


def at(minutes: float):
    return T0 + timedelta(minutes=minutes)


# --- storage ---------------------------------------------------------------


def test_rawbuffer_roundtrip_and_append(tmp_path):
    buffer = RawBuffer(tmp_path)
    assert buffer.append("events", [make_event(), make_event()], hour=T0, suffix="public") == 2
    assert buffer.append("events", [make_event()], hour=T0, suffix="public") == 1
    assert buffer.append("gists", [make_gist()], hour=T0) == 1
    assert len(list(buffer.read("events"))) == 3
    assert len(list(buffer.read())) == 4
    assert buffer.sources() == ["events", "gists"]
    assert buffer.partition("gharchive", T0).relative_to(tmp_path).as_posix() == "gharchive/2026-10-03/12.json.gz"


# --- sources ---------------------------------------------------------------


def test_feed_parse_and_paths():
    assert Feed.parse("public").path == "/events"
    assert Feed.parse("user:octocat").path == "/users/octocat/events/public"
    assert Feed.parse("org:github").path == "/orgs/github/events"
    assert Feed.parse("repo:a/b").path == "/repos/a/b/events"
    assert Feed.parse("repo:a/b").name == "repo-a__b"


def test_gharchive_naming():
    hour = parse_hour("2015-01-01-3")
    assert archive_name(hour) == "2015-01-01-3.json.gz"
    assert len(list(hour_range(hour, parse_hour("2015-01-02-2")))) == 24


# --- mapping ---------------------------------------------------------------


def test_graph_maps_events_and_gists():
    graph = ActivityGraph()
    graph.ingest([
        make_event("PushEvent", actor="alice", repo="acme/lib", org="acme"),
        make_event("ForkEvent", actor="bob", repo="acme/lib", org="acme",
                   payload={"forkee": {"full_name": "bob/lib"}}),
        make_event("WatchEvent", actor="carol", repo="dave/site"),
        make_gist(owner="alice"),
    ])
    summary = graph.summary()
    assert summary["nodes"] == {"user": 4, "repo": 3, "org": 1, "gist": 1}
    assert ("forked_to", "repo:bob/lib") in graph.neighbors("repo:acme/lib")
    assert ("owned_by", "user:dave") in graph.neighbors("repo:dave/site")
    assert ("~PushEvent", "user:alice") in graph.neighbors("repo:acme/lib")


# --- analysis --------------------------------------------------------------


def test_densest_window():
    times = [at(m) for m in (0, 1, 2, 100, 101)]
    window = densest_window(times, lambda t: t, timedelta(minutes=5))
    assert len(window) == 3 and window.start == at(0)


def test_gap_variation_regular_vs_bursty():
    regular = [at(m * 10) for m in range(10)]
    bursty = [at(m) for m in (0, 0.1, 0.2, 50, 50.1, 200)]
    assert gap_variation(regular) == 0
    assert gap_variation(bursty) > 1


def labels_for(records, **thresholds):
    labeler = Labeler(Thresholds(**thresholds))
    labeler.ingest(records)
    return {(label.name, label.target): label for label in labeler.run()}


def test_quiet_activity_gets_no_labels():
    records = [make_event(at=at(m * 37 % 300)) for m in range(5)]
    assert labels_for(records) == {}


def test_burst_and_bot_cadence():
    records = [make_event(actor="ticker", at=at(m)) for m in range(120)]  # one per minute
    labels = labels_for(records, burst_events=50)
    assert ("burst", "user:ticker") in labels
    assert labels[("bot-like-cadence", "user:ticker")].confidence == 1.0
    assert len(labels[("burst", "user:ticker")].evidence) == 61  # 60 min window, inclusive


def test_star_burst_and_fork_wave_on_repo():
    stars = [make_event("WatchEvent", actor=f"u{i}", repo="x/hyped", at=at(i % 30)) for i in range(60)]
    forks = [make_event("ForkEvent", actor=f"f{i}", repo="x/hyped", at=at(i)) for i in range(25)]
    labels = labels_for(stars + forks)
    assert labels[("star-burst", "repo:x/hyped")].details["distinct_actors"] == 60
    assert ("fork-wave", "repo:x/hyped") in labels


def test_push_flood_weights_commits():
    records = [make_event("PushEvent", actor="pusher", at=at(m), payload={"size": 100}) for m in range(6)]
    assert labels_for(records)[("push-flood", "user:pusher")].details["observed"] == 600


def test_mass_gist_drop_and_declared_bot():
    gists = [make_gist(owner="dropper", at=at(m)) for m in range(12)]
    bot = [make_event(actor="renovate[bot]")]
    labels = labels_for(gists + bot)
    assert ("mass-gist-drop", "user:dropper") in labels
    assert ("declared-bot", "user:renovate[bot]") in labels
