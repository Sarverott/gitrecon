"""PARKED (2026-10-05): local language models.

``ollama.py`` (the interface) and ``commit_handler.py`` (commit messages written by a model)
are kept commented out; nothing in gitrecon uses them. Committing per file lives in
``gitrecon.committing`` and takes handlers. The digest's own small HTTP client
(``gitrecon.digest.llm``) is a different, older thing and is untouched.
"""

# from gitrecon.llm.ollama import Ollama, find_host
#
# __all__ = ["Ollama", "find_host"]
