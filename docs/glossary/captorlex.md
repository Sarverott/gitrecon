# CaptorLex

> The deep reading of code: structure first, then meaning, reasoning and sense. *Step 1 built.*

## What it is

Where [[peekerlex]] peeks, CaptorLex captures - in steps, each broader than the last:

1. **structure** *(built)* - a real syntax tree per file: what is defined - functions,
   methods, classes, structs, interfaces, traits. Through tree-sitter for 26 languages (the
   `structure:` key in `resources/languages.yml`), and through the standard `ast` for Python
   (imports, decorators, docstrings);
2. **relations** - across files and repositories: which module uses which, the same code in
   several repositories, forks that diverged;
3. **meaning** - what a piece of code is *for*: needs language models (the `llm` extra) reading
   the structure from steps 1-2, not raw text.

## Where

Step 1: `gitrecon.code.structure` (tree-sitter; the `code` extra) and `gitrecon.code.pyast`;
`gitrecon analyze --deep`. A grammar is downloaded on first use and cached. Steps 2-3 are not built.

## Relations

Builds on [[peekerlex]]; step 3 meets the digest side (summaries by language models).
