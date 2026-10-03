# Using gitrecon from other programs

gitrecon is built to feed other things: scripts, data submodules, GUIs, web servers and
frontend apps. Every listing command speaks three [[output-mode|output modes]].

## On the command line

| Flag | stdout holds | Use it for |
| --- | --- | --- |
| *(none)* | readable text and a summary | people |
| `--json` | only JSON: a list for listings, an object for single results | programs, `jq`, APIs |
| `--urls` | only web addresses, one per line, deduplicated | browsers, link lists, crawlers |

In both machine modes, notes, progress and summaries go to **stderr**, so stdout can be piped
straight into another program. `--json` and `--urls` exclude each other.

```sh
gitrecon stars sarverott --urls                       # every starred repository's address
gitrecon stars sarverott --json | jq '.[] | select(.language == "Rust") | .repo'
gitrecon label --name star-burst --urls               # pages of repos with a star burst
gitrecon map --node org:github --json                 # neighbours with relation, key, url
gitrecon rfc --search quic --json > quic-rfcs.json
gitrecon events org:github --watch --json | my-consumer   # JSON Lines, one event per line, live
```

`--limit` of `label` only trims the readable list; machine modes always hand over everything.

## Which command gives what

| Command | `--json` | `--urls` |
| --- | --- | --- |
| `stars USER` | `[{user, repo, url, starred_at, language, stars, description, topics}]` | repositories |
| `gists` | `[gist]` with `files`, `owner`, `url` | gists |
| `gist-catalog USER` | `[{gistID, filelist, description, stars, comments, forks, commits, size, public, created_at, url}]` | gists |
| `gist-clone USER PATH` | `[{gistID, path, status, error}]` (status: cloned, exists, updated, failed) | gists |
| `events` | JSON Lines: `{id, type, action, actor, repo, org, created_at, url, payload}` | repositories of the events |
| `archive` | `[{hour, source, path, bytes}]` | archive files on gharchive.org |
| `links` | `[{url, kind, domain, found_in}]` | the links |
| `feeds` | `{feeds: [{url, new, error}], items: [item]}` | item links |
| `rfc` | `[rfc]` with relations and `url` | rfc-editor.org pages |
| `blog` | `[article]` with `markdown` | articles |
| `map` | summary `{nodes, edges, relations, hubs: [{key, degree, url}]}`; `--node`: `[{relation, key, url}]`; `--full`: `{nodes, edges}` | hubs / neighbours / every node |
| `label` | `[{name, target, confidence, evidence, details, url}]` | labeled entities |
| `status` | `{data_dir, datasets_dir, token, sources}` | - |
| `atlas ACTION` | `{repo, url, path, areas}` / `{root, changed}` / `{commit}` | dataset page / commit |
| `digest`, `posts`, `text` | the result as an object | - |

Item objects are exactly what the models' `to_json()` returns.

## From Python

The same shapes without the CLI - every model has `html_url` and `to_json()`:

```python
from gitrecon.sources import stars
from gitrecon.sources.github_api import GitHubClient

found = stars.starred(GitHubClient(), "sarverott")
urls = [star.html_url for star in found]
payload = [star.to_json() for star in found]   # ready for json.dumps, a template or an API response
```

`gitrecon.models.base.url_for_key("repo:owner/name")` turns any [[entity]] key into its page.

## In a web server

```python
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from gitrecon.sources import stars
from gitrecon.sources.github_api import GitHubClient

client = GitHubClient()

class Stars(BaseHTTPRequestHandler):
    def do_GET(self):  # GET /sarverott -> that user's stars as JSON
        body = json.dumps([s.to_json() for s in stars.starred(client, self.path.strip("/"))]).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

HTTPServer(("127.0.0.1", 8080), Stars).serve_forever()
```

## In a container or as a submodule

- Container: `task docker:run -- stars sarverott --json` (or `docker compose run --rm gitrecon ...`);
  stdout stays clean JSON, notes go to stderr.
- Another repository can vendor gitrecon as a git submodule and install it from there
  (`uv add ./vendor/gitrecon`, or `uv add './vendor/gitrecon[hub]'` for the map commands), then
  either import it or call the `gitrecon` command and parse `--json`.
