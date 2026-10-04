# Analysing code

```sh
gitrecon analyze                                  # the repository you are in
gitrecon analyze ~/__WORKSHOP/forge/rattish       # every repository in a folder
gitrecon analyze PATH --json                      # everything, for programs
gitrecon analyze PATH --urls                      # links found in code and comments
gitrecon gitgraph PATH --format mermaid --save    # its history as a Mermaid gitGraph
```

`analyze` reads the files git tracks (or all files of a plain folder, without `node_modules`,
`.venv`, `dist` and the like), skips binaries and files over 400 KB, and reports per language:
files, bytes, code / comment / blank lines; plus frameworks and tools, the most used names,
Python structure and the links it met. See [[code-analysis]] and [[git-graph]].

## Teaching it more

Everything it knows is in `resources/` - no code changes needed for:

| To add | Edit |
| --- | --- |
| a language | `resources/languages.yml` → `languages:` (extensions, file names, `family`, `kind`) |
| keywords to leave out of the names | `resources/languages.yml` → `families:` (quote `true`, `false`, `null`, `yes`, `no`, `on`) |
| a framework known by its package | `resources/frameworks.yml` → `packages:` under its ecosystem |
| a tool known by a file | `resources/frameworks.yml` → `files:` (a glob from the repository root) |
| a dependency file | `resources/frameworks.yml` → `manifests:` (a reader from `gitrecon.code.frameworks`) |
| a language family | `resources/grammars/lexical/<family>.lark` with `COMMENT`, `STRING`, `NUMBER`, `NAME`, `OTHER` + a `families:` entry |

`task test` checks the tables against each other: every family has a grammar with the five
terminals, every extension belongs to one language, every package list has a manifest.

> **Remember!** When gitrecon runs outside its repository (installed elsewhere, or in a
> container), point `GITRECON_RESOURCES` at the `resources/` folder; the image carries it in
> `/app/resources`.
