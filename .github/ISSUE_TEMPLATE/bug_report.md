---
name: Bug report
about: A command failed, printed something wrong, or the docs do not match what happens
title: ''
labels: bug
assignees: ''

---

**What happened**
A clear description of what went wrong.

**The command**
The exact command, and its output or the error (add `-v` for the log):

```sh
gitrecon ...
```

> Remove tokens, private repository names and anything else you would not publish before pasting.

**What you expected**
What should have happened instead.

**Environment**
 - gitrecon version (`gitrecon status` or `pyproject.toml`):
 - installed with: [uv in a clone / Docker image / other]
 - extras installed: [none / hub / llm / net / code / translate / all]
 - OS and Python version:
 - with a GitHub token: [yes, classic / yes, fine-grained / no]

**Additional context**
Anything else: the repository or user the command was pointed at (if public), how often it happens.
