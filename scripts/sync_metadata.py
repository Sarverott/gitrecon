"""Copy shared project info from metadata.json into package.json and pyproject.toml.

metadata.json is the single source of truth for name, version, description,
authors, links and tags. Run with --check to only report drift (exit code 1).
"""

import json
import re
import subprocess
import sys
from pathlib import Path

import tomlkit

ROOT = Path(__file__).resolve().parent.parent
METADATA = ROOT / "metadata.json"
PACKAGE_JSON = ROOT / "package.json"
PACKAGE_LOCK = ROOT / "package-lock.json"
PYPROJECT = ROOT / "pyproject.toml"

# "Name <email> (url)" — the npm person format used in metadata.json authors
PERSON = re.compile(r"^(?P<name>[^<(]+?)\s*(?:<(?P<email>[^>]+)>)?\s*(?:\((?P<url>[^)]+)\))?$")


def parse_person(text):
    match = PERSON.match(text.strip())
    return {key: value for key, value in match.groupdict().items() if value}


def own_repo(meta):
    """The link ending with this project's name, else the first link."""
    for link in meta["links"]:
        if link.rstrip("/").rsplit("/", 1)[-1] == meta["name"]:
            return link
    return meta["links"][0]


def sync_package_json(meta, data):
    data["name"] = meta["name"]
    data["version"] = meta["version"]
    data["description"] = meta["description"]
    data["keywords"] = meta["tags"]
    persons = [author[1] for author in meta["authors"]]
    data["author"] = persons[0]
    if len(persons) > 1:
        data["contributors"] = persons[1:]
    else:
        data.pop("contributors", None)
    repo = own_repo(meta)
    data["homepage"] = f"{repo}#readme"
    data["bugs"] = {"url": f"{repo}/issues"}
    data["repository"] = {"type": "git", "url": f"git+{repo}.git"}
    return data


def sync_package_lock(meta, data):
    data["name"] = meta["name"]
    data["version"] = meta["version"]
    data["packages"][""]["name"] = meta["name"]
    data["packages"][""]["version"] = meta["version"]
    return data


def sync_pyproject(meta, doc):
    project = doc["project"]
    project["name"] = meta["name"]
    project["version"] = meta["version"]
    project["description"] = meta["description"]
    project["keywords"] = meta["tags"]
    authors = tomlkit.array()
    for author in meta["authors"]:
        person = parse_person(author[1])
        entry = tomlkit.inline_table()
        entry["name"] = person["name"]
        if "email" in person:
            entry["email"] = person["email"]
        authors.append(entry)
    project["authors"] = authors.multiline(True)
    repo = own_repo(meta)
    urls = tomlkit.table()
    urls["Homepage"] = repo
    urls["Repository"] = repo
    urls["Issues"] = f"{repo}/issues"
    urls.add(tomlkit.nl())
    project["urls"] = urls
    return doc


def dump_json(data):
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def main():
    check = "--check" in sys.argv[1:]
    meta = json.loads(METADATA.read_text(encoding="utf-8"))

    updates = {
        PACKAGE_JSON: dump_json(sync_package_json(meta, json.loads(PACKAGE_JSON.read_text(encoding="utf-8")))),
        PACKAGE_LOCK: dump_json(sync_package_lock(meta, json.loads(PACKAGE_LOCK.read_text(encoding="utf-8")))),
        PYPROJECT: tomlkit.dumps(sync_pyproject(meta, tomlkit.parse(PYPROJECT.read_text(encoding="utf-8")))),
    }
    changed = [path for path, text in updates.items() if path.read_text(encoding="utf-8") != text]

    if check:
        for path in changed:
            print(f"out of sync with metadata.json: {path.name}")
        return 1 if changed else 0

    for path in changed:
        path.write_text(updates[path], encoding="utf-8")
        print(f"synced: {path.name}")
    if PYPROJECT in changed:
        # uv.lock records the project's own name and version
        subprocess.run(["uv", "lock", "--quiet"], cwd=ROOT, check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
