# PeekerLex

> The quick, light reading of code: enough to know what a repository is made of.

## What it is

The lexical layer of [[code-analysis]]. One Lark grammar per language *family*
(`resources/grammars/lexical/`) tells comments, strings, numbers and names apart; everything
else is an `OTHER` token, so it reads any language without failing and without knowing its
syntax. Together with the file-name tables and the dependency manifests it answers: which
languages, how much code and comment, which names and links, which frameworks.

It does **not** know what a function, a class or a call is - that is [[captorlex]].

## Where

`gitrecon.code.lexical` (lexer), `gitrecon.code.languages`, `gitrecon.code.frameworks`;
`gitrecon analyze`. Fast: a few hundred files per second.

## Relations

The first of two depths of reading; [[captorlex]] is the second.
