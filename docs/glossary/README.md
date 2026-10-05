# gitrecon glossary

> One page per element of gitrecon. Links between pages use Obsidian `[[wikilinks]]`;
> the site turns them into normal links.

## The pipeline

```
collect ──► raw buffer ──► activity graph ──► labels
   │            (append-only)                    │
   │                                             ▼
   ├──► link catalog ──► atlas (the map dataset on Hugging Face)
   └──► digest (local model) ──► post drafts
```

## Collecting

| Element | One line |
| --- | --- |
| [Event](event.md) | One thing that happened on GitHub: a push, a star, a fork, an issue... |
| [Events feed](events-feed.md) | An Events API endpoint gitrecon listens to: public, a user, an organization or a repository. |
| [GH Archive](gh-archive.md) | Every public GitHub event since 2011, one gzip file per hour (gharchive.org). |
| [Star](star.md) | One user starring one repository, at a known time. |
| [Gist](gist.md) | A GitHub gist: files, owner, description - and, for gitrecon, a notebook full of links. |
| [Link catalog](link-catalog.md) | Every URL found in cloned gists, classified by what it can feed. |
| [News feed](news-feed.md) | An RSS 2.0, Atom or RDF feed - blogs, changelogs, advisories, releases, exploit lists. |
| [RFC index](rfc-index.md) | The RFC Editor's list of every Request for Comments, parsed into records. |
| [Blog article](blog-article.md) | An article of a blog, captured as markdown with checksums. |

## Storing

| Element | One line |
| --- | --- |
| [Raw buffer](raw-buffer.md) | Append-only store of everything collected: gzip JSONL partitioned by source and UTC hour. |

## Recognizing

| Element | One line |
| --- | --- |
| [Entity](entity.md) | Anything gitrecon can map, with a kind and a stable key. |
| [Code analysis](code-analysis.md) | What a cloned repository is made of: languages, code and comment lines, names, links, Python structure, frameworks. |
| [PeekerLex](peekerlex.md) | The quick, light reading of code: enough to know what a repository is made of. |
| [CaptorLex](captorlex.md) | The deep reading of code: structure first, then meaning, reasoning and sense. *Steps 1 and 2 (one repository, one owner) built.* |
| [Commit writer](commit-writer.md) | A commit per changed file; who writes the messages is a handler. |
| [LLM interface](llm.md) | *Parked.* An interface to local language models through Ollama - tried, set aside. |
| [Humanish](humanish.md) | Human text read by grammar: sentences that follow rules become records. |
| [Translation](translation.md) | Offline translation with Argos Translate, the engine inside LibreTranslate. |
| [Score](score.md) | A repository's history as music: guitar tablature, ABC notation, a MIDI file. |
| [Contributor](contributor.md) | Who made a repository, read from its git log. |
| [Git graph](git-graph.md) | A repository's history across all branches, drawn as a Mermaid `gitGraph`. |
| [Network](network.md) | Repositories, users and organizations around one user, as a graph of relations. |
| [Activity graph](activity-graph.md) | Who touches what: entities as nodes, observed relations as edges with evidence. |
| [Label](label.md) | A conclusion about an entity: what is happening, how sure, and why. |
| [Labeler](labeler.md) | Groups activity per entity and runs every rule over it. |
| [Rule](rule.md) | One function that may conclude one label about one entity. |
| [Threshold](threshold.md) | The numbers a rule compares against, including the time window. |

## The map

| Element | One line |
| --- | --- |
| [Atlas (the map dataset)](atlas.md) | The shared map of identified areas, published as the Hugging Face dataset Apokryf/minimap-of-uce. |
| [Area](area.md) | A top-level folder of the map with one kind of data and its own path scheme. |
| [DNS tree](dnstree.md) | Domains as a reversed directory tree: `www.example.com` -> `dnstrees/com/example/www`. |
| [IP address record](ip-address-record.md) | A network at the path of its address: `140.82.112.0/20` -> `ip-address-records/v4/8C/52/70/0`. |
| [Host union](host-union.md) | Relations between URLs, domains, IPs and services, grouped by where they came from. |
| [User namespace](user-namespace.md) | Usernames across platforms, grouped by numeronym paths. |
| [Identity](identity.md) | One account, profile or address of someone on one platform. |

## Text

| Element | One line |
| --- | --- |
| [a12y numeronym](a12y.md) | A word shortened to first letter, length, last letter: `workflows` -> `w9s`. |
| [Word-chain](word-chain.md) | A sentence as tokens, with every symbol spelled out as an uppercase word. |
| [RAT script](rat-script.md) | A "rattish" script: a glossary section of numeronyms plus a section rebuilding the sentences. |

## Content

| Element | One line |
| --- | --- |
| [Digest](digest.md) | A summary of any amount of collected data, made by a local model. |
| [Post drafts](post-drafts.md) | An SEO article and social posts written from a digest - drafts, never published by gitrecon. |

## Interfaces

| Element | One line |
| --- | --- |
| [Menu](menu.md) | The full-screen, arrow-driven way to run gitrecon: commands, tasks, examples, manuals, status. |
| [Output mode](output-mode.md) | How a command prints: readable text, `--json` for programs, or `--urls` for addresses. |

## Environment

| Element | One line |
| --- | --- |
| [Gateway](gateway.md) | Traefik as the only way in: every web service is `<name>.gr.rs-tech.online`, nothing else publishes a port. |
| [Services](services.md) | The environment around gitrecon: docker compose services in five groups, started with their dependencies. |

## Delivery

| Element | One line |
| --- | --- |
| [Craft loop](craft-loop.md) | The branch loop every change travels: development -> revision -> testing -> releasing -> master. |
| [Metadata sync](metadata-sync.md) | One place for the project's name, version, description, authors and tags: `metadata.json`. |
| [Routine](routine.md) | A step done the same way around every commit, switched on in `.husky/bos.config.json`. |
