from conftest import make_event, make_gist

from gitrecon.models import Event, Gist, Organization, Project, Repository, User, from_record


def test_event_from_api_builds_nested_entities():
    raw = make_event("ForkEvent", actor="bob", repo="acme/lib", org="acme",
                     payload={"forkee": {"full_name": "bob/lib", "fork": True}})
    event = Event.from_api(raw)
    assert event.actor.key == "user:bob"
    assert event.repo.key == "repo:acme/lib"
    assert event.org.key == "org:acme"
    assert event.forkee.key == "repo:bob/lib"
    assert event.created_at.tzinfo is not None


def test_keys_are_case_insensitive():
    assert User(login="OctoCat").key == User(login="octocat").key
    assert Repository(full_name="Acme/Lib").key == "repo:acme/lib"


def test_repository_owner_and_name():
    repo = Repository.from_api({"name": "acme/lib"})
    assert (repo.owner, repo.name) == ("acme", "lib")


def test_user_bot_detection():
    assert User(login="dependabot[bot]").is_bot
    assert User(login="x", type="Bot").is_bot
    assert not User(login="alice").is_bot


def test_push_commit_count():
    event = Event.from_api(make_event("PushEvent", payload={"size": 7}))
    assert event.commit_count == 7
    assert Event.from_api(make_event("WatchEvent")).commit_count == 0


def test_gist_files_and_languages():
    gist = Gist.from_api(make_gist(owner="carol", filename="a.rs", language="Rust"))
    assert gist.owner == "carol"
    assert gist.languages == {"Rust"}


def test_organization_and_project():
    assert Organization.from_api({"login": "Acme"}).key == "org:acme"
    project = Project.from_api({"owner": {"login": "acme"}, "number": 3, "title": "Roadmap"})
    assert project.key == "project:acme/3"


def test_to_dict_drops_raw():
    data = User.from_api({"login": "alice", "id": 1}).to_dict()
    assert "raw" not in data and data["kind"] == "user"


def test_from_record_tells_shapes_apart():
    assert isinstance(from_record(make_event()), Event)
    assert isinstance(from_record(make_gist()), Gist)
    assert from_record({"something": "else"}) is None
