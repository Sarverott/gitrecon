# Grammars

Lark grammars gitrecon reads at run time (`gitrecon.config.resources_dir()`).

- `json.lark` - JSON as a parse tree (`gitrecon.text.jsonlark`).
- `lexical/*.lark` - **lexical patterns of language families**: what a comment, a string, a
  number and a name look like. One grammar serves every language of its family; which
  language belongs to which family is in `../languages.yml`. They are used with Lark's lexer
  only (`gitrecon.code.lexical`), so they never fail on unfamiliar syntax: whatever is not
  recognised is an `OTHER` token.

A new family = a new `lexical/<family>.lark` with the terminals `COMMENT`, `STRING`, `NUMBER`,
`NAME`, `OTHER`, and a `families:` entry in `languages.yml`.
