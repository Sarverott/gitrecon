"""Reading code: resources (grammars, tables), lexer, Python AST, frameworks, whole repositories."""

import json
from pathlib import Path

import pytest
import yaml

from gitrecon.code import analyze_repo, find_repos, frameworks, lexical, pyast
from gitrecon.code.languages import detect, families
from gitrecon.config import resource, resources_dir
from gitrecon.main import main

# --- resources -----------------------------------------------------------------------


def test_every_family_has_a_grammar_with_the_five_terminals():
    table = yaml.safe_load(resource("languages.yml").read_text())
    used = {spec["family"] for spec in table["languages"].values() if spec.get("family")}
    assert used == set(table["families"]) == set(families())
    for family in used:
        names = {t.name for t in lexical.lexer(family).terminals}
        assert {"COMMENT", "STRING", "NUMBER", "NAME", "OTHER"} <= names, family
    on_disk = {p.stem for p in (resources_dir() / "grammars" / "lexical").glob("*.lark")}
    assert on_disk == used  # no grammar without a language, no language without a grammar


def test_extensions_belong_to_one_language():
    table = yaml.safe_load(resource("languages.yml").read_text())
    seen: dict[str, str] = {}
    for name, spec in table["languages"].items():
        for extension in spec.get("extensions", []):
            assert seen.setdefault(extension.lower(), name) == name, extension


def test_packages_only_for_ecosystems_with_a_manifest():
    table = frameworks.rules()
    ecosystems = {spec["ecosystem"] for spec in table["manifests"].values()}
    assert set(table["packages"]) <= ecosystems
    assert {spec["reader"] for spec in table["manifests"].values()} <= set(frameworks.READERS)


def test_missing_resources_say_what_to_do(monkeypatch, tmp_path):
    monkeypatch.setenv("GITRECON_RESOURCES", str(tmp_path))
    with pytest.raises(FileNotFoundError, match="GITRECON_RESOURCES"):
        resource("languages.yml")


# --- languages and lexer ----------------------------------------------------------------


def test_detect_by_extension_and_filename():
    assert detect(Path("a/b/app.TS")).name == "TypeScript"
    assert detect(Path("Dockerfile")).family == "hash_family" and detect(Path("Dockerfile")).kind == "config"
    assert detect(Path("notes.md")).kind == "prose" and detect(Path("x.unknown")) is None
    assert {"true", "null", "if"} <= detect(Path("x.js")).keywords  # YAML booleans arrive as words


def test_c_family_tells_code_comments_and_strings_apart():
    source = '''// header comment
const url = "https://example.com/a // not a comment";  // see https://docs.example.org
/* block
   comment */
function fetchData(count) { return count + 0x1F; }
'''
    stats = lexical.lex(source, detect(Path("x.js")))
    assert (stats.lines, stats.code, stats.comment, stats.blank) == (5, 2, 3, 0)
    assert stats.tokens["COMMENT"] == 3 and stats.tokens["STRING"] == 1
    assert stats.names == {"url": 1, "fetchData": 1, "count": 2}          # keywords and short names left out
    assert stats.urls == ["https://example.com/a", "https://docs.example.org"]


def test_python_family_docstrings_are_strings_and_hash_is_comment():
    source = 'def run(path):\n    """Docstring # not a comment."""\n    return path  # trailing\n\n# only comment\n'
    stats = lexical.lex(source, detect(Path("x.py")))
    assert (stats.code, stats.comment, stats.blank) == (3, 1, 1)
    assert stats.comment_ratio == 0.25


@pytest.mark.parametrize(("name", "source", "comments"), [
    ("x.sh", "# c\necho 'a # b' # c2\n", 2),
    ("x.sql", "-- c\nSELECT 'it''s' FROM t; /* c2 */\n", 2),
    ("x.html", "<!-- c -->\n<a href=\"#x\">y</a>\n", 1),
])
def test_other_families(name, source, comments):
    assert lexical.lex(source, detect(Path(name))).tokens["COMMENT"] == comments


def test_lexer_never_fails_on_unfamiliar_text():
    garbage = "'unterminated \x00 ``` @@ §§ \"\n \\ /* never closed"
    for family_file in ("x.js", "x.py", "x.sh", "x.sql", "x.html"):
        assert lexical.lex(garbage, detect(Path(family_file))).lines == 2


# --- Python structure ---------------------------------------------------------------


def test_python_ast_summary():
    stats = pyast.PyStats()
    pyast.add_file(stats, '"""Module."""\nimport os.path\nfrom lark import Lark\nfrom . import sibling\n\n'
                          '@cache\ndef f():\n    """Doc."""\n\nasync def g(): pass\n\nclass C:\n    def m(self): pass\n')
    pyast.add_file(stats, "print 'python 2'\n")
    assert (stats.files, stats.unparsed, stats.functions, stats.async_functions, stats.classes) == (2, 1, 3, 1, 1)
    assert stats.imports == {"os": 1, "lark": 1} and stats.decorators == {"cache": 1}
    assert stats.docstring_ratio == 0.4  # module + f of 5 documentable


# --- frameworks and whole repositories ---------------------------------------------------


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "shop"
    (root / "src").mkdir(parents=True)
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / "package.json").write_text(json.dumps({"dependencies": {"vue": "^3", "left-pad": "1"},
                                                   "devDependencies": {"vite": "^8"}}))
    (root / "pyproject.toml").write_text('[project]\nname="x"\ndependencies=["Django>=5", "requests[socks]>=2"]\n'
                                         '[dependency-groups]\ndev=["pytest>=9", {include-group="x"}]\n')
    (root / "requirements-dev.txt").write_text("# tools\nrich==13.9\n-r other.txt\n")
    (root / "composer.json").write_text(json.dumps({"require": {"php": "^8", "laravel/framework": "^12"}}))
    (root / "go.mod").write_text("module x\n\nrequire (\n\tgithub.com/gin-gonic/gin v1.9.1\n)\n")
    (root / "Dockerfile").write_text("FROM alpine\n")
    (root / ".github" / "workflows" / "ci.yml").write_text("on: push\n")
    (root / "src" / "main.py").write_text('"""App."""\nimport django\n\ndef serve(): pass  # see https://x.example\n')
    (root / "src" / "app.js").write_text("// entry\nexport function mountApp(root) { return root; }\n")
    (root / "README.md").write_text("# shop\n\ntext\n")
    (root / "logo.bin").write_bytes(b"\x00\x01\x02")
    return root


def test_dependencies_and_frameworks(repo):
    files = [p for p in repo.rglob("*") if p.is_file()]
    found, deps = frameworks.detect(repo, files)
    assert deps == {"composer": ["laravel/framework"], "go": ["github.com/gin-gonic/gin"],
                    "npm": ["left-pad", "vite", "vue"], "pypi": ["django", "pytest", "requests", "rich"]}
    assert found == ["Django", "Docker", "Gin", "GitHub Actions", "Laravel", "pytest", "requests", "Rich",
                     "Vite", "Vue"]


def test_analyze_repo(repo):
    result = analyze_repo(repo)
    assert result["name"] == "shop" and result["main_language"] in ("Python", "JavaScript")
    assert result["languages"]["Python"] | {"bytes": 0} == {
        "kind": "code", "files": 1, "bytes": 0, "lines": 4, "code": 3, "comment": 0, "blank": 1,
        "comment_ratio": 0.0}
    assert result["languages"]["Markdown"]["lines"] == 3
    assert result["python"]["imports"] == {"django": 1} and result["python"]["functions"] == 1
    assert "mountApp" in result["names"] and "https://x.example" in result["urls"]
    assert result["unknown_extensions"] == {".bin": 1}
    assert "Laravel" in result["frameworks"]
    json.dumps(result)


def test_find_repos(tmp_path, repo):
    assert find_repos(repo) == []                     # a plain folder is not a repository...
    (repo / ".git").mkdir()
    assert find_repos(repo) == [repo]                 # ...a folder with .git is one
    assert find_repos(tmp_path) == [repo]             # and a folder of repositories lists them


def test_analyze_command(repo, capsys):
    (repo / ".git").mkdir()
    assert main(["analyze", str(repo.parent), "--json"]) == 0
    captured = capsys.readouterr()
    (result,) = json.loads(captured.out)
    assert result["name"] == "shop" and "Vue" in result["frameworks"]
    assert main(["analyze", str(repo)]) == 0
    text = capsys.readouterr().out
    assert "shop  (" in text and "frameworks & tools:" in text and "python: 1 functions" in text
