# Code analysis

> What a cloned repository is made of: languages, code and comment lines, names, links, Python structure, frameworks.

## What it is

Two depths of reading: [[peekerlex]] (quick and light - everything below except the Python
structure) and [[captorlex]] (deep - planned; Python's `ast` is its first piece). The layers,
all driven by tables and grammars in `resources/` rather than by code:

- **languages** - a file's language by extension or name (`resources/languages.yml`);
- **lexical patterns** - one Lark grammar per language *family* (`resources/grammars/lexical/`:
  `c_family`, `python`, `hash_family`, `dash_family`, `markup`) naming what a comment, a string,
  a number and a name look like. Used with the lexer only, so unfamiliar syntax never fails -
  it becomes `OTHER` tokens. From the tokens: code / comment / blank lines, the names used
  (keywords left out) and URLs in strings and comments;
- **structure** - Python files through the standard `ast`: imports, functions, classes,
  decorators, docstring coverage;
- **frameworks and tools** - from dependency manifests (`package.json`, `pyproject.toml`,
  `requirements*.txt`, `composer.json`, `Cargo.toml`, `go.mod`, `Gemfile`) and marker files
  (`resources/frameworks.yml`).

## Where

`gitrecon.code` (`languages`, `lexical`, `pyast`, `frameworks`, `analyze`). CLI:
`gitrecon analyze [PATH...]` - a repository, or a folder of repositories such as
`~/__WORKSHOP/forge/rattish`. Guide: [[analysing-code]].

## Where results go

By default both: the raw buffer (`data/raw/analysis/`, every run appended) and the map dataset
(`datasets/imperialmap/data-heuristicality/code-analysis/<platform>/<owner>/<repository>.json`,
rewritten only when the repository changed). `gitrecon analyze --no-save` only prints;
`repo-clone` / `org-clone` analyse what they clone unless `--no-analysis`.

## Relations

Works on what the clone commands bring ([[gist]]s, repositories); URLs it finds are the same
kind as the [[link-catalog]]'s; printed in every [[output-mode]].
