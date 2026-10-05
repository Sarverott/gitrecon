# LLM interface

> *Parked.* An interface to local language models through Ollama - tried, set aside.

## What it is

An `Ollama` object (plain answers, answers in a given shape, embeddings, model listing) and a
commit handler that had a model fill in the commit form. It worked mechanically; the
approach is being reconsidered, so the code is **commented out** and nothing in gitrecon
uses it. There is no `gitrecon llm` command.

## Where

`src/gitrecon/llm/ollama.py` and `src/gitrecon/llm/commit_handler.py` - kept as comments,
with a note at the top of each on how to bring them back. Their tests are skipped
(`tests/test_llm.py`). What was measured: [[scrapnote-1791187496508]].

## Relations

The working part of what was built went to [[commit-writer]] (handlers). The digest keeps
its own small HTTP client to Ollama (`gitrecon.digest.llm`), which is older and untouched.
