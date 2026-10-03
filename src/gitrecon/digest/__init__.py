"""Digest: summarizing huge data locally (Ollama) and writing posts from it (xAI)."""

from gitrecon.digest.llm import OllamaClient, XaiClient
from gitrecon.digest.posts import PostSet, write_posts
from gitrecon.digest.summarize import Summarizer, chunk_lines

__all__ = ["OllamaClient", "PostSet", "Summarizer", "XaiClient", "chunk_lines", "write_posts"]
