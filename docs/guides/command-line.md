# Command line

`gitrecon <command> --help` describes every option. Grouped by what they do.

**For programs:** most commands take `--json` (only data on stdout) and `--urls` (only web
addresses, one per line) - see [[integration]] for the shapes. Example:
`gitrecon stars sarverott --urls`.

## Collect

| Command | Does |
| --- | --- |
| `gitrecon events [public\|user:X\|org:X\|repo:O/N] [--watch]` | poll an [[events-feed]] into the [[raw-buffer]] |
| `gitrecon archive 2026-10-01-0 [2026-10-01-23]` | download [[gh-archive]] hours |
| `gitrecon gists [--user X]` | newest public gists, or one user's |
| `gitrecon stars USER [--json] [--save]` | repositories a user has starred ([[star]]) |
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
