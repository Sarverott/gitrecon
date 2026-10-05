"""CaptorLex step 2: which file uses which inside one repository."""

import json

import pytest

from gitrecon.code.imports import folder_edges, import_graph, imports_mermaid, rules
from gitrecon.main import main

FILES = {
    # Python: src layout, absolute, relative, package __init__, a cycle, a library
    "src/pkg/__init__.py": "from pkg.core import run\n",
    "src/pkg/core.py": "import os.path\nimport requests\nfrom . import util\nfrom .sub import deep\nfrom pkg.sub.deep import thing\n",
    "src/pkg/util.py": "from pkg import core\n",                       # core <-> util: a cycle
    "src/pkg/sub/__init__.py": "",
    "src/pkg/sub/deep.py": "from ..util import helper\nfrom .. import missing_name\n",
    "tests/test_core.py": "from pkg.core import run\nimport pytest\n",
    "broken.py": "def (:\n",
    # JavaScript / TypeScript
    "web/app.js": "import x from './lib/a.js';\nimport {\n  y,\n} from './lib';\nconst z = require('../web/lib/b');\n"
                  "import React from 'react';\nimport q from '@scope/pkg/deep';\nconst l = await import('./lazy.js');\n",
    "web/lib/a.ts": "export default 1;\n",
    "web/lib/b.js": "module.exports = 1;\n",
    "web/lib/index.js": "export * from './a';\n",
    # C, shell, PHP
    "fw/main.cpp": '#include <vector>\n#include "util/pins.h"\n#include "gone.h"\n',
    "fw/util/pins.h": "#define LED 1\n",
    "ops/run.sh": 'source "$(dirname "$0")/lib/common.sh"\n. ./lib/missing.sh\n',
    "ops/lib/common.sh": "say() { echo hi; }\n",
    "composer.json": json.dumps({"autoload": {"psr-4": {"App\\": "app/"}}}),
    "app/Http/Kernel.php": "<?php\nnamespace App\\Http;\nuse App\\Models\\User;\nuse Illuminate\\Http\\Request;\n"
                           "class Kernel {\n    use SomeTrait;\n}\nrequire_once __DIR__.'/helpers.php';\n",
    "app/Http/helpers.php": "<?php\n",
    "app/Models/User.php": "<?php\nnamespace App\\Models;\n",
}


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "mixed"
    for name, text in FILES.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return root


def edges_from(graph, file):
    return sorted(target for source, target in graph["edges"] if source == file)


def test_python_modules_resolve_to_files(repo):
    graph = import_graph(repo)
    assert edges_from(graph, "src/pkg/core.py") == ["src/pkg/sub/deep.py", "src/pkg/util.py"]
    assert edges_from(graph, "src/pkg/__init__.py") == ["src/pkg/core.py"]
    assert edges_from(graph, "src/pkg/sub/deep.py") == ["src/pkg/__init__.py", "src/pkg/util.py"]   # "..": the package
    assert edges_from(graph, "tests/test_core.py") == ["src/pkg/core.py"]
    assert edges_from(graph, "broken.py") == [] and "broken.py" in graph["unconnected"]
    assert graph["external"]["requests"] == 1 and graph["external"]["pytest"] == 1 and "pkg" not in graph["external"]


def test_other_languages_by_pattern(repo):
    graph = import_graph(repo)
    assert edges_from(graph, "web/app.js") == ["web/lib/a.ts", "web/lib/b.js", "web/lib/index.js"]  # a.js is a.ts
    assert edges_from(graph, "web/lib/index.js") == ["web/lib/a.ts"]
    assert edges_from(graph, "fw/main.cpp") == ["fw/util/pins.h"]
    assert edges_from(graph, "ops/run.sh") == ["ops/lib/common.sh"]
    assert edges_from(graph, "app/Http/Kernel.php") == ["app/Http/helpers.php", "app/Models/User.php"]
    external = graph["external"]
    assert external["react"] == 1 and external["@scope/pkg"] == 1 and external["vector"] == 1
    assert external["Illuminate"] == 1 and "SomeTrait" not in external                          # a trait is not an import
    assert graph["languages"]["Python"] == 7 and graph["languages"]["PHP"] == 3


def test_summary_cycles_and_diagrams(repo):
    graph = import_graph(repo)
    assert ["src/pkg/__init__.py", "src/pkg/core.py", "src/pkg/sub/deep.py", "src/pkg/util.py"] in graph["cycles"]
    assert graph["most_used"][0]["used_by"] >= 3
    assert folder_edges(graph, depth=1)[("tests", "src")] == 1
    folders = imports_mermaid(graph, level="folder", depth=2)
    assert folders.startswith("flowchart LR\n") and 'n_src_pkg["src/pkg"]' in folders
    files = imports_mermaid(graph, level="file", max_nodes=5)
    assert ":::cycle" in files and "more files not drawn (max_nodes=5)" in files and "classDef cycle" in files


def test_rules_cover_known_languages_only():
    from gitrecon.code.languages import _table

    known = {language.name for language in _table()[0].values()}
    assert set(rules()) <= known
    for name, spec in rules().items():
        assert spec["resolve"] in ("relative", "path", "include"), name
        assert all(pattern.groups == 1 for pattern in spec["patterns"]), name


def test_imports_command(repo, capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("GITRECON_DATA", str(tmp_path / "data"))
    assert main(["imports", str(repo)]) == 0
    out = capsys.readouterr().out
    assert "mixed: 18 files read" in out and "cycles: 1" in out and "between folders" in out
    assert main(["imports", str(repo), "--format", "mermaid", "--level", "file", "--save"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("flowchart LR") and "saved " in out
    assert "```mermaid\nflowchart LR" in (tmp_path / "data" / "imports" / "mixed-file.md").read_text()
    assert main(["imports", str(repo), "--json"]) == 0
    assert set(json.loads(capsys.readouterr().out)) >= {"files", "edges", "most_used", "cycles", "external", "mermaid"}
