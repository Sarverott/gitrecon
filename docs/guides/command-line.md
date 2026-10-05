# Command line

`gitrecon <command> --help` describes every option; `gitrecon menu` (or plain `gitrecon`) offers
them all as forms - see [[menu]]. Grouped by what they do.

**For programs:** most commands take `--json` (only data on stdout) and `--urls` (only web
addresses, one per line) - see [[integration]] for the shapes. Example:
`gitrecon stars sarverott --urls`.

> **Remember!** `--save` never writes into the folder you are standing in. Everything gitrecon
> saves lands in its data folder - `data/` in the repository, or wherever `GITRECON_DATA` points:
>
> | Saved by | Lands in |
> | --- | --- |
> | `network USER --save` | `data/networks/<user>-<level>.md`, with `--format mindmap`: `<user>-mindmap.md` |
> | `analyze PATH` (unless `--no-save`), `repo-clone` / `org-clone` (unless `--no-analysis`) | `data/raw/analysis/` and the map: `datasets/imperialmap/data-heuristicality/code-analysis/` |
> | `contributors PATH --save` | `data/contributors/<repository>.AUTHORS`, pie: `<repository>-<by>.md` |
> | `relations FOLDER --save` | `data/relations/<folder>.md` (a Mermaid diagram in markdown) |
> | `imports PATH --save` | `data/imports/<repository>-<level>.md` (a Mermaid diagram in markdown) |
> | `score PATH --format midi`, `score PATH --save` | `data/scores/<repository>.mid`, `.abc`, `.tab.txt` |
> | `gitgraph PATH --save` | `data/gitgraphs/<repository>.md` (a Mermaid gitGraph in markdown) |
> | `events`, `gists`, `archive`, `stars --save`, `feeds --save`, `blog --save` | `data/raw/<source>/<day>/` |
> | `links --save`, `rfc --save` | `data/catalog/` |
> | `digest`, `posts` | `data/digests/`, `data/posts/` |
>
> Each command prints `saved <path>` when it does. Only the clone commands differ: they write
> to the forge (`~/__WORKSHOP/forge/<user or org>/`) or the path you give.

## Collect

| Command | Does |
| --- | --- |
| `gitrecon events [public\|user:X\|org:X\|repo:O/N] [--watch]` | poll an [[events-feed]] into the [[raw-buffer]] |
| `gitrecon archive 2026-10-01-0 [2026-10-01-23]` | download [[gh-archive]] hours |
| `gitrecon gists [--user X]` | newest public gists, or one user's |
| `gitrecon stars USER [--json] [--save]` | repositories a user has starred ([[star]]) |
| `gitrecon gist-catalog USER [--privacy all]` | every [[gist]] of a user: files, stars, comments, forks, commits, size |
| `gitrecon gist-clone USER [PATH] [--limit N] [--dry-run] [--update]` | clone them as they are into `PATH/<gistID>` (default `<forge>/USER/my-gists`) |
| `gitrecon repos USER [--privacy all] [--no-forks] [--no-archived]` | repositories a user owns |
| `gitrecon orgs USER` | organizations a user belongs to (all of them with the user's own token) |
| `gitrecon org-repos ORG [--no-forks] [--no-archived]` | repositories of an organization |
| `gitrecon repo-clone USER [PATH] [--depth 1] [--limit N] [--dry-run] [--update]` | clone a user's repositories into `PATH/<name>` (default `<forge>/USER/`) |
| `gitrecon org-clone ORG [PATH] [--depth 1] [--limit N] [--dry-run] [--update]` | clone an organization's repositories into `PATH/<name>` (default `<forge>/ORG/`) |

`<forge>` is the forge of the active BOS workshop - `~/__WORKSHOP/forge` - or `GITRECON_FORGE`.
A folder already there under the same name in another letter case is reused.
| `gitrecon links [ROOT] [--kind feed] [--save]` | harvest the [[link-catalog]] from gist clones |
| `gitrecon feeds [URL...] [--items] [--save]` | read [[news-feed]]s (default: from the catalog) |
| `gitrecon rfc [--search W...] [--number N] [--save]` | the [[rfc-index]] |
| `gitrecon blog [URL] [--dump] [--save]` | [[blog-article]]s as markdown |

## Look and conclude

| Command | Does |
| --- | --- |
| `gitrecon status` | what is in the raw buffer |
| `gitrecon map [--node KEY] [--full]` | the [[activity-graph]] |
| `gitrecon label [--name NAME] [--json\|--urls]` | [[label]]s with confidence and evidence |
| `gitrecon imports [PATH] [--format mermaid] [--level folder\|file] [--save]` | which file uses which inside a repository: hubs, cycles, libraries ([[captorlex]]) |
| `gitrecon relations FOLDER [--format mermaid] [--all] [--save]` | ties between an owner's cloned repositories: submodules, then dependencies |
| `gitrecon relations REPOSITORY [--offline]` | what one repository holds on to: fork parent, then dependencies by origin |
| `gitrecon contributors [PATH] [--format list\|authors\|pie] [--ignorelist [FILE]] [--save]` | who made a repository ([[contributor]]) |
| `gitrecon score [PATH] [--format tab\|abc\|midi] [--contributors-band-mode] [--ignorelist [FILE]] [--save]` | history as guitar tablature, ABC notation or MIDI ([[score]]) |
| `gitrecon openapi [--format yaml\|json]` | every command and task as one OpenAPI document ([[openapi]]) |
| `gitrecon commit-files [PATH] --single [--apply]` | one commit of everything, message written from the changed files (`task save`) |
| `gitrecon commit-files [PATH] [--handler NAME] [--limit N] [--apply]` | a commit per changed file, messages by a handler ([[commit-writer]]) |
| `gitrecon commits [PATH] [--list] [--max-commits N]` | commit messages as records: forms, types, kinds of work, labels ([[humanish]]) |
| `gitrecon text requirements URL\|FILE [--raw]` | sentences with MUST / SHOULD / MAY and their level |
| `gitrecon translate text\|languages\|install` | offline [[translation]] (Argos) |
| `gitrecon analyze [PATH...] [--deep] [--no-save] [--map-priv-repos] [--json\|--urls]` | languages, lines, names, frameworks of cloned repositories ([[code-analysis]]) |
| `gitrecon gitgraph [PATH] [--format mermaid] [--max-commits N] [--labels] [--save]` | history across all branches as a Mermaid gitGraph ([[git-graph]]) |
| `gitrecon network USER [--format mermaid\|dot] [--level owners\|repos] [--save]` | relations around a user: repositories, organizations, where forks come from ([[network]]) |

## The map dataset

| Command | Does |
| --- | --- |
| `gitrecon atlas pull` | download the [[atlas]] into `datasets/imperialmap` |
| `gitrecon atlas update [--stars USER] [--heavy] [--no-meta]` | write findings into it |
| `gitrecon atlas status` | files per [[area]] |
| `gitrecon atlas push -m MSG [--pr]` | publish (one commit, or a Hub pull request) |

## Content (on hold: TODO llm-interfaces)

| Command | Does |
| --- | --- |
| `gitrecon digest stars:USER\|labels\|links\|file:PATH` | a [[digest]] by a local model |
| `gitrecon posts DIGEST.md` | [[post-drafts]] |

## Text experiments

`gitrecon text toc|tokens|rat [URL]` - see [[rat-script]].
