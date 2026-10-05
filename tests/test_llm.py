"""The Ollama interface and the per-file commit writer - with a faked server, offline."""

import json
import subprocess
from types import SimpleNamespace

import pytest

pytest.importorskip("pydantic")
pytest.importorskip("ollama")

from gitrecon.llm import Ollama, commit_writer, find_host  # noqa: E402
from gitrecon.main import main  # noqa: E402


class FakeServer:
    """Stands in for ``ollama.Client``: records calls, answers from a queue."""

    def __init__(self, answers=(), models=("deepseek-r1:1.5b",), refuse_think=False):
        self.answers, self.names, self.calls, self.refuse_think = list(answers), list(models), [], refuse_think

    def list(self):
        return SimpleNamespace(models=[SimpleNamespace(model=name) for name in self.names])

    def chat(self, **call):
        self.calls.append(call)
        if self.refuse_think and "think" in call:
            raise RuntimeError('"llama3" does not support thinking')
        answer = self.answers.pop(0) if self.answers else "{}"
        return SimpleNamespace(message=SimpleNamespace(content=answer if isinstance(answer, str) else json.dumps(answer)))

    def embed(self, model, input):  # noqa: A002
        return SimpleNamespace(embeddings=[[0.1, 0.2]] * (1 if isinstance(input, str) else len(input)))


def llm_with(*answers, **kw):
    return Ollama(host="http://test:11434", _client=FakeServer(answers, **kw))


def test_find_host(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "box:11434")
    assert find_host() == "http://box:11434"
    monkeypatch.delenv("OLLAMA_HOST")
    answering = SimpleNamespace(get=lambda url, timeout: SimpleNamespace(ok=":11435" in url))
    assert find_host(answering) == "http://localhost:11435"            # the services container
    silent = SimpleNamespace(get=lambda url, timeout: (_ for _ in ()).throw(OSError("refused")))
    assert find_host(silent) == "http://localhost:11434"               # nobody answers: the usual default


def test_model_choice_and_plain_chat(monkeypatch):
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    llm = llm_with("Warsaw")
    assert llm.models() == ["deepseek-r1:1.5b"]
    assert llm.chat("capital of Poland?", system="one word") == "Warsaw"
    call = llm.client.calls[0]
    assert call["model"] == "deepseek-r1:1.5b" and call["messages"][0] == {"role": "system", "content": "one word"}
    assert call["options"] == {"temperature": 0.0, "num_ctx": 8192}
    with pytest.raises(RuntimeError, match="has no models"):
        llm_with(models=()).pick_model()
    assert llm.embed(["a", "b"]) == [[0.1, 0.2], [0.1, 0.2]]


def test_structured_answers_validate_retry_and_think_switch():
    from pydantic import BaseModel

    class Pet(BaseModel):
        name: str
        age: int

    llm = llm_with('{"name": "Luna"}', {"name": "Luna", "age": 3})
    pet = llm.structured(Pet, "I have a cat named Luna, three years old")
    assert (pet.name, pet.age) == ("Luna", 3) and len(llm.client.calls) == 2      # the first answer lacked a field
    assert llm.client.calls[0]["format"] == Pet.model_json_schema() and llm.client.calls[0]["think"] is False
    with pytest.raises(ValueError, match="did not answer in the shape of Pet"):
        llm_with("nonsense", "more nonsense").structured(Pet, "x")
    old = llm_with({"name": "Loki", "age": 2}, refuse_think=True)                 # a model without a thinking mode
    assert old.structured(Pet, "x").name == "Loki" and "think" not in old.client.calls[-1]


# --- commit messages -----------------------------------------------------------------------


def test_build_message_is_always_a_conventional_commit():
    build = commit_writer.build_message
    assert build({"prefix": "feat", "scope": "cli tools", "subject": "Add the thing.", "body": "Because."}) == (
        "feat(cli-tools): add the thing\n\nBecause.")
    assert build({"prefix": "fix", "subject": "x" * 200}).splitlines()[0] == "fix: " + "x" * 72
    assert build({"prefix": "chore", "scope": "", "subject": "update lock"}) == "chore: update lock"
    breaking = build({"prefix": "feat", "subject": "drop v1", "is_breaking_change": True, "body": "v1 is gone"})
    assert "BREAKING CHANGE: v1 is gone" in breaking
    with pytest.raises(ValueError):
        build({"prefix": "feature", "subject": "x"})
    assert set(commit_writer.commit_form().model_json_schema()["properties"]) == {
        "prefix", "scope", "subject", "body", "is_breaking_change", "footer"}       # commitizen's own questions


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "proj"
    (root / "pkg").mkdir(parents=True)
    (root / "tests").mkdir()
    git = lambda *a: subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", *a],  # noqa: E731
                                    check=True, capture_output=True, text=True).stdout
    git("init", "--quiet", "-b", "development")
    (root / "pkg" / "__init__.py").write_text("")
    (root / "pkg" / "core.py").write_text("def add(a, b):\n    return a - b\n")
    (root / "old.txt").write_text("x\n")
    (root / "README.md").write_text("# proj\n")
    git("add", ".")
    git("commit", "--quiet", "-m", "feat: start")
    # the changes: a fix, a new module using it, a test, docs, a deletion
    (root / "pkg" / "core.py").write_text("def add(a, b):\n    return a + b\n")
    (root / "pkg" / "app.py").write_text("from pkg.core import add\n\nprint(add(1, 2))\n")
    (root / "tests" / "test_core.py").write_text("from pkg.core import add\n\ndef test_add():\n    assert add(1, 2) == 3\n")
    (root / "README.md").write_text("# proj\n\nAdds numbers.\n")
    (root / "old.txt").unlink()
    return root, git


def test_changes_and_their_order(repo):
    root, _ = repo
    changes = commit_writer.changed_files(root)
    assert {(c.path, c.status) for c in changes} == {
        ("pkg/core.py", "modified"), ("pkg/app.py", "added"), ("tests/test_core.py", "added"),
        ("README.md", "modified"), ("old.txt", "deleted")}
    ordered = [c.path for c in commit_writer.order_changes(root, changes)]
    assert ordered == ["pkg/core.py", "pkg/app.py", "tests/test_core.py", "README.md", "old.txt"]   # what is imported first
    diff = commit_writer.file_diff(root, changes[[c.path for c in changes].index("pkg/core.py")])
    assert "-    return a - b" in diff and "+    return a + b" in diff
    new = commit_writer.file_diff(root, commit_writer.Change("pkg/app.py", "added"))
    assert new.startswith("+from pkg.core import add")


def test_plan_with_a_model_and_fallback(repo):
    root, _ = repo
    llm = llm_with({"prefix": "fix", "scope": "core", "subject": "Add instead of subtracting.", "body": "The sum was a difference."},
                   "not json", "still not json")                       # the second file: the model fails twice
    plan = commit_writer.plan_commits(root, llm, limit=2)
    assert [(s["path"], s["by"]) for s in plan] == [("pkg/core.py", "deepseek-r1:1.5b"), ("pkg/app.py", "fallback")]
    assert plan[0]["message"] == "fix(core): add instead of subtracting\n\nThe sum was a difference."
    assert plan[1]["message"] == "chore(pkg): add app.py"
    prompt = llm.client.calls[0]["messages"][1]["content"]
    assert "File: pkg/core.py" in prompt and "+    return a + b" in prompt
    plain = commit_writer.plan_commits(root)                            # no model at all
    assert [s["message"] for s in plain] == ["chore(pkg): update core.py", "chore(pkg): add app.py",
                                             "test(tests): add test_core.py", "docs: update README.md",
                                             "docs: remove old.txt"]


def test_apply_makes_one_commit_per_file(repo, capsys):
    root, git = repo
    (root / "untouched.txt").write_text("left alone\n")
    plan = [s for s in commit_writer.plan_commits(root) if s["path"] != "untouched.txt"]
    done = commit_writer.apply_plan(root, plan)
    assert all(step["committed"] for step in done) and len(done) == 5
    log = git("log", "--format=%s", "--name-status").split("\n\n")
    assert git("log", "--format=%s").splitlines()[:5] == ["docs: remove old.txt", "docs: update README.md",
                                                           "test(tests): add test_core.py", "chore(pkg): add app.py",
                                                           "chore(pkg): update core.py"]
    assert git("show", "--stat", "--format=", "HEAD~1").count("|") == 1          # one file in each commit
    assert git("status", "--porcelain").strip() == "?? untouched.txt" and log    # the rest of the tree is as it was


def test_commit_files_command(repo, capsys, monkeypatch):
    root, git = repo
    assert main(["commit-files", str(root), "--no-model", "--limit", "2"]) == 0
    out = capsys.readouterr().out
    assert "modified  pkg/core.py" in out and "a plan of 2 commits; nothing was committed" in out
    assert git("log", "--oneline").count("\n") == 1                            # still only the first commit
    assert main(["commit-files", str(root), "--no-model", "--apply", "--json"]) == 0
    assert len([s for s in json.loads(capsys.readouterr().out) if s["committed"]]) == 5
    assert main(["commit-files", str(root), "--no-model"]) == 0 and "nothing changed" in capsys.readouterr().out


def test_commitizen_does_not_silence_our_loggers():
    import logging

    ours = logging.getLogger("gitrecon.sources.github_api")
    ours.disabled = False
    commit_writer.commit_types()
    commit_writer.build_message({"prefix": "feat", "subject": "x"})
    assert not ours.disabled
