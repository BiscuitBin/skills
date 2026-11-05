"""Recording benchmarks as named iterations in benchmarks/<skill>/<iteration>.json."""

import json
import shutil
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import pytest

from skills_tooling.evals.benchmark import aggregate
from skills_tooling.evals.history import HistoryError, assemble, load, record
from tests.evals.test_benchmark import FIXTURES
from tests.evals.test_benchmark import load as load_fixture

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

NOW = datetime(2026, 11, 3, 12, 0, tzinfo=UTC)


def stored_run(
    root: Path,
    scenario: str,
    edit: Callable[[dict[str, Any]], None] | None = None,
    **changes: Any,  # noqa: ANN401
) -> str:
    """Copy a benchmark fixture into root/eval-results as a finished run; return its run id.

    edit changes the run record before it is aggregated, as a different run would have.
    """
    run, gradings = load_fixture(scenario)
    run |= changes
    run_id: str = run["run_id"]
    for trial in run["trials"]:
        trial["agent"] = run["agent"]
    if edit is not None:
        edit(run)
    directory = root / "eval-results" / run_id
    directory.mkdir(parents=True)
    if (FIXTURES / scenario / "grading").is_dir():
        shutil.copytree(FIXTURES / scenario / "grading", directory / "grading")
    (directory / "results.json").write_text(json.dumps(run))
    (directory / "benchmark.json").write_text(json.dumps(aggregate(run, gradings)))
    return run_id


def test_recording_a_run_writes_its_benchmark_and_cases_under_the_iteration_name(
    tmp_path: Path,
) -> None:
    run_id = stored_run(tmp_path, "paired")
    path = record(tmp_path, "first", [run_id], now=NOW)
    assert path == tmp_path / "benchmarks/cowsay/first.json"
    saved = json.loads(path.read_text())
    assert saved["iteration"] == "first"
    assert saved["skill"] == "cowsay"
    assert saved["recorded_at"] == "2026-11-03T12:00:00+00:00"
    [run] = saved["runs"]
    assert run["run_id"] == run_id
    assert run["agent"] == "claude"
    assert run["provenance"]["requested_model"] == "claude-sonnet-5-5"
    assert [case["id"] for case in run["cases"]] == ["should-trigger", "behaviour-ship-it"]
    assert run["cases"][0]["should_trigger"] is True
    ship = run["benchmark"]["cases"]["behaviour-ship-it"]
    assert ship["delta"]["deterministic_pass_rate"]["value"] == pytest.approx(0.5)


def test_an_iteration_holds_one_run_per_agent(tmp_path: Path) -> None:
    claude = stored_run(tmp_path, "paired")
    codex = stored_run(tmp_path, "one-trial", run_id="20261030T130000Z-0003", agent="codex")
    saved = json.loads(record(tmp_path, "both", [claude, codex], now=NOW).read_text())
    assert [run["agent"] for run in saved["runs"]] == ["claude", "codex"]
    again = stored_run(tmp_path, "one-trial", run_id="20261030T140000Z-0004")
    with pytest.raises(HistoryError, match="two runs of claude"):
        record(tmp_path, "twice", [claude, again], now=NOW)


def test_runs_of_another_skill_or_another_skill_version_are_refused(tmp_path: Path) -> None:
    first = stored_run(tmp_path, "paired")
    other = stored_run(tmp_path, "one-trial", run_id="20261030T130000Z-0003", agent="codex")
    path = tmp_path / "eval-results" / other / "benchmark.json"
    changed = json.loads(path.read_text())
    changed["provenance"]["skill_sha256"] = "0" * 64
    path.write_text(json.dumps(changed))
    with pytest.raises(HistoryError, match="skill_sha256"):
        record(tmp_path, "mixed", [first, other], now=NOW)
    third = stored_run(
        tmp_path, "one-trial", run_id="20261030T140000Z-0004", agent="codex", skill="other"
    )
    with pytest.raises(HistoryError, match="skill"):
        record(tmp_path, "mixed", [first, third], now=NOW)


def test_an_existing_iteration_name_is_never_overwritten(tmp_path: Path) -> None:
    run_id = stored_run(tmp_path, "paired")
    record(tmp_path, "first", [run_id], now=NOW)
    with pytest.raises(HistoryError, match="already recorded"):
        record(tmp_path, "first", [run_id], now=NOW)


def test_a_run_already_recorded_is_refused_under_another_name(tmp_path: Path) -> None:
    run_id = stored_run(tmp_path, "paired")
    record(tmp_path, "first", [run_id], now=NOW)
    with pytest.raises(HistoryError, match=f"run {run_id} is already recorded in iteration first"):
        record(tmp_path, "second", [run_id], now=NOW)
    assert not (tmp_path / "benchmarks/cowsay/second.json").exists()


@pytest.mark.parametrize("name", ["", ".hidden", "a/b", "../up", "with space", "unrecorded"])
def test_an_iteration_name_must_be_a_plain_file_name(tmp_path: Path, name: str) -> None:
    run_id = stored_run(tmp_path, "paired")
    with pytest.raises(HistoryError, match="iteration name"):
        record(tmp_path, name, [run_id], now=NOW)


def test_a_run_without_a_benchmark_is_refused(tmp_path: Path) -> None:
    run_id = stored_run(tmp_path, "paired")
    (tmp_path / "eval-results" / run_id / "benchmark.json").unlink()
    with pytest.raises(HistoryError, match="no benchmark"):
        record(tmp_path, "first", [run_id], now=NOW)
    bench = {"trials_per_case": 1, "baseline": False, "provenance": {}, "agents": {}, "notes": []}
    (tmp_path / "eval-results" / run_id / "benchmark.json").write_text(json.dumps(bench))
    with pytest.raises(HistoryError, match="not a complete run"):
        record(tmp_path, "first", [run_id], now=NOW)
    with pytest.raises(HistoryError, match="no run"):
        record(tmp_path, "first", ["20990101T000000Z-ffff"], now=NOW)


def test_load_orders_iterations_by_when_their_runs_started_not_when_recorded(
    tmp_path: Path,
) -> None:
    later = stored_run(tmp_path, "paired", run_id="20261102T000000Z-0002", started_at="2026-11-02")
    earlier = stored_run(
        tmp_path, "paired", run_id="20261101T000000Z-0001", started_at="2026-11-01"
    )
    record(tmp_path, "zeta", [later], now=NOW)
    # A backfilled older run, recorded afterwards, is still the older iteration.
    record(tmp_path, "alpha", [earlier], now=NOW.replace(hour=13))
    assert [i["iteration"] for i in load(tmp_path, "cowsay")] == ["alpha", "zeta"]
    assert load(tmp_path, "nothing-recorded") == []


@pytest.mark.parametrize("missing", ["runs", "recorded_at", "iteration"])
def test_a_damaged_iteration_file_is_a_history_error(tmp_path: Path, missing: str) -> None:
    path = record(tmp_path, "first", [stored_run(tmp_path, "paired")], now=NOW)
    data = json.loads(path.read_text())
    del data[missing]
    path.write_text(json.dumps(data))
    with pytest.raises(HistoryError, match="not a schema-1 iteration"):
        load(tmp_path, "cowsay")


def test_unrecorded_runs_assemble_into_an_iteration_that_is_not_written(
    tmp_path: Path,
) -> None:
    run_id = stored_run(tmp_path, "paired")
    provisional = assemble(tmp_path, None, [run_id], now=NOW)
    assert provisional["iteration"] is None
    assert provisional["skill"] == "cowsay"
    assert not (tmp_path / "benchmarks").exists()
