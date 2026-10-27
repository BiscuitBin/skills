"""A local stand-in for the Anthropic Messages API that replays scripted turns.

The pinned Claude Code CLI talks to it through ANTHROPIC_BASE_URL, so tests run
the real CLI end to end without credentials. Each request is recorded with its
headers and body, which shows exactly what the model would have seen.
"""

import json
import threading
from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator

# One turn is the content blocks of one assistant reply, such as
# [{"type": "text", "text": "hi"}] or
# [{"type": "tool_use", "id": "toolu_1", "name": "Skill", "input": {"skill": "cowsay"}}].
# The reply to a request is the turn indexed by how many assistant messages the
# request already holds; the last turn repeats.
Turn = list[dict[str, Any]]
Script = list[Turn] | Mapping[str, list[Turn]]


@dataclass
class Request:
    path: str
    headers: dict[str, str]
    body: str


@dataclass
class FakeAnthropic:
    url: str
    requests: list[Request] = field(default_factory=list)

    def bodies(self) -> str:
        return "\n".join(request.body for request in self.requests)


def text(value: str) -> Turn:
    return [{"type": "text", "text": value}]


def tool(name: str, tool_input: dict[str, Any], tool_id: str) -> Turn:
    return [{"type": "tool_use", "id": tool_id, "name": name, "input": tool_input}]


def _event(kind: str, data: dict[str, Any]) -> bytes:
    return f"event: {kind}\ndata: {json.dumps(data)}\n\n".encode()


def _stream(turn: Turn, model: str, number: int) -> bytes:
    stop = "tool_use" if any(block["type"] == "tool_use" for block in turn) else "end_turn"
    message: dict[str, Any] = {
        "id": f"msg_{number}",
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": [],
        "stop_reason": None,
        "stop_sequence": None,
        "usage": {"input_tokens": 1, "output_tokens": 0},
    }
    parts = [_event("message_start", {"type": "message_start", "message": message})]
    for index, block in enumerate(turn):
        start: dict[str, Any]
        delta: dict[str, Any]
        if block["type"] == "text":
            start = {"type": "text", "text": ""}
            delta = {"type": "text_delta", "text": block["text"]}
        else:
            start = {"type": "tool_use", "id": block["id"], "name": block["name"], "input": {}}
            delta = {"type": "input_json_delta", "partial_json": json.dumps(block["input"])}
        parts += [
            _event(
                "content_block_start",
                {"type": "content_block_start", "index": index, "content_block": start},
            ),
            _event(
                "content_block_delta",
                {"type": "content_block_delta", "index": index, "delta": delta},
            ),
            _event("content_block_stop", {"type": "content_block_stop", "index": index}),
        ]
    parts += [
        _event(
            "message_delta",
            {
                "type": "message_delta",
                "delta": {"stop_reason": stop, "stop_sequence": None},
                "usage": {"output_tokens": 1},
            },
        ),
        _event("message_stop", {"type": "message_stop"}),
    ]
    return b"".join(parts)


def _script_for(request: dict[str, Any], turns: Script) -> list[Turn]:
    if isinstance(turns, list):
        return turns
    asked = json.dumps(request.get("messages", [])[:1])
    for prompt, script in turns.items():
        if json.dumps(prompt)[1:-1] in asked:
            return script
    return [text("No script for this prompt.")]


@contextmanager
def serve(turns: Script) -> Iterator[FakeAnthropic]:
    """Serve the scripted turns on a free local port until the block exits.

    `turns` is one script for every request, or a script per prompt: the first
    prompt found in the request's first message picks the script.
    """
    recorded: list[Request] = []

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_POST(self) -> None:
            body = self.rfile.read(int(self.headers.get("content-length", "0"))).decode()
            recorded.append(Request(self.path, dict(self.headers.items()), body))
            request = json.loads(body or "{}")
            model = str(request.get("model", "fake-model"))
            replies = sum(1 for m in request.get("messages", []) if m.get("role") == "assistant")
            script = _script_for(request, turns)
            turn = script[min(replies, len(script) - 1)]
            if request.get("stream"):
                data, kind = _stream(turn, model, len(recorded)), "text/event-stream"
            else:
                content = [b for b in turn if b["type"] == "text"] or text("ok")
                reply = {
                    "id": f"msg_{len(recorded)}",
                    "type": "message",
                    "role": "assistant",
                    "model": model,
                    "content": content,
                    "stop_reason": "end_turn",
                    "stop_sequence": None,
                    "usage": {"input_tokens": 1, "output_tokens": 1},
                }
                data, kind = json.dumps(reply).encode(), "application/json"
            self.send_response(200)
            self.send_header("content-type", kind)
            self.send_header("content-length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            self.send_response(404)
            self.send_header("content-length", "0")
            self.end_headers()

        def log_message(self, *_args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield FakeAnthropic(f"http://127.0.0.1:{server.server_address[1]}", recorded)
    finally:
        server.shutdown()
        server.server_close()
