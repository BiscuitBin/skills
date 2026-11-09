"""A stand-in for the Claude Code CLI that answers the way a grader would.

test_grader.py writes a shim that runs this with a JSON config first, then the
CLI's own arguments. It records the arguments, reads the expectations and the
material from its prompt, answers by expectation text, and prints a
stream-json transcript. The canary expectation's position is random, so
answering by text keeps the tests independent of it.

Config keys:
- record: a file each call's arguments and working directory are appended to,
  as one JSON line
- mode: "reply" (default), "hang", "fail" or "no_result"
- reply: a raw reply to print instead of an answer
- verdicts: {expectation text: {"passed": bool, "evidence": str, "quote": str | None}}
- otherwise: the verdict for any text not in verdicts, such as the canary;
  by default it fails
"""

import json
import re
import sys
import time
from pathlib import Path
from typing import Any

EXPECTATIONS = re.compile(r"Expectations to judge:\n(.*?)\n\n<graded-material-", re.DOTALL)
FAILED = {"passed": False, "evidence": "Not shown in the material.", "quote": None}


def answer(prompt: str, config: dict[str, Any]) -> str:
    listed = EXPECTATIONS.search(prompt)
    lines = listed.group(1).splitlines() if listed else []
    verdicts = config.get("verdicts", {})
    otherwise = config.get("otherwise", FAILED)
    items = []
    for line in lines:
        item_id, _, text = line.partition(": ")
        items.append({"id": item_id, **verdicts.get(text, otherwise)})
    return json.dumps({"expectations": items, "notes": config.get("notes", "")})


def main() -> int:
    config: dict[str, Any] = json.loads(Path(sys.argv[1]).read_text())
    argv = sys.argv[2:]
    with Path(config["record"]).open("a") as record:
        record.write(json.dumps({"argv": argv, "cwd": str(Path.cwd())}) + "\n")
    mode = config.get("mode", "reply")
    if mode == "hang":
        time.sleep(60)
        return 0
    if mode == "fail":
        print("API Error: 500", file=sys.stderr)
        return 1
    model = argv[argv.index("--model") + 1]
    init = {"type": "system", "subtype": "init", "model": model, "claude_code_version": "0.0.0"}
    print(json.dumps(init))
    if mode == "no_result":
        return 0
    prompt = argv[argv.index("-p") + 1]
    result = config.get("reply") or answer(prompt, config)
    print(
        json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": result})
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
