"""Tests for the cross-model-review dev skill's reviewer script."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from unittest import mock

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "dev-skills" / "cross-model-review" / "scripts" / "review.py"


def _load_review() -> ModuleType:
    spec = importlib.util.spec_from_file_location("cross_model_review", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


review = _load_review()


def probe_with(unavailable: dict[str, str]) -> Callable[[str], str | None]:
    """A probe where the named reviewers are unavailable for the given reason."""

    def probe(reviewer: str) -> str | None:
        return unavailable.get(reviewer)

    return probe


ALL_AVAILABLE = probe_with({})


class ModelFamilyTest(unittest.TestCase):
    def test_claude_models_are_anthropic(self) -> None:
        for model in (
            "claude-opus-5-5",
            "Claude-Sonnet-5-5",
            "anthropic/claude-opus-5-5",
            "us.anthropic.claude-opus-5-5",
            "global.anthropic.claude-opus-5-5",
            "openrouter/anthropic/claude-opus-5-5",
            "bedrock-claude-x",
            "opus",
        ):
            with self.subTest(model=model):
                self.assertEqual(review.model_family(model), "anthropic")

    def test_openai_models(self) -> None:
        for model in (
            "gpt-6-astra",
            "o4-mini",
            "codex-mini-latest",
            "openai/gpt-6-astra",
            "azure/gpt-5",
            "chatgpt-4o-latest",
            "openrouter/openai/o3",
        ):
            with self.subTest(model=model):
                self.assertEqual(review.model_family(model), "openai")

    def test_anything_else_is_other(self) -> None:
        for model in ("gemini-3-pro", "google/gemini-2.0-flash", "llama-4", "ollama:llama4", "o"):
            with self.subTest(model=model):
                self.assertEqual(review.model_family(model), "other")


class SelectReviewerTest(unittest.TestCase):
    def test_claude_code_implementer_gets_codex_astra(self) -> None:
        selection = review.select_reviewer("claude-code", None, ALL_AVAILABLE)
        self.assertEqual(selection.reviewer, "codex")
        self.assertEqual(selection.model, "gpt-6-astra")
        self.assertFalse(selection.fallback_used)

    def test_codex_implementer_gets_claude_opus(self) -> None:
        selection = review.select_reviewer("codex", None, ALL_AVAILABLE)
        self.assertEqual(selection.reviewer, "claude")
        self.assertEqual(selection.model, "claude-opus-5-5")
        self.assertFalse(selection.fallback_used)

    def test_other_implementer_is_routed_by_its_model_family(self) -> None:
        cases = {"claude-sonnet-5-5": "codex", "gpt-6-astra": "claude", "gemini-3-pro": "codex"}
        for model, expected in cases.items():
            with self.subTest(model=model):
                selection = review.select_reviewer("other", model, ALL_AVAILABLE)
                self.assertEqual(selection.reviewer, expected)
                self.assertEqual(selection.implementer_model, model)

    def test_other_implementer_must_state_its_model(self) -> None:
        with self.assertRaises(review.ReviewUnavailableError):
            review.select_reviewer("other", None, ALL_AVAILABLE)

    def test_other_family_falls_back_to_claude_and_reports_it(self) -> None:
        probe = probe_with({"codex": "codex not found on PATH"})
        selection = review.select_reviewer("other", "gemini-3-pro", probe)
        self.assertEqual(selection.reviewer, "claude")
        self.assertTrue(selection.fallback_used)
        self.assertIn("codex not found on PATH", " ".join(selection.notes))

    def test_same_family_fallback_is_refused_and_reported(self) -> None:
        probe = probe_with({"codex": "codex not found on PATH"})
        with self.assertRaises(review.ReviewUnavailableError) as ctx:
            review.select_reviewer("claude-code", None, probe)
        message = str(ctx.exception)
        self.assertIn("codex not found on PATH", message)
        self.assertIn("same model family", message)

    def test_codex_implementer_never_falls_back_to_codex(self) -> None:
        probe = probe_with({"claude": "claude is not authenticated"})
        with self.assertRaises(review.ReviewUnavailableError) as ctx:
            review.select_reviewer("codex", None, probe)
        self.assertIn("claude is not authenticated", str(ctx.exception))

    def test_no_reviewer_available_refuses(self) -> None:
        probe = probe_with({"codex": "codex missing", "claude": "claude missing"})
        with self.assertRaises(review.ReviewUnavailableError) as ctx:
            review.select_reviewer("other", "gemini-3-pro", probe)
        self.assertIn("codex missing", str(ctx.exception))
        self.assertIn("claude missing", str(ctx.exception))

    def test_stated_model_overrides_the_implementer_default(self) -> None:
        # Claude Code driving an OpenAI model must not be reviewed by Codex.
        selection = review.select_reviewer("claude-code", "gpt-6-astra", ALL_AVAILABLE)
        self.assertEqual(selection.reviewer, "claude")

    def test_provider_prefixed_model_never_gets_same_family_reviewer(self) -> None:
        with self.assertRaises(review.ReviewUnavailableError) as ctx:
            review.select_reviewer(
                "other", "anthropic/claude-opus-5-5", ALL_AVAILABLE, failed={"codex": "x"}
            )
        self.assertIn(
            "claude (claude-opus-5-5) refused: same model family as the implementer (anthropic)",
            str(ctx.exception),
        )
        selection = review.select_reviewer("other", "openai/gpt-6-astra", ALL_AVAILABLE)
        self.assertEqual(selection.reviewer, "claude")

    def test_known_implementer_keeps_its_family_for_unrecognised_model(self) -> None:
        with self.assertRaises(review.ReviewUnavailableError):
            review.select_reviewer(
                "claude-code", "mystery-1", ALL_AVAILABLE, failed={"codex": "x"}
            )
        self.assertEqual(
            review.select_reviewer("codex", "mystery-1", ALL_AVAILABLE).reviewer, "claude"
        )

    def test_excluded_reviewer_is_skipped_with_its_reason(self) -> None:
        selection = review.select_reviewer(
            "other", "gemini-3-pro", ALL_AVAILABLE, failed={"codex": "codex exited 1"}
        )
        self.assertEqual(selection.reviewer, "claude")
        self.assertTrue(selection.fallback_used)
        self.assertIn("codex exited 1", " ".join(selection.notes))

    def test_unrecognised_other_model_never_falls_back(self) -> None:
        probe = probe_with({"codex": "codex not found on PATH"})
        with self.assertRaises(review.ReviewUnavailableError) as ctx:
            review.select_reviewer("other", "company-production", probe)
        message = str(ctx.exception)
        self.assertIn("codex not found on PATH", message)
        self.assertIn("'company-production' is not a recognised family", message)


class SnapshotTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.root)
        (self.root / "src").mkdir()
        (self.root / "src" / "a.py").write_text("print('a')\n")
        (self.root / "ignored.log").write_text("log\n")

    def changes(self, before: dict[str, str]) -> list[str]:
        changes: list[str] = review.diff_snapshots(before, review.snapshot(self.root))
        return changes

    def test_unchanged_tree_has_no_changes(self) -> None:
        self.assertEqual(self.changes(review.snapshot(self.root)), [])

    def test_detects_modified_added_and_removed_files(self) -> None:
        before = review.snapshot(self.root)
        (self.root / "src" / "a.py").write_text("print('b')\n")
        (self.root / "new.txt").write_text("new\n")
        (self.root / "ignored.log").unlink()
        self.assertEqual(
            self.changes(before),
            ["modified: src/a.py", "added: new.txt", "removed: ignored.log"],
        )

    def test_same_mtime_and_size_still_detected_by_content(self) -> None:
        before = review.snapshot(self.root)
        target = self.root / "src" / "a.py"
        stat = target.stat()
        target.write_text("print('z')\n")
        os.utime(target, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        self.assertEqual(self.changes(before), ["modified: src/a.py"])

    def test_detects_retargeted_symlink(self) -> None:
        (self.root / "link").symlink_to("src")
        before = review.snapshot(self.root)
        (self.root / "link").unlink()
        (self.root / "link").symlink_to("elsewhere")
        self.assertEqual(self.changes(before), ["modified: link"])

    @unittest.skipIf(os.geteuid() == 0, "root can read anything")
    def test_unreadable_paths_are_recorded_not_fatal(self) -> None:
        (self.root / "locked").mkdir()
        (self.root / "locked" / "inner.txt").write_text("x\n")
        secret = self.root / "secret.txt"
        secret.write_text("x\n")
        secret.chmod(0)
        (self.root / "locked").chmod(0)
        try:
            entries = review.snapshot(self.root)
        finally:
            (self.root / "locked").chmod(0o755)
            secret.chmod(0o644)
        self.assertTrue(entries["secret.txt"].startswith("error:"))
        self.assertTrue(entries["locked"].startswith("error:"))

    def test_detects_permission_only_changes(self) -> None:
        script = self.root / "src" / "a.py"
        script.chmod(0o755)
        (self.root / "src").chmod(0o755)
        before = review.snapshot(self.root)
        script.chmod(0o644)
        (self.root / "src").chmod(0o700)
        self.assertEqual(self.changes(before), ["modified: src", "modified: src/a.py"])

    def test_detects_root_permission_change(self) -> None:
        self.root.chmod(0o755)
        before = review.snapshot(self.root)
        self.root.chmod(0o777)
        self.assertEqual(self.changes(before), ["modified: ."])

    def test_scratch_folder_and_git_dir_are_ignored(self) -> None:
        before = review.snapshot(self.root)
        (self.root / "ai_tmp").mkdir()
        (self.root / "ai_tmp" / "findings.md").write_text("x\n")
        (self.root / ".git").mkdir()
        (self.root / ".git" / "index").write_text("x\n")
        self.assertEqual(self.changes(before), [])

    def test_agent_runtime_writes_are_ignored_but_other_tools_are_monitored(self) -> None:
        tools = self.root / ".tools"
        homes = tools / "agent-homes"
        claude = homes / "claude"
        claude.mkdir(parents=True)
        before = review.snapshot(self.root)
        (claude / "mcp-needs-auth-cache.json").write_text("{}\n")
        (tools / "source.py").write_text("changed\n")
        self.assertEqual(self.changes(before), ["added: .tools/source.py"])

    def test_codex_runtime_writes_are_ignored(self) -> None:
        home = self.root / ".tools/agent-homes/codex"
        (home / "cache/remote_plugin_catalog").mkdir(parents=True)
        (home / "state_5.sqlite").write_text("x\n")
        before = review.snapshot(self.root)
        (home / "cache/remote_plugin_catalog/c.json").write_text("{}\n")
        (home / "models_cache.json").write_text("{}\n")
        (home / "state_5.sqlite").write_text("y\n")
        (home / "state_5.sqlite-wal").write_text("x\n")
        (home / "goals_1.sqlite-shm").write_text("x\n")
        (home / ".sqlite-maintenance.lock").write_text("")
        (home / "log").mkdir()
        (home / "tmp/arg0").mkdir(parents=True)
        (home / "shell_snapshots").mkdir()
        self.assertEqual(self.changes(before), [])

    def test_codex_config_memories_and_skills_remain_monitored(self) -> None:
        home = self.root / ".tools/agent-homes/codex"
        home.mkdir(parents=True)
        before = review.snapshot(self.root)
        (home / "config.toml").write_text('model = "x"\n')
        (home / "AGENTS.md").write_text("Persistent instructions\n")
        (home / "memories_1.sqlite").write_text("x\n")
        (home / "skills/canary").mkdir(parents=True)
        self.assertEqual(
            sorted(self.changes(before)),
            [
                "added: .tools/agent-homes/codex/AGENTS.md",
                "added: .tools/agent-homes/codex/config.toml",
                "added: .tools/agent-homes/codex/memories_1.sqlite",
                "added: .tools/agent-homes/codex/skills",
                "added: .tools/agent-homes/codex/skills/canary",
            ],
        )

    def test_agent_config_and_home_replacement_are_detected(self) -> None:
        home = self.root / ".tools/agent-homes/claude"
        home.mkdir(parents=True)
        config = home / "settings.json"
        config.write_text("{}\n")
        before = review.snapshot(self.root)
        config.write_text('{"hooks": {}}\n')
        self.assertEqual(
            self.changes(before), ["modified: .tools/agent-homes/claude/settings.json"]
        )
        before = review.snapshot(self.root)
        shutil.rmtree(home)
        home.symlink_to(self.root / "src", target_is_directory=True)
        self.assertIn("modified: .tools/agent-homes/claude", self.changes(before))

    def test_claude_config_and_auto_memory_remain_monitored(self) -> None:
        home = self.root / ".tools/agent-homes/claude"
        memory = home / "projects/repo/memory"
        memory.mkdir(parents=True)
        config = home / ".claude.json"
        config.write_text("{}\n")
        before = review.snapshot(self.root)
        config.write_text('{"mcpServers": {}}\n')
        (memory / "MEMORY.md").write_text("Persistent instructions\n")
        self.assertEqual(
            self.changes(before),
            [
                "modified: .tools/agent-homes/claude/.claude.json",
                "added: .tools/agent-homes/claude/projects/repo/memory/MEMORY.md",
            ],
        )


class OutputPathTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.root)

    def test_same_second_runs_reserve_distinct_files(self) -> None:
        frozen = datetime(2026, 1, 1, tzinfo=UTC)
        with mock.patch.object(review, "datetime") as clock:
            clock.now.return_value = frozen
            first = review._output_path(self.root, "review", "codex")
            second = review._output_path(self.root, "review", "codex")  # before first is written
        self.assertNotEqual(first, second)
        self.assertTrue(first.exists())
        self.assertTrue(second.exists())


def contains(args: list[str], flags: list[str]) -> bool:
    """True if `flags` appears as a contiguous run of whole arguments."""
    return any(args[i : i + len(flags)] == flags for i in range(len(args)))


FAKE_REVIEWER = """#!{python}
import os, sys
from pathlib import Path
name = Path(sys.argv[0]).name
args = sys.argv[1:]
log = os.environ.get("FAKE_LOG")
if log:
    with open(log, "a") as handle:
        handle.write(name + " " + " ".join(args) + "\\n")
if args[:2] in (["login", "status"], ["auth", "status"]):
    sys.exit(1 if os.environ.get("FAKE_UNAUTHED") == name else 0)
brief = sys.stdin.read()
mode = os.environ.get("FAKE_MODE_" + name.upper(), "ok")
if mode == "fail":
    print("model refused", file=sys.stderr)
    sys.exit(1)
if mode == "write":
    Path(os.environ["FAKE_ROOT"], "src", "a.py").write_text("tampered\\n")
print("## Findings from " + name)
print("brief was: " + brief.strip())
"""


class CliTest(unittest.TestCase):
    """Drives the script as a subprocess with only fake reviewer CLIs on PATH."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.root)
        (self.root / "src").mkdir()
        (self.root / "src" / "a.py").write_text("print('a')\n")
        self.bin = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.bin)
        self.brief = self.bin / "brief.md"
        self.brief.write_text("review this diff\n")
        self.log = self.bin / "calls.log"
        self.env = {"PATH": str(self.bin), "FAKE_ROOT": str(self.root), "FAKE_LOG": str(self.log)}

    def install(self, *names: str) -> None:
        for name in names:
            shim = self.bin / name
            shim.write_text(FAKE_REVIEWER.format(python=sys.executable))
            shim.chmod(0o755)

    def cli(self, *args: str, **env: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True,
            text=True,
            env={**self.env, **env},
            check=False,
        )

    def run_review(self, *args: str, **env: str) -> subprocess.CompletedProcess[str]:
        return self.cli("run", *args, "--brief", str(self.brief), "--root", str(self.root), **env)

    def test_select_hidden_codex_refuses_same_family_fallback(self) -> None:
        self.install("claude")
        result = self.cli("select", "--implementer", "claude-code")
        self.assertEqual(result.returncode, review.EXIT_UNAVAILABLE)
        self.assertIn("cross-model review unavailable", result.stderr)
        self.assertIn("codex not found on PATH", result.stderr)
        self.assertIn("same model family", result.stderr)

    def test_select_hidden_codex_falls_back_for_other_family(self) -> None:
        self.install("claude")
        result = self.cli("select", "--implementer", "other", "--model", "gemini-3-pro")
        self.assertEqual(result.returncode, 0, result.stderr)
        selection = json.loads(result.stdout)
        self.assertEqual(selection["reviewer"], "claude")
        self.assertTrue(selection["fallback_used"])

    def test_select_unauthenticated_reviewer_is_unavailable(self) -> None:
        self.install("codex", "claude")
        result = self.cli("select", "--implementer", "codex", FAKE_UNAUTHED="claude")
        self.assertEqual(result.returncode, review.EXIT_UNAVAILABLE)
        self.assertIn("not authenticated", result.stderr)

    def test_run_saves_findings_in_scratch_folder(self) -> None:
        self.install("codex", "claude")
        result = self.run_review("--implementer", "claude-code")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        findings = Path(report["findings_path"])
        self.assertEqual(findings.parent, self.root / "ai_tmp")
        self.assertIn("## Findings from codex", findings.read_text())
        self.assertIn("brief was: review this diff", findings.read_text())
        self.assertEqual(report["selection"]["reviewer"], "codex")

    def test_run_uses_read_only_cli_flags(self) -> None:
        self.install("codex", "claude")
        self.assertEqual(self.run_review("--implementer", "claude-code").returncode, 0)
        self.assertEqual(self.run_review("--implementer", "codex").returncode, 0)
        calls = [
            line.split() for line in self.log.read_text().splitlines() if "status" not in line
        ]
        codex_call, claude_call = calls
        self.assertEqual(codex_call[:2], ["codex", "exec"])
        for flags in (
            ["-m", "gpt-6-astra"],
            ["--sandbox", "read-only"],
            ["--ephemeral"],
            ["--ignore-user-config"],
            ["--ignore-rules"],
            ["--disable", "plugins"],
            ["--disable", "remote_plugin"],
            ["--disable", "apps"],
        ):
            with self.subTest(codex=flags):
                self.assertTrue(contains(codex_call, flags))
        self.assertEqual(claude_call[:2], ["claude", "-p"])
        for flags in (
            ["--model", "claude-opus-5-5"],
            ["--tools", "Read,Grep,Glob"],
            ["--restricted"],
            ["--strict-mcp-config"],
            ["--permission-prompts", "none"],
            ["--no-session-persistence"],
        ):
            with self.subTest(claude=flags):
                self.assertTrue(contains(claude_call, flags))
        self.assertNotIn("--bare", claude_call)

    def test_run_fails_loudly_when_reviewer_modifies_worktree(self) -> None:
        self.install("codex", "claude")
        result = self.run_review("--implementer", "claude-code", FAKE_MODE_CODEX="write")
        self.assertEqual(result.returncode, review.EXIT_MODIFIED, result.stderr)
        self.assertIn("modified: src/a.py", result.stderr)
        self.assertIn("not a valid review", result.stderr)
        self.assertEqual(list((self.root / "ai_tmp").glob("review-*.md")), [])
        (rejected,) = (self.root / "ai_tmp").glob("rejected-*-codex.md")
        self.assertIn("## Findings from codex", rejected.read_text())

    def test_usage_error_is_not_reported_as_unavailable(self) -> None:
        self.install("codex", "claude")
        result = self.cli("select", "--implementer", "pi")
        self.assertEqual(result.returncode, 2)
        self.assertNotEqual(review.EXIT_UNAVAILABLE, 2)

    @unittest.skipIf(os.geteuid() == 0, "root can read anything")
    def test_run_refuses_unreadable_paths_before_any_reviewer_runs(self) -> None:
        self.install("codex", "claude")
        secret = self.root / "secret.txt"
        secret.write_text("x\n")
        secret.chmod(0)
        self.addCleanup(secret.chmod, 0o644)
        result = self.run_review("--implementer", "claude-code")
        self.assertEqual(result.returncode, review.EXIT_ERROR, result.stderr)
        self.assertIn("secret.txt", result.stderr)
        self.assertFalse(self.log.exists())
        self.assertFalse((self.root / "ai_tmp").exists())

    def test_missing_brief_is_a_setup_error(self) -> None:
        self.install("codex", "claude")
        missing = str(self.bin / "no-such-brief.md")
        result = self.cli(
            "run", "--implementer", "claude-code", "--brief", missing, "--root", str(self.root)
        )
        self.assertEqual(result.returncode, review.EXIT_ERROR)
        self.assertIn("cannot read brief", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_run_falls_back_when_preferred_reviewer_fails_at_runtime(self) -> None:
        self.install("codex", "claude")
        result = self.run_review(
            "--implementer", "other", "--model", "gemini-3-pro", FAKE_MODE_CODEX="fail"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["selection"]["reviewer"], "claude")
        self.assertTrue(report["selection"]["fallback_used"])
        self.assertIn("model refused", " ".join(report["selection"]["notes"]))

    def test_run_refuses_same_family_after_runtime_failure(self) -> None:
        self.install("codex", "claude")
        result = self.run_review("--implementer", "claude-code", FAKE_MODE_CODEX="fail")
        self.assertEqual(result.returncode, review.EXIT_UNAVAILABLE)
        self.assertIn("model refused", result.stderr)
        self.assertIn("same model family", result.stderr)


if __name__ == "__main__":
    unittest.main()
