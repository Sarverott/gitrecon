# Analysing code

```sh
gitrecon analyze                                  # the repository you are in
gitrecon analyze ~/__WORKSHOP/forge/rattish       # every repository in a folder
gitrecon analyze PATH --json                      # everything, for programs
gitrecon analyze PATH --urls                      # links found in code and comments
gitrecon analyze PATH --deep                      # CaptorLex step 1: functions, methods, classes per language
gitrecon analyze PATH --no-save                   # only print, keep nothing
gitrecon commits PATH                             # its commit messages as records and labels
gitrecon imports PATH                             # which file uses which (CaptorLex step 2)
gitrecon imports PATH --format mermaid --save     # the same as a diagram of folders (--level file: of files)
gitrecon score PATH                               # its history as guitar tablature (--format abc | midi)
gitrecon gitgraph PATH --format mermaid --save    # its history as a Mermaid gitGraph
```

`analyze` reads the files git tracks (or all files of a plain folder, without `node_modules`,
`.venv`, `dist` and the like), skips binaries and files over 400 KB, and reports per language:
files, bytes, code / comment / blank lines; plus frameworks and tools, the most used names,
Python structure and the links it met. See [[code-analysis]] and [[git-graph]].

## Where results are kept

> **Remember!** `analyze` saves by default, in two places:
>
> | Where | What |
> | --- | --- |
> | `data/raw/analysis/<date>/<HH>.json.gz` | the raw buffer: every run appended, with the local path and the time |
> | `datasets/imperialmap/data-heuristicality/code-analysis/<platform>/<owner>/<repository>.json` | the map: one file per repository, rewritten only when the repository changed; no local path |
>
> A repository without an `origin` remote goes to the raw buffer only. `--no-save` keeps nothing.

> **Remember!** The map is published by `gitrecon atlas push`, so only repositories GitHub
> shows as public are written to it. `analyze` asks GitHub once per repository; private
> ones, ones on other platforms and ones it cannot ask about (no network) go to the raw
> buffer only. `--map-priv-repos` writes them to the map as well (`analyze`, `repo-clone`,
> `org-clone`).

`repo-clone` and `org-clone` analyse what they clone and save it the same way; each clone's
line then ends with `[language, files; frameworks]`. `--no-analysis` only clones - for mass
management of git data where reading the code is not wanted.

The reading done by default is [[peekerlex]]: quick and light. `--deep` adds the first step of
[[captorlex]]: what each file defines, through tree-sitter (the `code` extra; a language's
grammar is downloaded the first time it is met).

## Which file uses which

`gitrecon imports` reads every import inside the repository and reports the files used most,
the files using most, imports between folders, cycles (files that need each other in a ring),
files connected to nothing, and what is used from outside (libraries). Python is read exactly;
JavaScript, TypeScript, Vue, Svelte, C, C++, PHP (with composer's PSR-4 map), Ruby, shell and
CSS by the patterns in `resources/imports.yml`.

> **Remember!** `--save` writes `data/imports/<repository>-<level>.md`, in gitrecon's data folder.

## Teaching it more

Everything it knows is in `resources/` - no code changes needed for:

| To add | Edit |
| --- | --- |
| a language | `resources/languages.yml` → `languages:` (extensions, file names, `family`, `kind`) |
| keywords to leave out of the names | `resources/languages.yml` → `families:` (quote `true`, `false`, `null`, `yes`, `no`, `on`) |
| a framework known by its package | `resources/frameworks.yml` → `packages:` under its ecosystem |
| a tool known by a file | `resources/frameworks.yml` → `files:` (a glob from the repository root) |
| a dependency file | `resources/frameworks.yml` → `manifests:` (a reader from `gitrecon.code.frameworks`) |
| how a language names the files it uses | `resources/imports.yml` (patterns, how a target becomes a file) |
| deep reading for a language | `resources/languages.yml` -> `structure:` (a tree-sitter grammar name) |
| a language family | `resources/grammars/lexical/<family>.lark` with `COMMENT`, `STRING`, `NUMBER`, `NAME`, `OTHER` + a `families:` entry |

`task test` checks the tables against each other: every family has a grammar with the five
terminals, every extension belongs to one language, every package list has a manifest.

> **Remember!** When gitrecon runs outside its repository (installed elsewhere, or in a
> container), point `GITRECON_RESOURCES` at the `resources/` folder; the image carries it in
> `/app/resources`.
