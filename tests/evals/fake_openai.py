"""A local stand-in for the OpenAI Responses API that replays scripted turns.

The pinned Codex CLI talks to it through its `openai_base_url` setting, so tests
run the real CLI end to end without credentials. Each request is recorded with
its headers and body, which shows exactly what the model would have seen.
Codex tries a WebSocket first; the fake refuses it, and Codex falls back to
HTTPS after a few retries.
"""

import json
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator

# One turn is the output items of one model reply, such as [message("hi")] or
# [shell("cat SKILL.md", "call_1")]. The reply to a request is the turn indexed
# by how many tool results the request already holds; the last turn repeats.
Turn = list[dict[str, Any]]


@dataclass
class Request:
    path: str
    headers: dict[str, str]
    body: str


@dataclass
class FakeOpenAI:
    url: str
    requests: list[Request] = field(default_factory=list)

    def bodies(self) -> str:
        return "\n".join(request.body for request in self.requests)


def message(text: str) -> Turn:
    return [{"type": "message", "text": text}]


def shell(command: str, call_id: str) -> Turn:
    """One call of Codex's code-mode `exec` tool that runs `command` and returns its output."""
    script = f"const r = await tools.exec_command({{cmd: {json.dumps(command)}}}); text(r.output);"
    return [{"type": "custom_tool_call", "call_id": call_id, "name": "exec", "input": script}]


def _event(kind: str, data: dict[str, Any]) -> bytes:
    return f"event: {kind}\ndata: {json.dumps({'type': kind, **data})}\n\n".encode()


def _item(block: dict[str, Any], item_id: str) -> dict[str, Any]:
    if block["type"] != "message":
        return {**block, "id": item_id}
    text = {"type": "output_text", "text": block["text"], "annotations": []}
    return {
        "type": "message",
        "id": item_id,
        "role": "assistant",
        "status": "completed",
        "content": [text],
    }


def _stream(turn: Turn, number: int) -> bytes:
    response = f"resp_{number}"
    parts = [_event("response.created", {"response": {"id": response}})]
    for index, block in enumerate(turn):
        item = _item(block, f"item_{number}_{index}")
        parts += [
            _event("response.output_item.added", {"output_index": index, "item": item}),
            _event("response.output_item.done", {"output_index": index, "item": item}),
        ]
    usage = {
        "input_tokens": 1,
        "output_tokens": 1,
        "total_tokens": 2,
        "input_tokens_details": {"cached_tokens": 0},
        "output_tokens_details": {"reasoning_tokens": 0},
    }
    parts.append(_event("response.completed", {"response": {"id": response, "usage": usage}}))
    return b"".join(parts)


@contextmanager
def serve(turns: list[Turn], *, api_key: str | None = None) -> Iterator[FakeOpenAI]:
    """Serve the scripted turns on a free local port until the block exits.

    With `api_key`, a request without that bearer token gets a 401, as the real
    API answers a bad credential.
    """
    recorded: list[Request] = []

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def _reply(self, status: int, data: bytes, kind: str) -> None:
            self.send_response(status)
            self.send_header("content-type", kind)
            self.send_header("content-length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self) -> None:
            body = self.rfile.read(int(self.headers.get("content-length", "0"))).decode()
            recorded.append(Request(self.path, dict(self.headers.items()), body))
            if api_key is not None and self.headers.get("authorization") != f"Bearer {api_key}":
                error = {
                    "error": {"message": "Incorrect API key provided.", "code": "invalid_api_key"}
                }
                self._reply(401, json.dumps(error).encode(), "application/json")
                return
            request = json.loads(body or "{}")
            done = sum(
                1
                for item in request.get("input", [])
                if str(item.get("type", "")).endswith("call_output")
            )
            turn = turns[min(done, len(turns) - 1)]
            self._reply(200, _stream(turn, len(recorded)), "text/event-stream")

        def do_GET(self) -> None:
            # The WebSocket upgrade and any catalog lookups: refused, so Codex uses HTTPS.
            self._reply(404, b"", "text/plain")

        def log_message(self, *_args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield FakeOpenAI(f"http://127.0.0.1:{server.server_address[1]}/v1", recorded)
    finally:
        server.shutdown()
        server.server_close()
