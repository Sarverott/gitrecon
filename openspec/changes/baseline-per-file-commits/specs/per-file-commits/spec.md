# Spec Delta

## Purpose
Committing a working tree one file at a time: gitrecon plans a commit for every changed file, in an order where each commit stands on the ones before it, with messages written by a replaceable handler, and makes those commits only when asked.

## ADDED Requirements

### Requirement: A plan before any commit
The system SHALL, by default, only report what it would commit: every file that differs from the last commit (modified, new and untracked, deleted, renamed) with the message planned for it. It MUST NOT create commits, stage files or change the working tree unless applying is explicitly requested.

#### Scenario: Planning leaves the repository as it was
- **WHEN** the plan is requested for a repository with changed files
- **THEN** each changed file is listed once with its status and its planned message, and the commit history, the index and the working tree are unchanged

#### Scenario: Nothing to commit
- **WHEN** the plan is requested for a repository with no changes
- **THEN** the system says there is nothing to commit and exits successfully

#### Scenario: A file renamed in the index and then removed
- **WHEN** a file was renamed with git and the renamed file was then deleted from disk
- **THEN** the plan lists the original file as deleted, not a rename to a file that does not exist

### Requirement: Order of commits
The system SHALL order the plan so that a changed file imported by other changed files comes before them, including files git does not track yet. After that order, source code SHALL come before configuration, configuration before tests, and tests before prose; ties are settled by path.

#### Scenario: An imported file goes first
- **WHEN** a modified module and a new, untracked module that imports it are both changed
- **THEN** the modified module is planned before the new one

#### Scenario: Code, then tests, then prose
- **WHEN** a source file, a test file and a README are changed
- **THEN** they are planned in that order

### Requirement: Every message is a Conventional Commit
Every planned message SHALL be a valid Conventional Commit of this project: `type(scope): subject`, optional body and footer. The system MUST normalise an answer before using it - spaces in a scope become dashes, the subject starts in lower case, loses a trailing full stop and is cut to 72 characters - and MUST reject an answer whose type is not one the project allows.

#### Scenario: An answer is normalised
- **WHEN** an answer has scope "cli tools" and subject "Add the thing."
- **THEN** the message starts with `feat(cli-tools): add the thing` for type `feat`

#### Scenario: A breaking change
- **WHEN** an answer marks a breaking change
- **THEN** the message carries a `BREAKING CHANGE:` footer

#### Scenario: An unknown type
- **WHEN** an answer names a type outside the allowed list
- **THEN** the answer is rejected and is not used as a message

### Requirement: Messages come from a handler
The system SHALL obtain each message from a handler chosen by name. A handler MUST receive, for one file: what happened to it, the facts known about it (language, lines changed, which project files it uses and how many use it), its full diff on demand, the fields of the commit form with their allowed values, and its position in the plan. A handler answers the form or declines.

#### Scenario: A handler's answer becomes the message
- **WHEN** the chosen handler answers the form for a file
- **THEN** the plan shows the message built from that answer and names that handler as its author

#### Scenario: An unknown handler name
- **WHEN** a handler name that is not registered is requested
- **THEN** the command refuses to run and lists the available names

### Requirement: A plan is always complete
The system SHALL fall back to the plain path handler for a file whenever the chosen handler declines, fails, or answers something that does not make a valid message. The plan MUST record that the fallback wrote the message and why. One file's failure MUST NOT stop the planning of the others.

#### Scenario: The handler declines
- **WHEN** the chosen handler declines a file
- **THEN** that file gets the path handler's message, with a note that the chosen handler passed

#### Scenario: The handler fails
- **WHEN** the chosen handler raises an error for one file
- **THEN** that file gets the path handler's message with the error as a note, and the remaining files are still planned

### Requirement: The path handler
The system SHALL provide a handler that needs nothing but the file's path and status. Its type is `ci` for files under `.github/`, `test` for tests, `docs` for prose and documentation, `build` for manifests, lockfiles and container files, otherwise `chore`; its scope is the file's folder; its subject is `add`, `update`, `remove` or `rename` followed by the file name.

#### Scenario: A new test file
- **WHEN** `tests/test_core.py` is new
- **THEN** its message is `test(tests): add test_core.py`

#### Scenario: A modified README at the root
- **WHEN** `README.md` is modified
- **THEN** its message is `docs: update README.md`

### Requirement: Applying a plan
When applying is requested, the system SHALL create one commit per planned file, in plan order, each containing only that file. The repository's commit hooks SHALL run for every commit, but routines that act on the whole tree - staging everything, pushing - MUST be switched off for the series. The system MUST NOT push. Files outside the plan MUST stay as they were.

#### Scenario: One file per commit
- **WHEN** a plan of five files is applied
- **THEN** five commits exist, each touching exactly one file, in the plan's order, and nothing was pushed

#### Scenario: A file outside the plan
- **WHEN** a plan is applied while another changed file is not part of it
- **THEN** that file is still changed and uncommitted afterwards

### Requirement: Stopping at the first refused commit
If a commit of the series is refused (by a hook or by git), the system SHALL stop there, report the reason, leave the refused file changed but unstaged, leave every later file untouched, and exit with a failure status.

#### Scenario: A hook refuses the third commit
- **WHEN** the third commit of a plan is refused
- **THEN** two commits exist, the third file is changed and unstaged, the rest of the plan is not attempted, and the exit status reports failure

### Requirement: The plan as data
The system SHALL offer the plan, and the result of applying it, as JSON on standard output with notes and progress kept off it: per file the path, status, previous path of a rename, message, the handler that wrote it, its answers and the facts; after applying also whether it was committed, the commit's short hash, and the error if any.

#### Scenario: JSON output of a plan
- **WHEN** the plan is requested in JSON
- **THEN** standard output is one JSON list with an entry per file and nothing else
