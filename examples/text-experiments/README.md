# Text experiments

The project's first experiments (formerly `docs/tests-with-md-parsing-and-rattish-implementations.ipynb`)
on top of `gitrecon.text`:

- markdown → HTML → text (`gitrecon.text.markdown`), shown inline
- word-chains: symbols spelled as tokens, English (legacy) and Polish tables
- `a12y` numeronyms with a collision `Glossary`
- RAT scripts (`build_rat`), byte-identical to the original notebook
- a JSON grammar in Lark, and a README's table of contents

```sh
task launch
task run
```
