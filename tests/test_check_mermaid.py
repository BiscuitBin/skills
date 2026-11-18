"""Run scripts/check-mermaid.mjs as `just check-mermaid` runs it, on Markdown written here.

The checker renders each top-level `mermaid` block with the pinned Mermaid in the
pinned chrome-headless-shell, so these tests need `just initialize` to have
installed the browser. A missing browser fails them; it never skips them.
"""

import http.server
import json
import os
import shutil
import subprocess
import threading
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts/check-mermaid.mjs"
# The Mermaid version GitHub's viewer bundle hard-coded on 2026-11-10. GitHub
# publishes no version, so change this, and the override, only after reading
# GitHub's again (an `info` block in a comment preview shows it).
GITHUB_MERMAID = "12.2.0"
FENCE = "```"
GOOD = f"{FENCE}mermaid\nflowchart LR\n    A --> B\n{FENCE}\n"
# Mermaid's flowchart grammar rejects an unquoted parenthesis inside a label.
BAD = f"{FENCE}mermaid\nflowchart LR\n    A[load(path)] --> B\n{FENCE}\n"


def check(
    tmp_path: Path, files: dict[str, str], *args: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    for name, text in files.items():
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    node = shutil.which("node")
    assert node
    return subprocess.run(
        [node, str(SCRIPT), *(args or files)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_a_valid_block_passes(tmp_path: Path) -> None:
    result = check(tmp_path, {"ok.md": "# Title\n\n" + GOOD})
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines()[-1] == "check-mermaid: 1 block in 1 file, 0 failed."


def test_a_syntax_error_fails_and_names_the_opening_fence_line(tmp_path: Path) -> None:
    result = check(tmp_path, {"bad.md": "# Title\n\nSome prose.\n\n" + BAD})
    assert result.returncode == 1, result.stdout + result.stderr
    [first] = [line for line in result.stdout.splitlines() if line.startswith("bad.md:")]
    assert first.startswith("bad.md:5: Parse error on line 2:")
    # Mermaid's own message follows, without the browser's stack frames.
    assert "Expecting" in result.stdout
    assert "mermaid-cli-intercept" not in result.stdout
    assert result.stdout.splitlines()[-1] == "check-mermaid: 1 block in 1 file, 1 failed."


def test_only_the_bad_block_among_good_ones_is_named(tmp_path: Path) -> None:
    # The blocks open on lines 1, 8 and 15.
    text = GOOD + "\nProse.\n\n" + BAD + "\nMore prose.\n\n" + GOOD
    result = check(tmp_path, {"mixed.md": text})
    assert result.returncode == 1, result.stdout + result.stderr
    named = [line.split(":")[1] for line in result.stdout.splitlines() if line.startswith("mixed")]
    assert named == ["8"]
    assert result.stdout.splitlines()[-1] == "check-mermaid: 3 blocks in 1 file, 1 failed."


def test_a_block_inside_a_longer_outer_fence_is_not_checked(tmp_path: Path) -> None:
    # GitHub shows a nested fence as code, so its diagram is never rendered.
    for outer in ("````", "~~~"):
        result = check(tmp_path, {"nested.md": f"{outer}markdown\n{BAD}{outer}\n"})
        assert result.returncode == 0, result.stdout + result.stderr
        assert result.stdout.splitlines()[-1] == "check-mermaid: 0 blocks in 1 file, 0 failed."


def test_a_fence_inside_an_html_comment_opens_nothing(tmp_path: Path) -> None:
    # CommonMark ends the comment at the first line holding -->, so the block after it is real.
    result = check(tmp_path, {"hidden.md": f"<!--\n````text\n-->\n\n{BAD}"})
    assert result.returncode == 1, result.stdout + result.stderr
    named = [
        line.split(":")[1] for line in result.stdout.splitlines() if line.startswith("hidden")
    ]
    assert named == ["5"]


def test_a_block_inside_an_html_comment_is_not_checked(tmp_path: Path) -> None:
    # GitHub drops the comment, so a block in it is never rendered; `; two` would not parse.
    block = f"{FENCE}mermaid\nsequenceDiagram\n    A->>B: one; two\n{FENCE}\n"
    result = check(tmp_path, {"comment.md": f"<!--\n{block}-->\n"})
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines()[-1] == "check-mermaid: 0 blocks in 1 file, 0 failed."


def test_a_flowchart_arrow_ends_an_html_comment(tmp_path: Path) -> None:
    # BAD's arrow line holds -->, which ends the comment; the fence after it has no info string.
    result = check(tmp_path, {"arrow.md": f"<!--\n{BAD}-->\n"})
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines()[-1] == "check-mermaid: 0 blocks in 1 file, 0 failed."


def test_a_comment_opener_inside_a_fence_starts_nothing(tmp_path: Path) -> None:
    result = check(tmp_path, {"code.md": f"{FENCE}text\n<!--\n{FENCE}\n\n{BAD}"})
    assert result.returncode == 1, result.stdout + result.stderr
    named = [line.split(":")[1] for line in result.stdout.splitlines() if line.startswith("code")]
    assert named == ["5"]


def test_scanning_resumes_after_an_outer_fence_closes(tmp_path: Path) -> None:
    text = f"````markdown\n{BAD}````\n\n{BAD}"
    result = check(tmp_path, {"after.md": text})
    assert result.returncode == 1, result.stdout + result.stderr
    named = [line.split(":")[1] for line in result.stdout.splitlines() if line.startswith("after")]
    assert named == ["8"]


def test_a_tilde_fence_and_an_unclosed_fence_are_checked(tmp_path: Path) -> None:
    tilde = "~~~mermaid\nflowchart LR\n    A[f(x)] --> B\n~~~\n"
    # CommonMark runs an unclosed fence to the end of the document.
    unclosed = "# Title\n\n" + BAD.removesuffix(f"{FENCE}\n")
    result = check(tmp_path, {"tilde.md": tilde, "unclosed.md": unclosed})
    assert result.returncode == 1, result.stdout + result.stderr
    assert any(line.startswith("tilde.md:1: Parse error") for line in result.stdout.splitlines())
    assert any(
        line.startswith("unclosed.md:3: Parse error") for line in result.stdout.splitlines()
    )


def test_a_file_without_mermaid_passes(tmp_path: Path) -> None:
    result = check(tmp_path, {"prose.md": f"# Title\n\n{FENCE}python\nprint(1)\n{FENCE}\n"})
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines()[-1] == "check-mermaid: 0 blocks in 1 file, 0 failed."


def test_a_block_over_mermaids_max_text_size_fails(tmp_path: Path) -> None:
    # Mermaid itself draws a "Maximum text size in diagram exceeded" diagram
    # and reports no error, so the checker counts the characters itself.
    body = "flowchart LR\n" + "    A --> B\n" * 4200
    assert len(body) > 50_000
    result = check(tmp_path, {"big.md": f"{FENCE}mermaid\n{body}{FENCE}\n"})
    assert result.returncode == 1, result.stdout + result.stderr
    assert result.stdout.startswith("big.md:1: ")
    assert "50,000" in result.stdout


def test_a_block_that_draws_mermaids_error_diagram_fails(tmp_path: Path) -> None:
    # `error` is a diagram type that draws the "Syntax error" bomb and resolves.
    result = check(tmp_path, {"bomb.md": f"{FENCE}mermaid\nerror\n{FENCE}\n"})
    assert result.returncode == 1, result.stdout + result.stderr
    assert result.stdout.startswith("bomb.md:1: ")


def test_labels_mode_prints_each_label_as_rendered(tmp_path: Path) -> None:
    flow = f'{FENCE}mermaid\nflowchart LR\n    A["say #quot;hi#quot;"] --> B\n{FENCE}\n'
    # A bare `#` ends a sequence message, so this one renders as "see".
    sequence = f"{FENCE}mermaid\nsequenceDiagram\n    A->>B: see #12 now\n{FENCE}\n"
    result = check(tmp_path, {"labels.md": f"{flow}\n{BAD}\n{sequence}"}, "--labels", "labels.md")
    assert result.returncode == 1, result.stdout + result.stderr
    lines = result.stdout.splitlines()
    assert "labels.md:1: rendered" in lines
    assert '    nodeLabel: "say \\"hi\\""' in lines
    assert any(line.startswith("labels.md:6: error: Parse error") for line in lines)
    assert "labels.md:11: rendered" in lines
    assert '    messageText: "see"' in lines
    assert not any("see #12" in line for line in lines)


def test_a_glob_is_expanded_and_one_matching_nothing_is_an_error(tmp_path: Path) -> None:
    files = {"docs/a/one.md": GOOD, "docs/two.md": BAD, "docs/skip.txt": BAD}
    result = check(tmp_path, files, "docs/**/*.md")
    assert result.returncode == 1, result.stdout + result.stderr
    assert result.stdout.splitlines()[0].startswith("docs/two.md:1: ")
    assert result.stdout.splitlines()[-1] == "check-mermaid: 2 blocks in 2 files, 1 failed."
    empty = check(tmp_path, {}, "nothing/**/*.md")
    assert empty.returncode == 2
    assert "nothing/**/*.md" in empty.stderr


def test_it_refuses_to_run_outside_just(tmp_path: Path) -> None:
    # Without the Justfile's PUPPETEER_CACHE_DIR, Puppeteer would look for its
    # browser in ~/.cache/puppeteer.
    env = {k: v for k, v in os.environ.items() if k != "PUPPETEER_CACHE_DIR"}
    result = check(tmp_path, {"ok.md": GOOD}, env=env)
    assert result.returncode == 2
    assert "just check-mermaid" in result.stderr


def test_mermaid_is_held_at_githubs_version_and_the_page_runs_it(tmp_path: Path) -> None:
    package = json.loads((ROOT / "package.json").read_text())
    lock = json.loads((ROOT / "package-lock.json").read_text())
    assert package["overrides"]["mermaid"] == GITHUB_MERMAID
    assert lock["packages"]["node_modules/mermaid"]["version"] == GITHUB_MERMAID
    # mermaid-cli loads Mermaid from node_modules into the page, so the
    # override reaches the renderer; `info` draws the version it runs.
    result = check(
        tmp_path, {"info.md": f"{FENCE}mermaid\ninfo\n{FENCE}\n"}, "--labels", "info.md"
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert f'    version: "v{GITHUB_MERMAID}"' in result.stdout.splitlines()


def test_the_justfile_keeps_puppeteer_and_its_browser_in_the_project() -> None:
    # `just test` runs this, so the environment is the Justfile's.
    cache = Path(os.environ["PUPPETEER_CACHE_DIR"])
    assert cache.resolve() == (ROOT / ".tools/puppeteer").resolve()
    assert os.environ["PUPPETEER_SKIP_DOWNLOAD"] == "true"


def test_a_diagram_never_reaches_the_network(tmp_path: Path) -> None:
    # The checker renders agent output, and antiscript keeps HTML such as an
    # <img> in a label, which Chrome would fetch. A local server stands in for
    # any host; the browser must not request anything from it.
    requests: list[str] = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            requests.append(self.path)
            self.send_response(404)
            self.end_headers()

        def log_message(self, *args: object) -> None:
            pass

    with http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{server.server_address[1]}/x.png"
        block = f"{FENCE}mermaid\nflowchart LR\n    A[\"<img src='{url}'> x\"] --> B\n{FENCE}\n"
        result = check(tmp_path, {"img.md": block}, "--labels", "img.md")
        server.shutdown()
    assert result.returncode == 0, result.stdout + result.stderr
    assert requests == []
