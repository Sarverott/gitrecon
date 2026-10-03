# RAT script

> A "rattish" script: a glossary section of numeronyms plus a section rebuilding the sentences.

## What it is

Built from markdown -> text -> [[word-chain]]s -> [[a12y]] glossary. Output is byte-identical to the project's first notebook (pinned by `tests/fixtures/taskfile-llms.*`).

## Where

`gitrecon.text.rat.build_rat()`. CLI: `gitrecon text rat URL`; example `examples/text-experiments/`.

## Relations

Uses [[a12y]] and [[word-chain]]s.
