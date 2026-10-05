# CaptorLex

> The deep reading of code: structure first, then meaning, reasoning and sense. *Steps 1 and 2 (one repository, one owner) built.*

## What it is

Where [[peekerlex]] peeks, CaptorLex captures - in steps, each broader than the last:

1. **structure** *(built)* - a real syntax tree per file: what is defined - functions,
   methods, classes, structs, interfaces, traits. Through tree-sitter for 26 languages (the
   `structure:` key in `resources/languages.yml`), and through the standard `ast` for Python
   (imports, decorators, docstrings);
2. **relations** - what holds on to what, in nesting order:
   - inside one repository *(built)*: which file uses which;
   - between the repositories of one owner *(built)*: submodules first (one repository
     carries another), then dependencies (a manifest names another's package - softer);
   - one repository towards the world *(built, up to dependencies)*, firmest first: the
     parent of a fork, dependencies from the public registry, from a custom registry, straight
     from git, a file behind http; then stars; links in code, and after them links in text,
     are the weakest tie and come last;
3. **meaning** - what a piece of code is *for*: needs language models (the `llm` extra) reading
   the structure from steps 1-2, not raw text.

## Where

Step 1: `gitrecon.code.structure` (tree-sitter; the `code` extra) and `gitrecon.code.pyast`;
`gitrecon analyze --deep`. A grammar is downloaded on first use and cached.
Step 2, inside one repository: `gitrecon.code.imports`, `gitrecon imports [PATH]` - Python
exactly (through `ast`), other languages by the patterns in `resources/imports.yml`.
Step 2, one owner: `gitrecon.code.relations`, `gitrecon relations FOLDER`; one repository
towards the world: `gitrecon relations REPOSITORY`. Stars and links as ties, and step 3, are
not built.

## Relations

Builds on [[peekerlex]]; step 3 meets the digest side (summaries by language models).
