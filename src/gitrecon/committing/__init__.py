"""Committing changes one file at a time, with the messages left to a handler.

- ``changes``  - what differs from the last commit, the facts about each file, the order
- ``form``     - the commit form (commitizen's) and the message built from its answers
- ``handlers`` - who answers the form: the registry, the context a handler gets, the plain ``path`` handler
- ``plan``     - the plan of commits, and carrying it out
"""

from gitrecon.committing.changes import Change, changed_files, file_diff, file_facts, order_changes
from gitrecon.committing.form import build_message, commit_types, form_fields
from gitrecon.committing.handlers import HANDLERS, ChangeContext, Handler, path_handler, register
from gitrecon.committing.plan import apply_plan, plan_commits, save, save_message

__all__ = ["HANDLERS", "Change", "ChangeContext", "Handler", "apply_plan", "build_message", "changed_files",
           "commit_types", "file_diff", "file_facts", "form_fields", "order_changes", "path_handler", "plan_commits",
           "register", "save", "save_message"]
