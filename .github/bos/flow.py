"""BOS craft loop: pull requests, auto-merge and version bumps driven by .github/bos.config.json.

Commands (run from the repository root, inside GitHub Actions with GH_TOKEN set):
  explain              print how the config resolves (safe to run locally)
  next-pr BRANCH       open the PR from BRANCH to its next stage, then start its checks
  automerge PR         merge PR if its direction allows it, then start the next step
  bump                 bump version, changelog and tag for a release on master

Events made with the default GITHUB_TOKEN don't start other workflows, except
workflow_dispatch. So every step starts the next one explicitly with `gh workflow run`.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

CONFIG = Path(".github/bos.config.json")
CHECKS_WORKFLOW = "pr-checks.yml"
FLOW_WORKFLOW = "bos-flow.yml"
RELEASE_WORKFLOW = "release.yml"
RELEASE_BRANCH = "master"

# Work branches outside the canonical loop: PRs into development are opened for them, never auto-merged.
WORK_BRANCH = re.compile(r"^(feature|fix)/")
WORK_TARGET = "development"

FLAG_AUTOCREATE = "autocreate_loopedPR"
FLAG_AUTOMERGE = "automerge_loopedPR_"

BREAKING = re.compile(r"^\w+(\([^)]*\))?!:|^BREAKING[ -]CHANGE:", re.MULTILINE)


def load_config():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    branches = config["branches"]
    for source, targets in branches["directions"].items():
        for name in [source, *targets]:
            if name not in branches["canonical"]:
                raise SystemExit(f"bos.config.json: '{name}' in directions is not a canonical branch")
    return config


def primary_target(config, branch):
    """The forward stage of a branch: the first of its directions."""
    if WORK_BRANCH.match(branch):
        return WORK_TARGET
    targets = config["branches"]["directions"].get(branch, [])
    return targets[0] if targets else None


def automerge_allowed(config, source, target):
    """Read automerge_loopedPR_<from>-<to>, where <from>/<to> are branch names or their initials.

    Initials are matched against primary directions only, so "r-m" means releasing → master
    and can't be confused with revision or rejection.
    """
    if WORK_BRANCH.match(source):
        return False
    directions = config["branches"]["directions"]
    primary = {s: t[0] for s, t in directions.items() if t}
    for key, value in config["branches"].get("flags", {}).items():
        if not key.startswith(FLAG_AUTOMERGE):
            continue
        left, _, right = key[len(FLAG_AUTOMERGE):].partition("-")
        matches = [(s, t) for s, t in primary.items() if s.startswith(left) and t.startswith(right)]
        if len(matches) != 1:
            raise SystemExit(f"bos.config.json: flag '{key}' matches {len(matches)} directions {matches}, expected exactly one")
        if matches[0] == (source, target):
            return bool(value)
    return False


def run(*args, capture=True):
    result = subprocess.run(args, check=True, text=True, capture_output=capture)
    return result.stdout.strip() if capture else ""


def gh_json(*args):
    return json.loads(run("gh", *args))


def dispatch(workflow, ref, **inputs):
    fields = [f"--field={k}={v}" for k, v in inputs.items()]
    run("gh", "workflow", "run", workflow, f"--ref={ref}", *fields)
    print(f"started {workflow} on {ref} {inputs}")


def output(name, value):
    if "GITHUB_OUTPUT" in os.environ:
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as fh:
            fh.write(f"{name}={value}\n")


def worth_proposing(repo, source, target):
    """Skip PRs that would only carry merge commits and version bumps back and forth.

    The way back from master is the exception: it carries the release bump to development.
    """
    compare = gh_json("api", f"repos/{repo}/compare/{target}...{source}")
    if compare["ahead_by"] == 0:
        return False
    if source == RELEASE_BRANCH:
        return True
    return any(
        len(c["parents"]) == 1 and not c["commit"]["message"].startswith("bump:")
        for c in compare["commits"]
    )


def cmd_next_pr(branch):
    config = load_config()
    repo = os.environ["GITHUB_REPOSITORY"]
    if not config["branches"].get("flags", {}).get(FLAG_AUTOCREATE, False):
        print(f"{FLAG_AUTOCREATE} is off, nothing to do.")
        return
    target = primary_target(config, branch)
    if target is None:
        print(f"{branch} is not part of the loop, nothing to do.")
        return
    if not worth_proposing(repo, branch, target):
        print(f"{branch} has nothing new for {target} (only merges and version bumps), no PR.")
        return

    existing = gh_json("pr", "list", "--head", branch, "--base", target, "--state", "open", "--json", "number")
    if existing:
        number = existing[0]["number"]
        print(f"PR #{number} {branch} → {target} is already open.")
    else:
        url = run(
            "gh", "pr", "create", "--base", target, "--head", branch,
            "--title", f"Merge {branch} into {target}",
            "--body",
            f"### Loop step: `{branch}` → `{target}`\n\n"
            f"Opened by the BOS craft loop (`.github/bos.config.json`).\n"
            f"Auto-merge for this step: **{'on' if automerge_allowed(config, branch, target) else 'off'}**.",
        )
        number = int(url.rstrip("/").rsplit("/", 1)[-1])
        print(f"opened PR #{number} {branch} → {target}")
    output("pr", number)
    # a PR opened or updated by the GITHUB_TOKEN gets no pull_request event, start its checks directly
    dispatch(CHECKS_WORKFLOW, branch, pr=number)


def cmd_automerge(number):
    config = load_config()
    pr = gh_json("pr", "view", str(number), "--json", "state,baseRefName,headRefName,isCrossRepository")
    source, target = pr["headRefName"], pr["baseRefName"]
    if pr["state"] != "OPEN":
        print(f"PR #{number} is {pr['state'].lower()}, nothing to merge.")
        return
    if pr["isCrossRepository"] or not automerge_allowed(config, source, target):
        print(f"Auto-merge is off for {source} → {target}, PR #{number} waits for a human.")
        return
    run("gh", "pr", "merge", str(number), "--merge", capture=False)
    print(f"merged PR #{number} {source} → {target}")
    # the merge push made with the GITHUB_TOKEN starts nothing by itself
    if target == RELEASE_BRANCH:
        dispatch(RELEASE_WORKFLOW, RELEASE_BRANCH)
    else:
        dispatch(FLOW_WORKFLOW, target, branch=target)


def cmd_bump():
    config = load_config()
    versioning = config.get("versioning", {})
    loop = versioning.get("loop", "PATCH")
    breaking = versioning.get("breaking", "MINOR")
    try:
        last_tag = run("git", "describe", "--tags", "--abbrev=0")
        log_range = f"{last_tag}..HEAD"
    except subprocess.CalledProcessError:
        last_tag, log_range = None, "HEAD"
    messages = run("git", "log", log_range, "--format=%B%x00")
    increment = breaking if BREAKING.search(messages) else loop
    print(f"last release: {last_tag or 'none'}, increment: {increment}")
    run("uv", "run", "cz", "bump", "--yes", "--increment", increment, "--allow-no-commit", "--git-output-to-stderr", capture=False)


def cmd_explain():
    config = load_config()
    print(f"{FLAG_AUTOCREATE}: {config['branches'].get('flags', {}).get(FLAG_AUTOCREATE, False)}")
    for source in config["branches"]["canonical"]:
        target = primary_target(config, source)
        if target:
            others = config["branches"]["directions"][source][1:]
            merge = "auto-merge" if automerge_allowed(config, source, target) else "human merge"
            print(f"  {source:12} → {target:12} {merge:12} other directions: {', '.join(others) or '-'}")
    print(f"  {'feature/*, fix/*':12} → {WORK_TARGET:12} human merge")
    versioning = config.get("versioning", {})
    print(f"release on {RELEASE_BRANCH}: {versioning.get('loop', 'PATCH')} per loop, {versioning.get('breaking', 'MINOR')} on breaking change")


def main():
    commands = {"explain": cmd_explain, "next-pr": cmd_next_pr, "automerge": cmd_automerge, "bump": cmd_bump}
    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        raise SystemExit(__doc__)
    commands[sys.argv[1]](*sys.argv[2:])


if __name__ == "__main__":
    main()
