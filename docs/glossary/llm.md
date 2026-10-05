# LLM interface

> Local language models through Ollama: plain answers, answers in a given shape, embeddings.

## What it is

One object, `gitrecon.llm.Ollama`:

- `chat(prompt)` - a plain answer;
- `structured(Shape, prompt)` - the answer as a filled-in pydantic model: the server gets the
  model's JSON schema and may only answer in it; an answer that does not validate is asked
  for again;
- `embed(texts)` - vectors, for a vector database;
- `models()`, `pull(name)` - what the server has, and getting more.

Where the server is: `OLLAMA_HOST`, else whichever answers of `localhost:11434` (a host
install) and `localhost:11435` (the `ollama` service of [[services]]). Which model:
`--model`, else `OLLAMA_MODEL`, else the server's first.

## Where

`gitrecon.llm.ollama`; needs the `llm` extra. CLI: `gitrecon llm models | pull MODEL | ask
WORDS...`. Built on it: [[commit-writer]].

## Relations

The digest keeps its own small HTTP client (`gitrecon.digest.llm`) and finds the server the
same way. Step 3 of [[captorlex]] (meaning) will stand on this.
