"""Argos Translate: list languages, install language packages, translate - all on this machine.

    install("en", "pl")                       # downloads the model once (about 100 MB)
    translate("Hello world", "en", "pl")

Needs the ``translate`` extra (``uv sync --extra translate``). A package translates one
direction (``en`` -> ``pl``); between two languages without a direct package Argos goes
through English when both halves are installed. Packages live where Argos keeps them
(``~/.local/share/argos-translate``; ``ARGOS_PACKAGES_DIR`` moves them) - the same packages a
local LibreTranslate would use.
"""

from __future__ import annotations

import logging
from typing import Any


def _argos():
    try:
        import argostranslate.package
        import argostranslate.translate
    except ImportError as error:
        raise RuntimeError("translation needs the translate extra: uv sync --extra translate") from error
    logging.getLogger("argostranslate").setLevel(logging.WARNING)  # it reports every call at INFO
    logging.getLogger("argostranslate.utils").setLevel(logging.WARNING)
    logging.getLogger("stanza").setLevel(logging.ERROR)
    return argostranslate


def _package(p: Any) -> dict[str, Any]:
    return {"from": p.from_code, "from_name": p.from_name, "to": p.to_code, "to_name": p.to_name,
            "version": getattr(p, "package_version", None)}


def installed_packages() -> list[dict[str, Any]]:
    """Translation directions ready to use: ``{"from", "from_name", "to", "to_name", "version"}``."""
    packages = _argos().package.get_installed_packages()
    return sorted((_package(p) for p in packages), key=lambda p: (p["from"], p["to"]))


def installed_languages() -> list[dict[str, Any]]:
    """Languages at hand and what each can be translated into: ``{"code", "name", "to": [codes]}``."""
    languages = _argos().translate.get_installed_languages()
    listed = []
    for language in languages:
        targets = sorted(t.code for t in languages if t.code != language.code and language.get_translation(t))
        listed.append({"code": language.code, "name": language.name, "to": targets})
    return sorted(listed, key=lambda entry: entry["code"])


def available_packages(refresh: bool = True) -> list[dict[str, Any]]:
    """Every direction the Argos package index offers (``refresh``: download the index first)."""
    argos = _argos()
    if refresh:
        argos.package.update_package_index()
    return sorted((_package(p) for p in argos.package.get_available_packages()), key=lambda p: (p["from"], p["to"]))


def install(from_code: str, to_code: str, refresh: bool = True) -> dict[str, Any]:
    """Download and install the package ``from_code`` -> ``to_code``; a no-op when it is there.

    Returns the package with ``"status": "installed" | "exists"``. Raises ``LookupError`` when
    the index has no such direction.
    """
    argos = _argos()
    for package in argos.package.get_installed_packages():
        if (package.from_code, package.to_code) == (from_code, to_code):
            return _package(package) | {"status": "exists"}
    if refresh:
        argos.package.update_package_index()
    wanted = [p for p in argos.package.get_available_packages() if (p.from_code, p.to_code) == (from_code, to_code)]
    if not wanted:
        raise LookupError(f"Argos has no package {from_code} -> {to_code}; see the available ones "
                          "(often both languages have a package to and from English: install both halves)")
    argos.package.install_from_path(wanted[0].download())
    return _package(wanted[0]) | {"status": "installed"}


def translate(text: str, from_code: str, to_code: str) -> str:
    """``text`` translated ``from_code`` -> ``to_code``. ``LookupError`` when no installed path exists."""
    argos = _argos()
    languages = {language.code: language for language in argos.translate.get_installed_languages()}
    source, target = languages.get(from_code), languages.get(to_code)
    translation = source.get_translation(target) if source and target else None
    if translation is None:
        raise LookupError(f"no installed translation {from_code} -> {to_code}: "
                          f"gitrecon translate install {from_code} {to_code}")
    return translation.translate(text)
