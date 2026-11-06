"""Release metadata that has to stay in sync by hand."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def project_field(name: str) -> str:
    # tomllib only exists from Python 3.11; the [project] fields we need are simple strings
    match = re.search(rf'^{name} = "([^"]+)"$', (ROOT / "pyproject.toml").read_text(), re.MULTILINE)
    assert match, name
    return match.group(1)


def test_server_json_matches_the_package():
    server = json.loads((ROOT / "server.json").read_text())
    (pypi,) = server["packages"]
    assert pypi["registryType"] == "pypi"
    assert pypi["identifier"] == project_field("name")
    assert server["version"] == pypi["version"] == project_field("version")


def test_readme_carries_the_mcp_registry_ownership_marker():
    # The registry checks for this marker in the PyPI description (the README).
    name = json.loads((ROOT / "server.json").read_text())["name"]
    assert re.search(rf"<!-- mcp-name: {re.escape(name)} -->", (ROOT / "README.md").read_text())
