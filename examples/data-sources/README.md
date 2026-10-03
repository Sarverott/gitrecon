# Data sources

Four chapters, one per source beyond the GitHub API:

| Chapter | Source | Main calls |
| --- | --- | --- |
| `01-gist-links.ipynb` | links in cloned gists | `harvest_gists()`, `expand_pattern()`, `save_catalog()` |
| `02-feeds.ipynb` | RSS / Atom / RDF feeds | `FeedReader().poll()`, `poll_many()`, `parse_feed()` |
| `03-rfc-index.ipynb` | RFC Editor index | `rfc_index.parse_index(fetch_index())` |
| `04-blog.ipynb` | blog articles | `article_links()`, `discover_feeds()`, `html_to_article()` |

Chapter 2 reads the catalog saved by chapter 1, so run them in order the first time.

```sh
task launch
task run
```
