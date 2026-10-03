import json

import pytest
from conftest import FakeResponse, FakeSession, make_repo

from gitrecon.digest import OllamaClient, Summarizer, XaiClient, chunk_lines, write_posts
from gitrecon.digest.inputs import star_lines
from gitrecon.digest.llm import parse_json_reply
from gitrecon.digest.posts import TWEET_LIMIT, build_posts
from gitrecon.models import Star


class EchoModel:
    """Fake chat client: answers with a short tag per call, records what it was asked."""

    model = "fake"

    def __init__(self):
        self.calls = []

    def chat(self, messages, json_mode=False):
        self.calls.append(messages)
        return f"S{len(self.calls)}"


def test_chunk_lines_packs_and_cuts():
    chunks = list(chunk_lines(["a" * 4, "b" * 4, "c" * 4, "d" * 30], max_chars=10))
    assert chunks == ["aaaa\nbbbb", "cccc", "d" * 10]


def test_summarizer_map_reduce_until_one_summary():
    model = EchoModel()
    lines = [f"line {i} " + "x" * 40 for i in range(100)]  # ~5k chars
    summary = Summarizer(model, max_chars=1000).summarize(lines)

    map_calls = [c for c in model.calls if "one slice" in c[0]["content"]]
    reduce_calls = [c for c in model.calls if "partial summaries" in c[0]["content"]]
    assert len(map_calls) == 5  # ~49 chars per line -> 20 lines per 1000-char chunk
    assert len(reduce_calls) >= 1
    assert summary == f"S{len(model.calls)}"


def test_summarizer_single_chunk_needs_no_reduce():
    model = EchoModel()
    assert Summarizer(model).summarize(["tiny"]) == "S1"
    assert len(model.calls) == 1


def test_summarizer_empty_input():
    assert Summarizer(EchoModel()).summarize([]) == ""


def test_star_lines_for_sarverott():
    star = Star.from_api("sarverott", {"starred_at": "2026-09-30T10:00:00Z",
                                       "repo": make_repo("go-task/task", "Go", 13000, "Task runner")})
    assert list(star_lines([star])) == ["go-task/task [Go] *13000 starred 2026-09-30: Task runner"]


def test_ollama_client_request_shape():
    session = FakeSession({"http://ollama:11434/api/chat": [FakeResponse({"message": {"content": "ok"}})]})
    client = OllamaClient(model="llama3", host="http://ollama:11434", session=session)
    assert client.chat([{"role": "user", "content": "hi"}], json_mode=True) == "ok"
    body = session.calls[0][2]["json"]
    assert body["model"] == "llama3" and body["stream"] is False and body["format"] == "json"


def test_xai_client_needs_key_and_sends_bearer():
    with pytest.raises(RuntimeError):
        XaiClient(api_key=None).chat([])
    session = FakeSession({
        "https://api.x.ai/v1/chat/completions": [FakeResponse({"choices": [{"message": {"content": "hey"}}]})]
    })
    client = XaiClient(model="grok-x", api_key="k", base_url="https://api.x.ai/v1", session=session)
    assert client.chat([{"role": "user", "content": "hi"}]) == "hey"
    assert session.calls[0][2]["headers"]["Authorization"] == "Bearer k"
    assert session.calls[0][2]["json"]["model"] == "grok-x"


def test_parse_json_reply_tolerates_fences_and_chatter():
    assert parse_json_reply('{"a": 1}') == {"a": 1}
    assert parse_json_reply('Sure!\n```json\n{"a": 2}\n```') == {"a": 2}
    assert parse_json_reply('here: {"a": 3} done') == {"a": 3}


REPLY = {
    "article": {
        "title": "What sarverott stars",
        "slug": "what-sarverott-stars",
        "meta_description": "m" * 200,
        "keywords": ["github", "osint"],
        "body_markdown": "## Themes\n\nTask runners.",
    },
    "tweets": ["short one", "word " * 80],
    "linkedin": "post",
    "mastodon": "toot",
}


def test_build_posts_trims_and_warns():
    posts = build_posts(REPLY)
    assert len(posts.article.meta_description) == 160
    assert len(posts.tweets[1]) <= TWEET_LIMIT and posts.tweets[1].endswith("…")
    assert posts.tweets[0] == "short one"
    assert any("tweet 2" in w for w in posts.warnings)
    assert posts.article.to_markdown().startswith('---\ntitle: "What sarverott stars"')


def test_write_posts_and_save(tmp_path):
    class JsonModel:
        model = "fake"

        def chat(self, messages, json_mode=False):
            assert json_mode
            return json.dumps(REPLY)

    posts = write_posts(JsonModel(), "summary text", language="Polish")
    out = posts.save(tmp_path / "post")
    assert (out / "article.md").read_text().count("# What sarverott stars") == 1
    assert json.loads((out / "posts.json").read_text())["linkedin"] == "post"
