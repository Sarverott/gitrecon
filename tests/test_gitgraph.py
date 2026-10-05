"""Git history as a Mermaid gitGraph: lanes, ordering, merges - on small real repositories."""

import subprocess

import pytest

from gitrecon.main import main
from gitrecon.mapping.gitgraph import assign_lanes, branch_tips, git_graph, read_history


class Repo:
    def __init__(self, path):
        self.path = path
        path.mkdir(parents=True)
        self.git("init", "--quiet", "-b", "master")
        self.n = 0

    def git(self, *args):
        cmd = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *args]
        return subprocess.run(cmd, cwd=self.path, check=True, capture_output=True, text=True).stdout.strip()

    def commit(self, message):
        self.n += 1
        (self.path / f"f{self.n}.txt").write_text(str(self.n))  # a file per commit: merges never conflict
        self.git("add", ".")
        # distinct, increasing times keep the order stable
        env_date = f"2026-01-01T00:{self.n // 60:02d}:{self.n % 60:02d}"
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "--quiet", "-m", message,
                        "--date", env_date], cwd=self.path, check=True, capture_output=True,
                       env={"GIT_COMMITTER_DATE": env_date, "PATH": "/usr/bin:/bin", "HOME": str(self.path)})
        return self.git("rev-parse", "--short=7", "HEAD")


@pytest.fixture
def loop(tmp_path):
    """master -> development (2 commits) -> merged back; a feature branch merged and deleted; a tag."""
    r = Repo(tmp_path / "tool")
    ids = {"root": r.commit("first")}
    r.git("checkout", "--quiet", "-b", "development")
    ids["d1"] = r.commit("feat: one")
    r.git("checkout", "--quiet", "-b", "feature/x")
    ids["f1"] = r.commit("feat: on a feature branch")
    r.git("checkout", "--quiet", "development")
    ids["d2"] = r.commit("feat: two")
    r.git("merge", "--quiet", "--no-ff", "feature/x", "-m", "Merge branch 'feature/x' into development")
    ids["m1"] = r.git("rev-parse", "--short=7", "HEAD")
    r.git("branch", "-D", "feature/x")
    r.git("checkout", "--quiet", "master")
    r.git("merge", "--quiet", "--no-ff", "development", "-m", "Merge pull request #1 from me/development")
    ids["m2"] = r.git("rev-parse", "--short=7", "HEAD")
    r.git("tag", "v1.0.0")
    return r, ids


def test_lanes_follow_first_parents_and_revive_deleted_branches(loop):
    repo, ids = loop
    commits = read_history(repo.path)
    lanes = assign_lanes(commits, branch_tips(repo.path))
    lane = {c.short: c.lane for c in commits}
    assert lanes == ["master", "development", "feature/x"]
    assert lane[ids["root"]] == lane[ids["m2"]] == "master"
    assert lane[ids["d1"]] == lane[ids["d2"]] == lane[ids["m1"]] == "development"
    assert lane[ids["f1"]] == "feature/x"            # the branch is gone; its name comes from the merge
    assert [c.short for c in commits][0] == ids["root"]  # parents before children


def test_gitgraph_script(loop):
    repo, ids = loop
    lines = git_graph(repo.path).splitlines()
    assert lines[:7] == ["---", "config:", "  gitGraph:", '    mainBranchName: "master"',
                         "    showCommitLabel: false", "---", "gitGraph"]
    body = lines[7:]
    at = {line: i for i, line in enumerate(body)}
    commit = lambda key: f'  commit id:"{ids[key]}"'  # noqa: E731
    assert body[0] == commit("root") and body[1] == '  branch "development"'
    # a lane opens right after the commit it starts from: feature/x straight after d1
    assert body[at[commit("d1")] + 1] == '  branch "feature/x"'
    assert at[commit("d1")] < at[commit("f1")] and at[commit("d1")] < at[commit("d2")]
    merge_feature = f'  merge "feature/x" id:"{ids["m1"]}"'
    assert at[commit("f1")] < at[merge_feature] and at[commit("d2")] < at[merge_feature]
    assert body[-2:] == ['  checkout "master"', f'  merge "development" id:"{ids["m2"]}" tag:"v1.0.0"']
    # every commit drawn once, on a lane that exists by then
    assert sum(line.startswith(("  commit", "  merge")) for line in body) == 6


def test_truncated_history_stays_valid(loop):
    repo, ids = loop
    script = git_graph(repo.path, max_commits=3, labels=True)
    assert "%% the newest 3 commits; older history is not drawn" in script
    lines = script.splitlines()
    drawn = [line for line in lines if line.startswith(("  commit", "  merge"))]
    assert len(drawn) == 3 and "showCommitLabel: true" in script
    # lanes whose start is outside the drawing hang on the main lane; nothing is used before it exists
    created = {lines[3].split('"')[1]}
    for line in lines:
        words = line.split('"')
        if line.startswith("  branch"):
            created.add(words[1])
        elif line.startswith(("  checkout", "  merge")):
            assert words[1] in created, line


def test_same_branch_merge_and_revert_are_marked(tmp_path):
    r = Repo(tmp_path / "r")
    r.commit("first")
    r.commit("Revert \"first\"")
    script = git_graph(r.path)
    assert 'type:REVERSE' in script and "merge " not in script


def test_gitgraph_command(loop, tmp_path, monkeypatch, capsys):
    repo, _ = loop
    monkeypatch.setenv("GITRECON_DATA", str(tmp_path / "data"))
    assert main(["gitgraph", str(repo.path), "--save"]) == 0
    out = capsys.readouterr().out
    assert "tool: 6 commits, 2 merges, 3 lanes" in out and "tags: v1.0.0" in out
    saved = (tmp_path / "data" / "gitgraphs" / "tool.md").read_text()
    assert saved.startswith("# Git graph of tool\n\n```mermaid\n---\nconfig:") and saved.endswith("```\n")
