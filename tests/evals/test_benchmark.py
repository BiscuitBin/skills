"""The benchmark: per-case, per-arm statistics, deltas, notes and provenance."""

import json
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any

import pytest

from skills_tooling.evals import workspace
from skills_tooling.evals.benchmark import (
    aggregate,
    file_sha256,
    git_state,
    provenance,
    stat,
    table,
    tree_sha256,
)

if TYPE_CHECKING:
    from collections.abc import Callable

FIXTURES = Path(__file__).parents[1] / "fixtures/evals/benchmark"
SHIP = "behaviour-ship-it"


def load(scenario: str) -> tuple[dict[str, Any], dict[str, dict[str, Any] | None]]:
    """The run record and its gradings, keyed by path, None for a file that is missing."""
    root = FIXTURES / scenario
    run: dict[str, Any] = json.loads((root / "results.json").read_text())
    gradings: dict[str, dict[str, Any] | None] = {}
    for trial in run["trials"]:
        if trial["grading"] is None:
            continue
        # The recorded path is eval-results/<run-id>/grading/...; the fixture keeps grading/...
        inside = PurePosixPath(trial["grading"]).relative_to(f"eval-results/{run['run_id']}")
        path = root / inside
        gradings[trial["grading"]] = json.loads(path.read_text()) if path.exists() else None
    return run, gradings


def test_stat_of_two_values_has_a_sample_stddev() -> None:
    assert stat([1.0, 0.5]) == {
        "mean": 0.75,
        "stddev": pytest.approx(0.353553, abs=1e-6),
        "min": 0.5,
        "max": 1.0,
        "n": 2,
    }


def test_stat_of_nothing_is_null_and_of_one_value_has_no_stddev() -> None:
    assert stat([]) is None
    assert stat([0.0]) == {"mean": 0.0, "stddev": None, "min": 0.0, "max": 0.0, "n": 1}


def test_one_trial_has_no_stddev_and_says_its_spread_is_not_meaningful() -> None:
    case = aggregate(*load("one-trial"))["agents"]["claude"]["cases"][SHIP]
    skill = case["skill"]
    assert skill["n_planned"] == 1
    assert skill["n_scored"] == 1
    assert skill["metrics"]["deterministic_pass_rate"] == {
        "mean": 0.5,
        "stddev": None,
        "min": 0.5,
        "max": 0.5,
        "n": 1,
    }
    assert skill["metrics"]["graded_pass_rate"]["mean"] == pytest.approx(2 / 3)
    assert skill["metrics"]["outcome_pass_rate"]["mean"] == pytest.approx(0.6)
    assert skill["metrics"]["trigger_accuracy"]["mean"] == 1.0
    assert skill["metrics"]["skill_use_pass_rate"]["mean"] == 1.0
    assert any(note.startswith("n < 3: spread not meaningful") for note in case["notes"])


def test_the_baseline_does_not_apply_trigger_accuracy_or_skill_use() -> None:
    baseline = aggregate(*load("paired"))["agents"]["claude"]["cases"][SHIP]["baseline"]
    assert baseline["n_planned"] == 3
    assert baseline["metrics"]["trigger_accuracy"] == "not_applicable"
    assert baseline["metrics"]["skill_use_pass_rate"] == "not_applicable"
    # Its outcome assertions are scored: 1 of 2, 0 of 2, 1 of 2.
    assert baseline["metrics"]["deterministic_pass_rate"]["n"] == 3
    assert baseline["metrics"]["deterministic_pass_rate"]["mean"] == pytest.approx(1 / 3)


def test_delta_is_skill_mean_minus_baseline_mean_with_both_arms_n() -> None:
    case = aggregate(*load("paired"))["agents"]["claude"]["cases"][SHIP]
    # Skill: deterministic 1, 1/2, 1; graded 2/3, 1, 1; outcome 4/5, 4/5, 5/5.
    # Baseline: deterministic 1/2, 0, 1/2; graded 2/3, (grader error), 0 (invalid reply);
    # outcome 3/5, (grader error), 1/5.
    assert case["delta"] == {
        "deterministic_pass_rate": {
            "value": pytest.approx(0.5),
            "n_skill": 3,
            "n_baseline": 3,
        },
        "graded_pass_rate": {"value": pytest.approx(5 / 9), "n_skill": 3, "n_baseline": 2},
        "outcome_pass_rate": {
            "value": pytest.approx(7 / 15),
            "n_skill": 3,
            "n_baseline": 2,
        },
    }
    unequal = [note for note in case["notes"] if note.startswith("unequal n")]
    assert len(unequal) == 2
    assert any("graded_pass_rate" in note and "3" in note and "2" in note for note in unequal)


def test_delta_is_null_when_only_the_baseline_has_nothing_to_measure() -> None:
    run, gradings = load("paired")
    for trial in run["trials"]:
        if trial["case"] == SHIP and trial["arm"] == "baseline":
            gradings[trial["grading"]] = None
    case = aggregate(run, gradings)["agents"]["claude"]["cases"][SHIP]
    assert case["delta"]["graded_pass_rate"] == {"value": None, "n_skill": 3, "n_baseline": 0}
    assert case["delta"]["outcome_pass_rate"] == {"value": None, "n_skill": 3, "n_baseline": 0}
    # A null delta has no unequal-n note; the grader-error note says why it is null.
    assert not any(note.startswith("unequal n") for note in case["notes"])
    assert "grader errors excluded: 0 (skill) / 3 (baseline)" in case["notes"]
    # The skill passed the first two in 3 of 3, but the baseline has no verdict to compare.
    assert [row["baseline"] for row in case["expectations"]] == [{"passed": 0, "n": 0}] * 3
    assert not any(note.startswith("non-discriminating") for note in case["notes"])


def test_the_grader_error_note_names_an_error_in_either_arm_alone() -> None:
    # The fixture's only grader error is baseline-2.
    notes = aggregate(*load("paired"))["agents"]["claude"]["cases"][SHIP]["notes"]
    assert "grader errors excluded: 0 (skill) / 1 (baseline)" in notes
    run, gradings = load("paired")
    root = f"eval-results/{run['run_id']}/grading/{SHIP}"
    gradings[f"{root}/baseline-2.json"] = gradings[f"{root}/baseline-1.json"]
    gradings[f"{root}/skill-1.json"] = None
    notes = aggregate(run, gradings)["agents"]["claude"]["cases"][SHIP]["notes"]
    assert "grader errors excluded: 1 (skill) / 0 (baseline)" in notes


def test_a_case_skipped_in_the_baseline_has_no_baseline_and_an_empty_delta() -> None:
    case = aggregate(*load("paired"))["agents"]["claude"]["cases"]["should-trigger"]
    assert case["baseline"] == "skipped"
    assert case["delta"] == {}


def test_a_missing_grading_file_is_a_grader_error_excluded_only_from_graded_metrics() -> None:
    run, gradings = load("paired")
    # skill-2's file is unreadable; baseline-2's grader timed out in the fixture.
    gradings[f"eval-results/{run['run_id']}/grading/{SHIP}/skill-2.json"] = None
    case = aggregate(run, gradings)["agents"]["claude"]["cases"][SHIP]
    skill, baseline = case["skill"], case["baseline"]
    assert skill["n_scored"] == 3
    assert skill["n_grader_error"] == 1
    assert baseline["n_grader_error"] == 1
    assert skill["metrics"]["trigger_accuracy"]["n"] == 3
    assert skill["metrics"]["skill_use_pass_rate"]["n"] == 3
    assert skill["metrics"]["deterministic_pass_rate"]["n"] == 3
    assert skill["metrics"]["graded_pass_rate"]["n"] == 2
    assert skill["metrics"]["outcome_pass_rate"]["n"] == 2
    assert baseline["metrics"]["deterministic_pass_rate"]["n"] == 3
    assert baseline["metrics"]["graded_pass_rate"]["n"] == 2
    # Excluded, not counted as 0: skill-1 and skill-3 graded 2/3 and 3/3.
    assert skill["metrics"]["graded_pass_rate"]["mean"] == pytest.approx(5 / 6)
    assert "grader errors excluded: 1 (skill) / 1 (baseline)" in case["notes"]


def test_a_scorable_trial_with_no_grading_path_is_a_grader_error() -> None:
    run, gradings = load("one-trial")
    run["trials"][0]["grading"] = None
    skill = aggregate(run, gradings)["agents"]["claude"]["cases"][SHIP]["skill"]
    assert skill["n_grader_error"] == 1
    assert skill["metrics"]["deterministic_pass_rate"]["n"] == 1
    assert skill["metrics"]["graded_pass_rate"] is None
    assert skill["metrics"]["outcome_pass_rate"] is None


def test_a_rejected_and_an_invalid_reply_grading_each_count_as_zero_whatever_they_say() -> None:
    run, gradings = load("paired")
    rejected = gradings[f"eval-results/{run['run_id']}/grading/{SHIP}/skill-3.json"]
    invalid = gradings[f"eval-results/{run['run_id']}/grading/{SHIP}/baseline-3.json"]
    assert rejected is not None
    assert invalid is not None
    # skill-3's file says 3 of 3 passed; the status overrides it.
    rejected["grader"]["status"] = "rejected"
    for expectation in invalid["expectations"]:
        expectation["passed"] = True
    case = aggregate(run, gradings)["agents"]["claude"]["cases"][SHIP]
    skill, baseline = case["skill"], case["baseline"]
    assert skill["n_rejected"] == 1
    # Graded 2/3, 1, 0 (rejected); outcome 4/5, 4/5, 2/5 (both assertions, no expectation).
    assert skill["metrics"]["graded_pass_rate"]["n"] == 3
    assert skill["metrics"]["graded_pass_rate"]["mean"] == pytest.approx(5 / 9)
    assert skill["metrics"]["graded_pass_rate"]["min"] == 0.0
    assert skill["metrics"]["outcome_pass_rate"]["mean"] == pytest.approx(2 / 3)
    # baseline-3's reply was invalid: 2/3 and 0.
    assert baseline["n_invalid_reply"] == 1
    assert baseline["metrics"]["graded_pass_rate"]["n"] == 2
    assert baseline["metrics"]["graded_pass_rate"]["mean"] == pytest.approx(1 / 3)
    assert baseline["metrics"]["graded_pass_rate"]["min"] == 0.0
    # Their verdicts count as fails: skill-1 failed the third, skill-3 now fails all three.
    assert [(row["skill"], row["baseline"]) for row in case["expectations"]] == [
        ({"passed": 2, "n": 3}, {"passed": 1, "n": 2}),
        ({"passed": 2, "n": 3}, {"passed": 1, "n": 2}),
        ({"passed": 1, "n": 3}, {"passed": 0, "n": 2}),
    ]


def no_expectations(grading: dict[str, Any]) -> None:
    grading["expectations"] = []


def swapped_expectations(grading: dict[str, Any]) -> None:
    first, second, third = grading["expectations"]
    grading["expectations"] = [second, first, third]


def renamed_expectation(grading: dict[str, Any]) -> None:
    grading["expectations"][0]["text"] = "The response is written in English."


def extra_expectation(grading: dict[str, Any]) -> None:
    grading["expectations"].append({**grading["expectations"][0], "text": "An extra expectation."})


def no_status(grading: dict[str, Any]) -> None:
    del grading["grader"]["status"]


def no_grader_model(grading: dict[str, Any]) -> None:
    del grading["grader"]["model"]


def no_grader_cli_version(grading: dict[str, Any]) -> None:
    del grading["grader"]["cli_version"]


def unhashable_grader_model(grading: dict[str, Any]) -> None:
    grading["grader"]["model"] = ["claude-opus-5-5"]


def no_grader(grading: dict[str, Any]) -> None:
    del grading["grader"]


def no_expectations_key(grading: dict[str, Any]) -> None:
    del grading["expectations"]


def untexted_expectation(grading: dict[str, Any]) -> None:
    del grading["expectations"][0]["text"]


def no_passed(grading: dict[str, Any]) -> None:
    del grading["expectations"][0]["passed"]


def no_disclosure(grading: dict[str, Any]) -> None:
    del grading["arm_disclosed"]


def not_an_object(grading: dict[str, Any]) -> None:
    grading.clear()
    grading["grader"] = "ok"
    grading["expectations"] = "e1"


@pytest.mark.parametrize(
    "spoil",
    [
        no_expectations,
        swapped_expectations,
        renamed_expectation,
        extra_expectation,
        no_status,
        no_grader_model,
        no_grader_cli_version,
        unhashable_grader_model,
        no_grader,
        no_expectations_key,
        untexted_expectation,
        no_passed,
        no_disclosure,
        not_an_object,
    ],
)
def test_a_grading_that_does_not_match_the_cases_rubric_is_a_grader_error(
    spoil: Callable[[dict[str, Any]], None],
) -> None:
    run, gradings = load("paired")
    skill_1 = gradings[f"eval-results/{run['run_id']}/grading/{SHIP}/skill-1.json"]
    assert skill_1 is not None
    spoil(skill_1)
    case = aggregate(run, gradings)["agents"]["claude"]["cases"][SHIP]
    skill = case["skill"]
    assert skill["n_grader_error"] == 1
    assert skill["metrics"]["deterministic_pass_rate"]["n"] == 3
    # Only skill-2 and skill-3 are graded, 3 of 3 each.
    assert skill["metrics"]["graded_pass_rate"] == {
        "mean": 1.0,
        "stddev": 0.0,
        "min": 1.0,
        "max": 1.0,
        "n": 2,
    }
    assert skill["metrics"]["outcome_pass_rate"]["n"] == 2
    assert [row["skill"] for row in case["expectations"]] == [{"passed": 2, "n": 2}] * 3


def test_all_infra_errors_leave_every_metric_null_and_are_counted() -> None:
    run, gradings = load("paired")
    for trial in run["trials"]:
        if trial["case"] == SHIP:
            trial["status"] = "infra_error"
    case = aggregate(run, gradings)["agents"]["claude"]["cases"][SHIP]
    for arm in ("skill", "baseline"):
        assert case[arm]["n_planned"] == 3
        assert case[arm]["n_scored"] == 0
        assert case[arm]["n_infra_error"] == 3
        assert case[arm]["n_grader_error"] == 0
    assert all(value is None for value in case["skill"]["metrics"].values())
    assert case["baseline"]["metrics"]["deterministic_pass_rate"] is None
    assert case["delta"]["outcome_pass_rate"] == {"value": None, "n_skill": 0, "n_baseline": 0}


def test_contaminated_and_secret_found_trials_are_excluded_from_every_metric() -> None:
    run, gradings = load("paired")
    trials = {(t["case"], t["arm"], t["trial"]): t for t in run["trials"]}
    trials[SHIP, "skill", 2]["contamination"]["passed"] = False
    # A secret found outranks the contamination failure it also has.
    trials[SHIP, "skill", 3]["contamination"]["passed"] = False
    trials[SHIP, "skill", 3]["secret_found"] = {"files": ["notes.txt"], "deleted": True}
    skill = aggregate(run, gradings)["agents"]["claude"]["cases"][SHIP]["skill"]
    assert skill["n_scored"] == 1
    assert skill["n_contaminated"] == 1
    assert skill["n_secret_found"] == 1
    assert {name: metric["n"] for name, metric in skill["metrics"].items()} == dict.fromkeys(
        skill["metrics"], 1
    )


def test_a_trial_counts_once_secret_found_then_infra_error_then_contaminated() -> None:
    run, gradings = load("paired")
    trials = {(t["case"], t["arm"], t["trial"]): t for t in run["trials"]}
    # A secret found outranks an infra error and a failed contamination check.
    trials[SHIP, "skill", 1]["secret_found"] = {"files": ["notes.txt"], "deleted": True}
    trials[SHIP, "skill", 1]["status"] = "infra_error"
    trials[SHIP, "skill", 1]["contamination"]["passed"] = False
    # A failed preflight is an infra error whose contamination check also failed.
    trials[SHIP, "skill", 2]["status"] = "infra_error"
    trials[SHIP, "skill", 2]["contamination"]["passed"] = False
    # A check that never gave a verdict on a finished trial is not a pass.
    trials[SHIP, "skill", 3]["contamination"]["passed"] = None
    skill = aggregate(run, gradings)["agents"]["claude"]["cases"][SHIP]["skill"]
    counts = ("n_scored", "n_secret_found", "n_infra_error", "n_contaminated")
    assert {key: skill[key] for key in counts} == {
        "n_scored": 0,
        "n_secret_found": 1,
        "n_infra_error": 1,
        "n_contaminated": 1,
    }
    assert all(metric is None for metric in skill["metrics"].values())


def test_unscored_and_not_applicable_assertions_leave_every_denominator() -> None:
    run, gradings = load("paired")
    skill_1 = next(t for t in run["trials"] if t["case"] == SHIP and t["arm"] == "skill")
    skill_1["assertions"] += [
        {"type": "file_exists", "class": "outcome", "result": "not_scored", "evidence": ""},
        {"type": "script_ran", "class": "skill_use", "result": "not_applicable", "evidence": ""},
    ]
    metrics = aggregate(run, gradings)["agents"]["claude"]["cases"][SHIP]["skill"]["metrics"]
    # Unchanged: deterministic 1, 1/2, 1; skill use 1, 0, 1; outcome 4/5, 4/5, 5/5.
    assert metrics["deterministic_pass_rate"]["mean"] == pytest.approx(5 / 6)
    assert metrics["skill_use_pass_rate"]["mean"] == pytest.approx(2 / 3)
    assert metrics["outcome_pass_rate"]["mean"] == pytest.approx(13 / 15)


def test_a_grading_on_a_case_without_expectations_is_ignored() -> None:
    run, gradings = load("paired")
    should_trigger = next(t for t in run["trials"] if t["case"] == "should-trigger")
    should_trigger["grading"] = f"eval-results/{run['run_id']}/grading/{SHIP}/skill-1.json"
    skill = aggregate(run, gradings)["agents"]["claude"]["cases"]["should-trigger"]["skill"]
    assert skill["n_grader_error"] == 0
    assert skill["metrics"]["graded_pass_rate"] is None
    # Its only assertion is skill use, so there is no outcome to measure.
    assert skill["metrics"]["outcome_pass_rate"] is None


def test_a_skill_trial_that_did_not_trigger_still_counts_in_its_outcome_metrics() -> None:
    skill = aggregate(*load("paired"))["agents"]["claude"]["cases"][SHIP]["skill"]
    # skill-2 did not trigger: trigger 0, deterministic 1/2, outcome 4/5, all still counted.
    assert skill["metrics"]["trigger_accuracy"]["mean"] == pytest.approx(2 / 3)
    assert skill["metrics"]["deterministic_pass_rate"] == {
        "mean": pytest.approx(5 / 6),
        "stddev": pytest.approx(0.288675, abs=1e-6),
        "min": 0.5,
        "max": 1.0,
        "n": 3,
    }
    assert skill["metrics"]["outcome_pass_rate"]["n"] == 3


def test_a_trigger_that_sometimes_matches_is_flagged_flaky() -> None:
    cases = aggregate(*load("paired"))["agents"]["claude"]["cases"]
    assert any(note.startswith("flaky trigger") for note in cases[SHIP]["notes"])
    # should-trigger matched in both scored trials.
    assert not any(note.startswith("flaky trigger") for note in cases["should-trigger"]["notes"])


def test_a_trigger_that_never_matches_is_a_failure_not_flaky() -> None:
    run, gradings = load("paired")
    for trial in run["trials"]:
        if trial["case"] == "should-trigger":
            trial["trigger"]["matched"] = False
    case = aggregate(run, gradings)["agents"]["claude"]["cases"]["should-trigger"]
    assert case["skill"]["metrics"]["trigger_accuracy"]["mean"] == 0.0
    assert not any(note.startswith("flaky trigger") for note in case["notes"])


def test_the_spread_note_names_each_arm_with_fewer_than_three_scored_trials() -> None:
    run, gradings = load("paired")
    for trial in run["trials"]:
        if trial["case"] == SHIP and trial["arm"] == "baseline" and trial["trial"] != 2:
            trial["status"] = "infra_error"
    notes = aggregate(run, gradings)["agents"]["claude"]["cases"][SHIP]["notes"]
    spread = [note for note in notes if note.startswith("n < 3: spread not meaningful")]
    assert len(spread) == 1
    assert "baseline" in spread[0]


def test_each_expectation_counts_its_passes_per_arm_over_graded_trials() -> None:
    run, gradings = load("paired")
    texts = [e["text"] for e in run["cases"][1]["expectations"]]
    rows = aggregate(run, gradings)["agents"]["claude"]["cases"][SHIP]["expectations"]
    # Baseline: baseline-2 is a grader error (no verdicts); baseline-3's invalid reply fails all.
    assert rows == [
        {
            "text": texts[0],
            "blinded": True,
            "skill": {"passed": 3, "n": 3},
            "baseline": {"passed": 1, "n": 2},
        },
        {
            "text": texts[1],
            "blinded": True,
            "skill": {"passed": 3, "n": 3},
            "baseline": {"passed": 1, "n": 2},
        },
        {
            "text": texts[2],
            "blinded": True,
            "skill": {"passed": 2, "n": 3},
            "baseline": {"passed": 0, "n": 2},
        },
    ]


def test_expectations_have_no_baseline_row_when_the_case_is_skipped() -> None:
    rows = aggregate(*load("one-trial"))["agents"]["claude"]["cases"][SHIP]["expectations"]
    assert [(row["skill"], row["baseline"]) for row in rows] == [
        ({"passed": 1, "n": 1}, None),
        ({"passed": 1, "n": 1}, None),
        ({"passed": 0, "n": 1}, None),
    ]


def test_an_expectation_passed_in_every_trial_of_both_arms_is_non_discriminating() -> None:
    run, gradings = load("paired")
    texts = [e["text"] for e in run["cases"][1]["expectations"]]
    baseline_3 = gradings[f"eval-results/{run['run_id']}/grading/{SHIP}/baseline-3.json"]
    assert baseline_3 is not None
    baseline_3["grader"]["status"] = "ok"
    for expectation in baseline_3["expectations"]:
        expectation["passed"] = True
    notes = aggregate(run, gradings)["agents"]["claude"]["cases"][SHIP]["notes"]
    flagged = [note for note in notes if note.startswith("non-discriminating")]
    # The first two passed 3 of 3 and 2 of 2; the third failed in skill-1 and baseline-1.
    assert len(flagged) == 2
    assert texts[0] in flagged[0]
    assert texts[1] in flagged[1]


def test_arm_disclosures_are_counted_and_noted_on_the_graded_delta() -> None:
    case = aggregate(*load("paired"))["agents"]["claude"]["cases"][SHIP]
    # skill-2's material named the arm.
    assert case["skill"]["n_arm_disclosed"] == 1
    assert case["baseline"]["n_arm_disclosed"] == 0
    assert (
        "arm disclosed to the grader in 1 of 3 trials (skill) / 0 of 2 (baseline)" in case["notes"]
    )


def test_a_disclosure_on_a_grader_error_is_not_counted_so_k_never_exceeds_n() -> None:
    run, gradings = load("paired")
    baseline_2 = gradings[f"eval-results/{run['run_id']}/grading/{SHIP}/baseline-2.json"]
    # The fixture's grader timed out after its material, which named the arm, was sent.
    assert baseline_2 is not None
    assert baseline_2["grader"]["status"] == "grader_error"
    assert baseline_2["arm_disclosed"] is True
    skill_2 = gradings[f"eval-results/{run['run_id']}/grading/{SHIP}/skill-2.json"]
    assert skill_2 is not None
    skill_2["arm_disclosed"] = False
    case = aggregate(run, gradings)["agents"]["claude"]["cases"][SHIP]
    assert case["baseline"]["n_grader_error"] == 1
    assert case["baseline"]["n_arm_disclosed"] == 0
    assert not any(note.startswith("arm disclosed") for note in case["notes"])


def test_no_disclosure_note_when_no_grader_was_told_the_arm() -> None:
    run, gradings = load("paired")
    disclosed = gradings[f"eval-results/{run['run_id']}/grading/{SHIP}/skill-2.json"]
    assert disclosed is not None
    disclosed["arm_disclosed"] = False
    case = aggregate(run, gradings)["agents"]["claude"]["cases"][SHIP]
    assert case["skill"]["n_arm_disclosed"] == 0
    assert not any(note.startswith("arm disclosed") for note in case["notes"])


def test_all_skill_trials_failing_give_mean_zero_and_a_negative_delta() -> None:
    run, gradings = load("paired")
    for trial in run["trials"]:
        if trial["case"] == SHIP and trial["arm"] == "skill":
            for assertion in trial["assertions"]:
                assertion["result"] = "failed"
            grading = gradings[trial["grading"]]
            assert grading is not None
            for expectation in grading["expectations"]:
                expectation["passed"] = False
    case = aggregate(run, gradings)["agents"]["claude"]["cases"][SHIP]
    for metric in ("deterministic_pass_rate", "graded_pass_rate", "outcome_pass_rate"):
        assert case["skill"]["metrics"][metric] == {
            "mean": 0.0,
            "stddev": 0.0,
            "min": 0.0,
            "max": 0.0,
            "n": 3,
        }
    assert case["delta"]["deterministic_pass_rate"]["value"] == pytest.approx(-1 / 3)
    assert case["delta"]["graded_pass_rate"]["value"] == pytest.approx(-1 / 3)
    assert case["delta"]["outcome_pass_rate"]["value"] == pytest.approx(-0.4)


def test_pooled_means_weight_every_trial_and_the_agent_delta_weights_every_case() -> None:
    agent = aggregate(*load("pooling"))["agents"]["claude"]
    # Deterministic: case-a skill 1, 1 / baseline 0, 0; case-b skill 1/2 (one infra error)
    # / baseline 1/2, 1/2. No expectations, so outcome_pass_rate is the same measure.
    pooled_skill = agent["pooled"]["skill"]
    assert pooled_skill["deterministic_pass_rate"]["mean"] == pytest.approx(5 / 6)
    assert pooled_skill["deterministic_pass_rate"]["n"] == 3
    assert pooled_skill["trigger_accuracy"]["mean"] == 1.0
    assert pooled_skill["skill_use_pass_rate"] is None
    assert pooled_skill["graded_pass_rate"] is None
    pooled_baseline = agent["pooled"]["baseline"]
    assert pooled_baseline["deterministic_pass_rate"]["mean"] == pytest.approx(0.25)
    assert pooled_baseline["deterministic_pass_rate"]["n"] == 4
    assert pooled_baseline["trigger_accuracy"] == "not_applicable"
    # Case deltas 1 and 0: their mean, not the pooled 5/6 - 1/4.
    assert agent["delta"] == {
        "deterministic_pass_rate": {"value": pytest.approx(0.5), "n_cases": 2},
        "graded_pass_rate": {"value": None, "n_cases": 0},
        "outcome_pass_rate": {"value": pytest.approx(0.5), "n_cases": 2},
    }


def test_without_a_baseline_there_is_no_pooled_baseline_and_no_agent_delta() -> None:
    agent = aggregate(*load("one-trial"))["agents"]["claude"]
    assert agent["pooled"]["baseline"] is None
    assert agent["pooled"]["skill"]["deterministic_pass_rate"]["n"] == 1
    assert agent["delta"]["outcome_pass_rate"] == {"value": None, "n_cases": 0}


def test_the_agent_notes_a_pooled_arm_with_fewer_than_three_trials() -> None:
    agent = aggregate(*load("one-trial"))["agents"]["claude"]
    assert any(note.startswith("n < 3: spread not meaningful") for note in agent["notes"])
    assert aggregate(*load("pooling"))["agents"]["claude"]["notes"] == []


def test_the_benchmark_carries_the_run_and_the_distinct_versions_reported() -> None:
    benchmark = aggregate(*load("paired"))
    assert benchmark["run_id"] == "20261030T120000Z-0002"
    assert benchmark["skill"] == "cowsay"
    assert benchmark["trials_per_case"] == 3
    assert benchmark["baseline"] is True
    assert benchmark["skipped_in_baseline"] == ["should-trigger"]
    assert benchmark["provenance"] == {
        "git_commit": "fb1d9ce0000000000000000000000000000000ab",
        "git_dirty": False,
        "skill_sha256": "a" * 64,
        "evals_sha256": "b" * 64,
        "grader_prompt_sha256": "c" * 64,
        "agent": "claude",
        "requested_model": "claude-sonnet-5-5",
        # The infra error reported neither.
        "agent_cli_versions": ["2.1.309", "2.1.310"],
        "agent_models": ["claude-sonnet-5-5", "claude-sonnet-5-5-20261001"],
        "grader_model_requested": "claude-opus-5-5",
        "grader_models": ["claude-opus-5-5", "claude-opus-5-5-20261001"],
        "grader_cli_versions": ["2.1.309", "2.1.310"],
    }
    assert len(benchmark["notes"]) == 1
    assert benchmark["notes"][0].startswith("No significance test or confidence interval")


def test_file_sha256_is_the_sha256_of_the_bytes(tmp_path: Path) -> None:
    path = tmp_path / "evals.json"
    path.write_bytes(b"hello\n")
    assert file_sha256(path) == "5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03"


def skill_tree(tmp_path: Path) -> Path:
    skill = tmp_path / "cowsay"
    (skill / "scripts").mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: cowsay\n---\n")
    (skill / "scripts/cowsay.py").write_text("print('moo')\n")
    return skill


def test_tree_sha256_is_stable_and_ignores_pycache(tmp_path: Path) -> None:
    skill = skill_tree(tmp_path)
    before = tree_sha256(skill)
    assert len(before) == 64
    assert tree_sha256(skill) == before
    (skill / "scripts/__pycache__").mkdir()
    (skill / "scripts/__pycache__/cowsay.cpython-314.pyc").write_bytes(b"\x00compiled")
    assert tree_sha256(skill) == before


def test_tree_sha256_changes_when_a_files_bytes_change(tmp_path: Path) -> None:
    skill = skill_tree(tmp_path)
    before = tree_sha256(skill)
    (skill / "scripts/cowsay.py").write_text("print('moo!')\n")
    assert tree_sha256(skill) != before


def test_tree_sha256_changes_when_a_file_is_renamed(tmp_path: Path) -> None:
    skill = skill_tree(tmp_path)
    before = tree_sha256(skill)
    (skill / "scripts/cowsay.py").rename(skill / "scripts/cowsays.py")
    assert tree_sha256(skill) != before


def test_tree_sha256_keeps_a_files_bytes_apart_from_the_next_files_name(tmp_path: Path) -> None:
    # Without a boundary, "a" holding "bc" and "abc" holding "" could hash alike.
    one, two = tmp_path / "one", tmp_path / "two"
    one.mkdir()
    two.mkdir()
    (one / "a").write_text("b")
    (one / "c").write_text("")
    (two / "a").write_text("")
    (two / "bc").write_text("")
    assert tree_sha256(one) != tree_sha256(two)


def test_tree_sha256_of_a_missing_directory_raises(tmp_path: Path) -> None:
    # Not the SHA-256 of nothing, which would look like a real skill's hash.
    with pytest.raises(FileNotFoundError):
        tree_sha256(tmp_path / "cowsy")


def committed_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    for args in (
        ("init", "--quiet", "--initial-branch=main"),
        ("commit", "--quiet", "--allow-empty", "--message", "start"),
    ):
        assert workspace.git(*args, cwd=repo).returncode == 0
    return repo


def test_git_state_reads_the_commit_and_turns_dirty_with_an_untracked_file(
    tmp_path: Path,
) -> None:
    repo = committed_repo(tmp_path)
    head = workspace.git("rev-parse", "HEAD", cwd=repo).stdout.strip()
    assert len(head) == 40
    assert git_state(repo) == {"git_commit": head, "git_dirty": False}
    (repo / "notes.txt").write_text("untracked\n")
    assert git_state(repo) == {"git_commit": head, "git_dirty": True}


def test_git_state_is_null_for_a_directory_that_is_not_a_repos_root(tmp_path: Path) -> None:
    # tmp_path may sit inside this repo's worktree, so "outside a repo" is a plain
    # directory that is not a git root.
    plain = tmp_path / "plain"
    plain.mkdir()
    assert git_state(plain) == {"git_commit": None, "git_dirty": None}


def test_provenance_hashes_the_skill_tree_and_its_evals_file(tmp_path: Path) -> None:
    repo = committed_repo(tmp_path)
    skill = skill_tree(repo / "skills")
    (repo / "evals/cowsay").mkdir(parents=True)
    (repo / "evals/cowsay/evals.json").write_bytes(b"hello\n")
    recorded = provenance(repo, "cowsay")
    assert recorded["skill_sha256"] == tree_sha256(skill)
    assert recorded["evals_sha256"] == (
        "5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03"
    )
    assert recorded["git_dirty"] is True
    assert set(recorded) == {"git_commit", "git_dirty", "skill_sha256", "evals_sha256"}


def test_provenance_of_a_misspelt_skill_fails_loudly(tmp_path: Path) -> None:
    repo = committed_repo(tmp_path)
    skill_tree(repo / "skills")
    (repo / "evals/cowsy").mkdir(parents=True)
    (repo / "evals/cowsy/evals.json").write_bytes(b"hello\n")
    with pytest.raises(FileNotFoundError):
        provenance(repo, "cowsy")


def test_table_shows_mean_and_stddev_with_n_and_marks_what_was_not_measured() -> None:
    printed = table(aggregate(*load("paired")))
    lines = printed.splitlines()
    # behaviour-ship-it, skill arm: deterministic 1, 1/2, 1.
    skill_row = next(line for line in lines if SHIP in line and "skill" in line)
    assert "0.83 ± 0.29 (n=3)" in skill_row
    baseline_row = next(line for line in lines if "baseline" in line and "0.33" in line)
    assert "n/a" in baseline_row
    # The deterministic delta, 5/6 - 1/3, with both arms' n.
    assert "+0.50 (n=3/3)" in printed
    assert "should-trigger" in printed
    assert "skipped" in printed
    assert "unequal n on graded_pass_rate" in printed
    assert "No significance test" in printed


def test_table_shows_a_single_value_without_a_spread_and_a_null_as_no_data() -> None:
    run, gradings = load("one-trial")
    run["trials"][0]["grading"] = None
    printed = table(aggregate(run, gradings))
    assert "0.50 (n=1)" in printed
    assert "±" not in printed
    assert "no data" in printed


def baseline_cell(printed: str, case_id: str) -> str:
    """The first cell of the baseline row under the case's skill row."""
    lines = printed.splitlines()
    row = next(i for i, line in enumerate(lines) if line.startswith(f"{case_id} "))
    arm, cell, *_ = lines[row + 1].split()
    assert arm == "baseline"
    return cell


def test_table_says_off_for_every_case_when_the_run_had_no_baseline() -> None:
    printed = table(aggregate(*load("one-trial")))
    assert baseline_cell(printed, SHIP) == "off"
    assert baseline_cell(printed, "all cases") == "off"
    assert "skipped" not in printed


def test_table_says_skipped_only_for_a_case_left_out_of_a_baseline_that_ran() -> None:
    printed = table(aggregate(*load("paired")))
    assert baseline_cell(printed, "should-trigger") == "skipped"
    assert baseline_cell(printed, SHIP) == "n/a"


def test_the_spread_note_follows_each_metrics_own_n() -> None:
    notes = aggregate(*load("paired"))["agents"]["claude"]["cases"][SHIP]["notes"]
    # Three baseline trials were scored, but the grader error leaves graded n = 2.
    spread = [note for note in notes if note.startswith("n < 3: spread not meaningful")]
    assert spread == ["n < 3: spread not meaningful (baseline, n = 2)"]
