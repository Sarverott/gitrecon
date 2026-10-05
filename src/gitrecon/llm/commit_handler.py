"""PARKED (2026-10-05): the model-backed commit handler. Nothing imports this module.

What used to be the model half of the commit writer: the prompts, the form as a pydantic
model, the reader's notes, and the function that asked the model(s). Kept commented out.
The working half moved to ``gitrecon.committing``; a new handler there has this signature:

    @register("name")
    def handler(context: ChangeContext) -> dict | None: ...
"""

# SYSTEM = """You write git commit messages in the Conventional Commits form, one changed file at a time.
# Fields:
# - prefix: the type of change. feat = a new capability; fix = a defect repaired; docs = documentation only;
#   style = formatting only; refactor = restructured without new behaviour; perf = faster; test = tests only;
#   build = build system or dependencies; ci = CI configuration; chore = housekeeping.
# - scope: one short word for the part of the project touched (a folder or module name), no spaces; may be empty.
# - subject: an imperative summary of WHAT changed in this file, lower case, no full stop, at most 60 characters.
# - body: one or two sentences on WHY, or empty.
# - is_breaking_change: true only when users of the code must change something.
# - footer: empty unless an issue is referenced.
# Describe only what the diff shows. Do not invent."""
#
# def commit_form() -> type:
#     """The pydantic model of commitizen's commit form (built on demand: pydantic comes with the llm extra)."""
#     from typing import Literal
#
#     from pydantic import BaseModel, Field
#
#     kinds = tuple(dict.fromkeys(commit_types()))
#
#     class CommitForm(BaseModel):
#         prefix: Literal[kinds]  # type: ignore[valid-type]
#         scope: str = Field(default="", description="one word, no spaces; may be empty")
#         subject: str = Field(description="imperative, lower case, no full stop, at most 60 characters")
#         body: str = ""
#         is_breaking_change: bool = False
#         footer: str = ""
#
#     return CommitForm
#
# def _facts_text(facts: dict[str, Any]) -> str:
#     lines = [f"File: {facts['path']}", f"What happened: {facts['status']}"]
#     if facts.get("language"):
#         lines.append(f"Language: {facts['language']} ({facts['kind']})")
#     if "lines_added" in facts:
#         lines.append(f"Lines: +{facts['lines_added']} -{facts.get('lines_deleted', 0)}")
#     if facts.get("imports"):
#         lines.append("It uses these files of the project: " + ", ".join(facts["imports"]))
#     if facts.get("used_by"):
#         lines.append(f"It is used by {facts['used_by']} file(s) of the project, e.g. " + ", ".join(facts["used_by_examples"]))
#     return "\n".join(lines)
#
#
# READER_SYSTEM = """You read one changed file of a software project and take notes for the person who will write
# its commit message. Say only what the facts and the diff show.
# - summary: one sentence - what this change does.
# - changes: the separate things that changed, each a short phrase (at most five).
# - kind: the type of change (feat = new capability, fix = defect repaired, docs, style, refactor, perf, test,
#   build, ci, chore).
# - reason: why the change was made, if the diff shows it; else empty."""
#
#
# def change_notes() -> type:
#     """The shape of the reader's notes (a pydantic model)."""
#     from typing import Literal
#
#     from pydantic import BaseModel
#
#     kinds = tuple(dict.fromkeys(commit_types()))
#
#     class ChangeNotes(BaseModel):
#         summary: str
#         changes: list[str] = []
#         kind: Literal[kinds]  # type: ignore[valid-type]
#         reason: str = ""
#
#     return ChangeNotes
#
# def write_message(repo: str | Path, change: Change, llm: Any, model: str | None = None, reader: str | None = None,
#                   graph: dict[str, Any] | None = None) -> dict[str, Any]:
#     """``{"path", "status", "message", "by", "answers", "facts", "notes"}`` for one file.
#
#     ``by`` is the model that wrote the message, or ``fallback``. With ``reader`` (a model name)
#     that model reads the facts and the diff first; the writer works from its notes.
#     """
#     hint = fallback_answers(change)
#     facts = file_facts(repo, change, graph)
#     known = (_facts_text(facts) + (f"\nIt was called: {change.old_path}" if change.old_path else "")
#              # "chore" is only the fallback's shrug: saying it would talk the model out of feat and fix
#              + (f"\nJudging by where the file lives, the type is probably: {hint['prefix']}" if hint["prefix"] != "chore" else "")
#              + (f"\nA likely scope: {hint['scope']}" if hint["scope"] else ""))
#     diff = file_diff(repo, change)
#     room = {"num_predict": 1500}  # room for a reasoning model that thinks whatever it is told
#     notes = None
#     if reader:
#         try:
#             notes = llm.structured(change_notes(), f"{known}\n\nThe change:\n{diff}", model=reader,
#                                    system=READER_SYSTEM, options=room).model_dump()
#         except Exception:  # noqa: BLE001 - without notes the writer reads the diff itself
#             notes = None
#     if notes:
#         listed = "\n".join(f"- {item}" for item in notes["changes"])
#         prompt = (f"{known}\n\nNotes of a reader who studied the change:\nSummary: {notes['summary']}\n"
#                   f"Changes:\n{listed}\nKind, as the reader sees it: {notes['kind']}\nReason: {notes['reason'] or '(not shown)'}"
#                   f"\n\nThe beginning of the change itself:\n{diff[:1200]}")
#     else:
#         prompt = f"{known}\n\nThe change:\n{diff}"
#     try:
#         form = llm.structured(commit_form(), prompt, model=model, system=SYSTEM, options=room)
#         answers = form.model_dump()
#         message, by = build_message(answers), model or llm.model
#     except Exception as error:  # noqa: BLE001 - a model that fails must not stop the commit plan
#         answers, by = hint | {"note": str(error)[:200]}, "fallback"
#         message = build_message(hint)
#     return {"path": change.path, "status": change.status, "old_path": change.old_path, "message": message, "by": by,
#             "answers": answers, "facts": facts, "notes": notes}
