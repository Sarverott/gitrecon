# llms

Configuration for language-model tooling. gitrecon keeps the files; it does not run a model
server, pull models, or start agents.

- `litellm.yaml` - LiteLLM proxy: which model answers to which name (`local-writer`,
  `local-reader`, `local-embed`, `ollama/<model>`, `grok`). How to run it is in its header.
