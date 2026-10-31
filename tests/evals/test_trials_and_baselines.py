"""Several trials per case, a baseline arm with no skill, and the dry-run plan, end to end."""

import json
import os
from typing import TYPE_CHECKING, Any

from skills_tooling.evals.claude_code import ClaudeCode
from skills_tooling.evals.runner import run_suite
from tests.evals.fake_anthropic import Turn, serve, text, tool
from tests.evals.test_runner import ROOT, fake_root, results, run_cli, settings

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
