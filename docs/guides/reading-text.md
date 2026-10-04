# Reading text

Human text that follows rules, read by grammar ([[humanish]]), and offline [[translation]].

## Commit messages

```sh
gitrecon commits                      # the repository you are in
gitrecon commits PATH --list          # also every commit: form, type, subject
gitrecon commits PATH --json
```

Every commit of every branch is read as one of four forms - `conventional`
(`type(scope)!: subject`), `merge`, `revert`, `plain` - and the summary says how much of the
work was features, fixes, upkeep, delivery or documentation. Labels concluded:

| Label | When (thresholds in `resources/humanish.yml`) |
| --- | --- |
| `conventional-commits` | at least 80% of own (non-merge) commits follow the form |
| `fix-heavy` | at least half of the conventional commits are fixes or reverts |
| `release-automation` | at least 3 `bump:` commits |
| `breaking-changes` | any commit marked `!` or carrying `BREAKING CHANGE:` |

No conclusion from fewer than 10 own commits. `gitrecon label` concludes the same from pushes
in the raw buffer, where the events carry commit messages (GH Archive hours do).

## Requirement sentences

```sh
gitrecon text requirements https://www.rfc-editor.org/rfc/rfc9110.txt --raw
gitrecon text requirements docs/some-spec.md --json
```

Lists every sentence holding MUST, MUST NOT, SHALL, SHOULD, SHOULD NOT, RECOMMENDED, NOT
RECOMMENDED, MAY, REQUIRED or OPTIONAL in capitals, with its level. `--raw` for plain text;
without it the input is taken as markdown.

## Translation

```sh
uv sync --extra translate                         # once (task install brings every extra)
gitrecon translate languages --available          # what Argos offers
gitrecon translate install en pl                  # download one direction (about 100 MB)
gitrecon translate languages                      # what is installed
gitrecon translate text --from en --to pl "A client MUST send the header."
cat notes.txt | gitrecon translate text --from en --to pl -
```

> **Remember!** Language packages are kept by Argos in `~/.local/share/argos-translate`
> (`ARGOS_PACKAGES_DIR` moves them), not in gitrecon's data folder.

## Teaching it more

| To add | Edit |
| --- | --- |
| a commit type and what work it is | `resources/humanish.yml` -> `commit_types:` |
| label thresholds | `resources/humanish.yml` -> `commit_labels:` |
| another commit sentence | `resources/grammars/humanish/commit.lark` |
| requirement keywords | `resources/grammars/humanish/rfc2119.lark` + `requirement_levels:` |
