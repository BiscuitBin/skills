"""The runner end to end: the pinned CLI, the fake API, results and exit codes."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from skills_tooling.evals import runner, workspace
from skills_tooling.evals.assertions import expected_script_output
from skills_tooling.evals.claude_code import ClaudeCode
from skills_tooling.evals.contamination import NeverAppear
from skills_tooling.evals.runner import RunSettings, run_suite
from tests.evals.fake_anthropic import Turn, serve, text, tool

if TYPE_CHECKING:
    import pytest

ROOT = Path(__file__).parents[2]
TOKEN = "sk-ant-oat01-fake-runner-test"
TRIGGER = "Make a cow say moo."
NO_TRIGGER = "Tell me three facts about cows."
BEHAVIOUR = "Have a cow say: Ship it, team!"
ARGS = ["--", "Ship it, team!"]
COW = expected_script_output(ROOT / "skills/cowsay", "scripts/cowsay.py", tuple(ARGS))
RUN = "python3 .claude/skills/cowsay/scripts/cowsay.py -- 'Ship it, team!'"
CASES: list[dict[str, Any]] = [
    {"id": "trigger-moo", "kind": "trigger", "prompt": TRIGGER, "should_trigger": True},
    {"id": "no-trigger-facts", "kind": "trigger", "prompt": NO_TRIGGER, "should_trigger": False},
    {
        "id": "behaviour-ship-it",
        "kind": "behaviour",
        "prompt": BEHAVIOUR,
        "should_trigger": True,
        "assertions": [
            {"type": "skill_triggered"},
            {"type": "script_ran", "script": "scripts/cowsay.py", "args": ARGS},
            {"type": "final_contains_script_output", "script": "scripts/cowsay.py", "args": ARGS},
        ],
    },
]
GOOD: dict[str, list[Turn]] = {
    TRIGGER: [tool("Skill", {"skill": "cowsay"}, "toolu_1"), text("Moo.")],
    NO_TRIGGER: [text("Cows have four stomach compartments.")],
    BEHAVIOUR: [
        tool("Skill", {"skill": "cowsay"}, "toolu_1"),
        tool("Bash", {"command": RUN, "description": "Run cowsay"}, "toolu_2"),
        text(f"```text\n{COW}```"),
    ],
}


def fake_root(tmp_path: Path, cases: list[dict[str, Any]] = CASES) -> Path:
    root = tmp_path / "repo"
    shutil.copytree(ROOT / "skills/cowsay", root / "skills/cowsay")
    (root / "evals/cowsay").mkdir(parents=True)
    (root / "evals/cowsay/evals.json").write_text(
        json.dumps({"skill_name": "cowsay", "evals": cases})
    )
    (root / ".gitignore").write_text(".eval-workspaces/\neval-results/\n")
    workspace.git("init", "--quiet", cwd=root)
    return root


def settings(root: Path, url: str, **overrides: object) -> RunSettings:
    fields: dict[str, Any] = {
        "root": root,
        "skill": "cowsay",
        "adapter": ClaudeCode(ROOT / "node_modules/.bin/claude", api_base_url=url),
        "model": "claude-sonnet-5-5",
        "timeout": 90.0,
        "credentials": {"CLAUDE_CODE_OAUTH_TOKEN": TOKEN},
        "case_ids": (),
        "run_id": "test-run",
        "never": NeverAppear({"cross-model-review": "dev skill"}, ()),
        **overrides,
    }
    return RunSettings(**fields)


def results(root: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((root / "eval-results/test-run/results.json").read_text())
    return data


def test_a_passing_run_records_every_trial_and_exits_zero(tmp_path: Path) -> None:
    root = fake_root(tmp_path)
    with serve(GOOD) as server:
        exit_code = run_suite(settings(root, server.url))
    data = results(root)
    assert exit_code == 0, json.dumps(data, indent=2)
    assert (data["skill"], data["agent"], data["passed"]) == ("cowsay", "claude", True)
    assert data["credential_env"] == ["CLAUDE_CODE_OAUTH_TOKEN"]
    by_case = {trial["case"]: trial for trial in data["trials"]}
    assert set(by_case) == {"trigger-moo", "no-trigger-facts", "behaviour-ship-it"}
    trial = by_case["behaviour-ship-it"]
    assert (trial["cli_version"], trial["model"], trial["status"]) == (
        "2.1.309",
        "claude-sonnet-5-5",
        "ok",
    )
    assert trial["trigger"] == {"expected": True, "actual": True, "matched": True}
    assert trial["contamination"]["passed"] is True
    assert [(a["type"], a["result"]) for a in trial["assertions"]] == [
        ("skill_triggered", "passed"),
        ("script_ran", "passed"),
        ("final_contains_script_output", "passed"),
    ]
    assert trial["started_at"] <= trial["finished_at"]
    assert by_case["no-trigger-facts"]["trigger"] == {
        "expected": False,
        "actual": False,
        "matched": True,
    }
    transcript = root / trial["transcript"]
    assert transcript.is_file()
    assert transcript.is_relative_to(root / "eval-results/test-run/transcripts")
    kept = root / ".eval-workspaces/test-run/behaviour-ship-it"
    assert [p.name for p in kept.iterdir()] == ["workspace"]


def test_a_wrong_trigger_fails_the_run(tmp_path: Path) -> None:
    root = fake_root(tmp_path)
    script = dict(GOOD)
    script[NO_TRIGGER] = [tool("Skill", {"skill": "cowsay"}, "toolu_1"), text("Moo.")]
    with serve(script) as server:
        assert run_suite(settings(root, server.url, case_ids=("no-trigger-facts",))) == 1
    [trial] = results(root)["trials"]
    assert trial["trigger"] == {"expected": False, "actual": True, "matched": False}


def test_an_infrastructure_error_is_not_scored(tmp_path: Path) -> None:
    root = fake_root(tmp_path)
    hang = [tool("Bash", {"command": "sleep 600", "description": "Wait"}, "toolu_1"), text("x")]
    with serve(hang) as server:
        assert run_suite(settings(root, server.url, timeout=3)) == 1
    for trial in results(root)["trials"]:
        assert trial["status"] == "infra_error"
        assert "timed out" in trial["status_reason"]
        assert trial["trigger"]["matched"] is None
        assert {a["result"] for a in trial["assertions"]} <= {"not_scored"}


def test_the_case_filter_runs_exactly_one_trial(tmp_path: Path) -> None:
    root = fake_root(tmp_path)
    with serve(GOOD) as server:
        assert run_suite(settings(root, server.url, case_ids=("no-trigger-facts",))) == 0
        assert len([r for r in server.requests if r.path.startswith("/v1/messages")]) == 1
    assert [t["case"] for t in results(root)["trials"]] == ["no-trigger-facts"]


def test_a_contaminated_trial_fails_even_when_the_case_passes(tmp_path: Path) -> None:
    class Leaky(ClaudeCode):
        def install_skill(self, skill_dir: Path | None, workspace: Path) -> Path | None:
            installed = super().install_skill(skill_dir, workspace)
            canary = workspace.parent / "home/.claude/skills/cross-model-review"
            canary.mkdir(parents=True)
            (canary / "SKILL.md").write_text(
                "---\nname: cross-model-review\ndescription: x\n---\n"
            )
            return installed

    root = fake_root(tmp_path)
    with serve(GOOD) as server:
        leaky = Leaky(ROOT / "node_modules/.bin/claude", api_base_url=server.url)
        assert run_suite(settings(root, server.url, adapter=leaky, case_ids=("trigger-moo",))) == 1
    [trial] = results(root)["trials"]
    assert trial["trigger"]["matched"] is True
    assert trial["contamination"]["passed"] is False
    assert any("cross-model-review" in p for p in trial["contamination"]["problems"])


def test_a_failed_preflight_skips_the_agent(tmp_path: Path) -> None:
    root = fake_root(tmp_path)
    (root / ".gitignore").write_text("eval-results/\n")
    with serve(GOOD) as server:
        assert run_suite(settings(root, server.url, case_ids=("trigger-moo",))) == 1
        assert server.requests == []
    [trial] = results(root)["trials"]
    assert trial["status"] == "infra_error"
    assert "gitignored" in trial["status_reason"]


def run_cli(*args: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "skills_tooling.evals", "run", *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_the_command_refuses_to_start_without_the_token(tmp_path: Path) -> None:
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CODE_OAUTH_TOKEN"}
    root = fake_root(tmp_path)
    result = run_cli("cowsay", "--agent", "claude", "--root", str(root), env=env)
    assert result.returncode == 2
    assert "CLAUDE_CODE_OAUTH_TOKEN" in result.stderr
    assert not (root / "eval-results").exists()


def test_the_command_rejects_an_unknown_case(tmp_path: Path) -> None:
    env = {**os.environ, "CLAUDE_CODE_OAUTH_TOKEN": TOKEN}
    root = fake_root(tmp_path)
    result = run_cli("cowsay", "--agent", "claude", "--case", "nope", "--root", str(root), env=env)
    assert result.returncode == 2
    assert "unknown case 'nope'" in result.stderr
    assert not (root / "eval-results").exists()


def test_a_harness_error_in_one_trial_is_recorded_and_the_rest_still_run(tmp_path: Path) -> None:
    class Broken(ClaudeCode):
        def run(self, prompt: str, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
            if prompt == TRIGGER:
                msg = "simulated harness failure"
                raise RuntimeError(msg)
            return super().run(prompt, *args, **kwargs)

    root = fake_root(tmp_path)
    with serve(GOOD) as server:
        broken = Broken(ROOT / "node_modules/.bin/claude", api_base_url=server.url)
        assert run_suite(settings(root, server.url, adapter=broken)) == 1
    by_case = {trial["case"]: trial for trial in results(root)["trials"]}
    assert by_case["trigger-moo"]["status"] == "infra_error"
    assert "simulated harness failure" in by_case["trigger-moo"]["status_reason"]
    assert by_case["no-trigger-facts"]["passed"] is True
    assert [p.name for p in (root / ".eval-workspaces/test-run/trigger-moo").iterdir()] == [
        "workspace"
    ]


def test_the_command_refuses_to_start_without_the_pinned_cli(tmp_path: Path) -> None:
    env = {**os.environ, "CLAUDE_CODE_OAUTH_TOKEN": TOKEN}
    root = fake_root(tmp_path)
    result = run_cli("cowsay", "--agent", "claude", "--root", str(root), env=env)
    assert result.returncode == 2
    assert "node_modules/.bin/claude" in result.stderr
    assert "just initialize" in result.stderr
    assert not (root / "eval-results").exists()


def test_a_scoring_failure_keeps_the_runs_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(*_args: object, **_kwargs: object) -> object:
        raise subprocess.TimeoutExpired(["cowsay.py"], 30)

    monkeypatch.setattr(runner, "evaluate", broken)
    root = fake_root(tmp_path)
    with serve(GOOD) as server:
        assert run_suite(settings(root, server.url, case_ids=("behaviour-ship-it",))) == 1
    [trial] = results(root)["trials"]
    assert trial["status"] == "infra_error"
    assert "while scoring" in trial["status_reason"]
    assert (trial["cli_version"], trial["model"]) == ("2.1.309", "claude-sonnet-5-5")
    assert (root / trial["transcript"]).is_file()
    assert trial["contamination"]["passed"] is True
    assert {a["result"] for a in trial["assertions"]} == {"not_scored"}
    assert trial["passed"] is False


def test_the_codex_command_refuses_to_start_without_a_project_login(tmp_path: Path) -> None:
    root = fake_root(tmp_path)
    empty = tmp_path / "codex-home"
    empty.mkdir()
    env = {**os.environ, "CODEX_HOME": str(empty)}
    result = run_cli("cowsay", "--agent", "codex", "--root", str(root), env=env)
    assert result.returncode == 2
    assert f"{empty}/auth.json" in result.stderr
    assert "codex login" in result.stderr
    assert not (root / "eval-results").exists()


def test_the_codex_command_refuses_to_start_without_codex_home(tmp_path: Path) -> None:
    root = fake_root(tmp_path)
    env = {k: v for k, v in os.environ.items() if k != "CODEX_HOME"}
    result = run_cli("cowsay", "--agent", "codex", "--root", str(root), env=env)
    assert result.returncode == 2
    assert "CODEX_HOME is not set" in result.stderr


def test_the_codex_command_refuses_to_start_without_the_pinned_cli(tmp_path: Path) -> None:
    root = fake_root(tmp_path)
    home = tmp_path / "codex-home"
    home.mkdir()
    (home / "auth.json").write_text('{"auth_mode": "apikey", "OPENAI_API_KEY": "sk-fake"}')
    env = {**os.environ, "CODEX_HOME": str(home)}
    result = run_cli("cowsay", "--agent", "codex", "--root", str(root), env=env)
    assert result.returncode == 2
    assert "node_modules/@openai" in result.stderr
    assert "just initialize" in result.stderr
