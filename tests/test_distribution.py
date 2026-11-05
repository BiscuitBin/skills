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


def distribution_root(tmp_path: Path, plugins: list[dict[str, str]]) -> Path:
    (tmp_path / "skills").mkdir()
    (tmp_path / ".claude-plugin").mkdir()
    (tmp_path / ".claude-plugin/marketplace.json").write_text(json.dumps({"plugins": plugins}))
    return tmp_path


def check_distribution(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "skills_tooling.distribution", "--root", str(root)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_an_unlisted_skill_fails_with_the_entry_to_add(tmp_path: Path) -> None:
    root = distribution_root(tmp_path, [])
    plugin = root / "skills/tea-timer/.claude-plugin"
    plugin.mkdir(parents=True)
    (plugin / "plugin.json").write_text(
        '{"name": "tea-timer", "version": "0.2.0", "description": "Time tea."}'
    )
    result = check_distribution(root)
    assert result.returncode == 1
    assert "skills/tea-timer is not listed in .claude-plugin/marketplace.json" in result.stderr
    assert (
        '{"name": "tea-timer", "description": "Time tea.", '
        '"source": "./skills/tea-timer", "version": "0.2.0"}'
    ) in result.stderr


def test_an_unlisted_skill_without_a_plugin_manifest_says_to_create_one(tmp_path: Path) -> None:
    root = distribution_root(tmp_path, [])
    (root / "skills/tea-timer").mkdir()
    result = check_distribution(root)
    assert result.returncode == 1
    assert "Create skills/tea-timer/.claude-plugin/plugin.json" in result.stderr
    assert '"skills": ["./"]' in result.stderr
    assert '"source": "./skills/tea-timer"' in result.stderr


def test_a_listed_plugin_with_no_skill_fails_with_the_entry_to_remove(tmp_path: Path) -> None:
    root = distribution_root(tmp_path, [{"name": "gone", "source": "./skills/gone"}])
    result = check_distribution(root)
    assert result.returncode == 1
    assert (
        "remove the gone entry from .claude-plugin/marketplace.json; skills/gone does not exist"
    ) in result.stderr


def test_description_drift_fails_and_just_format_copies_it(tmp_path: Path) -> None:
    root = distribution_root(
        tmp_path,
        [
            {
                "name": "tea-timer",
                "description": "TODO(new-skill) Old.",
                "source": "./skills/tea-timer",
                "version": "0.1.0",
            }
        ],
    )
    plugin = root / "skills/tea-timer/.claude-plugin"
    plugin.mkdir(parents=True)
    (plugin / "plugin.json").write_text(
        '{"name": "tea-timer", "version": "0.1.0", "description": "Time tea."}'
    )
    result = check_distribution(root)
    assert result.returncode == 1
    assert "tea-timer: marketplace description differs from plugin.json" in result.stderr
    assert "just format" in result.stderr
    write = subprocess.run(
        [sys.executable, "-m", "skills_tooling.distribution", "--root", str(root), "--write"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert write.returncode == 0, write.stderr
    entry = json.loads((root / ".claude-plugin/marketplace.json").read_text())["plugins"][0]
    assert entry["description"] == "Time tea."
    assert check_distribution(root).returncode == 0


def test_uncommitted_distribution_files_fail_before_installing(tmp_path: Path) -> None:
    env = isolated_environment(tmp_path)
    project = tmp_path / "repo"
    project.mkdir()
    run(["git", "init", "--quiet"], project, env)
    (project / "skills/cowsay/.claude-plugin").mkdir(parents=True)
    (project / "skills/cowsay/.claude-plugin/plugin.json").write_text(
        '{"name":"cowsay","version":"0.1.0"}'
    )
    (project / ".claude-plugin").mkdir()
    (project / ".claude-plugin/marketplace.json").write_text(
        '{"plugins":[{"name":"cowsay","version":"0.1.0","source":"./skills/cowsay"}]}'
    )
    run(["git", "add", "."], project, env)
    run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "--quiet",
            "-m",
            "Fixture",
        ],
        project,
        env,
    )
    (project / "skills/cowsay/evals.json").write_text("{}")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "skills_tooling.distribution",
            "--root",
            str(project),
            "--committed",
        ],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert result.returncode == 1
    assert "Commit distribution source changes" in result.stderr
    assert "evals.json" in result.stderr


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
        "HTTP_PROXY": "http://127.0.0.1:9",
        "HTTPS_PROXY": "http://127.0.0.1:9",
        "ALL_PROXY": "http://127.0.0.1:9",
        "NO_PROXY": "",
        "NODE_USE_ENV_PROXY": "1",
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


def redirect_git_source(source: Path, env: dict[str, str]) -> None:
    """Exercise documented source parsing with only local Git transport."""
    env.update(
        {
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": f"url.{source.as_uri()}.insteadOf",
            "GIT_CONFIG_VALUE_0": "https://github.com/BiscuitBin/skills.git",
            "GIT_ALLOW_PROTOCOL": "file",
        }
    )


def install_marketplace(source: Path, project: Path, env: dict[str, str]) -> Path:
    cli = str(ROOT / "node_modules/.bin/claude")
    run([cli, "plugin", "marketplace", "add", "BiscuitBin/skills"], project, env)
    run(
        [cli, "plugin", "install", "cowsay@biscuitbin-skills", "--scope", "project"],
        project,
        env,
    )
    registry = json.loads(
        (Path(env["CLAUDE_CONFIG_DIR"]) / "plugins/installed_plugins.json").read_text()
    )
    installs = registry["plugins"]["cowsay@biscuitbin-skills"]
    assert set(registry["plugins"]) == {"cowsay@biscuitbin-skills"}
    assert len(installs) == 1
    assert installs[0]["gitCommitSha"] == run(["git", "rev-parse", "HEAD"], source, env).strip()
    installed = Path(installs[0]["installPath"])
    assert installed.is_relative_to(Path(env["CLAUDE_CONFIG_DIR"]) / "plugins/cache")
    assert installs[0]["scope"] == "project"
    settings = json.loads((project / ".claude/settings.json").read_text())
    assert settings["enabledPlugins"] == {"cowsay@biscuitbin-skills": True}
    manifest = json.loads((installed / ".claude-plugin/plugin.json").read_text())
    assert manifest["skills"] == ["./"]
    return installed


def install_skills(
    project: Path, env: dict[str, str], agents: list[str], shipped: set[str]
) -> list[Path]:
    # npm exec is npx's implementation; --prefix selects the locked local
    # binary while cwd remains the throwaway project. Offline forbids fetches.
    npx = ["npm", "exec", "--offline", "--no", "--prefix", str(ROOT), "--", "skills"]
    listing = run([*npx, "add", "BiscuitBin/skills", "--list"], project, env)
    listing = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", listing)
    assert f"Found {len(shipped)} skill" in listing
    assert all(name in listing for name in shipped)
    assert "cross-model-review" not in listing
    output = run([*npx, "add", "BiscuitBin/skills", "--agent", *agents, "--yes"], project, env)
    assert all(name in output for name in shipped)
    installs = []
    for agent in agents:
        discovered = ".claude/skills" if agent == "claude-code" else ".agents/skills"
        directory = project / discovered
        assert {path.name for path in directory.iterdir()} == shipped
        for name in sorted(shipped):
            installed = directory / name
            assert installed.resolve().is_relative_to(project)
            installs.append(installed)
    return installs


@pytest.mark.parametrize("agent", ["marketplace", "claude-code", "codex", "pi", "shared"])
def test_committed_install_round_trip(
    tmp_path: Path, agent: str, record_property: Callable[[str, object], None]
) -> None:
    env = isolated_environment(tmp_path)
    run([sys.executable, "-m", "skills_tooling.distribution", "--committed"], ROOT, env)
    project = tmp_path / "project"
    project.mkdir()
    source = tmp_path / "source"
    run(["git", "clone", "--no-local", str(ROOT), str(source)], project, env)
    run(["git", "init", "--quiet"], project, env)
    assert run(["git", "status", "--porcelain"], source, env) == ""
    redirect_git_source(source, env)
    # Every skill the clone ships, so a second skill is installed and checked too.
    expected = {
        skill.name: {
            str(path.relative_to(skill)): path.read_bytes()
            for path in skill.rglob("*")
            if path.is_file()
        }
        for skill in (source / "skills").iterdir()
        if skill.is_dir()
    }
    assert set(expected["cowsay"]) == {
        "SKILL.md",
        "scripts/cowsay.py",
        "agents/openai.yaml",
        ".claude-plugin/plugin.json",
    }
    installs = (
        [install_marketplace(source, project, env)]
        if agent == "marketplace"
        else install_skills(
            project, env, ["claude-code", "codex"] if agent == "shared" else [agent], set(expected)
        )
    )

    modes = ["symlink" if installed.is_symlink() else "copy" for installed in installs]
    record_property("installation_mode", ",".join(modes))
    print(f"{agent}: {','.join(modes)}")
    if agent == "shared":
        assert modes == ["symlink"] * len(expected) + ["copy"] * len(expected)
    # Remove every installer source/cache except the actual plugin payload.
    # npx's symlinks must point at its project-local canonical copy.
    shutil.rmtree(source)
    marketplace_cache = Path(env["CLAUDE_CONFIG_DIR"]) / "plugins/marketplaces"
    if marketplace_cache.exists():
        shutil.rmtree(marketplace_cache)
    assert_project_inventory(project, expected, installs, marketplace=agent == "marketplace")
    for installed in installs:
        # The marketplace installs only cowsay, into a cache directory named by version.
        name = "cowsay" if agent == "marketplace" else installed.name
        assert {
            str(path.relative_to(installed)): path.read_bytes()
            for path in installed.rglob("*")
            if path.is_file()
        } == expected[name]
        for path in installed.rglob("*"):
            assert path.resolve().is_relative_to(installed.resolve())
        if name != "cowsay":
            continue
        rendered = run(
            [
                sys.executable,
                "-I",
                "-S",
                "-c",
                RUN_INSTALLED,
                str(installed / "scripts/cowsay.py"),
            ],
            project,
            env,
        )
        assert rendered.startswith(" _______\n< hello >\n -------\n")
        assert "(oo)" in rendered


def assert_project_inventory(
    project: Path,
    payloads: dict[str, dict[str, bytes]],
    installs: list[Path],
    *,
    marketplace: bool,
) -> None:
    files = {Path(".claude/settings.json")} if marketplace else {Path("skills-lock.json")}
    roots: set[Path] = set()
    if not marketplace:
        roots = {path.relative_to(project) for path in installs} | {
            path.resolve().relative_to(project) for path in installs
        }
        assert roots <= {
            Path(parent) / name
            for name in payloads
            for parent in (".agents/skills", ".claude/skills")
        }
        for prefix in roots:
            payload = payloads[prefix.name]
            files.update(prefix / name for name in payload)
            installed = project / prefix
            assert {
                str(path.relative_to(installed)): path.read_bytes()
                for path in installed.rglob("*")
                if path.is_file()
            } == payload
        lock = json.loads((project / "skills-lock.json").read_text())
        assert set(lock["skills"]) == set(payloads)
        for name in payloads:
            assert lock["skills"][name]["source"] == "BiscuitBin/skills"
            assert lock["skills"][name]["sourceType"] == "github"
            assert lock["skills"][name]["skillPath"] == f"skills/{name}/SKILL.md"
    directories = {parent for path in files for parent in path.parents}
    for path in project.rglob("*"):
        relative = path.relative_to(project)
        if relative.parts[0] == ".git":
            continue
        if path.is_symlink():
            assert relative in roots
            assert relative.parent == Path(".claude/skills")
            assert path.resolve() == project / ".agents/skills" / relative.name
        elif path.is_dir():
            assert relative in directories, f"unexpected installed directory: {relative}"
        else:
            assert path.is_file() and relative in files, f"unexpected installed file: {relative}"
