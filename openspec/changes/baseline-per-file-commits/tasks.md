# Tasks

## 1. Behaviour (already implemented)

- [x] 1.1 List changed files with their status, including untracked files and index renames that were then removed
- [x] 1.2 Order changes by the import graph, then code, configuration, tests, prose
- [x] 1.3 Build and validate Conventional Commit messages from form answers
- [x] 1.4 Handler registry and context; fall back to the path handler with a note
- [x] 1.5 Apply a plan: one commit per file, whole-tree routines off, stop at the first refusal, never push
- [x] 1.6 `gitrecon commit-files` with `--handler`, `--limit`, `--apply`, `--json`; `task commit:files`

## 2. Verification

- [x] 2.1 Tests cover the scenarios of the spec except "a hook refuses the third commit" (`tests/test_committing.py`)
- [ ] 2.2 Add a test for the refused-commit scenario: a failing pre-commit hook in a throwaway repository; two commits exist, the third file is unstaged, exit status 1
- [x] 2.3 Documentation: glossary `commit-writer`, guide `committing-and-releasing`, `AGENTS.md`

## 3. Adoption

- [ ] 3.1 Review this spec against what you expect of the capability; correct the spec, not the code, where they differ on purpose
- [ ] 3.2 Archive the change so `openspec/specs/per-file-commits/spec.md` becomes the first main spec
