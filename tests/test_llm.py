"""PARKED with gitrecon/llm/ (2026-10-05): tests of the Ollama interface and the model-backed
commit handler. Skipped as a whole; kept for the day the approach is taken up again.
"""

import pytest

pytest.skip("gitrecon.llm is parked (the Ollama approach is set aside)", allow_module_level=True)

import json  # noqa: E402
from types import SimpleNamespace  # noqa: E402

from gitrecon.llm import Ollama, commit_writer, find_host  # noqa: E402, F401


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


def test_reader_model_takes_notes_for_the_writer(repo):
    root, _ = repo
    notes = {"summary": "The sum was computed as a difference.", "changes": ["add instead of subtract"],
             "kind": "fix", "reason": "wrong operator"}
    form = {"prefix": "fix", "scope": "core", "subject": "add the operands instead of subtracting them"}
    llm = llm_with(notes, form)
    plan = commit_writer.plan_commits(root, llm, model="writer:7b", reader="reader:1.5b", limit=1)
    step = plan[0]
    assert step["message"] == "fix(core): add the operands instead of subtracting them" and step["by"] == "writer:7b"
    assert step["notes"] == notes
    assert step["facts"] | {"used_by_examples": []} == {
        "path": "pkg/core.py", "status": "modified", "language": "Python", "kind": "code", "lines_added": 1,
        "lines_deleted": 1, "imports": [], "used_by": 2, "used_by_examples": []}
    read, write = llm.client.calls
    assert read["model"] == "reader:1.5b" and "It is used by 2 file(s)" in read["messages"][1]["content"]
    assert write["model"] == "writer:7b" and "Notes of a reader who studied the change" in write["messages"][1]["content"]
    assert "- add instead of subtract" in write["messages"][1]["content"]
    # a reader that fails leaves the writer with the diff itself
    alone = llm_with("junk", "junk", form)
    step = commit_writer.plan_commits(root, alone, reader="reader:1.5b", limit=1)[0]
    assert step["notes"] is None and step["message"].startswith("fix(core)")
    assert "The change:" in alone.client.calls[-1]["messages"][1]["content"]
