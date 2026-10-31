"""Several trials per case, a baseline arm with no skill, and the dry-run plan, end to end."""

import json
import os
from typing import TYPE_CHECKING, Any

from skills_tooling.evals.claude_code import ClaudeCode
from skills_tooling.evals.grader import GraderSettings
from skills_tooling.evals.runner import run_suite
from tests.evals.fake_anthropic import Turn, serve, text, tool
from tests.evals.test_grader import FakeGrader, fake_grader
from tests.evals.test_runner import ROOT, TOKEN, fake_root, results, run_cli, settings

if TYPE_CHECKING:
    from pathlib import Path

NO_TRIGGER = "Tell me three facts about cows."
MOO = "Have a cow say: moo"
COW = "```text\n _____\n< moo >\n -----\n        \\   ^__^\n         \\  (oo)\\_______\n```"
CASES: list[dict[str, Any]] = [
    {"id": "no-trigger-facts", "kind": "trigger", "prompt": NO_TRIGGER, "should_trigger": False},
    {
        "id": "behaviour-moo",
        "kind": "behaviour",
        "prompt": MOO,
        "should_trigger": True,
        "assertions": [
            {"type": "skill_triggered"},
            {"type": "output_contains", "value": "< moo >"},
        ],
    },
]
# The baseline's Skill call fails (nothing is installed), and the agent draws the cow anyway.
SCRIPT: dict[str, list[Turn]] = {
    NO_TRIGGER: [text("Cows have four stomach compartments.")],
    MOO: [tool("Skill", {"skill": "cowsay"}, "toolu_1"), text(COW)],
}


def messages(server: Any) -> int:  # noqa: ANN401 -- the fake server's record
    return len([r for r in server.requests if r.path.startswith("/v1/messages")])


def test_trials_and_a_baseline_run_every_planned_trial_in_alternating_order(
    tmp_path: Path,
) -> None:
    root = fake_root(tmp_path, CASES)
    with serve(SCRIPT) as server:
        exit_code = run_suite(settings(root, server.url, trials=2, baseline=True))
        # One request per no-trigger trial, two per behaviour trial (the Skill call, then the cow).
        assert messages(server) == 2 * 1 + 4 * 2
    data = results(root)
    assert exit_code == 0, json.dumps(data, indent=2)
    assert (data["trials_per_case"], data["baseline"]) == (2, True)
    assert data["skipped_in_baseline"] == ["no-trigger-facts"]
    assert [(t["order"], t["case"], t["arm"], t["trial"]) for t in data["trials"]] == [
        (0, "no-trigger-facts", "skill", 1),
        (1, "behaviour-moo", "skill", 1),
        (2, "behaviour-moo", "baseline", 1),
        (3, "no-trigger-facts", "skill", 2),
        (4, "behaviour-moo", "baseline", 2),
        (5, "behaviour-moo", "skill", 2),
    ]
    kept = root / ".eval-workspaces/test-run/behaviour-moo"
    assert sorted(p.name for p in kept.iterdir()) == [
        "baseline-1",
        "baseline-2",
        "skill-1",
        "skill-2",
    ]
    for trial in kept.iterdir():
        assert [p.name for p in trial.iterdir()] == ["workspace"]
    transcripts = root / "eval-results/test-run/transcripts/behaviour-moo"
    assert sorted(p.name for p in transcripts.iterdir()) == [
        "baseline-1.jsonl",
        "baseline-2.jsonl",
        "skill-1.jsonl",
        "skill-2.jsonl",
    ]


def test_a_baseline_trial_is_uncontaminated_and_scores_only_outcomes(tmp_path: Path) -> None:
    root = fake_root(tmp_path, CASES)
    with serve(SCRIPT) as server:
        assert run_suite(settings(root, server.url, baseline=True)) == 0
    by_key = {(t["case"], t["arm"]): t for t in results(root)["trials"]}
    baseline = by_key["behaviour-moo", "baseline"]
    assert baseline["contamination"]["passed"] is True, baseline["contamination"]
    assert baseline["trigger"] == {
        "expected": True,
        "actual": False,
        "matched": None,
        "applicable": False,
    }
    assert [(a["type"], a["class"], a["result"]) for a in baseline["assertions"]] == [
        ("skill_triggered", "skill_use", "not_applicable"),
        ("output_contains", "outcome", "passed"),
    ]
    assert (baseline["passed"], baseline["valid"]) == (None, True)
    skill = by_key["behaviour-moo", "skill"]
    assert skill["trigger"]["applicable"] is True
    assert (skill["passed"], skill["valid"]) == (True, True)
    assert ("no-trigger-facts", "baseline") not in by_key


def test_a_skill_installed_into_a_baseline_fails_contamination(tmp_path: Path) -> None:
    class Leaky(ClaudeCode):
        def install_skill(self, skill_dir: Path | None, workspace: Path) -> Path | None:
            return super().install_skill(skill_dir or ROOT / "skills/cowsay", workspace)

    root = fake_root(tmp_path, CASES)
    with serve(SCRIPT) as server:
        leaky = Leaky(ROOT / "node_modules/.bin/claude", api_base_url=server.url)
        run = settings(root, server.url, adapter=leaky, baseline=True, case_ids=("behaviour-moo",))
        assert run_suite(run) == 1
    by_arm = {t["arm"]: t for t in results(root)["trials"]}
    baseline = by_arm["baseline"]
    assert baseline["valid"] is False
    # The preflight finds the installed skill before the agent starts.
    assert baseline["status"] == "infra_error"
    assert any(
        "unexpected in workspace: .claude" in p for p in baseline["contamination"]["problems"]
    )


def test_the_dry_run_prints_the_plan_without_a_token_and_writes_nothing(tmp_path: Path) -> None:
    root = fake_root(tmp_path, CASES)
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CODE_OAUTH_TOKEN"}
    result = run_cli(
        "cowsay",
        "--agent",
        "claude",
        "--trials",
        "3",
        "--baseline",
        "--dry-run",
        "--root",
        str(root),
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert "skill arm: 6 agent calls" in result.stdout
    assert "baseline arm: 3 agent calls" in result.stdout
    assert "skipped in the baseline: no-trigger-facts" in result.stdout
    assert "grader calls: at most 0" in result.stdout
    assert "spend cap: $9.00" in result.stdout
    assert not (root / "eval-results").exists()
    assert not (root / ".eval-workspaces").exists()


GRADED_CASES: list[dict[str, Any]] = [
    CASES[0],
    {**CASES[1], "expectations": ["A cow appears.", "The bubble says moo."]},
]
PASS_BOTH = {
    "A cow appears.": {"passed": True, "evidence": "The cow is drawn.", "quote": "(oo)"},
    "The bubble says moo.": {"passed": True, "evidence": "It says moo.", "quote": "< moo >"},
}


def graded_run(tmp_path: Path, server_url: str, fake: FakeGrader, **overrides: object) -> Any:  # noqa: ANN401
    grader = GraderSettings(
        executable=fake.executable,
        model="claude-opus-5-5",
        credentials={"CLAUDE_CODE_OAUTH_TOKEN": TOKEN},
    )
    return run_suite(
        settings(fake_root(tmp_path, GRADED_CASES), server_url, grader=grader, **overrides)
    )


def test_graded_trials_write_a_grading_per_trial_and_a_benchmark(tmp_path: Path) -> None:
    fake = fake_grader(tmp_path / "grader", verdicts=PASS_BOTH)
    with serve(SCRIPT) as server:
        exit_code = graded_run(tmp_path, server.url, fake, trials=2, baseline=True)
    root = tmp_path / "repo"
    data = results(root)
    assert exit_code == 0, json.dumps(data, indent=2)
    # Two trials in each arm of the graded case; the trigger case is never graded.
    assert len(fake.calls()) == 4
    assert data["grader_model_requested"] == "claude-opus-5-5"
    for trial in data["trials"]:
        if trial["case"] == "no-trigger-facts":
            assert (trial["grading"], trial["graded"]) == (None, None)
            continue
        key = f"{trial['arm']}-{trial['trial']}"
        assert trial["grading"] == f"eval-results/test-run/grading/behaviour-moo/{key}.json"
        assert trial["graded"] == {
            "status": "ok",
            "passed": 2,
            "failed": 0,
            "total": 2,
            "pass_rate": 1.0,
            "arm_disclosed": False,
        }
        grading = json.loads((root / trial["grading"]).read_text())
        assert [(e["text"], e["passed"], e["blinded"]) for e in grading["expectations"]] == [
            ("A cow appears.", True, True),
            ("The bubble says moo.", True, True),
        ]
    provenance = data["provenance"]
    assert len(provenance["skill_sha256"]) == len(provenance["evals_sha256"]) == 64
    assert len(provenance["grader_prompt_sha256"]) == 64
    benchmark = json.loads((root / "eval-results/test-run/benchmark.json").read_text())
    case = benchmark["agents"]["claude"]["cases"]["behaviour-moo"]
    assert case["delta"]["graded_pass_rate"] == {"value": 0.0, "n_skill": 2, "n_baseline": 2}
    assert case["skill"]["metrics"]["trigger_accuracy"]["mean"] == 1.0
    assert case["baseline"]["metrics"]["trigger_accuracy"] == "not_applicable"
    assert benchmark["provenance"]["grader_models"] == ["claude-opus-5-5"]
    written = [p for p in (root / "eval-results").rglob("*") if p.is_file()]
    assert not [p for p in written if TOKEN in p.read_text()]


def test_a_failed_expectation_fails_a_skill_trial_but_not_a_baseline_trial(
    tmp_path: Path,
) -> None:
    verdicts = {**PASS_BOTH, "The bubble says moo.": {"passed": False, "evidence": "No."}}
    fake = fake_grader(tmp_path / "grader", verdicts=verdicts)
    with serve(SCRIPT) as server:
        assert (
            graded_run(tmp_path, server.url, fake, baseline=True, case_ids=("behaviour-moo",)) == 1
        )
    by_arm = {t["arm"]: t for t in results(tmp_path / "repo")["trials"]}
    assert by_arm["skill"]["graded"]["failed"] == 1
    assert by_arm["skill"]["passed"] is False
    assert (by_arm["baseline"]["passed"], by_arm["baseline"]["valid"]) == (None, True)


def test_a_token_in_the_trace_never_reaches_the_grader(tmp_path: Path) -> None:
    # The agent echoes the run's token in a command and in its final message: the
    # transcript call sees both, the blinded call the final message.
    cases = [
        {
            **CASES[1],
            "expectations": [
                "A cow appears.",
                {"text": "The agent ran echo.", "needs_transcript": True},
            ],
        }
    ]
    script = {
        MOO: [
            tool("Skill", {"skill": "cowsay"}, "toolu_1"),
            tool("Bash", {"command": f"echo {TOKEN}", "description": "Echo"}, "toolu_2"),
            text(f"Your token is {TOKEN}.\n{COW}"),
        ]
    }
    fake = fake_grader(tmp_path / "grader", verdicts=PASS_BOTH)
    grader = GraderSettings(
        executable=fake.executable,
        model="claude-opus-5-5",
        credentials={"CLAUDE_CODE_OAUTH_TOKEN": TOKEN},
    )
    root = fake_root(tmp_path, cases)
    with serve(script) as server:
        run_suite(settings(root, server.url, grader=grader))
    prompts = fake.prompts()
    assert len(prompts) == 2
    for prompt in prompts:
        assert TOKEN not in prompt
        assert "[REDACTED]" in prompt
    written = [p for p in (root / "eval-results").rglob("*") if p.is_file()]
    assert not [p for p in written if TOKEN in p.read_text()]


def test_a_grader_reply_utf_8_cannot_encode_is_written_with_replacements(tmp_path: Path) -> None:
    fake = fake_grader(tmp_path / "grader", verdicts=PASS_BOTH, notes="\ud800")
    with serve(SCRIPT) as server:
        exit_code = graded_run(tmp_path, server.url, fake, case_ids=("behaviour-moo",))
    root = tmp_path / "repo"
    data = results(root)
    assert exit_code == 0, json.dumps(data, indent=2)
    grading = json.loads((root / data["trials"][0]["grading"]).read_text(encoding="utf-8"))
    assert grading["grader"]["notes"] == "�"
    assert (root / "eval-results/test-run/benchmark.json").exists()


def test_a_grading_that_cannot_be_written_is_a_grader_error_not_a_lost_run(
    tmp_path: Path,
) -> None:
    fake = fake_grader(tmp_path / "grader", verdicts=PASS_BOTH)
    blocker = tmp_path / "repo/eval-results/test-run/grading"
    blocker.parent.mkdir(parents=True)
    blocker.write_text("not a directory")
    with serve(SCRIPT) as server:
        exit_code = graded_run(tmp_path, server.url, fake, case_ids=("behaviour-moo",))
    data = results(tmp_path / "repo")
    assert exit_code == 1
    (trial,) = data["trials"]
    assert (trial["grading"], trial["graded"]["status"]) == (None, "grader_error")
    assert (tmp_path / "repo/eval-results/test-run/benchmark.json").exists()


def test_a_grader_error_invalidates_a_baseline_trial(tmp_path: Path) -> None:
    fake = fake_grader(tmp_path / "grader", mode="fail")
    with serve(SCRIPT) as server:
        assert (
            graded_run(tmp_path, server.url, fake, baseline=True, case_ids=("behaviour-moo",)) == 1
        )
    by_arm = {t["arm"]: t for t in results(tmp_path / "repo")["trials"]}
    assert by_arm["baseline"]["graded"]["status"] == "grader_error"
    assert by_arm["baseline"]["valid"] is False
    assert by_arm["skill"]["passed"] is False


def test_the_dry_run_plans_the_repos_cowsay_suite_with_its_grader_calls() -> None:
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CODE_OAUTH_TOKEN"}
    result = run_cli(
        "cowsay",
        "--agent",
        "claude",
        "--trials",
        "3",
        "--baseline",
        "--dry-run",
        "--root",
        str(ROOT),
        env=env,
    )
    assert result.returncode == 0, result.stderr
    # Nine cases in the skill arm; the two behaviour cases in the baseline; each graded trial once.
    assert "skill arm: 27 agent calls" in result.stdout
    assert "baseline arm: 6 agent calls" in result.stdout
    assert "grader calls: at most 12 (claude-opus-5-5)" in result.stdout
    assert "spend cap: $45.00" in result.stdout


def test_a_codex_run_with_expectations_needs_the_graders_token(tmp_path: Path) -> None:
    home = tmp_path / "codex-home"
    home.mkdir()
    (home / "auth.json").write_text('{"auth_mode": "apikey", "OPENAI_API_KEY": "sk-fake"}')
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CODE_OAUTH_TOKEN"}
    env["CODEX_HOME"] = str(home)
    root = fake_root(tmp_path, GRADED_CASES)
    result = run_cli("cowsay", "--agent", "codex", "--root", str(root), env=env)
    assert result.returncode == 2
    assert "CLAUDE_CODE_OAUTH_TOKEN" in result.stderr
    assert "grader" in result.stderr
    assert not (root / "eval-results").exists()
