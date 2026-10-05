"""Reading the code of repositories: languages, lexical statistics, Python structure, frameworks.

Knowledge lives in ``resources/`` (``languages.yml``, ``frameworks.yml``, ``grammars/``), not
in the code: a new language or framework is a line there.
"""

from gitrecon.code.analyze import analyze_repo, find_repos

__all__ = ["analyze_repo", "find_repos"]
