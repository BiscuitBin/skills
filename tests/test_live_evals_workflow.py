"""The manual live-eval workflow's safety properties, read from its YAML.

See docs/how-to/live-evals-in-ci.md and docs/adr/0004-eval-tiers-and-ci.md.
"""

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).parents[1]
WORKFLOWS = ROOT / ".github/workflows"
PINNED = re.compile(r"[^@\s]+@[0-9a-f]{40}")
# The only form a secret may take outside a step's env: a presence test.
PRESENCE = re.compile(r"\$\{\{ secrets\.[A-Z_]+ != '' \}\}")


def load(name: str) -> dict[Any, Any]:
    data: dict[Any, Any] = yaml.safe_load((WORKFLOWS / name).read_text())
    return data


@pytest.fixture(scope="module")
def workflow() -> dict[Any, Any]:
    return load("live-evals.yml")


@pytest.fixture(scope="module")
def steps(workflow: dict[Any, Any]) -> list[dict[str, Any]]:
    [job] = workflow["jobs"].values()
    found: list[dict[str, Any]] = job["steps"]
    return found


def test_it_runs_only_when_dispatched_by_hand(workflow: dict[Any, Any]) -> None:
    # YAML 1.1 reads the key `on` as True.
    assert set(workflow[True]) == {"workflow_dispatch"}
    inputs = workflow[True]["workflow_dispatch"]["inputs"]
    assert set(inputs) == {"skills", "agents", "trials", "baseline"}
    assert inputs["agents"]["options"] == ["both", "claude", "codex"]
    assert inputs["trials"]["default"] == "1"
    assert inputs["baseline"] == {**inputs["baseline"], "type": "boolean", "default": False}


def test_it_has_the_least_token_permission_and_an_environment(workflow: dict[Any, Any]) -> None:
    assert workflow["permissions"] == {}
    [job] = workflow["jobs"].values()
    assert job["permissions"] == {"contents": "read"}
    assert job["environment"] == "live-evals"
    assert job["timeout-minutes"] <= 120
    assert workflow["concurrency"]["cancel-in-progress"] is False


def test_every_action_is_pinned_to_a_commit(steps: list[dict[str, Any]]) -> None:
    used = [step["uses"] for step in steps if "uses" in step]
    assert used
    assert [u for u in used if not PINNED.fullmatch(u)] == []


def test_no_expression_is_pasted_into_a_command(steps: list[dict[str, Any]]) -> None:
    assert [step["run"] for step in steps if "${{" in step.get("run", "")] == []


def test_secrets_reach_only_a_steps_env(
    workflow: dict[Any, Any], steps: list[dict[str, Any]]
) -> None:
    for step in steps:
        rest = {k: v for k, v in step.items() if k != "env"}
        assert "secrets." not in yaml.safe_dump(rest), step
        for name, value in step.get("env", {}).items():
            if "secrets." in str(value) and not PRESENCE.fullmatch(str(value)):
                # A value, not a presence test: only the step that needs it.
                assert value == f"${{{{ secrets.{name} }}}}", (name, value)
    [job] = workflow["jobs"].values()
    assert "env" not in job
    assert "env" not in workflow


def test_the_checkout_keeps_no_credential(steps: list[dict[str, Any]]) -> None:
    [checkout] = [s for s in steps if s.get("uses", "").startswith("actions/checkout@")]
    assert checkout["with"]["persist-credentials"] is False


def test_an_agent_cannot_read_the_run_list(steps: list[dict[str, Any]]) -> None:
    [evals] = [s for s in steps if s.get("id") == "evals"]
    assert "</dev/null" in evals["run"]


def test_nothing_is_uploaded_unless_the_scan_passed(steps: list[dict[str, Any]]) -> None:
    [upload] = [s for s in steps if s.get("uses", "").startswith("actions/upload-artifact@")]
    assert "steps.scan.outcome == 'success'" in upload["if"]
    assert upload["with"]["path"] == "eval-results/"


def test_the_setup_matches_the_gate(steps: list[dict[str, Any]]) -> None:
    [ci] = load("ci.yml")["jobs"].values()
    setup = {s["uses"]: s.get("with") for s in ci["steps"] if "uses" in s}
    mine = {s["uses"]: s.get("with") for s in steps if "uses" in s}
    for action, settings in setup.items():
        if action.startswith("actions/checkout@"):
            assert action in mine
            continue
        assert mine.get(action) == settings, action
    runs = [s["run"] for s in steps if "run" in s]
    assert "just initialize" in runs


def test_a_failed_eval_or_report_fails_the_job_after_the_upload(
    steps: list[dict[str, Any]],
) -> None:
    names = [s.get("id") or s.get("name") for s in steps]
    final = steps[-1]
    assert names.index("upload") < len(steps) - 1
    assert "steps.evals.outputs.failed == '1'" in final["if"]
    assert "steps.report.outputs.failed == '1'" in final["if"]
    [report] = [s for s in steps if s.get("id") == "report"]
    assert 'echo "failed=$failed" >>"$GITHUB_OUTPUT"' in report["run"]
