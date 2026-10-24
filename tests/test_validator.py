"""Validate skills through their public API and command-line interface."""

import json
import subprocess
import sys
from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from skills_tooling.validator import EXTENSIONS, Extension, validate_skill

if TYPE_CHECKING:
    from collections.abc import Iterator

FIXTURES: list[dict[str, Any]] = json.loads(
    (Path(__file__).parent / "fixtures/validator/cases.json").read_text()
)


def materialize(tmp_path: Path, case: dict[str, Any]) -> Path:
    skill = tmp_path / str(case.get("directory", "example"))
    skill.mkdir()
    body = case.get("body", case.get("repeat", "") * case.get("count", 0))
    (skill / "SKILL.md").write_text("---\n" + case["yaml"] + "---\n" + body)
    for name, content in case.get("files", {}).items():
        target = skill / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    return skill


@pytest.mark.parametrize("case", FIXTURES, ids=[case["id"] for case in FIXTURES])
def test_rule_fixture(tmp_path: Path, case: dict[str, Any]) -> None:
    skill = materialize(tmp_path, case)
    extensions = dict(EXTENSIONS)
    if case.get("synthetic_rejection"):
        # Explicitly synthetic evidence exercises the conditional rejection policy.
        extensions["user-invocable"] = Extension("boolean", ("supported", "rejected", "ignored"))
    diagnostics = validate_skill(skill, shipped=case.get("shipped", True), extensions=extensions)
    assert any(
        item.rule == case["rule"] and item.severity == case.get("severity", "error")
        for item in diagnostics
    ), diagnostics
    assert all(item.file.is_relative_to(skill) and item.hint for item in diagnostics)


def test_minimal_skill_passes(tmp_path: Path) -> None:
    skill = tmp_path / "example"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "---\nname: example\ndescription: An example.\n---\n# Example\n"
    )
    assert validate_skill(skill) == []


def test_unknown_field_names_file_rule_and_hint(tmp_path: Path) -> None:
    skill = tmp_path / "example"
    skill.mkdir()
    file = skill / "SKILL.md"
    file.write_text("---\nname: example\ndescription: Example.\ntypo: value\n---\n")
    (diagnostic,) = validate_skill(skill)
    assert diagnostic.rule == "field-unknown"
    assert diagnostic.file == file
    assert diagnostic.severity == "error"
    assert "typo" in str(diagnostic)
    assert "hint:" in str(diagnostic)


@pytest.mark.parametrize("case", FIXTURES, ids=[case["id"] for case in FIXTURES])
def test_reference_verdicts_and_documented_differences(
    tmp_path: Path, case: dict[str, Any]
) -> None:
    skill = materialize(tmp_path, case)
    reference = import_module("skills_ref")
    reference_ok = not reference.validate(skill)
    assert reference_ok == case["ref"]
    ours_ok = not any(
        item.severity == "error"
        for item in validate_skill(skill, shipped=case.get("shipped", True))
    )
    if reference_ok != ours_ok:
        assert case.get("difference")


@pytest.mark.parametrize(
    "case",
    json.loads((Path(__file__).parent / "fixtures/validator/reference-cases.json").read_text()),
    ids=lambda case: case["id"],
)
def test_shared_spec_and_parser_differences(tmp_path: Path, case: dict[str, Any]) -> None:
    skill = materialize(tmp_path, case)
    ours_ok = not any(
        item.severity == "error"
        for item in validate_skill(skill, shipped=case.get("shipped", True))
    )
    reference_ok = not import_module("skills_ref").validate(skill)
    assert ours_ok == case["ours"]
    assert reference_ok == case["ref"]
    if ours_ok != reference_ok:
        assert case["difference"]


@pytest.mark.parametrize(
    ("field", "value", "rule"),
    [
        ("name", "''", "name-format"),
        ("name", "a" * 65, "name-format"),
        ("name", "-example", "name-format"),
        ("name", "example-", "name-format"),
        ("name", "exam--ple", "name-format"),
        ("name", "exam_ple", "name-format"),
        ("name", "123", "name-format"),
        ("description", "''", "description"),
        ("description", "'  '", "description"),
        ("description", "42", "description"),
        ("compatibility", "''", "compatibility"),
        ("compatibility", "[]", "compatibility"),
        ("metadata", "[]", "metadata"),
        ("metadata", "{key: [nested]}", "metadata"),
        ("allowed-tools", "[Read]", "field-type"),
        ("context", "inline", "extension-type"),
        ("paths", "[42]", "extension-type"),
        ("hooks", "true", "extension-type"),
    ],
)
def test_invalid_field_values(tmp_path: Path, field: str, value: str, rule: str) -> None:
    fields = {"name": "example", "description": "Example.", field: value}
    skill = materialize(
        tmp_path, {"yaml": "".join(f"{key}: {text}\n" for key, text in fields.items())}
    )
    assert rule in {item.rule for item in validate_skill(skill)}


@pytest.mark.parametrize(
    "content",
    [
        "",
        "# No YAML\n",
        "---\nname: example\n",
        "---\n[]\n---\n",
        "---\nname: example\nname: duplicate\n---\n",
    ],
)
def test_frontmatter_errors(tmp_path: Path, content: str) -> None:
    skill = tmp_path / "example"
    skill.mkdir()
    (skill / "SKILL.md").write_text(content)
    assert validate_skill(skill)[0].rule == "frontmatter"


def test_valid_boundaries(tmp_path: Path) -> None:
    skill = materialize(
        tmp_path,
        {
            "yaml": "name: example\ndescription: "
            + "x" * 1024
            + "\ncompatibility: "
            + "x" * 500
            + "\n",
            "repeat": "line\n",
            "count": 499,
        },
    )
    assert validate_skill(skill) == []
    name = "a" * 64
    skill.rename(tmp_path / name)
    skill = tmp_path / name
    file = skill / "SKILL.md"
    file.write_text(file.read_text().replace("name: example", f"name: {name}"))
    assert validate_skill(skill) == []


def test_dev_extensions_and_claude_tools_list(tmp_path: Path) -> None:
    skill = materialize(
        tmp_path,
        {
            "yaml": "name: example\ndescription: Example.\nallowed-tools: [Read, Grep]\ndisable-model-invocation: true\npaths: [src/**]\nhooks: {}\n"
        },
    )
    assert validate_skill(skill, shipped=False) == []
    diagnostics = validate_skill(skill)
    assert {item.rule for item in diagnostics} == {"field-type", "extension-portability"}


@pytest.mark.parametrize(
    "target",
    [
        "references/deep/more/file.txt",
        "references/a%20b.txt",
        "references/deep/more/file.txt#part",
    ],
)
def test_links_resolve_at_any_directory_depth(tmp_path: Path, target: str) -> None:
    skill = materialize(
        tmp_path,
        {
            "yaml": "name: example\ndescription: Example.\n",
            "body": f"[Read][ref]\n\n[ref]: {target}\n",
            "files": {"references/deep/more/file.txt": "done", "references/a b.txt": "done"},
        },
    )
    assert validate_skill(skill) == []


@pytest.mark.parametrize(
    "body", ["`scripts/missing.py`", "![Image](assets/missing.png)", "[Read](%2e%2e/outside.md)"]
)
def test_concrete_inline_and_image_references(tmp_path: Path, body: str) -> None:
    skill = materialize(tmp_path, {"yaml": "name: example\ndescription: Example.\n", "body": body})
    assert any(
        item.rule.startswith("reference-") and item.severity == "error"
        for item in validate_skill(skill)
    )


def test_symlinks_cannot_escape_skill(tmp_path: Path) -> None:
    skill = materialize(
        tmp_path,
        {
            "yaml": "name: example\ndescription: Example.\n",
            "body": "[Read](references/link.txt)\n",
        },
    )
    outside = tmp_path / "outside.txt"
    outside.write_text("outside")
    (skill / "references").mkdir()
    (skill / "references/link.txt").symlink_to(outside)
    assert validate_skill(skill)[0].rule == "reference-escape"


@pytest.mark.parametrize("target", ["missing.txt", "../../outside.txt"])
def test_chained_broken_references_are_errors(tmp_path: Path, target: str) -> None:
    skill = materialize(
        tmp_path,
        {
            "yaml": "name: example\ndescription: Example.\n",
            "body": "[Read](references/one.txt)\n",
            "files": {"references/one.txt": f"[Next]({target})\n"},
        },
    )
    diagnostics = validate_skill(skill)
    assert any(
        item.rule == "reference-chain" and item.severity == "warning" for item in diagnostics
    )
    assert any(
        item.rule in {"reference-missing", "reference-escape"} and item.file.name == "one.txt"
        for item in diagnostics
    )


def test_cycles_and_external_links_terminate(tmp_path: Path) -> None:
    skill = materialize(
        tmp_path,
        {
            "yaml": "name: example\ndescription: Example.\n",
            "body": "[Read](references/one.txt) [Web](https://example.com/a) [Anchor](#here)\n",
            "files": {"references/one.txt": "[Back](../SKILL.md)"},
        },
    )
    diagnostics = validate_skill(skill)
    assert [item.rule for item in diagnostics] == ["reference-chain"]


def test_full_codex_metadata_shape(tmp_path: Path) -> None:
    skill = materialize(
        tmp_path,
        {
            "yaml": "name: example\ndescription: Example.\n",
            "files": {
                "agents/openai.yaml": "interface:\n  display_name: Example\n  short_description: A sufficiently long description\n  icon_small: ./assets/icon.png\n  icon_large: ./assets/icon.png\n  brand_color: '#112233'\n  default_prompt: Use $example.\npolicy:\n  allow_implicit_invocation: false\n  products: []\ndependencies:\n  tools:\n    - type: mcp\n      value: example\n      description: Example\n      transport: stdio\n      command: example\n      url: https://example.com\n      oauth_callback_port: 65535\n"
            },
        },
    )
    assert validate_skill(skill) == []


@pytest.mark.parametrize(
    "metadata",
    [
        "[]",
        "interface: []",
        "interface: {typo: value}",
        "policy: []",
        "policy: {allow_implicit_invocation: 'false'}",
        "policy: {products: all}",
        "dependencies: []",
        "dependencies: {tools: {}}",
        "dependencies: {tools: [bad]}",
        "dependencies: {tools: [{type: mcp}]}",
        "dependencies: {tools: [{type: mcp, value: x, oauth_callback_port: true}]}",
        "dependencies: {tools: [{type: mcp, value: x, oauth_callback_port: 65536}]}",
    ],
)
def test_invalid_codex_shapes(tmp_path: Path, metadata: str) -> None:
    skill = materialize(
        tmp_path,
        {
            "yaml": "name: example\ndescription: Example.\n",
            "files": {"agents/openai.yaml": metadata},
        },
    )
    assert validate_skill(skill)[0].rule == "openai-shape"


def test_cli_error_status_and_warning_status(tmp_path: Path) -> None:
    skill = materialize(tmp_path, next(case for case in FIXTURES if case["id"] == "field-unknown"))
    result = subprocess.run(
        [sys.executable, "-m", "skills_tooling.validator", str(skill)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert str(skill / "SKILL.md") in result.stdout
    assert "[field-unknown]" in result.stdout and "hint:" in result.stdout
    (skill / "SKILL.md").write_text(
        "---\nname: example\ndescription: Example.\nuser-invocable: true\n---\n"
    )
    result = subprocess.run(
        [sys.executable, "-m", "skills_tooling.validator", str(skill)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0 and "1 warnings" in result.stdout


def test_default_discovery_checks_dev_and_shipped_but_not_nested_resources(tmp_path: Path) -> None:
    for root in ("skills", "dev-skills"):
        directory = tmp_path / root
        directory.mkdir()
        skill = materialize(
            directory,
            {
                "yaml": "name: example\ndescription: Example.\n",
                "files": {"assets/template/SKILL.md": "deliberately not a skill"},
            },
        )
        assert skill.is_dir()
    result = subprocess.run(
        [sys.executable, "-m", "skills_tooling.validator"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0 and "Validated 2 skills" in result.stdout
    (tmp_path / "dev-skills/example/SKILL.md").unlink()
    result = subprocess.run(
        [sys.executable, "-m", "skills_tooling.validator"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1 and "[frontmatter]" in result.stdout


def test_nested_inline_bundled_paths_are_skill_relative(tmp_path: Path) -> None:
    skill = materialize(
        tmp_path,
        {
            "yaml": "name: example\ndescription: Example.\n",
            "body": "[Read](references/guide.md)\n",
            "files": {
                "references/guide.md": "Run `scripts/run.py`.\n",
                "scripts/run.py": "print('hi')\n",
            },
        },
    )
    diagnostics = validate_skill(skill)
    assert [item.rule for item in diagnostics] == ["reference-chain"]


def test_reference_case_is_portable(tmp_path: Path) -> None:
    skill = materialize(
        tmp_path,
        {
            "yaml": "name: example\ndescription: Example.\n",
            "body": "[Read](references/guide.txt)\n",
            "files": {"references/Guide.txt": "content\n"},
        },
    )
    assert validate_skill(skill)[0].rule == "reference-missing"


def test_cli_current_directory_and_missing_entrypoint(tmp_path: Path) -> None:
    skill = materialize(tmp_path, {"yaml": "name: example\ndescription: Example.\n"})
    result = subprocess.run(
        [sys.executable, "-m", "skills_tooling.validator", "."],
        cwd=skill,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout
    (skill / "SKILL.md").unlink()
    (item,) = validate_skill(skill)
    assert item.rule == "frontmatter"
    assert "missing SKILL.md" in item.message and "create SKILL.md" in item.hint


def test_unknown_codex_key_and_invalid_name_are_specific(tmp_path: Path) -> None:
    skill = materialize(
        tmp_path,
        {
            "yaml": "name: bad--name\ndescription: Example.\n",
            "files": {"agents/openai.yaml": "interface: {typo: value}\n"},
        },
    )
    diagnostics = validate_skill(skill)
    assert any(item.rule == "openai-shape" and "typo" in item.message for item in diagnostics)
    assert any(
        item.rule == "name-format"
        and "bad--name" in item.message
        and "consecutive" in item.message
        for item in diagnostics
    )


@pytest.mark.parametrize(
    "filename,content",
    [
        ("scripts/run.py", "def run():\n    handlers[name](args)\n"),
        ("scripts/run.sh", "#!/bin/sh\n`scripts/x.sh`\n"),
    ],
)
def test_linked_source_is_not_markdown(tmp_path: Path, filename: str, content: str) -> None:
    skill = materialize(
        tmp_path,
        {
            "yaml": "name: example\ndescription: Example.\n",
            "body": f"[Run]({filename})\n",
            "files": {filename: content},
        },
    )
    assert validate_skill(skill) == []


@pytest.mark.parametrize(
    "body,rule",
    [
        ('<a href="references/guide.md">Read</a>', None),
        ('<img src="references/missing.png">', "reference-missing"),
        ('<a href="../outside.md">Read</a>', "reference-escape"),
        ('```html\n<img src="missing.png">\n```', None),
    ],
)
def test_html_resources(tmp_path: Path, body: str, rule: str | None) -> None:
    skill = materialize(
        tmp_path,
        {
            "yaml": "name: example\ndescription: Example.\n",
            "body": body,
            "files": {"references/guide.md": "Done.\n"},
        },
    )
    assert [item.rule for item in validate_skill(skill)] == ([] if rule is None else [rule])


def test_reference_case_does_not_list_ancestors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    skill = materialize(
        tmp_path,
        {
            "yaml": "name: example\ndescription: Example.\n",
            "body": "[Read](references/guide.md)",
            "files": {"references/guide.md": "Done.\n"},
        },
    )
    original = Path.iterdir

    def only_inside(path: Path) -> Iterator[Path]:
        assert path.is_relative_to(skill), f"listed ancestor {path}"
        return original(path)

    monkeypatch.setattr(Path, "iterdir", only_inside)
    assert validate_skill(skill) == []


def test_discovery_missing_roots_is_actionable(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "skills_tooling.validator"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "skills: error [discovery]" in result.stdout
    assert "dev-skills: error [discovery]" in result.stdout
    assert "hint:" in result.stdout and "repository root" in result.stdout
    assert "Traceback" not in result.stderr
