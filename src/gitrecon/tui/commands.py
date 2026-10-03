"""gitrecon's own commands as forms: read from the argparse parser, turned back into argv.

Nothing here is written twice: every option, default, choice and help text comes from
``gitrecon.cli.build_parser()``, so a new command or flag shows up in the menu by itself.
"""

from __future__ import annotations

import argparse
import shlex
from dataclasses import dataclass, field
from typing import Any

MODES = ("text", "json", "urls")
OUTPUT_DESTS = {"json", "urls"}
HIDDEN = {"menu"}  # the menu does not offer itself


@dataclass
class Option:
    dest: str
    flag: str | None  # None for positionals
    help: str = ""
    kind: str = "value"  # value | flag | int | choice | list
    required: bool = False
    default: Any = None
    choices: list[str] = field(default_factory=list)
    repeat: bool = False  # --kind a --kind b (append) instead of --search a b (nargs)

    @property
    def positional(self) -> bool:
        return self.flag is None

    @property
    def label(self) -> str:
        return self.flag or self.dest


@dataclass
class CommandSpec:
    name: str
    help: str = ""
    section: str = ""
    options: list[Option] = field(default_factory=list)
    modes: list[str] = field(default_factory=lambda: ["text"])

    @property
    def positionals(self) -> list[Option]:
        return [o for o in self.options if o.positional]

    @property
    def optionals(self) -> list[Option]:
        return [o for o in self.options if not o.positional]

    def argv(self, answers: dict[str, Any], mode: str = "text") -> list[str]:
        """Answers by ``dest`` -> the arguments after ``gitrecon``."""
        argv = [self.name]
        for option in self.positionals:
            value = answers.get(option.dest)
            if option.kind == "list":
                argv += _as_list(value)
            elif value not in (None, ""):
                argv.append(str(value))
        for option in self.optionals:
            value = answers.get(option.dest)
            if option.kind == "flag":
                if value:
                    argv.append(option.flag)
            elif option.kind == "list":
                values = _as_list(value)
                if values and option.repeat:
                    for item in values:
                        argv += [option.flag, item]
                elif values:
                    argv += [option.flag, *values]
            elif value not in (None, "") and value != option.default:  # defaults need no flag
                argv += [option.flag, str(value)]
        if mode in ("json", "urls"):
            argv.append(f"--{mode}")
        return argv

    def line(self, answers: dict[str, Any], mode: str = "text") -> str:
        return "gitrecon " + shlex.join(self.argv(answers, mode))


def _as_list(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value]
    return shlex.split(str(value))


def _option(action: argparse.Action) -> Option:
    flag = max(action.option_strings, key=len) if action.option_strings else None
    option = Option(dest=action.dest, flag=flag, help=action.help or "", default=action.default,
                    required=bool(action.required) or (flag is None and action.nargs is None))
    if isinstance(action, (argparse._StoreTrueAction, argparse._StoreFalseAction)):
        option.kind = "flag"
    elif isinstance(action, argparse._AppendAction):
        option.kind, option.repeat = "list", True
    elif action.nargs in ("*", "+"):
        option.kind = "list"
        option.required = flag is None and action.nargs == "+"
    elif action.choices:
        option.kind, option.choices = "choice", [str(c) for c in action.choices]
    elif action.type is int:
        option.kind = "int"
    if option.kind == "flag":
        option.default = bool(action.default)
    return option


def section_of(parser: argparse.ArgumentParser) -> str:
    func = parser.get_default("func")
    return func.__module__.rsplit(".", 1)[-1] if func else ""


def discover(parser: argparse.ArgumentParser | None = None) -> list[CommandSpec]:
    if parser is None:
        from gitrecon.cli import build_parser

        parser = build_parser()
    sub = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    helps = {choice.dest: choice.help or "" for choice in sub._choices_actions}
    specs = []
    for name, command in sub.choices.items():
        if name in HIDDEN:
            continue
        spec = CommandSpec(name=name, help=helps.get(name, ""), section=section_of(command))
        for action in command._actions:
            if isinstance(action, argparse._HelpAction):
                continue
            if action.dest in OUTPUT_DESTS:
                spec.modes.append(action.dest)
                continue
            spec.options.append(_option(action))
        specs.append(spec)
    return specs
