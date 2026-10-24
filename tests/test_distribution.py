"""Exercise distribution through its command-line and installation boundaries."""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

ROOT = Path(__file__).parents[1]


def test_version_drift_fails_with_a_repair_hint(tmp_path: Path) -> None:
    plugin = tmp_path / "skills/cowsay/.claude-plugin"
    plugin.mkdir(parents=True)
    (plugin / "plugin.json").write_text('{"name": "cowsay", "version": "0.1.0"}')
    marketplace = tmp_path / ".claude-plugin"
    marketplace.mkdir()
    (marketplace / "marketplace.json").write_text(
        json.dumps(
            {"plugins": [{"name": "cowsay", "source": "./skills/cowsay", "version": "9.0.0"}]}
        )
    )
    result = subprocess.run(
        [sys.executable, "-m", "skills_tooling.distribution", "--root", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "version" in result.stderr
    assert "just format" in result.stderr


def run(command: list[str], project: Path, env: dict[str, str]) -> str:
    result = subprocess.run(
        command,
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def isolated_environment(base: Path) -> dict[str, str]:
    """No inherited agent credentials, user configuration, caches or Git helpers."""
    home = base / "home"
    temp = base / "tmp"
    home.mkdir()
    temp.mkdir()
    env = {
        "PATH": os.environ["PATH"],
        "HOME": str(home),
        "TMPDIR": str(temp),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "XDG_CACHE_HOME": str(home / ".cache"),
        "XDG_DATA_HOME": str(home / ".local/share"),
        "XDG_STATE_HOME": str(home / ".local/state"),
        "CLAUDE_CONFIG_DIR": str(home / ".claude"),
        "CODEX_HOME": str(home / ".codex"),
        "PI_CODING_AGENT_DIR": str(home / ".pi/agent"),
        "npm_config_cache": str(base / "npm-cache"),
        "npm_config_update_notifier": "false",
        "npm_config_offline": "true",
        "DISABLE_AUTOUPDATER": "1",
        "DISABLE_TELEMETRY": "1",
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        "DO_NOT_TRACK": "1",
        "CI": "1",
        "NO_COLOR": "1",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
    }
    for agent_home in ("CLAUDE_CONFIG_DIR", "CODEX_HOME", "PI_CODING_AGENT_DIR"):
        Path(env[agent_home]).mkdir(parents=True)
    return env


# Python audit hooks deny file reads outside the install and the pinned Python
# runtime. Even an accidental absolute reference into the development checkout
# cannot satisfy the smoke test. -I -S also removes PYTHONPATH and site packages.
RUN_INSTALLED = """
import pathlib, runpy, sys
script = pathlib.Path(sys.argv[1]).resolve()
allowed = (script.parent.parent, pathlib.Path(sys.base_prefix).resolve())
def restrict(event, args):
    if event == 'open' and isinstance(args[0], (str, bytes)):
        path = pathlib.Path(args[0]).resolve()
        if not any(path.is_relative_to(root) for root in allowed):
            raise PermissionError('outside installed skill and Python runtime: ' + str(path))
sys.addaudithook(restrict)
sys.argv = [str(script), '--', 'hello']
runpy.run_path(str(script), run_name='__main__')
"""


def install_marketplace(source: Path, project: Path, env: dict[str, str]) -> Path:
    cli = str(ROOT / "node_modules/.bin/claude")
    # Claude rejects file:// marketplace URLs. Keep its hosted Git-source
    # path, but let Git redirect this reserved hostname to our local clone.
    # Only file transport is allowed, so this cannot reach the network.
    git_url = "https://distribution.invalid/skills.git"
    env.update(
        {
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": f"url.{source.as_uri()}.insteadOf",
            "GIT_CONFIG_VALUE_0": git_url,
            "GIT_ALLOW_PROTOCOL": "file",
        }
    )
    run([cli, "plugin", "marketplace", "add", git_url], project, env)
    run(
        [cli, "plugin", "install", "cowsay@biscuitbin-skills", "--scope", "project"],
        project,
        env,
    )
    registry = json.loads(
        (Path(env["CLAUDE_CONFIG_DIR"]) / "plugins/installed_plugins.json").read_text()
    )
    installs = registry["plugins"]["cowsay@biscuitbin-skills"]
    assert len(installs) == 1
    installed = Path(installs[0]["installPath"])
    assert installed.is_relative_to(Path(env["CLAUDE_CONFIG_DIR"]) / "plugins/cache")
    assert installs[0]["scope"] == "project"
    settings = json.loads((project / ".claude/settings.json").read_text())
    assert settings["enabledPlugins"] == {"cowsay@biscuitbin-skills": True}
    manifest = json.loads((installed / ".claude-plugin/plugin.json").read_text())
    assert manifest["skills"] == ["./"]
    return installed


def install_skills(source: Path, project: Path, env: dict[str, str], agent: str) -> Path:
    # npm exec is npx's implementation; --prefix selects the locked local
    # binary while cwd remains the throwaway project. Offline forbids fetches.
    npx = ["npm", "exec", "--offline", "--no", "--prefix", str(ROOT), "--", "skills"]
    listing = run([*npx, "add", source.as_uri(), "--list"], project, env)
    listing = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", listing)
    assert "Found 1 skill" in listing
    assert "cowsay" in listing
    assert "cross-model-review" not in listing
    output = run([*npx, "add", source.as_uri(), "--agent", agent, "--yes", "--json"], project, env)
    assert "cowsay" in output
    discovered = ".claude/skills" if agent == "claude-code" else ".agents/skills"
    directory = project / discovered
    assert {path.name for path in directory.iterdir()} == {"cowsay"}
    installed = directory / "cowsay"
    assert installed.resolve().is_relative_to(project)
    return installed


@pytest.mark.parametrize("agent", ["marketplace", "claude-code", "codex", "pi"])
def test_committed_install_round_trip(
    tmp_path: Path, agent: str, record_property: Callable[[str, object], None]
) -> None:
    env = isolated_environment(tmp_path)
    project = tmp_path / "project"
    project.mkdir()
    source = tmp_path / "source"
    run(["git", "clone", "--no-local", str(ROOT), str(source)], project, env)
    run(["git", "init", "--quiet"], project, env)
    assert run(["git", "status", "--porcelain"], source, env) == ""
    shipped = source / "skills/cowsay"
    expected = {
        str(path.relative_to(shipped)): path.read_bytes()
        for path in shipped.rglob("*")
        if path.is_file()
    }
    assert set(expected) == {
        "SKILL.md",
        "scripts/cowsay.py",
        "agents/openai.yaml",
        ".claude-plugin/plugin.json",
    }
    installed = (
        install_marketplace(source, project, env)
        if agent == "marketplace"
        else install_skills(source, project, env, agent)
    )

    mode = "symlink" if installed.is_symlink() else "copy"
    record_property("installation_mode", mode)
    print(f"{agent}: {mode}")
    # Remove every installer source/cache except the actual plugin payload.
    # npx's symlinks must point at its project-local canonical copy.
    shutil.rmtree(source)
    marketplace_cache = Path(env["CLAUDE_CONFIG_DIR"]) / "plugins/marketplaces"
    if marketplace_cache.exists():
        shutil.rmtree(marketplace_cache)
    assert {
        str(path.relative_to(installed)): path.read_bytes()
        for path in installed.rglob("*")
        if path.is_file()
    } == expected
    for path in installed.rglob("*"):
        assert path.resolve().is_relative_to(installed.resolve())
    rendered = run(
        [sys.executable, "-I", "-S", "-c", RUN_INSTALLED, str(installed / "scripts/cowsay.py")],
        project,
        env,
    )
    assert rendered.startswith(" _______\n< hello >\n -------\n")
    assert "(oo)" in rendered
