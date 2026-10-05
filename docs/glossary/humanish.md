# Humanish

> Human text read by grammar: sentences that follow rules become records.

## What it is

Three levels, from sure to ambitious; gitrecon has the first:

1. **controlled sentences** *(built)* - text that already follows rules:
   - commit messages: `type(scope)!: subject`, git's merge and revert sentences, trailers
     (`BREAKING CHANGE: ...`, `Co-Authored-By: ...`) -> form, type, scope, kind of work,
     breaking mark; from many commits the labels `conventional-commits`, `fix-heavy`,
     `release-automation`, `breaking-changes`;
   - requirement keywords of normative text (RFC 2119 / 8174: MUST, SHOULD, MAY ... in
     capitals; a keyword in quotes is a mention) -> each sentence holding one, with its level:
     obligation, prohibition, recommendation, discouragement, permission;
2. **normative text** *(not built; other projects)* - who + modality + action + condition +
   reference, as in statutes;
3. **free text** *(not built)* - read by language models, checked by the grammars below it.

## Where

Grammars: `resources/grammars/humanish/` (`commit.lark`, `rfc2119.lark`); meanings and
thresholds: `resources/humanish.yml`. Code: `gitrecon.humanish` (`commits`, `requirements`).
CLI: `gitrecon commits [PATH]`, `gitrecon text requirements URL|FILE [--raw]`. The
[[label]]er reads commit messages of pushes in the raw buffer where events carry them.

## Relations

The same method as [[peekerlex]] - tokens, a grammar in `resources/`, records - applied to
sentences; its token side is the word-chain tokenizer and the a12y glossary (`gitrecon.text`).
