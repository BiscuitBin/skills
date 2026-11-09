"""The cross-agent benchmark report: matrix, deltas, provenance, history and regressions."""

import copy
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import pytest

from skills_tooling.evals.history import assemble
from skills_tooling.evals.report import build, render_html
from tests.evals.test_history import stored_run

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

START = datetime(2026, 11, 1, tzinfo=UTC)
SHIP = "behaviour-ship-it"
TRIGGER = "should-trigger"
QUIET = "should-not-trigger"


def no_trigger_case(run: dict[str, Any], matched: tuple[bool, ...] = (True, True, True)) -> None:
    """Add a should-not-trigger case, its trials copied from the should-trigger case's."""
    run["cases"].insert(
        1,
        {
            "id": QUIET,
            "kind": "trigger",
            "should_trigger": False,
            "expectations": [],
            "in_baseline": False,
        },
    )
    template = next(t for t in run["trials"] if t["case"] == TRIGGER)
    for n, ok in enumerate(matched, start=1):
        trial = copy.deepcopy(template)
        trial |= {"case": QUIET, "trial": n, "assertions": [], "passed": ok}
        trial["trigger"] |= {"expected": False, "actual": not ok, "matched": ok}
        run["trials"].append(trial)


def set_trigger(case: str, matched: tuple[bool, ...]) -> Callable[[dict[str, Any]], None]:
    def edit(run: dict[str, Any]) -> None:
        trials = [t for t in run["trials"] if t["case"] == case and t["arm"] == "skill"]
        for trial, ok in zip(trials, matched, strict=True):
            trial["trigger"]["matched"] = ok

    return edit


def fail_outcomes(run: dict[str, Any]) -> None:
    """Fail every outcome assertion of the ship-it case's skill arm."""
    for trial in run["trials"]:
        if trial["case"] == SHIP and trial["arm"] == "skill":
            for assertion in trial["assertions"]:
                if assertion["class"] == "outcome":
                    assertion["result"] = "failed"


def both(*edits: Callable[[dict[str, Any]], None]) -> Callable[[dict[str, Any]], None]:
    def edit(run: dict[str, Any]) -> None:
        for each in edits:
            each(run)

    return edit


def base(run: dict[str, Any]) -> None:
    """The fixture with a should-not-trigger case, and ship-it triggering in every trial."""
    no_trigger_case(run)
    set_trigger(SHIP, (True, True, True))(run)


class History:
    """Builds recorded iterations from the paired benchmark fixture, one hour apart."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.count = 0

    def run(
        self,
        agent: str = "claude",
        edit: Callable[[dict[str, Any]], None] | None = None,
        **changes: Any,  # noqa: ANN401
    ) -> str:
        self.count += 1
        run_id = f"20261101T{self.count:02d}0000Z-{self.count:04x}"
        return stored_run(self.root, "paired", edit or base, run_id=run_id, agent=agent, **changes)

    def iteration(self, name: str | None, *run_ids: str) -> dict[str, Any]:
        when = START + timedelta(hours=self.count)
        return assemble(self.root, name, list(run_ids), now=when)


@pytest.fixture
def history(tmp_path: Path) -> History:
    return History(tmp_path)


def cell(report: dict[str, Any], case: str, agent: str) -> dict[str, Any]:
    row = next(r for r in report["matrix"]["rows"] if r["case"] == case)
    result: dict[str, Any] = row["cells"][agent]
    return result


def series(report: dict[str, Any], agent: str, scope: str, metric: str) -> list[dict[str, Any]]:
    row = next(s for s in report["history"][agent] if (s["scope"], s["metric"]) == (scope, metric))
    values: list[dict[str, Any]] = row["values"]
    return values


def flagged(report: dict[str, Any]) -> set[tuple[str, str, str]]:
    return {(r["agent"], r["scope"], r["metric"]) for r in report["regressions"]}


# ------------------------------------------------------------------ matrix ---


def test_the_matrix_shows_trigger_accuracy_and_pass_rate_per_agent_and_case(
    history: History,
) -> None:
    first = history.iteration("first", history.run("claude"), history.run("codex"))
    report = build([first])
    assert report["agents"] == ["claude", "codex"]
    assert [r["case"] for r in report["matrix"]["rows"]] == [TRIGGER, QUIET, SHIP]
    assert [r["should_trigger"] for r in report["matrix"]["rows"]] == [True, False, True]
    ship = cell(report, SHIP, "codex")
    assert ship["trigger"] == {"state": "value", "mean": 1.0, "stddev": 0.0, "n": 3}
    # Outcome: 4/5, 4/5, 5/5 over three trials.
    assert ship["pass"]["state"] == "value"
    assert ship["pass"]["mean"] == pytest.approx(13 / 15)
    assert ship["pass"]["stddev"] == pytest.approx(0.11547, abs=1e-5)
    assert ship["pass"]["n"] == 3
    assert ship["delta"]["state"] == "value"
    assert ship["delta"]["mean"] == pytest.approx(7 / 15)


def test_a_should_not_trigger_case_scores_trigger_accuracy_and_has_no_pass_rate(
    history: History,
) -> None:
    run = history.run(edit=lambda r: no_trigger_case(r, (True, False, True)))
    report = build([history.iteration("first", run)])
    quiet = cell(report, QUIET, "claude")
    assert quiet["trigger"]["mean"] == pytest.approx(2 / 3)
    assert quiet["trigger"]["n"] == 3
    # Nothing to measure is not a zero.
    assert quiet["pass"] == {"state": "not_applicable"}
    assert quiet["delta"] == {"state": "not_applicable"}


def test_an_agent_that_never_ran_shows_as_not_run(history: History) -> None:
    report = build([history.iteration("first", history.run("claude"))])
    # Codex has never been benchmarked, and still gets a column that says so.
    assert report["agents"] == ["claude", "codex"]
    assert cell(report, SHIP, "codex") == {
        "trigger": {"state": "not_run"},
        "pass": {"state": "not_run"},
        "delta": {"state": "not_run"},
    }
    assert {v["state"] for v in report["deltas"]["codex"].values()} == {"not_run"}
    assert "codex has not been run in any iteration" in render_html([report])
    two = build(
        [
            history.iteration("first", history.run("codex")),
            history.iteration("second", history.run("claude")),
        ]
    )
    # The latest iteration ran Claude only, so Codex's column says so.
    assert cell(two, SHIP, "codex") == {
        "trigger": {"state": "not_run"},
        "pass": {"state": "not_run"},
        "delta": {"state": "not_run"},
    }


def test_a_case_added_later_is_missing_in_earlier_iterations_never_zero(
    history: History,
) -> None:
    before = history.iteration("before", history.run(edit=lambda _: None))
    after = history.iteration("after", history.run())
    report = build([before, after])
    trigger = series(report, "claude", QUIET, "trigger_accuracy")
    assert trigger[0] == {"state": "case_absent"}
    assert trigger[1]["state"] == "value"
    assert not flagged(report)


def test_a_metric_with_no_scored_trials_is_no_data(history: History) -> None:
    def crash(run: dict[str, Any]) -> None:
        no_trigger_case(run)
        for trial in run["trials"]:
            if trial["case"] == SHIP and trial["arm"] == "skill":
                trial["status"] = "infra_error"

    report = build([history.iteration("first", history.run(edit=crash))])
    ship = cell(report, SHIP, "claude")
    assert ship["trigger"] == {"state": "no_scored"}
    assert ship["pass"] == {"state": "no_scored"}
    assert ship["delta"] == {"state": "no_scored"}


def test_a_case_whose_every_grading_failed_has_no_pass_rate_data(history: History) -> None:
    def ungraded(run: dict[str, Any]) -> None:
        no_trigger_case(run)
        for trial in run["trials"]:
            if trial["case"] == SHIP and trial["arm"] == "skill":
                trial["grading"] = None

    ship = cell(build([history.iteration("first", history.run(edit=ungraded))]), SHIP, "claude")
    assert ship["pass"] == {"state": "no_data"}


# ------------------------------------------------------------------ deltas ---


def test_each_agents_delta_against_the_baseline_is_shown_with_its_case_count(
    history: History,
) -> None:
    report = build([history.iteration("first", history.run("claude"))])
    delta = report["deltas"]["claude"]
    assert delta["outcome_pass_rate"]["state"] == "value"
    assert delta["outcome_pass_rate"]["mean"] == pytest.approx(7 / 15)
    assert delta["outcome_pass_rate"]["n"] == 1


def test_a_run_without_a_baseline_has_no_delta_rather_than_a_zero(history: History) -> None:
    def no_baseline(run: dict[str, Any]) -> None:
        no_trigger_case(run)
        run["baseline"] = False
        run["trials"] = [t for t in run["trials"] if t["arm"] == "skill"]
        for case in run["cases"]:
            case["in_baseline"] = False

    report = build([history.iteration("first", history.run(edit=no_baseline))])
    assert report["deltas"]["claude"]["outcome_pass_rate"] == {"state": "baseline_off"}
    assert cell(report, SHIP, "claude")["delta"] == {"state": "baseline_off"}


# -------------------------------------------------------------- provenance ---


def test_provenance_names_the_cli_versions_and_models_behind_every_number(
    history: History,
) -> None:
    report = build([history.iteration("first", history.run("claude"), history.run("codex"))])
    [claude, codex] = report["provenance"]
    assert claude["iteration"] == "first"
    assert claude["agent"] == "claude"
    assert claude["agent_cli_versions"] == ["2.1.309", "2.1.310"]
    assert claude["agent_models"] == ["claude-sonnet-5-5", "claude-sonnet-5-5-20261001"]
    assert claude["grader_models"] == ["claude-opus-5-5", "claude-opus-5-5-20261001"]
    assert claude["grader_cli_versions"]
    assert claude["trials_per_case"] == 3
    assert codex["agent"] == "codex"


# ----------------------------------------------------------------- history ---


def test_history_has_a_value_per_iteration_for_each_metric(history: History) -> None:
    first = history.iteration("first", history.run())
    second = history.iteration(
        "second", history.run(edit=both(no_trigger_case, set_trigger(SHIP, (True, True, False))))
    )
    report = build([first, second])
    assert [c["name"] for c in report["columns"]] == ["first", "second"]
    values = series(report, "claude", SHIP, "trigger_accuracy")
    assert [v["mean"] for v in values] == pytest.approx([1.0, 2 / 3])
    pooled = series(report, "claude", "all cases", "trigger_accuracy")
    # should-trigger's third trial is an infrastructure error, excluded from both.
    assert [v["n"] for v in pooled] == [8, 8]
    assert series(report, "claude", "all cases", "delta:outcome_pass_rate")[0]["state"] == "value"


# ------------------------------------------------------------- regressions ---


def test_a_fall_beyond_the_threshold_since_the_last_benchmark_is_flagged(
    history: History,
) -> None:
    first = history.iteration("first", history.run())
    second = history.iteration(
        "second", history.run(edit=both(no_trigger_case, set_trigger(SHIP, (True, False, False))))
    )
    report = build([first, second], threshold=0.1)
    assert ("claude", SHIP, "trigger_accuracy") in flagged(report)
    found = next(r for r in report["regressions"] if r["scope"] == SHIP)
    assert (found["from"], found["to"]) == ("first", "second")
    assert found["change"] == pytest.approx(-2 / 3)
    assert found["labels"] == []
    assert found["comparable"] is True
    # The same fall is within a threshold of 0.7.
    assert ("claude", SHIP, "trigger_accuracy") not in flagged(
        build([first, second], threshold=0.7)
    )


def test_a_should_not_trigger_case_that_starts_triggering_is_flagged(history: History) -> None:
    first = history.iteration("first", history.run())
    second = history.iteration(
        "second", history.run(edit=lambda r: no_trigger_case(r, (False, False, True)))
    )
    assert ("claude", QUIET, "trigger_accuracy") in flagged(build([first, second]))


def test_an_improvement_or_an_unchanged_metric_is_not_flagged(history: History) -> None:
    worse = both(no_trigger_case, set_trigger(SHIP, (True, False, False)))
    first = history.iteration("first", history.run(edit=worse))
    second = history.iteration("second", history.run())
    third = history.iteration("third", history.run())
    assert not flagged(build([first, second]))
    assert not flagged(build([first, second, third]))


def test_only_the_last_two_benchmarks_of_the_same_agent_are_compared(history: History) -> None:
    worse = both(no_trigger_case, set_trigger(SHIP, (True, False, False)))
    first = history.iteration("first", history.run("claude"), history.run("codex"))
    # Codex is not rerun in second; Claude's fall is measured against first.
    second = history.iteration("second", history.run("claude", edit=worse))
    report = build([first, second])
    assert flagged(report) >= {("claude", SHIP, "trigger_accuracy")}
    assert not {f for f in flagged(report) if f[0] == "codex"}
    # A third iteration with only Codex keeps Claude's flag: nothing newer replaced it.
    third = history.iteration("third", history.run("codex"))
    assert ("claude", SHIP, "trigger_accuracy") in flagged(build([first, second, third]))


def test_regressions_compare_an_agents_own_runs_in_the_order_they_ran(
    history: History,
) -> None:
    # Iteration A pairs an early Claude run with a later Codex run, so it sorts after B,
    # whose Claude run came in between and fell.
    early = history.run("claude", started_at="2026-11-01T00:00:00.000+00:00")
    late = history.run("codex", started_at="2026-11-03T00:00:00.000+00:00")
    fell = history.run(
        "claude",
        both(base, set_trigger(TRIGGER, (False, False, False))),
        started_at="2026-11-02T00:00:00.000+00:00",
    )
    a = history.iteration("A", early, late)
    b = history.iteration("B", fell)
    report = build([b, a])
    assert ("claude", TRIGGER, "trigger_accuracy") in flagged(report)
    claude = next(c for c in report["comparisons"] if c["agent"] == "claude")
    assert (claude["from"], claude["to"]) == ("A", "B")


def test_a_run_counted_twice_is_compared_once(history: History) -> None:
    good = history.iteration("good", history.run())
    fell = history.run(edit=both(base, set_trigger(TRIGGER, (False, False, False))))
    # The fallen run is recorded, then passed again with --run.
    report = build([good, history.iteration("fell", fell), history.iteration(None, fell)])
    assert ("claude", TRIGGER, "trigger_accuracy") in flagged(report)
    assert (report["comparisons"][0]["from"], report["comparisons"][0]["to"]) == ("good", "fell")


def test_an_unrecorded_run_is_compared_with_the_last_recorded_benchmark(
    history: History,
) -> None:
    worse = both(no_trigger_case, set_trigger(SHIP, (True, False, False)))
    first = history.iteration("first", history.run())
    provisional = history.iteration(None, history.run(edit=worse))
    report = build([first, provisional])
    assert report["columns"][-1] == {
        "name": "unrecorded",
        "recorded": False,
        "recorded_at": None,
    }
    found = next(r for r in report["regressions"] if r["scope"] == SHIP)
    assert (found["from"], found["to"]) == ("first", "unrecorded")


def test_a_fall_across_a_different_model_or_cli_is_labelled_not_like_for_like(
    history: History,
) -> None:
    worse = both(no_trigger_case, set_trigger(SHIP, (True, False, False)))

    def other_cli(run: dict[str, Any]) -> None:
        worse(run)
        for trial in run["trials"]:
            trial["cli_version"] = "2.2.0"

    first = history.iteration("first", history.run())
    second = history.iteration(
        "second", history.run(edit=other_cli, requested_model="claude-opus-5-5")
    )
    found = next(r for r in build([first, second])["regressions"] if r["scope"] == SHIP)
    assert found["comparable"] is False
    assert "agent CLI version changed" in found["labels"]
    assert "agent model changed" in found["labels"]


def test_changed_cases_rubric_or_grader_are_labelled(history: History) -> None:
    worse = both(no_trigger_case, set_trigger(SHIP, (True, False, False)))
    first = history.iteration("first", history.run())

    def new_rubric(run: dict[str, Any]) -> None:
        worse(run)
        run["provenance"] = run["provenance"] | {
            "evals_sha256": "d" * 64,
            "grader_prompt_sha256": "e" * 64,
        }
        run["grader_model_requested"] = "claude-sonnet-5-5"

    second = history.iteration("second", history.run(edit=both(new_rubric, fail_outcomes)))
    found = {r["metric"]: r for r in build([first, second])["regressions"] if r["scope"] == SHIP}
    # The grader decides no trigger, so only the case and rubric change is named there.
    assert found["trigger_accuracy"]["labels"] == ["cases or rubric changed"]
    outcome = found["outcome_pass_rate"]
    assert outcome["comparable"] is False
    assert outcome["labels"] == [
        "cases or rubric changed",
        "grader prompt changed",
        "grader model changed",
    ]


def test_a_new_skill_version_alone_is_a_like_for_like_comparison(history: History) -> None:
    worse = both(no_trigger_case, set_trigger(SHIP, (True, False, False)))

    def new_skill(run: dict[str, Any]) -> None:
        worse(run)
        run["provenance"] = run["provenance"] | {"skill_sha256": "f" * 64, "git_commit": "1" * 40}

    first = history.iteration("first", history.run())
    second = history.iteration("second", history.run(edit=new_skill))
    found = next(r for r in build([first, second])["regressions"] if r["scope"] == SHIP)
    assert found["comparable"] is True


def test_a_case_definition_change_is_labelled_on_that_case(history: History) -> None:
    def flipped(run: dict[str, Any]) -> None:
        no_trigger_case(run)
        run["cases"][0]["kind"] = "behaviour"
        set_trigger(TRIGGER, (True, False, False))(run)

    first = history.iteration("first", history.run())
    second = history.iteration("second", history.run(edit=flipped))
    found = next(r for r in build([first, second])["regressions"] if r["scope"] == TRIGGER)
    assert "case changed" in found["labels"]
    assert found["comparable"] is False


def test_a_comparison_over_a_different_case_selection_is_not_like_for_like(
    history: History,
) -> None:
    # Same case file and provenance; the second run selected fewer cases.
    first = history.iteration("first", history.run())
    second = history.iteration("second", history.run(edit=lambda _: None))
    report = build([first, second])
    assert "case set changed" in report["comparisons"][0]["labels"]
    assert "claude: first → second: case set changed." in render_html([report])


def test_a_comparison_where_a_case_was_redefined_is_not_like_for_like(
    history: History,
) -> None:
    def redefined(run: dict[str, Any]) -> None:
        base(run)
        run["cases"][0]["kind"] = "behaviour"

    first = history.iteration("first", history.run())
    second = history.iteration("second", history.run(edit=redefined))
    assert "case changed" in build([first, second])["comparisons"][0]["labels"]


def test_a_thin_sample_is_flagged_with_both_ns(history: History) -> None:
    def thin(run: dict[str, Any]) -> None:
        no_trigger_case(run)
        trials = [t for t in run["trials"] if t["case"] == SHIP and t["arm"] == "skill"]
        trials[0]["trigger"]["matched"] = False
        trials[1]["status"] = "infra_error"

    first = history.iteration("first", history.run())
    second = history.iteration("second", history.run(edit=thin))
    found = next(
        r
        for r in build([first, second])["regressions"]
        if (r["scope"], r["metric"]) == (SHIP, "trigger_accuracy")
    )
    assert found["thin"] is True
    assert (found["before"]["n"], found["after"]["n"]) == (3, 2)


def test_a_case_dropped_from_the_latest_run_is_never_a_regression(history: History) -> None:
    first = history.iteration("first", history.run())
    second = history.iteration("second", history.run(edit=lambda _: None))
    report = build([first, second])
    assert series(report, "claude", QUIET, "trigger_accuracy")[1] == {"state": "case_absent"}
    assert not {f for f in flagged(report) if f[1] == QUIET}


# ------------------------------------------------------------------- html ---


def test_the_html_report_is_self_contained_and_labels_missing_data(history: History) -> None:
    worse = both(no_trigger_case, set_trigger(SHIP, (True, False, False)))
    first = history.iteration("first", history.run("claude"), history.run("codex"))
    second = history.iteration("second<script>", history.run("claude", edit=worse))
    page = render_html([build([first, second])])
    assert page.startswith("<!doctype html>")
    assert "<script" not in page
    assert "second&lt;script&gt;" in page
    assert "http://" not in page
    assert "https://" not in page
    assert "not run" in page
    assert "n/a" in page
    assert "regression" in page
    assert "1.00 ± 0.00 (n=3)" in page
    assert "2.1.309, 2.1.310" in page
    assert "claude-opus-5-5" in page


def test_an_agent_delta_over_fewer_cases_is_labelled(history: History) -> None:
    def second_case(run: dict[str, Any]) -> None:
        """A second behaviour case, a copy of ship-it, whose baseline is far ahead."""
        base(run)
        meta = next(c for c in run["cases"] if c["id"] == SHIP)
        run["cases"].append(meta | {"id": "other"})
        for trial in [t for t in run["trials"] if t["case"] == SHIP]:
            other = copy.deepcopy(trial) | {"case": "other"}
            if other["arm"] == "skill":
                for assertion in other["assertions"]:
                    if assertion["class"] == "outcome":
                        assertion["result"] = "failed"
            run["trials"].append(other)

    def other_ungraded(run: dict[str, Any]) -> None:
        second_case(run)
        for trial in run["trials"]:
            if trial["case"] == "other":
                trial["grading"] = None

    def ship_ungraded(run: dict[str, Any]) -> None:
        second_case(run)
        for trial in run["trials"]:
            if trial["case"] == SHIP:
                trial["grading"] = None

    first = history.iteration("first", history.run(edit=other_ungraded))
    second = history.iteration("second", history.run(edit=ship_ungraded))
    found = next(
        r
        for r in build([first, second])["regressions"]
        if (r["scope"], r["metric"]) == ("all cases", "delta:outcome_pass_rate")
    )
    assert "measured over different cases" in found["labels"]


def test_figures_over_all_cases_say_no_scored_trials_when_every_trial_was_excluded(
    history: History,
) -> None:
    def all_crashed(run: dict[str, Any]) -> None:
        base(run)
        for trial in run["trials"]:
            trial["status"] = "infra_error"

    report = build([history.iteration("first", history.run(edit=all_crashed))])
    assert report["matrix"]["pooled"]["claude"]["trigger"] == {"state": "no_scored"}
    assert report["matrix"]["pooled"]["claude"]["pass"] == {"state": "no_scored"}
    assert report["deltas"]["claude"]["outcome_pass_rate"] == {"state": "no_scored"}


def test_a_case_delta_says_no_scored_trials_when_either_arm_had_none(history: History) -> None:
    def baseline_crashed(run: dict[str, Any]) -> None:
        base(run)
        for trial in run["trials"]:
            if trial["arm"] == "baseline":
                trial["status"] = "infra_error"

    def skill_crashed(run: dict[str, Any]) -> None:
        base(run)
        for trial in run["trials"]:
            if trial["case"] == SHIP and trial["arm"] == "skill":
                trial["status"] = "infra_error"

    for edit in (baseline_crashed, skill_crashed):
        report = build([history.iteration("first", history.run(edit=edit))])
        assert cell(report, SHIP, "claude")["delta"] == {"state": "no_scored"}
