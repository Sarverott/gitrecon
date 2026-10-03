"""Turning a summary into an SEO article and social media posts (drafts, never published here)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from gitrecon.digest.llm import ChatClient, parse_json_reply

TWEET_LIMIT = 280
MASTODON_LIMIT = 500
META_DESCRIPTION_LIMIT = 160

POSTS_PROMPT = """You are a technical content writer for a GitHub reconnaissance project.
From the analysis summary given by the user, write in {language}:

1. an SEO article: a title (max 60 chars), a slug, a meta description (max 160 chars),
   5-10 keywords, and a markdown body (600-1200 words) with H2 sections, concrete
   project names and numbers from the summary, and a short conclusion;
2. a thread of 3-6 tweets, each at most 280 characters including hashtags;
3. one LinkedIn post (max 1300 characters);
4. one Mastodon post (max 500 characters).

Use only facts present in the summary. No invented numbers, no clickbait.
Reply with a single JSON object:
{{"article": {{"title": "", "slug": "", "meta_description": "", "keywords": [], "body_markdown": ""}},
  "tweets": [""], "linkedin": "", "mastodon": ""}}"""


@dataclass
class Article:
    title: str
    slug: str
    meta_description: str
    keywords: list[str]
    body_markdown: str

    def to_markdown(self) -> str:
        front = {
            "title": self.title,
            "slug": self.slug,
            "description": self.meta_description,
            "keywords": self.keywords,
        }
        header = "\n".join(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in front.items())
        return f"---\n{header}\n---\n\n# {self.title}\n\n{self.body_markdown.strip()}\n"


@dataclass
class PostSet:
    article: Article
    tweets: list[str]
    linkedin: str
    mastodon: str
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def save(self, directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "article.md").write_text(self.article.to_markdown(), encoding="utf-8")
        (directory / "posts.json").write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        return directory


def _fit(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    cut = text[: limit - 1].rsplit(" ", 1)[0]
    return cut.rstrip(" ,;:-") + "…"


def build_posts(data: dict[str, Any]) -> PostSet:
    """Validate a model reply; over-long fields are trimmed and reported in ``warnings``."""
    warnings: list[str] = []
    a = data.get("article") or {}
    article = Article(
        title=str(a.get("title", "")).strip(),
        slug=str(a.get("slug", "")).strip(),
        meta_description=str(a.get("meta_description", "")).strip(),
        keywords=[str(k) for k in a.get("keywords") or []],
        body_markdown=str(a.get("body_markdown", "")),
    )
    if not article.title or not article.body_markdown.strip():
        warnings.append("article title or body is empty")
    if len(article.meta_description) > META_DESCRIPTION_LIMIT:
        warnings.append(f"meta description trimmed from {len(article.meta_description)} chars")
        article.meta_description = _fit(article.meta_description, META_DESCRIPTION_LIMIT)

    tweets = []
    for i, tweet in enumerate(data.get("tweets") or [], start=1):
        tweet = str(tweet)
        if len(tweet) > TWEET_LIMIT:
            warnings.append(f"tweet {i} trimmed from {len(tweet)} chars")
        tweets.append(_fit(tweet, TWEET_LIMIT))

    mastodon = str(data.get("mastodon", ""))
    if len(mastodon) > MASTODON_LIMIT:
        warnings.append(f"mastodon post trimmed from {len(mastodon)} chars")
    return PostSet(article, tweets, str(data.get("linkedin", "")).strip(), _fit(mastodon, MASTODON_LIMIT), warnings)


def write_posts(client: ChatClient, summary: str, language: str = "English") -> PostSet:
    reply = client.chat(
        [
            {"role": "system", "content": POSTS_PROMPT.format(language=language)},
            {"role": "user", "content": summary},
        ],
        json_mode=True,
    )
    return build_posts(parse_json_reply(reply))
