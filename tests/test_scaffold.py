"""`just new-skill`: scaffold a shipped skill, its eval suite and its marketplace entry."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from skills_tooling import distribution, scaffold
from skills_tooling.evals.cases import load_suite
from skills_tooling.validator import validate_skill

ROOT = Path(__file__).parents[1]
FORMAT_CONFIG = (
    ".prettierrc.json",
    ".prettierignore",
    ".markdownlint-cli2.jsonc",
    ".editorconfig",
)


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """A copy of the repo's skills, evals and manifests, with its format configuration."""
    for directory in ("skills", "evals", "dev-skills", ".claude-plugin"):
        shutil.copytree(ROOT / directory, tmp_path / directory, symlinks=True)
    for name in FORMAT_CONFIG:
        shutil.copy(ROOT / name, tmp_path / name)
    return tmp_path


def new_skill(root: Path, name: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "skills_tooling.scaffold", "--root", str(root), "--", name],
        capture_output=True,
        text=True,
        check=False,
    )


def snapshot(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_a_new_skill_passes_every_check_straight_away(root: Path) -> None:
    result = new_skill(root, "tea-timer")
    assert result.returncode == 0, result.stderr
    skill = root / "skills/tea-timer"
    assert {str(path.relative_to(skill)) for path in skill.rglob("*") if path.is_file()} == {
        "SKILL.md",
        "agents/openai.yaml",
        ".claude-plugin/plugin.json",
    }
    diagnostics = validate_skill(skill)
    assert [d for d in diagnostics if d.severity == "error"] == []
    suite = load_suite(root, "tea-timer")
    kinds = {(case.kind, case.should_trigger) for case in suite.cases}
    assert kinds == {("trigger", True), ("trigger", False), ("behaviour", True)}
    validate = subprocess.run(
        [sys.executable, "-m", "skills_tooling.evals", "validate", "--root", str(root)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert validate.returncode == 0, validate.stderr
    suites = len(list((ROOT / "evals").glob("*/evals.json"))) + 1
    assert f"{suites} eval suites valid." in validate.stdout
    distribution.check(root)
    entry = json.loads((root / ".claude-plugin/marketplace.json").read_text())["plugins"][-1]
    assert entry == {
        "name": "tea-timer",
        "description": entry["description"],
        "source": "./skills/tea-timer",
        "version": "0.1.0",
    }
    assert "tea-timer" in result.stdout


def test_a_new_skill_is_flagged_as_unwritten(root: Path) -> None:
    new_skill(root, "tea-timer")
    skill = root / "skills/tea-timer"
    diagnostics = validate_skill(skill)
    assert {d.rule for d in diagnostics} == {"placeholder"}
    assert {str(d.file.relative_to(skill.resolve())) for d in diagnostics} == {
        "SKILL.md",
        "agents/openai.yaml",
        ".claude-plugin/plugin.json",
    }
    assert all(case.placeholder for case in load_suite(root, "tea-timer").cases)


def test_generated_files_are_already_formatted(root: Path) -> None:
    new_skill(root, "tea-timer")
    files = [
        "skills/tea-timer/SKILL.md",
        "skills/tea-timer/agents/openai.yaml",
        "skills/tea-timer/.claude-plugin/plugin.json",
        "evals/tea-timer/evals.json",
        ".claude-plugin/marketplace.json",
    ]
    bin_dir = ROOT / "node_modules/.bin"
    for command in (
        [str(bin_dir / "prettier"), "--check", *files],
        [str(bin_dir / "markdownlint-cli2"), "skills/tea-timer/SKILL.md"],
    ):
        result = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
        assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    ("name", "reason"),
    [
        ("Tea-Timer", "lowercase"),
        ("tea--timer", "consecutive hyphens"),
        ("-tea", "leading or trailing hyphen"),
        ("t" * 65, "expected 1-64"),
        ("cowsay", "skills/cowsay already exists"),
        ("cross-model-review", "dev-skills/cross-model-review already exists"),
    ],
)
def test_a_bad_name_is_rejected_and_nothing_is_written(root: Path, name: str, reason: str) -> None:
    before = snapshot(root)
    result = new_skill(root, name)
    assert result.returncode == 1
    assert result.stderr.startswith("new-skill: ")
    assert reason in result.stderr
    assert snapshot(root) == before


def test_a_name_taken_only_by_an_eval_suite_is_rejected(root: Path) -> None:
    (root / "evals/tea-timer").mkdir()
    before = snapshot(root)
    result = new_skill(root, "tea-timer")
    assert result.returncode == 1
    assert "evals/tea-timer already exists" in result.stderr
    assert snapshot(root) == before


def test_a_name_taken_only_in_the_marketplace_is_rejected(root: Path) -> None:
    path = root / ".claude-plugin/marketplace.json"
    marketplace = json.loads(path.read_text())
    marketplace["plugins"].append({"name": "tea-timer", "source": "./skills/tea-timer"})
    path.write_text(json.dumps(marketplace))
    before = snapshot(root)
    result = new_skill(root, "tea-timer")
    assert result.returncode == 1
    assert "already listed in .claude-plugin/marketplace.json" in result.stderr
    assert snapshot(root) == before


def test_a_failure_part_way_leaves_nothing_behind(root: Path) -> None:
    # The marketplace is written last, after the skill and eval directories are in place.
    marketplace = root / ".claude-plugin/marketplace.json"
    marketplace.chmod(0o444)
    before = snapshot(root)
    result = new_skill(root, "tea-timer")
    marketplace.chmod(0o644)
    assert result.returncode == 1
    assert result.stderr.startswith("new-skill: ")
    assert snapshot(root) == before
    assert not (root / "skills/tea-timer").exists()
    assert not (root / "evals/tea-timer").exists()


def test_a_marketplace_write_cut_mid_character_is_restored(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    marketplace = root / ".claude-plugin/marketplace.json"
    data = json.loads(marketplace.read_text())
    data["plugins"][0]["description"] = "Brew tea — gently."
    marketplace.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    before = snapshot(root)
    write_text = Path.write_text

    def cut_short(self: Path, text: str) -> int:
        if self == marketplace and "tea-timer" in text:
            encoded = text.encode()
            # Stop inside the em dash's three bytes, as a full disk might.
            self.write_bytes(encoded[: encoded.index("—".encode()) + 1])
            raise OSError(28, "No space left on device")
        return write_text(self, text)

    monkeypatch.setattr(Path, "write_text", cut_short)
    with pytest.raises(scaffold.ScaffoldError, match="nothing was kept"):
        scaffold.scaffold(root, "tea-timer")
    monkeypatch.undo()
    assert snapshot(root) == before


def test_the_starter_evals_are_reported_unwritten_not_run(root: Path) -> None:
    new_skill(root, "tea-timer")

    def evals(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "skills_tooling.evals", *args, "--root", str(root)],
            capture_output=True,
            text=True,
            check=False,
        )

    planned = evals("run", "tea-timer", "--agent", "codex", "--dry-run")
    assert planned.returncode == 2
    assert planned.stderr.count("UNWRITTEN tea-timer/") == 3
    validated = evals("validate")
    assert validated.returncode == 0, validated.stderr
    assert "warning: tea-timer is in .claude-plugin/marketplace.json" in validated.stderr
    assert "cowsay" not in validated.stderr


@pytest.mark.parametrize(
    "name", ["123", "true", "null", "yes", "off", "2026-11-05", "2026-99-99", "2026-02-30", "1e3"]
)
def test_a_name_yaml_would_read_as_another_type_still_validates(root: Path, name: str) -> None:
    result = new_skill(root, name)
    assert result.returncode == 0, result.stderr
    skill = root / "skills" / name
    assert [d for d in validate_skill(skill) if d.severity == "error"] == []
    load_suite(root, name)
    distribution.check(root)
