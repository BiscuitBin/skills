"""A fake secret reaches the agent, and never the results, transcripts or workspace."""

import contextlib
import json
import os
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from skills_tooling.evals import runner, workspace
from skills_tooling.evals.claude_code import ClaudeCode
from skills_tooling.evals.results import SecretLeakError, files_holding, gone, scrub, verify_clean
from skills_tooling.evals.runner import run_suite
from tests.evals.fake_anthropic import serve, text, tool
from tests.evals.test_runner import CASES, GOOD, TRIGGER, fake_root, settings

if TYPE_CHECKING:
    from collections.abc import Mapping

    from skills_tooling.evals.adapter import Homes, RawRun, Trace, TrialPaths

ROOT = Path(__file__).parents[2]
SECRET = "sk-ant-oat01-FAKE-0123456789abcdef-secret"


def test_a_fake_token_reaches_the_api_but_not_the_results(tmp_path: Path) -> None:
    root = fake_root(tmp_path, [CASES[0]])
    # The fake API echoes the token back, so it lands in the agent's stream and
    # final message: the run must scrub it everywhere it writes.
    script = {
        TRIGGER: [
            tool("Skill", {"skill": "cowsay"}, "toolu_1"),
            text(f"Your token is {SECRET}."),
        ]
    }
    with serve(script) as server:
        exit_code = run_suite(
            settings(root, server.url, credentials={"CLAUDE_CODE_OAUTH_TOKEN": SECRET})
        )
    assert exit_code == 0
    assert server.requests[0].headers["Authorization"] == f"Bearer {SECRET}"
    written = [p for p in (root / "eval-results").rglob("*") if p.is_file()]
    assert {p.relative_to(root / "eval-results/test-run").as_posix() for p in written} == {
        "benchmark.json",
        "results.json",
        "transcripts/trigger-moo/skill-1.jsonl",
    }
    for path in written:
        assert SECRET not in path.read_text(), path
    assert (
        "[REDACTED]"
        in (root / "eval-results/test-run/transcripts/trigger-moo/skill-1.jsonl").read_text()
    )
    trial = root / ".eval-workspaces/test-run/trigger-moo/skill-1"
    assert [p.name for p in trial.iterdir()] == ["workspace"]
    for path in trial.rglob("*"):
        if path.is_file():
            assert SECRET.encode() not in path.read_bytes(), path


def test_scrub_replaces_every_secret() -> None:
    assert scrub(f"a {SECRET} b {SECRET}", [SECRET, ""]) == "a [REDACTED] b [REDACTED]"


def test_a_file_that_still_holds_a_secret_is_deleted_and_rejected(tmp_path: Path) -> None:
    clean, leaked = tmp_path / "clean.json", tmp_path / "leaked.json"
    clean.write_text("{}")
    leaked.write_text(f'{{"token": "{SECRET}"}}')
    with pytest.raises(SecretLeakError, match=r"leaked\.json"):
        verify_clean(tmp_path, [SECRET])
    assert clean.exists()
    assert not leaked.exists()


def test_a_file_whose_path_holds_a_secret_is_deleted_and_rejected(tmp_path: Path) -> None:
    # The grader lists every output file by its path, so a name can carry a secret too.
    named, nested = tmp_path / f"{SECRET}.txt", tmp_path / f"d-{SECRET}" / "a.txt"
    nested.parent.mkdir()
    named.write_text("moo\n")
    nested.write_text("moo\n")
    (tmp_path / f"link-{SECRET}").symlink_to(named)
    with pytest.raises(SecretLeakError) as raised:
        verify_clean(tmp_path, [SECRET])
    assert SECRET not in str(raised.value)
    assert [p.name for p in tmp_path.rglob("*")] == [f"d-{SECRET}"]


def test_the_agents_bash_commands_never_see_the_token(tmp_path: Path) -> None:
    # The harness hands the token only to the CLI; the CLI must not pass it on
    # to the processes its Bash tool starts. Checked on the unscrubbed trace.
    trial = workspace.create_trial(tmp_path, "run", "case")
    env_dump = tool("Bash", {"command": "env", "description": "Show env"}, "toolu_1")
    with serve([env_dump, text("done")]) as server:
        adapter = ClaudeCode(ROOT / "node_modules/.bin/claude", api_base_url=server.url)
        homes = adapter.prepare_homes(trial)
        raw = adapter.run(
            "Show the environment.",
            trial,
            homes,
            model=adapter.default_model,
            timeout=90,
            credentials={"CLAUDE_CODE_OAUTH_TOKEN": SECRET},
        )
    [command] = adapter.parse(raw).commands
    assert command.ok
    assert f"HOME={trial.home}" in command.output
    assert SECRET not in command.output
    assert "CLAUDE_CODE_OAUTH_TOKEN" not in command.output


def test_a_secret_left_outside_the_workspace_deletes_the_trial_and_fails_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    class Spills(ClaudeCode):
        def run(  # noqa: PLR0913 -- the Adapter signature
            self,
            prompt: str,
            trial: TrialPaths,
            homes: Homes,
            *,
            model: str,
            timeout: float,
            credentials: Mapping[str, str],
        ) -> RawRun:
            # Beside the workspace, where removing only the workspace would miss it.
            (trial.root / "token.txt").write_text(credentials["CLAUDE_CODE_OAUTH_TOKEN"])
            return super().run(
                prompt, trial, homes, model=model, timeout=timeout, credentials=credentials
            )

    root = fake_root(tmp_path, [CASES[0]])
    with serve(GOOD) as server:
        adapter = Spills(ROOT / "node_modules/.bin/claude", api_base_url=server.url)
        exit_code = run_suite(
            settings(
                root, server.url, adapter=adapter, credentials={"CLAUDE_CODE_OAUTH_TOKEN": SECRET}
            )
        )
    assert exit_code == 1
    [trial] = json.loads((root / "eval-results/test-run/results.json").read_text())["trials"]
    assert trial["passed"] is False
    assert trial["secret_found"] == {"files": ["token.txt"], "deleted": True}
    assert not (root / ".eval-workspaces/test-run/trigger-moo/skill-1").exists()
    assert "secret found in the trial directory" in capsys.readouterr().out


def test_failure_diagnostics_on_stdout_are_scrubbed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    class EchoesTheToken(ClaudeCode):
        def parse(self, raw: RawRun) -> Trace:
            trace = super().parse(raw)
            return replace(
                trace, status="infra_error", status_reason=f"agent reported an error: {SECRET}"
            )

    root = fake_root(tmp_path, [CASES[0]])
    with serve(GOOD) as server:
        adapter = EchoesTheToken(ROOT / "node_modules/.bin/claude", api_base_url=server.url)
        exit_code = run_suite(
            settings(
                root, server.url, adapter=adapter, credentials={"CLAUDE_CODE_OAUTH_TOKEN": SECRET}
            )
        )
    assert exit_code == 1
    out = capsys.readouterr().out
    assert SECRET not in out
    assert "agent reported an error: [REDACTED]" in out


@pytest.mark.skipif(os.geteuid() == 0, reason="root can read any file")
@pytest.mark.parametrize("mode", [0o000, 0o100, 0o200, 0o300, 0o400, 0o600])
def test_a_directory_the_sweep_cannot_enter_raises_instead_of_passing(
    tmp_path: Path, mode: int
) -> None:
    locked = tmp_path / "locked"
    locked.mkdir()
    (locked / "token.txt").write_text(SECRET)
    locked.chmod(mode)
    try:
        with pytest.raises(PermissionError):
            files_holding(tmp_path, [SECRET])
    finally:
        locked.chmod(0o755)


def test_the_sweep_reads_files_and_names_links_but_never_opens_anything_else(
    tmp_path: Path,
) -> None:
    (tmp_path / "held").mkdir()
    (tmp_path / "held/token.txt").write_text(SECRET)
    (tmp_path / "clean.txt").write_text("moo")
    os.mkfifo(tmp_path / "pipe")
    (tmp_path / f"{SECRET}-file").symlink_to(tmp_path / "clean.txt")
    (tmp_path / f"{SECRET}-dir").symlink_to(tmp_path / "held")
    assert files_holding(tmp_path, [SECRET]) == [
        tmp_path / "held/token.txt",
        tmp_path / f"{SECRET}-dir",
        tmp_path / f"{SECRET}-file",
    ]


@pytest.mark.skipif(os.geteuid() == 0, reason="root can read any file")
def test_a_results_path_it_cannot_read_deletes_the_rest_and_names_no_secret(
    tmp_path: Path,
) -> None:
    (tmp_path / "leaked.json").write_text(SECRET)
    locked = tmp_path / f"d-{SECRET}"
    locked.mkdir()
    (locked / "token.txt").write_text(SECRET)
    locked.chmod(0)
    try:
        with pytest.raises(SecretLeakError) as raised:
            verify_clean(tmp_path, [SECRET])
    finally:
        with contextlib.suppress(FileNotFoundError):
            locked.chmod(0o755)
    assert SECRET not in str(raised.value)
    assert "could not be deleted" not in str(raised.value)
    assert not tmp_path.exists()


@pytest.mark.skipif(os.geteuid() == 0, reason="root can read any file")
def test_a_results_directory_that_stays_locked_says_so_and_names_no_secret(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(workspace, "restore_access", lambda _root: None)
    (tmp_path / "leaked.json").write_text(SECRET)
    locked = tmp_path / f"d-{SECRET}"
    locked.mkdir()
    locked.chmod(0)
    try:
        with pytest.raises(SecretLeakError) as raised:
            verify_clean(tmp_path, [SECRET])
    finally:
        locked.chmod(0o755)
    assert SECRET not in str(raised.value)
    assert "could not be deleted" in str(raised.value)
    assert not (tmp_path / "leaked.json").exists()


@pytest.mark.skipif(os.geteuid() == 0, reason="root can write anywhere")
def test_a_leak_in_a_read_only_directory_is_deleted(tmp_path: Path) -> None:
    locked = tmp_path / "a_locked"
    locked.mkdir()
    (locked / f"{SECRET}.txt").write_text("{}")
    (tmp_path / "z.json").write_text(SECRET)
    locked.chmod(0o555)
    try:
        with pytest.raises(SecretLeakError) as raised:
            verify_clean(tmp_path, [SECRET])
    finally:
        locked.chmod(0o755)
    assert SECRET not in str(raised.value)
    assert "secret found and deleted" in str(raised.value)
    assert list(locked.iterdir()) == []
    assert not (tmp_path / "z.json").exists()


def test_a_leak_that_cannot_be_deleted_says_so_and_the_rest_still_go(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stuck = tmp_path / f"a-{SECRET}.txt"
    stuck.write_text("{}")
    (tmp_path / "z.json").write_text(SECRET)
    real_unlink = Path.unlink

    def unlink(self: Path, *, missing_ok: bool = False) -> None:
        if self == stuck:
            raise PermissionError(1, "denied", str(self))
        real_unlink(self, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", unlink)
    with pytest.raises(SecretLeakError) as raised:
        verify_clean(tmp_path, [SECRET])
    assert SECRET not in str(raised.value)
    assert "1 could not be deleted" in str(raised.value)
    assert not (tmp_path / "z.json").exists()


def test_gone_is_true_only_for_a_path_that_is_really_absent(tmp_path: Path) -> None:
    assert gone(tmp_path / "missing")
    (tmp_path / "dangling").symlink_to(tmp_path / "missing")
    assert not gone(tmp_path / "dangling")
    parent = tmp_path / "parent"
    parent.mkdir()
    (parent / "kept").mkdir()
    parent.chmod(0)
    try:
        # exists() says False here.
        assert not gone(parent / "kept")
    finally:
        parent.chmod(0o755)


def test_results_under_a_locked_parent_are_not_reported_deleted(tmp_path: Path) -> None:
    parent = tmp_path / "eval-results"
    run = parent / "run"
    run.mkdir(parents=True)
    (run / "results.json").write_text("{}")
    parent.chmod(0)
    try:
        with pytest.raises(SecretLeakError, match="some of it could not be deleted"):
            verify_clean(run, [SECRET])
    finally:
        parent.chmod(0o755)
    assert (run / "results.json").exists()


def test_a_trial_under_a_locked_parent_is_not_reported_deleted(tmp_path: Path) -> None:
    class Locks(ClaudeCode):
        def run(  # noqa: PLR0913 -- the Adapter signature
            self,
            prompt: str,
            trial: TrialPaths,
            homes: Homes,
            *,
            model: str,
            timeout: float,
            credentials: Mapping[str, str],
        ) -> RawRun:
            finished = super().run(
                prompt, trial, homes, model=model, timeout=timeout, credentials=credentials
            )
            # The trial's parent: restore_access starts at the trial, so it stays locked.
            trial.root.parent.chmod(0)
            return finished

    root = fake_root(tmp_path, [CASES[0]])
    case_directory = root / ".eval-workspaces/test-run/trigger-moo"
    try:
        with serve(GOOD) as server:
            adapter = Locks(ROOT / "node_modules/.bin/claude", api_base_url=server.url)
            run_suite(settings(root, server.url, adapter=adapter))
    finally:
        case_directory.chmod(0o755)
    [trial] = json.loads((root / "eval-results/test-run/results.json").read_text())["trials"]
    assert trial["status"] == "infra_error"
    assert trial["status_reason"].endswith("the trial directory could not be deleted")


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores a locked directory")
def test_a_leak_in_a_trial_that_cannot_be_confirmed_gone_is_not_reported_deleted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class Spills(ClaudeCode):
        def run(  # noqa: PLR0913 -- the Adapter signature
            self,
            prompt: str,
            trial: TrialPaths,
            homes: Homes,
            *,
            model: str,
            timeout: float,
            credentials: Mapping[str, str],
        ) -> RawRun:
            (trial.root / "token.txt").write_text(credentials["CLAUDE_CODE_OAUTH_TOKEN"])
            return super().run(
                prompt, trial, homes, model=model, timeout=timeout, credentials=credentials
            )

    sweep = runner._sweep

    def sweep_then_lock_the_parent(
        trial: TrialPaths, secrets: list[str]
    ) -> tuple[list[Path], str]:
        # What a process that left the group could do: the sweep succeeds, then
        # rmtree cannot enter, and exists() would say False on the denied stat.
        found = sweep(trial, secrets)
        trial.root.parent.chmod(0)
        return found

    monkeypatch.setattr(runner, "_sweep", sweep_then_lock_the_parent)
    root = fake_root(tmp_path, [CASES[0]])
    case_directory = root / ".eval-workspaces/test-run/trigger-moo"
    try:
        with serve(GOOD) as server:
            adapter = Spills(ROOT / "node_modules/.bin/claude", api_base_url=server.url)
            exit_code = run_suite(
                settings(
                    root,
                    server.url,
                    adapter=adapter,
                    credentials={"CLAUDE_CODE_OAUTH_TOKEN": SECRET},
                )
            )
    finally:
        case_directory.chmod(0o755)
    assert exit_code == 1
    [trial] = json.loads((root / "eval-results/test-run/results.json").read_text())["trials"]
    assert trial["secret_found"] == {"files": ["token.txt"], "deleted": False}
    assert (case_directory / "skill-1/token.txt").exists()
    assert "(token.txt), NOT deleted" in capsys.readouterr().out
