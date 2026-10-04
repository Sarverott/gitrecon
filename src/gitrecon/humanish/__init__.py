"""Humanish, level 1: controlled sentences read with grammars from ``resources/grammars/humanish``.

Text that already follows rules - commit messages, requirement keywords of normative
documents - becomes records, by grammar rather than by guess. The method (tokens -> grammar
in ``resources/`` -> records) is the same PeekerLex uses for code.
"""

from gitrecon.humanish.commits import ParsedCommit, commit_labels, parse_commit, read_commits, summarize_commits
from gitrecon.humanish.requirements import Requirement, find_requirements

__all__ = ["ParsedCommit", "Requirement", "commit_labels", "find_requirements", "parse_commit", "read_commits",
           "summarize_commits"]
