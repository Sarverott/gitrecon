# Atlas (the map dataset)

> The shared map of identified areas, published as the Hugging Face dataset Apokryf/minimap-of-uce.

## What it is

Kept locally in `datasets/imperialmap` (git-ignored), pulled and pushed with `MapDataset`. gitrecon writes its findings into the map deterministically: sorted, only when content differs - re-running an update without new findings changes nothing.

## Where

`gitrecon.hub.huggingface.MapDataset`, `gitrecon.atlas` (`AtlasUpdate`, `paths`, `namespace`). CLI: `gitrecon atlas pull|status|update|push`; `task map:refresh`, `task map:push`; example `examples/map-dataset/`. Credentials: `HF_TOKEN`.

## Relations

Made of [[area]]s: [[dnstree]]s, [[ip-address-record]]s, [[host-union]]s, the [[user-namespace]].
