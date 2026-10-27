"""Eval cases: evals/<skill>/evals.json. The schema is in docs/reference/evals.md.

It extends skill-creator's evals.json with a case kind, an expected-trigger
flag and deterministic assertions. Unknown keys are rejected everywhere, so a
later field such as rubric `expectations` has to be added on purpose.
"""

import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from pathlib import Path

Kind = Literal["trigger", "behaviour"]
SLUG = re.compile(r"[a-z0-9][a-z0-9-]*")
SUITE_KEYS = {"skill_name", "evals"}
CASE_KEYS = {"id", "kind", "prompt", "should_trigger", "expected_output", "files", "assertions"}
# Each assertion type's required and optional fields, beyond `type`.
ASSERTION_FIELDS: dict[str, tuple[set[str], set[str]]] = {
    "skill_triggered": (set(), set()),
    "script_ran": ({"script"}, {"args"}),
    "final_contains_script_output": ({"script", "args"}, set()),
    "output_contains": ({"value"}, set()),
    "output_matches": ({"pattern"}, set()),
}


@dataclass(frozen=True)
class Assertion:
    type: str
    script: str | None = None
    args: tuple[str, ...] | None = None
    value: str | None = None
    pattern: str | None = None


@dataclass(frozen=True)
class Case:
    id: str
    kind: Kind
    prompt: str
    should_trigger: bool
    expected_output: str | None
    assertions: tuple[Assertion, ...]


@dataclass(frozen=True)
class Suite:
    skill_name: str
    path: Path
    cases: tuple[Case, ...]


class CaseError(Exception):
    """A suite failed validation; `problems` lists every reason."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__("\n".join(problems))
        self.problems = problems


def _unknown(data: dict[str, object], allowed: set[str], where: str) -> list[str]:
    return [f"{where}: unknown key {key!r}" for key in sorted(set(data) - allowed)]


def _assertion(data: object, where: str, skill_dir: Path, problems: list[str]) -> Assertion | None:
    if not isinstance(data, dict):
        problems.append(f"{where}: an assertion must be an object")
        return None
    kind = data.get("type")
    if not isinstance(kind, str) or kind not in ASSERTION_FIELDS:
        problems.append(f"{where}: unknown assertion type {kind!r}")
        return None
    required, optional = ASSERTION_FIELDS[kind]
    before = len(problems)
    problems += _unknown(data, {"type"} | required | optional, where)
    problems += [f"{where}: missing {key!r}" for key in sorted(required - set(data))]
    for key in ("script", "value", "pattern"):
        if key in data and not isinstance(data[key], str):
            problems.append(f"{where}: {key} must be a string")
    args = data.get("args")
    if args is not None and not (isinstance(args, list) and all(isinstance(a, str) for a in args)):
        problems.append(f"{where}: args must be a list of strings")
    script = data.get("script")
    if isinstance(script, str):
        resolved = (skill_dir / script).resolve()
        if not resolved.is_relative_to(skill_dir.resolve()) or not resolved.is_file():
            problems.append(f"{where}: script {script!r} must be a file inside the skill")
    pattern = data.get("pattern")
    if isinstance(pattern, str):
        try:
            re.compile(pattern)
        except re.error as error:
            problems.append(f"{where}: pattern does not compile: {error}")
    if len(problems) > before:
        return None
    return Assertion(
        type=kind,
        script=script if isinstance(script, str) else None,
        args=tuple(args) if isinstance(args, list) else None,
        value=data.get("value"),
        pattern=pattern if isinstance(pattern, str) else None,
    )


def _case(data: object, where: str, skill_dir: Path, problems: list[str]) -> Case | None:  # noqa: PLR0912 -- one check per schema rule
    if not isinstance(data, dict):
        problems.append(f"{where}: a case must be an object")
        return None
    before = len(problems)
    case_id = data.get("id")
    if isinstance(case_id, str):
        where = f"{where} ({case_id})"
        if SLUG.fullmatch(case_id) is None:
            problems.append(f"{where}: id must be a lowercase slug ([a-z0-9-])")
    else:
        problems.append(f"{where}: missing 'id' or it is not a string")
    problems += _unknown(data, CASE_KEYS, where)
    kind = data.get("kind")
    if kind not in ("trigger", "behaviour"):
        problems.append(f"{where}: kind must be 'trigger' or 'behaviour', got {kind!r}")
    prompt = data.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        problems.append(f"{where}: prompt must be a nonempty string")
    if "should_trigger" not in data:
        problems.append(f"{where}: missing 'should_trigger'")
    should = data.get("should_trigger")
    if "should_trigger" in data and not isinstance(should, bool):
        problems.append(f"{where}: should_trigger must be true or false")
    expected = data.get("expected_output")
    if expected is not None and not isinstance(expected, str):
        problems.append(f"{where}: expected_output must be a string")
    files = data.get("files", [])
    if files != []:
        problems.append(
            f"{where}: input files are not staged yet (deferred to a later ticket); "
            "remove 'files' or leave it empty"
        )
    raw_assertions = data.get("assertions", [])
    if not isinstance(raw_assertions, list):
        problems.append(f"{where}: assertions must be a list")
        raw_assertions = []
    assertions = [
        _assertion(item, f"{where}: assertions[{index}]", skill_dir, problems)
        for index, item in enumerate(raw_assertions)
    ]
    if kind == "behaviour":
        if should is not True:
            problems.append(f"{where}: behaviour cases need should_trigger: true")
        if not raw_assertions:
            problems.append(f"{where}: behaviour cases need at least one assertion")
    if len(problems) > before:
        return None
    return Case(
        id=str(case_id),
        kind="trigger" if kind == "trigger" else "behaviour",
        prompt=str(prompt),
        should_trigger=bool(should),
        expected_output=expected,
        assertions=tuple(a for a in assertions if a is not None),
    )


def load_suite(root: Path, directory: str) -> Suite:
    """Load and validate evals/<directory>/evals.json, or raise CaseError."""
    path = root / "evals" / directory / "evals.json"
    where = path.relative_to(root).as_posix()
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as error:
        raise CaseError([f"{where}: not valid JSON: {error}"]) from error
    if not isinstance(data, dict):
        raise CaseError([f"{where}: the suite must be a JSON object"])
    problems = _unknown(data, SUITE_KEYS, where)
    name = data.get("skill_name")
    skill_dir = root / "skills" / str(name)
    if name != directory:
        problems.append(f"{where}: skill_name {name!r} must match its directory {directory!r}")
    if not (skill_dir / "SKILL.md").is_file():
        problems.append(f"{where}: no shipped skill skills/{name}/ for skill_name {name!r}")
    raw_cases = data.get("evals")
    if not isinstance(raw_cases, list) or not raw_cases:
        problems.append(f"{where}: evals must be a nonempty list")
        raw_cases = []
    cases = [
        _case(item, f"{where}: evals[{index}]", skill_dir, problems)
        for index, item in enumerate(raw_cases)
    ]
    ids = [item.get("id") for item in raw_cases if isinstance(item, dict)]
    problems += [
        f"{where}: duplicate id {case_id!r}"
        for case_id in sorted({i for i in ids if isinstance(i, str) and ids.count(i) > 1})
    ]
    if problems:
        raise CaseError(problems)
    return Suite(str(name), path, tuple(case for case in cases if case is not None))


def validate_all(root: Path) -> list[str]:
    """Every problem in every evals/*/evals.json; empty when all are valid."""
    problems: list[str] = []
    for path in sorted((root / "evals").glob("*/evals.json")):
        try:
            load_suite(root, path.parent.name)
        except CaseError as error:
            problems += error.problems
    return problems
