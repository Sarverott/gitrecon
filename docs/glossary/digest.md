# Digest

> A summary of any amount of collected data, made by a local model.

## What it is

Map-reduce: lines are packed into chunks that fit the model's context, each chunk is summarized, then the summaries are merged until one remains. Read digests before using them: small models can garble names.

## Where

`gitrecon.digest` (`Summarizer`, `OllamaClient`). CLI: `gitrecon digest stars:USER | labels | links | file:PATH`; saved in `data/digests/`. TODO(llm-interfaces): on hold.

## Relations

Turned into [[post-drafts]].
