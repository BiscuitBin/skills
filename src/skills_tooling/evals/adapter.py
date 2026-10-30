"""The adapter interface: what the harness needs from each agent CLI.

See docs/reference/evals.md. Each adapter prepares isolated homes, installs a
skill into a workspace (or nothing, for a baseline), runs one prompt headless,
and normalises the agent's event stream into a Trace.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar, Literal, Protocol

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

Status = Literal["ok", "infra_error"]
# How a discovery location is kept out of a trial. See discovery_locations().
Mitigation = Literal["redirected", "suppressed", "reported", "controlled", "not-a-location"]


@dataclass(frozen=True)
class TrialPaths:
    """One trial's directory: .eval-workspaces/<run-id>/<case-id>/."""

    root: Path
    workspace: Path
    home: Path
    tmp: Path
    bin: Path

    @property
    def python_log(self) -> Path:
        """Where the trial's python3 wrapper records each invocation."""
        return self.tmp / "python-exec.log"


@dataclass(frozen=True)
class Homes:
    """The isolated agent and user homes, and the child's whole environment."""

    agent_home: Path
    user_home: Path
    env: Mapping[str, str]


@dataclass(frozen=True)
class Location:
    """A place the agent looks for skills or instructions, and how a trial handles it."""

    name: str
    path: str
    mitigations: tuple[Mitigation, ...]
    canary: str


@dataclass(frozen=True)
class PythonCall:
    """One invocation of the trial's python3, from the wrapper's log."""

    cwd: str
    argv: tuple[str, ...]


@dataclass(frozen=True)
class RawRun:
    """What one headless run left behind, before parsing."""

    exit_code: int | None
    timed_out: bool
    transcript: Path
    stderr: str
    debug_lines: tuple[str, ...]
    python_calls: tuple[PythonCall, ...]
    survivors: bool
    elapsed: float


@dataclass(frozen=True)
class Command:
    """A shell command the agent ran, whether it succeeded, and what it printed."""

    command: str
    ok: bool
    output: str


@dataclass(frozen=True)
class Trace:
    """An agent's event stream, normalised. The input to contamination and grading."""

    skills_triggered: list[str]
    skills_invoked: list[str]
    commands: list[Command]
    final_message: str
    cli_version: str
    model: str
    exit_code: int | None
    timed_out: bool
    stream_completed: bool
    status: Status
    status_reason: str
    visible_skills: frozenset[str] | None
    visible_plugins: frozenset[str] | None
    # Slash commands at startup, and every later list the agent reported.
    # Commands in the second but not the first were discovered mid-run.
    initial_commands: frozenset[str] | None = None
    dynamic_commands: list[str] = field(default_factory=list)
    debug_lines: tuple[str, ...] = ()
    python_calls: tuple[PythonCall, ...] = ()


class CredentialError(Exception):
    """The caller's credential is missing or unreadable; nothing ran."""


class Adapter(Protocol):
    """Drives one agent CLI. Pi (ticket 07) implements it too."""

    name: ClassVar[str]
    default_model: ClassVar[str]
    # The caller's environment variables the credential comes from. results.json
    # records these names, never a value.
    credential_env: ClassVar[tuple[str, ...]]
    # The variables that move the agent's home; each must point inside the trial.
    home_env: ClassVar[tuple[str, ...]]
    # Where install_skill puts a skill, relative to the workspace.
    skills_dir: ClassVar[str]
    # Whether the agent reports the skills and plugins it loaded. When it does,
    # a missing report fails closed; when it does not, the contamination proof
    # rests on the preflight and the canary sweep.
    reports_skills: ClassVar[bool]
    # Skills and plugins built into the pinned CLI, keyed by CLI version.
    builtin_skills: ClassVar[Mapping[str, frozenset[str]]]
    builtin_plugins: ClassVar[Mapping[str, frozenset[str]]]
    # The pinned CLI binary the adapter runs.
    executable: Path

    def read_credentials(self, environ: Mapping[str, str]) -> Mapping[str, str]:
        """The credential, read from the caller; raises CredentialError when it is missing."""
        ...

    def secrets(self, credentials: Mapping[str, str]) -> list[str]:
        """Every value in the credential that must never reach a results file."""
        ...

    def trial_secrets(self, trial: TrialPaths) -> list[str]:
        """Credential values that appeared in the trial, such as a refreshed login.

        The runner reads these after the run and again before teardown, on
        every path, and scrubs and sweeps for them too. Raises when they
        cannot be read after the run, and the runner then fails the trial and
        deletes it.
        """
        ...

    def trial_credentials(
        self, trial: TrialPaths, credentials: Mapping[str, str]
    ) -> Mapping[str, str]:
        """The credential the next trial starts from.

        The trial's own copy if the agent refreshed it, else `credentials`. It
        is never written back to the caller.
        """
        ...

    def discovery_locations(self, trial: TrialPaths) -> list[Location]: ...

    def context_isolation(self, env: Mapping[str, str]) -> list[str]:
        """Problems that would let instruction files load; empty when isolated."""
        ...

    def prepare_homes(self, trial: TrialPaths) -> Homes: ...

    def install_skill(self, skill_dir: Path | None, workspace: Path) -> Path | None: ...

    def run(  # noqa: PLR0913 -- every argument is part of one headless run
        self,
        prompt: str,
        trial: TrialPaths,
        homes: Homes,
        *,
        model: str,
        timeout: float,
        credentials: Mapping[str, str],
    ) -> RawRun: ...

    def parse(self, raw: RawRun) -> Trace: ...

    def discovery_report_problems(
        self, trace: Trace, trial: TrialPaths, *, installed: bool, system_root: Path
    ) -> list[str]:
        """Problems in the agent's own report of where it looked for skills."""
        ...
