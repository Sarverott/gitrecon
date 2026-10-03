"""user-namespace layout, per datasets/imperialmap/user-namespace/README.md."""

import json

from conftest import make_repo

from gitrecon.atlas.namespace import (
    Identity,
    UserNamespace,
    github_owner_identities,
    identity_hash,
    identity_path,
    link_identities,
    name_a12y,
    platform_a12y,
)
from gitrecon.config import parse_env
from gitrecon.models import Star
from gitrecon.sources.links import Link


def test_readme_example_path():
    # README: UserName on github.com -> u8e/g6-3m/6784ce76fa5dbf3d7e73f94cc2df055f.json
    assert name_a12y("UserName") == "u8e"
    assert platform_a12y("github.com") == "g6-3m"
    assert identity_hash("UserName", "github.com") == "6784ce76fa5dbf3d7e73f94cc2df055f"
    assert str(identity_path("UserName", "github.com")) == "u8e/g6-3m/6784ce76fa5dbf3d7e73f94cc2df055f.json"


def test_platform_a12y_multi_label():
    assert platform_a12y("gist.github.com") == "g4-6-3m"


def test_add_link_and_index(tmp_path):
    ns = UserNamespace(tmp_path)
    profile = Identity("UserName", "github.com")
    gists = Identity("UserName", "gist.github.com", description="gists")
    ns.link(profile, gists)
    ns.flush()

    file = tmp_path / "user-namespace/NS/u8e/g6-3m/6784ce76fa5dbf3d7e73f94cc2df055f.json"
    data = json.loads(file.read_text())
    assert data == {
        "user": "UserName",
        "platform": "github.com",
        "type": "profile",
        "sibiling": [str(gists.path)],
        "description": "",
    }
    index = json.loads((tmp_path / "user-namespace/index.json").read_text())
    assert index == {"UserName": sorted([str(profile.path), str(gists.path)])}


def test_add_merges_and_is_idempotent(tmp_path):
    ns = UserNamespace(tmp_path)
    ns.add(Identity("remy", "github.com", sibiling=["a.json"], description="first"))
    ns.add(Identity("remy", "github.com", sibiling=["b.json"]))
    ns.flush()
    merged = ns.load("remy", "github.com")
    assert merged.sibiling == ["a.json", "b.json"] and merged.description == "first"

    again = UserNamespace(tmp_path)
    again.add(Identity("remy", "github.com", sibiling=["a.json", "b.json"]))
    again.flush()
    assert again.changed == []


def test_github_owner_identities_from_stars():
    org_repo = make_repo("PyGithub/PyGithub")
    org_repo["owner"]["type"] = "Organization"
    found = [Star.from_api("sarverott", r) for r in (org_repo, make_repo("remy/mit-license"),
                                                      make_repo("remy/nodemon"))]
    identities = github_owner_identities(found)
    assert [(i.user, i.description) for i in identities] == [
        ("PyGithub", "github organization"),
        ("remy", "github user"),
    ]


def test_link_identities_pairs_gist_authors():
    links = [
        Link("https://github.com/remy", "github-user", "github.com"),
        Link("https://github.com/remy/mit-license", "github-repo", "github.com"),
        Link("https://gist.github.com/Sarverott/1401c96de346dac7659f1eddeb2251d6", "gist", "gist.github.com"),
        Link("https://www.wireguard.com/", "site", "www.wireguard.com"),
    ]
    pairs = {p.user: g for p, g in link_identities(links)}
    assert set(pairs) == {"remy", "Sarverott"}
    assert pairs["remy"] is None
    assert pairs["Sarverott"].platform == "gist.github.com"


def test_parse_env():
    text = '# secrets\nHF_TOKEN=hf_abc\nexport GH_TOKEN="gh_x"\nEMPTY=\nnot a line\n'
    assert parse_env(text) == {"HF_TOKEN": "hf_abc", "GH_TOKEN": "gh_x", "EMPTY": ""}
