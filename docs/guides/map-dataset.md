# Working with the map dataset

The [[atlas]] is the Hugging Face dataset **Apokryf/minimap-of-uce**, kept locally in
`datasets/imperialmap`.

## Refresh and publish

```sh
task map:refresh                         # pull (if needed), harvest gist links, update
gitrecon atlas update --stars sarverott  # also: owners of starred repos -> user-namespace
gitrecon atlas status
task map:push -- -m "dnstrees from new gists"        # or --pr for a Hub pull request
```

The whole flow from Python, chapter by chapter: `examples/map-dataset/`.

## What gets written

| Area | From | Path scheme |
| --- | --- | --- |
| [[dnstree]]s | [[link-catalog]] | `dnstrees/com/github/api/.holders.yml` |
| [[ip-address-record]]s | GitHub `/meta` | `ip-address-records/v4/8C/52/70/0/.index.json` |
| [[host-union]]s | both | `host-unions/<union>/.index.json` |
| [[user-namespace]] | stars, gist links | `user-namespace/NS/u8e/g6-3m/<md5>.json` + `index.json` |
| every area | - | `<area>/.index.json` (recursive listing) |

Writes are deterministic: a second update without new findings changes nothing, so a
push carries only real changes.

## Before pushing

The dataset is public. Look at what changed (`gitrecon atlas update` lists the files),
keep edits made by hand (pulling over them would overwrite them - `pull` only when you
mean it), and prefer `--pr` for bigger changes.
