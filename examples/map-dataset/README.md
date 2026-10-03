# The map dataset

The map is the Hugging Face dataset **Apokryf/minimap-of-uce**, kept locally in
`datasets/imperialmap`.

| Chapter | Does |
| --- | --- |
| `01-dataset.ipynb` | `MapDataset(...)`: pull when missing, list areas, `ensure_area()`, login |
| `02-findings.ipynb` | `AtlasUpdate`: links → dnstrees/host-unions, GitHub `/meta` → ip-address-records; `UserNamespace`: identities; reindex |
| `03-push.ipynb` | `dataset.push(...)`, only with `PUSH = True`; what is on the Hub |

Chapter 2 writes into your local copy of the map, and writing is idempotent.
Chapter 3 publishes to a public dataset, so review the changes first.

```sh
task launch
task run       # safe: 03-push does not push unless PUSH = True
```

The CLI equivalent of all three: `task map:refresh` then `task map:push -- -m "..."`.
