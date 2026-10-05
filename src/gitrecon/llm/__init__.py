"""Local language models through Ollama (the ``llm`` extra): chat, structured answers, embeddings.

    from gitrecon.llm import Ollama
    answer = Ollama().structured(CommitForm, "Describe this change: ...")

What is built on it: ``gitrecon.llm.commit_writer`` (a commit message per changed file).
"""

from gitrecon.llm.ollama import Ollama, find_host

__all__ = ["Ollama", "find_host"]
