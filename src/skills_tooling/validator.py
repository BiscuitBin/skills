"""Validate portable Agent Skills and repo dev skills. See docs/reference/skill-validator.md."""

import argparse
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import TYPE_CHECKING, Literal
from urllib.parse import unquote, urlsplit

import yaml
from markdown_it import MarkdownIt
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

if TYPE_CHECKING:
    from collections.abc import Mapping

    from markdown_it.token import Token

MAX_NAME = 64
CLAUDE_DESCRIPTION = 1536
BODY_LINE_LIMIT = 500
TOKEN_WARNING = 5000
SHORT_DESCRIPTION_MIN = 25
SHORT_DESCRIPTION_MAX = 64
MAX_PORT = 65535

SPEC_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
AGENTS = ("claude-code", "codex", "pi")
Severity = Literal["error", "warning"]


@dataclass(frozen=True)
class Diagnostic:
    """One actionable validation result."""

    file: Path
    rule: str
    severity: Severity
    message: str
    hint: str

    def __str__(self) -> str:
        return f"{self.file}: {self.severity} [{self.rule}] {self.message}; hint: {self.hint}"


@dataclass(frozen=True)
class Extension:
    """Documented value kind and target support, in AGENTS order."""

    kind: str
    support: tuple[str, str, str] = ("supported", "ignored", "ignored")


EXTENSIONS = {
    **dict.fromkeys(("user-invocable",), Extension("boolean")),
    "disable-model-invocation": Extension("boolean", ("supported", "ignored", "supported")),
    **dict.fromkeys(
        ("when_to_use", "argument-hint", "model", "agent", "shell", "effort"), Extension("string")
    ),
    "context": Extension("fork"),
    **dict.fromkeys(("arguments", "paths", "disallowed-tools"), Extension("string-list")),
    "hooks": Extension("mapping"),
}


def _unique_keys(node: Node, seen: set[int]) -> None:
    if id(node) in seen:
        return
    seen.add(id(node))
    if isinstance(node, MappingNode):
        keys: set[str] = set()
        for key, value in node.value:
            if not isinstance(key, ScalarNode) or key.tag != "tag:yaml.org,2002:str":
                message = "YAML keys must be strings"
                raise ValueError(message)
            if key.value in keys:
                message = f"duplicate YAML key: {key.value}"
                raise ValueError(message)
            keys.add(key.value)
            _unique_keys(value, seen)
    elif isinstance(node, SequenceNode):
        for value in node.value:
            _unique_keys(value, seen)


def _load_yaml(text: str) -> dict[str, object]:
    node = yaml.compose(text, Loader=yaml.SafeLoader)
    if node is not None:
        _unique_keys(node, set())
    data: object = yaml.safe_load(text)
    if not isinstance(data, dict):
        message = "expected a YAML mapping"
        raise TypeError(message)
    return {str(key): value for key, value in data.items()}


def _strings(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _kind_matches(value: object, kind: str) -> bool:
    if kind == "boolean":
        return isinstance(value, bool)
    if kind == "mapping":
        return isinstance(value, dict)
    if kind == "fork":
        return value == "fork"
    if kind == "string-list":
        return isinstance(value, str) or _strings(value)
    return isinstance(value, str)


def _name_error(name: object) -> str | None:
    if not isinstance(name, str):
        return f"name must be a string, got {name!r}"
    if not 1 <= len(name) <= MAX_NAME:
        return f"name {name!r} has {len(name)} characters; expected 1-64"
    if re.fullmatch(r"[a-z0-9-]+", name) is None:
        return f"name {name!r} must contain only lowercase ASCII letters, digits and hyphens"
    if name.startswith("-") or name.endswith("-"):
        return f"name {name!r} has a leading or trailing hyphen"
    if "--" in name:
        return f"name {name!r} has consecutive hyphens"
    return None


class _HTMLReferences(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.targets: list[tuple[str, bool]] = []

    def handle_starttag(self, _tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if key in {"href", "src"} and value is not None:
                self.targets.append((value, False))


def _references(tokens: list[Token]) -> list[tuple[str, bool]]:
    """Return destinations and whether they use the inline skill-root convention."""
    targets: list[tuple[str, bool]] = []
    for token in tokens:
        if token.type in {"link_open", "image"}:
            target = token.attrGet("href" if token.type == "link_open" else "src")
            if isinstance(target, str):
                targets.append((target, False))
        elif token.type in {"html_inline", "html_block"}:
            html = _HTMLReferences()
            html.feed(token.content)
            targets.extend(html.targets)
        elif token.type == "code_inline":
            path = token.content.removeprefix("./")
            if (
                path.startswith(("scripts/", "references/", "assets/"))
                and not path.endswith("/")
                and not any(character.isspace() or character in "<>*?{}" for character in path)
            ):
                targets.append((token.content, True))
        if token.children:
            targets.extend(_references(token.children))
    return targets


def _exact_case(path: Path, root: Path) -> bool:
    """Require the same spelling on case-sensitive and case-insensitive filesystems."""
    current = root
    for part in path.relative_to(root).parts:
        if part == "..":
            current = current.parent
        elif part != ".":
            if current.is_relative_to(root) and part not in {
                entry.name for entry in current.iterdir()
            }:
                return False
            current = (current / part).resolve()
    return True


def _root_case_alias(path: Path, root: Path) -> bool:
    """Recognize an alternate root spelling by filesystem identity, without listing ancestors."""
    alias = Path(*path.parts[: len(root.parts)])
    try:
        return alias != root and alias.samefile(root)
    except OSError:
        return False


def _reference_path(file: Path, root: Path, target: str, *, skill_relative: bool) -> Path | None:
    """Interpret inline paths literally and Markdown/HTML destinations as URLs."""
    if skill_relative:
        return root / target
    url = urlsplit(target)
    if url.scheme or url.netloc or not url.path:
        return None
    return file.parent / unquote(url.path)


class _Validator:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.diagnostics: list[Diagnostic] = []
        self.visited: set[Path] = set()

    def report(
        self, file: Path, rule: str, message: str, hint: str, severity: Severity = "error"
    ) -> None:
        self.diagnostics.append(Diagnostic(file, rule, severity, message, hint))

    def frontmatter(self, file: Path) -> tuple[dict[str, object], str] | None:
        try:
            text = file.read_text(encoding="utf-8")
            lines = text.splitlines(keepends=True)
            _shape(bool(lines) and lines[0].strip() == "---", "missing opening YAML delimiter")
            end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
            return _load_yaml("".join(lines[1:end])), "".join(lines[end + 1 :])
        except FileNotFoundError:
            self.report(
                file,
                "frontmatter",
                "missing SKILL.md entrypoint",
                "create SKILL.md in this skill directory",
            )
            return None
        except (
            OSError,
            UnicodeError,
            ValueError,
            TypeError,
            StopIteration,
            yaml.YAMLError,
        ) as error:
            self.report(
                file,
                "frontmatter",
                str(error) or "unclosed YAML",
                "provide UTF-8 SKILL.md with a unique-key YAML mapping between --- lines",
            )
            return None

    def fields(
        self,
        file: Path,
        data: dict[str, object],
        shipped: bool,
        extensions: Mapping[str, Extension],
    ) -> None:
        name = data.get("name")
        name_error = _name_error(name)
        if name_error is not None:
            self.report(
                file,
                "name-format",
                name_error,
                "use 1-64 lowercase ASCII letters/digits with single internal hyphens",
            )
        if isinstance(name, str) and name != self.root.name:
            self.report(
                file,
                "name-directory",
                f"name {name!r} differs from directory {self.root.name!r}",
                "make name and parent directory identical",
            )
        for field, limit in (("description", 1024), ("compatibility", 500)):
            if field == "compatibility" and field not in data:
                continue
            value = data.get(field)
            if not isinstance(value, str) or not value.strip() or len(value) > limit:
                self.report(
                    file,
                    field,
                    f"{field} must be a nonblank string of at most {limit} characters",
                    f"write a {field} within the length limit",
                )
        metadata = data.get("metadata", {})
        if not isinstance(metadata, dict) or any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in metadata.items()
        ):
            self.report(
                file,
                "metadata",
                "metadata must map strings to strings",
                "quote every metadata key and value",
            )
        for field in ("license", "allowed-tools"):
            if field in data and not isinstance(data[field], str):
                if field == "allowed-tools" and not shipped and _strings(data[field]):
                    continue
                self.report(
                    file,
                    "field-type",
                    f"{field} must be a string",
                    "use the spec string form (dev allowed-tools also permits string lists)",
                )
        self.extensions(file, data, shipped, extensions)

    def extensions(
        self,
        file: Path,
        data: dict[str, object],
        shipped: bool,
        extensions: Mapping[str, Extension],
    ) -> None:
        for field, value in data.items():
            if field in SPEC_FIELDS:
                continue
            extension = extensions.get(field)
            if extension is None:
                self.report(
                    file,
                    "field-unknown",
                    f"unknown field {field!r}",
                    "remove it or use string metadata; document new extensions before allowlisting",
                )
                continue
            if not _kind_matches(value, extension.kind):
                self.report(
                    file,
                    "extension-type",
                    f"{field} expects {extension.kind}",
                    "use the documented extension value type",
                )
            if shipped:
                rejected = [
                    agent
                    for agent, status in zip(AGENTS, extension.support, strict=True)
                    if status == "rejected"
                ]
                if rejected:
                    self.report(
                        file,
                        "extension-portability",
                        f"{field} rejected by {', '.join(rejected)}",
                        "use spec fields or agent-specific metadata",
                    )
                elif any(status != "supported" for status in extension.support):
                    self.report(
                        file,
                        "extension-portability",
                        f"{field} semantics are not supported by every target",
                        "prefer spec fields or agents/openai.yaml for Codex policy",
                        "warning",
                    )
        description, when = data.get("description"), data.get("when_to_use")
        if (
            isinstance(description, str)
            and isinstance(when, str)
            and len(description + when) > CLAUDE_DESCRIPTION
        ):
            self.report(
                file,
                "claude-description",
                "Claude truncates description plus when_to_use above 1536 characters",
                "shorten the combined text",
                "warning",
            )

    def body(self, file: Path, body: str) -> None:
        if len(body.splitlines()) >= BODY_LINE_LIMIT:
            self.report(
                file,
                "body-lines",
                "body has 500 or more lines",
                "move optional detail into referenced files; keep body under 500 lines",
            )
        tokens = (len(body.encode("utf-8")) + 3) // 4
        if tokens > TOKEN_WARNING:
            self.report(
                file,
                "body-tokens",
                f"body is approximately {tokens} tokens (UTF-8 bytes/4)",
                "shorten body or move detail to references; estimate is language dependent",
                "warning",
            )
        self.references(file, body)

    def references(self, file: Path, text: str) -> None:
        resolved = file.resolve()
        if resolved in self.visited:
            return
        self.visited.add(resolved)
        targets = _references(MarkdownIt("commonmark").parse(text))
        descendants: list[Path] = []
        has_relative = False
        for target, skill_relative in dict.fromkeys(targets):
            try:
                literal = _reference_path(file, self.root, target, skill_relative=skill_relative)
                if literal is None:
                    continue
                path = literal.resolve()
                has_relative |= path not in {resolved, self.root / "SKILL.md"}
                if not path.is_relative_to(self.root):
                    case_alias = _root_case_alias(path, self.root)
                    self.report(
                        file,
                        "reference-missing" if case_alias else "reference-escape",
                        f"reference {target!r} differs in skill-directory case"
                        if case_alias
                        else f"reference {target!r} leaves skill",
                        "correct the reference, including the skill directory's exact case"
                        if case_alias
                        else "bundle the target inside this skill and use a relative path",
                    )
                    continue
                if (
                    not path.is_file()
                    or not _exact_case(literal, self.root)
                    or not _exact_case(path, self.root)
                ):
                    self.report(
                        file,
                        "reference-missing",
                        f"reference {target!r} is missing or differs in filename case",
                        "create the bundled file or correct the reference, including exact case",
                    )
                    continue
                descendants.append(path)
            except (OSError, ValueError, RuntimeError) as error:
                self.report(
                    file,
                    "reference-missing",
                    f"cannot resolve {target!r}: {error}",
                    "use a readable, valid relative file path",
                )
        if has_relative and resolved != self.root / "SKILL.md":
            self.report(
                file,
                "reference-chain",
                "referenced file contains further file references",
                "remove unnecessary cross-links; link required resources directly from SKILL.md",
                "warning",
            )
        for path in descendants:
            if path.suffix.lower() not in {".md", ".markdown", ".txt"}:
                continue  # Validate source/binary resources without interpreting code as Markdown.
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeError:
                continue  # Binary resources have no Markdown references.
            except OSError as error:
                self.report(
                    file,
                    "reference-missing",
                    f"unreadable reference: {error}",
                    "make the bundled file readable",
                )
                continue
            if "\0" not in content:
                self.references(path, content)

    def openai(self) -> None:
        file = self.root / "agents/openai.yaml"
        if not file.exists() and not file.is_symlink():
            return
        try:
            _shape(file.resolve().is_relative_to(self.root), "openai.yaml leaves skill")
            data = _load_yaml(file.read_text(encoding="utf-8"))
            _openai_shape(data)
        except (OSError, UnicodeError, ValueError, TypeError, yaml.YAMLError) as error:
            self.report(
                file,
                "openai-shape",
                str(error),
                "use the documented interface, policy and dependencies mappings",
            )
            return
        interface = data.get("interface")
        if isinstance(interface, dict):
            short = interface.get("short_description")
            if (
                isinstance(short, str)
                and not SHORT_DESCRIPTION_MIN <= len(short) <= SHORT_DESCRIPTION_MAX
            ):
                self.report(
                    file,
                    "openai-description",
                    "short_description should have 25-64 characters",
                    "write a concise UI label in that range",
                    "warning",
                )


def _shape(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _keys(data: Mapping[str, object], allowed: set[str], section: str) -> None:
    unknown = data.keys() - allowed
    _shape(not unknown, f"unknown {section} key(s): {', '.join(sorted(unknown))}")


def _openai_shape(data: dict[str, object]) -> None:
    _keys(data, {"interface", "policy", "dependencies"}, "openai.yaml")
    interface = data.get("interface", {})
    _shape(isinstance(interface, dict), "interface must be a mapping")
    if isinstance(interface, dict):
        _keys(
            interface,
            {
                "display_name",
                "short_description",
                "icon_small",
                "icon_large",
                "brand_color",
                "default_prompt",
            },
            "interface",
        )
        _shape(
            all(isinstance(value, str) for value in interface.values()),
            "interface values must be strings",
        )
    policy = data.get("policy", {})
    _shape(isinstance(policy, dict), "policy must be a mapping")
    if isinstance(policy, dict):
        _keys(policy, {"allow_implicit_invocation", "products"}, "policy")
        if "allow_implicit_invocation" in policy:
            _shape(
                isinstance(policy["allow_implicit_invocation"], bool),
                "allow_implicit_invocation must be boolean",
            )
        if "products" in policy:
            _shape(_strings(policy["products"]), "products must be a string list")
    dependencies = data.get("dependencies", {})
    _shape(isinstance(dependencies, dict), "dependencies must be a mapping")
    if isinstance(dependencies, dict):
        _keys(dependencies, {"tools"}, "dependencies")
        tools = dependencies.get("tools", [])
        _shape(isinstance(tools, list), "tools must be a list")
        if isinstance(tools, list):
            for tool in tools:
                _tool_shape(tool)


def _tool_shape(tool: object) -> None:
    _shape(isinstance(tool, dict), "tool must be a mapping")
    if not isinstance(tool, dict):
        return
    _keys(
        tool,
        {"type", "value", "description", "transport", "url", "command", "oauth_callback_port"},
        "tool",
    )
    for required in ("type", "value"):
        value = tool.get(required)
        _shape(
            isinstance(value, str) and bool(value.strip()),
            f"tool {required} must be a nonblank string",
        )
    for key, value in tool.items():
        if key == "oauth_callback_port":
            _shape(
                type(value) is int and 0 <= value <= MAX_PORT,
                "oauth_callback_port must be an integer 0-65535",
            )
        else:
            _shape(isinstance(value, str), f"tool {key} must be a string")


def validate_skill(
    path: Path, *, shipped: bool = True, extensions: Mapping[str, Extension] | None = None
) -> list[Diagnostic]:
    """Return diagnostics for a skill directory."""
    validator = _Validator(path)
    file = validator.root / "SKILL.md"
    parsed = validator.frontmatter(file)
    if parsed is not None:
        data, body = parsed
        validator.fields(file, data, shipped, EXTENSIONS if extensions is None else extensions)
        validator.body(file, body)
    validator.openai()
    return validator.diagnostics


def main() -> int:
    """Validate every source skill or explicitly provided skill directories."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--dev", action="store_true", help="Allow documented agent extensions.")
    args = parser.parse_args()
    diagnostics: list[Diagnostic] = []
    skills: list[tuple[Path, bool]] = []
    if args.paths:
        skills = [(path, not args.dev) for path in args.paths]
    else:
        for root in (Path("skills"), Path("dev-skills")):
            try:
                skills.extend(
                    (path, root.name == "skills")
                    for path in sorted(root.iterdir())
                    if path.is_dir() and not path.name.startswith(".")
                )
            except OSError as error:
                diagnostics.append(
                    Diagnostic(
                        root,
                        "discovery",
                        "error",
                        f"cannot discover skills: {error}",
                        "run from the repository root or supply explicit skill directories",
                    )
                )
    diagnostics.extend(
        item for path, shipped in skills for item in validate_skill(path, shipped=shipped)
    )
    for item in diagnostics:
        print(item)
    errors = sum(item.severity == "error" for item in diagnostics)
    print(
        f"Validated {len(skills)} skills: {errors} errors, {len(diagnostics) - errors} warnings."
    )
    return int(errors > 0)


if __name__ == "__main__":
    raise SystemExit(main())
