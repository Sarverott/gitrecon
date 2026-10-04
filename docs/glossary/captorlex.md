# CaptorLex

> The deep reading of code: structure first, then meaning, reasoning and sense. *Planned.*

## What it is

Where [[peekerlex]] peeks, CaptorLex captures - in steps, each broader than the last:

1. **structure** - a real syntax tree per file: functions, classes, imports, calls, who calls
   whom. For Python this exists already through the standard `ast` (`gitrecon.code.pyast`);
   for other languages the candidate is tree-sitter (compiled grammars for ~100 languages);
2. **relations** - across files and repositories: which module uses which, the same code in
   several repositories, forks that diverged;
3. **meaning** - what a piece of code is *for*: needs language models (the `llm` extra) reading
   the structure from steps 1-2, not raw text.

## Where

Today only step 1 for Python: `gitrecon.code.pyast`. The rest is not built.

## Relations

Builds on [[peekerlex]]; step 3 meets the digest side (summaries by language models).
