import json

import pytest
import yaml

from gitrecon.atlas import AtlasUpdate, domain_path, ip_path
from gitrecon.sources.links import (
    classify,
    expand_pattern,
    gist_clones,
    harvest,
    harvest_gists,
    load_catalog,
    save_catalog,
)

GIST_MD = """# sources
- https://api.github.com/events - everything
- https://www.exploit-db.com/rss.xml - exploits
- https://gist.github.com/{USER}.atom - pattern
- see [remy](https://github.com/remy) and https://github.com/remy/mit-license.
- **https://opensource.org/**
"""


@pytest.fixture
def workshop(tmp_path):
    """A scope dir with one gist clone, one normal repo, and notes in both."""
    gist = tmp_path / "d8e8e531f1402662c31d9b12c8ff3458"
    (gist / ".git").mkdir(parents=True)
    (gist / ".git" / "config").write_text(
        '[remote "origin"]\n\turl = https://gist.github.com/d8e8e531f1402662c31d9b12c8ff3458.git\n'
    )
    (gist / "README.md").write_text(GIST_MD)
    (gist / "nb.ipynb").write_text(json.dumps({"cells": [{"source": ["x = 'https://huggingface.co/x'"]}]}))

    site = tmp_path / "some-website"
    (site / ".git").mkdir(parents=True)
    (site / ".git" / "config").write_text('[remote "origin"]\n\turl = https://github.com/Sarverott/site.git\n')
    (site / "index.md").write_text("https://not-from-a-gist.example.com/")
    return tmp_path


@pytest.mark.parametrize(
    ("url", "kind"),
    [
        ("https://api.github.com/meta", "github-api"),
        ("https://github.blog/changelog/feed/", "feed"),
        ("https://www.exploit-db.com/rss.xml", "feed"),
        ("https://github.com/nodejs/node/releases.atom", "feed"),
        ("https://gist.github.com/{USER}.atom", "pattern"),
        ("https://github.blog/${EACHDIR}/feed", "pattern"),
        ("https://github.com/remy", "github-user"),
        ("https://github.com/remy/mit-license", "github-repo"),
        ("https://github.com/topics", "github-site"),
        ("https://gist.github.com/Sarverott/1401c96de346dac7659f1eddeb2251d6", "gist"),
        ("https://standardgalactic.github.io/", "github-pages"),
        ("https://huggingface.co/", "dataset-hub"),
        ("https://pypi.org/", "package-registry"),
        ("https://www.wireguard.com/", "site"),
    ],
)
def test_classify(url, kind):
    assert classify(url) == kind


def test_harvest_gists_only_reads_gist_clones(workshop):
    assert [c.name for c in gist_clones(workshop)] == ["d8e8e531f1402662c31d9b12c8ff3458"]
    links = {link.url: link for link in harvest_gists(workshop)}
    assert "https://not-from-a-gist.example.com/" not in links
    assert links["https://github.com/remy/mit-license"].kind == "github-repo"
    assert links["https://github.com/remy"].found_in == ["d8e8e531f1402662c31d9b12c8ff3458/README.md:5"]
    assert "https://opensource.org/" in links  # markdown emphasis stripped
    assert links["https://huggingface.co/x"].found_in == ["d8e8e531f1402662c31d9b12c8ff3458/nb.ipynb:1"]


def test_harvest_everything(workshop):
    assert "https://not-from-a-gist.example.com/" in {link.url for link in harvest(workshop)}


def test_catalog_roundtrip(workshop, tmp_path):
    links = harvest_gists(workshop)
    path = save_catalog(links, tmp_path / "catalog" / "links.jsonl")
    assert load_catalog(path) == links


def test_expand_pattern():
    assert expand_pattern("https://gist.github.com/{USER}.atom", user="sarverott") == (
        "https://gist.github.com/sarverott.atom"
    )
    assert expand_pattern("https://github.blog/${EACHDIR}/feed", eachdir="changelog") == (
        "https://github.blog/changelog/feed"
    )


# --- atlas -----------------------------------------------------------------


def test_map_paths_follow_dataset_readme():
    assert domain_path("api.github.com").as_posix() == "com/github/api"
    assert ip_path("127.0.0.1").as_posix() == "v4/7F/0/0/1"
    assert ip_path("140.82.112.0/20").as_posix() == "v4/8C/52/70/0"
    assert ip_path("2a0a:a440::/29").as_posix() == "v6/2A0A/A440/0/0/0/0/0/0"


META = {
    "verifiable_password_authentication": False,
    "ssh_keys": ["ssh-ed25519 AAAAC3Nza/C1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl"],
    "hooks": ["192.30.252.0/22"],
    "web": ["192.30.252.0/22", "140.82.112.0/20"],
    "actions": ["4.148.0.0/16"],
    "domains": {"website": ["*.github.com", "github.com"]},
}


def test_atlas_update_writes_map_and_is_idempotent(workshop, tmp_path):
    root = tmp_path / "imperialmap"
    update = AtlasUpdate(root)
    update.add_links(harvest_gists(workshop), union="gist-harvest")
    update.add_github_meta(META)
    update.reindex()

    holders = yaml.safe_load((root / "dnstrees/com/github/.holders.yml").read_text())
    assert holders["unions"] == ["host-unions/gist-harvest"]
    assert "https://github.com/remy/mit-license" in holders["links"]
    assert not (root / "dnstrees/com/github/gist").exists()  # patterns are not mapped

    node = json.loads((root / "ip-address-records/v4/C0/1E/FC/0/.index.json").read_text())
    assert node["cidrs"] == {"192.30.252.0/22": ["hooks", "web"]}
    assert not (root / "ip-address-records/v4/4/94/0/0").exists()  # actions skipped by default

    union = json.loads((root / "host-unions/github-meta/.index.json").read_text())
    assert union["domains"] == {"website": ["*.github.com", "github.com"]}
    assert union["skipped"] == ["actions", "actions_macos"]

    listing = json.loads((root / "dnstrees/.index.json").read_text())
    assert "com/github/.holders.yml" in listing["files"]

    again = AtlasUpdate(root)
    again.add_links(harvest_gists(workshop), union="gist-harvest")
    again.add_github_meta(META)
    again.reindex()
    assert again.changed == []


def test_atlas_update_merges_links_with_existing_holders(workshop, tmp_path):
    root = tmp_path / "imperialmap"
    node = root / "dnstrees/com/github/.holders.yml"
    node.parent.mkdir(parents=True)
    node.write_text(yaml.safe_dump({"domain": "github.com", "unions": ["host-unions/old"],
                                    "links": ["https://github.com/old/one"]}))
    AtlasUpdate(root).add_links(harvest_gists(workshop), union="gist-harvest")
    holders = yaml.safe_load(node.read_text())
    assert holders["unions"] == ["host-unions/gist-harvest", "host-unions/old"]
    assert "https://github.com/old/one" in holders["links"]


def test_map_dataset_path_is_anchored_to_project_root(monkeypatch):
    monkeypatch.delenv("GITRECON_DATASETS", raising=False)
    from gitrecon.config import PROJECT_ROOT
    from gitrecon.hub.huggingface import MapDataset

    assert MapDataset().local_dir == PROJECT_ROOT / "datasets" / "imperialmap"
    assert (PROJECT_ROOT / "pyproject.toml").exists()
