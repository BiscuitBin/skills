"""`just eval-report` and `just eval-record` end to end, from committed fixture iterations.

The fixture history has two iterations of cowsay: v1 ran Claude Code and Codex,
v2 reran only Claude Code, whose ship-it case then triggered in 1 of 3 trials.
Both carry a should-trigger and a should-not-trigger case.
"""

import shutil
import subprocess
import sys
from pathlib import Path

from tests.evals.test_history import stored_run

FIXTURE = Path(__file__).parents[1] / "fixtures/evals/report"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "skills_tooling.evals", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def history_root(tmp_path: Path) -> Path:
    shutil.copytree(FIXTURE / "benchmarks", tmp_path / "benchmarks")
    return tmp_path


def test_the_report_flags_the_regression_and_can_exit_nonzero(tmp_path: Path) -> None:
    root = history_root(tmp_path)
    result = run_cli("report", "--root", str(root), "--fail-on-regression")
    assert result.returncode == 1, result.stderr
    assert "cowsay: 2 iteration(s): v1, v2" in result.stdout
    assert "claude behaviour-ship-it trigger_accuracy: 1.00 ± 0.00 (n=3) -> 0.33" in result.stdout
    assert "codex" not in result.stdout.split("Regressions", 1)[1]
    page = (root / "eval-results/report.html").read_text()
    assert "should-not-trigger" in page
    assert "no trigger" in page
    # Codex was not rerun in v2, so the matrix shows it as not run, not as 0.
    assert "not run" in page
    # Without the flag the same regression is reported and the exit is 0.
    assert run_cli("report", "--root", str(root)).returncode == 0


def test_the_report_can_be_scoped_to_one_skill(tmp_path: Path) -> None:
    root = history_root(tmp_path)
    out = tmp_path / "cowsay.html"
    result = run_cli("report", "cowsay", "--root", str(root), "--out", str(out))
    assert result.returncode == 0, result.stderr
    assert out.is_file()
    missing = run_cli("report", "no-such-skill", "--root", str(root))
    assert missing.returncode == 2
    assert "no benchmark recorded for no-such-skill" in missing.stderr


def test_a_threshold_above_the_fall_flags_nothing(tmp_path: Path) -> None:
    root = history_root(tmp_path)
    result = run_cli("report", "--root", str(root), "--threshold", "0.7", "--fail-on-regression")
    assert result.returncode == 0, result.stdout
    assert "No regression beyond 0.70." in result.stdout
    assert run_cli("report", "--root", str(root), "--threshold", "2").returncode == 2


def test_a_recorded_run_joins_the_history(tmp_path: Path) -> None:
    root = history_root(tmp_path)
    run_id = stored_run(root, "paired", run_id="20261103T010000Z-0009", agent="codex")
    recorded = run_cli("record", "v3", run_id, "--root", str(root))
    assert recorded.returncode == 0, recorded.stderr
    assert (root / "benchmarks/cowsay/v3.json").is_file()
    again = run_cli("record", "v3", run_id, "--root", str(root))
    assert again.returncode == 2
    assert "already recorded" in again.stderr
    result = run_cli("report", "--root", str(root))
    assert "cowsay: 3 iteration(s): v1, v2, v3" in result.stdout


def test_an_unrecorded_run_is_reported_without_being_written(tmp_path: Path) -> None:
    root = history_root(tmp_path)
    run_id = stored_run(root, "paired", run_id="20261103T010000Z-0009", agent="codex")
    result = run_cli("report", "--root", str(root), "--run", run_id)
    assert result.returncode == 0, result.stderr
    assert "v1, v2, unrecorded" in result.stdout
    assert sorted(p.name for p in (root / "benchmarks/cowsay").iterdir()) == [
        "v1.json",
        "v2.json",
    ]


def test_the_report_writes_the_headline_matrix_as_markdown(tmp_path: Path) -> None:
    root = history_root(tmp_path)
    markdown = tmp_path / "summary.md"
    result = run_cli("report", "cowsay", "--root", str(root), "--markdown", str(markdown))
    assert result.returncode == 0, result.stderr
    text = markdown.read_text()
    assert text.startswith("### cowsay: iteration v2\n")
    assert "| case | expects | claude trigger | claude pass rate | claude Δ pass rate |" in text
    assert "| should-not-trigger | no trigger |" in text
    # Codex was not rerun in v2: a state, never a 0.
    assert "| not run | not run | not run |" in text
    assert "| all cases |" in text
    assert "claude behaviour-ship-it trigger_accuracy: 1.00 ± 0.00 (n=3) -> 0.33" in text
