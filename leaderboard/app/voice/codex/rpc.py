"""Async JSON-RPC client for `codex app-server` (ChatGPT/Codex subscription lane).

Adapted from reference/gpt-live-voice (copied, not imported, per reference/README.md).
Probed and load-tested in playground/luis/pipecat-quickstart/server (10 concurrent calls).
One process per call: the app-server is single-lane, and calls must not share state.

Only the WebRTC transport works on a subscription: websocket mode (audio relayed as
JSON-RPC) fails with "realtime conversation requires API key auth" (probed 2026-09-18,
codex-cli 0.154). So our server is the WebRTC peer: we send an SDP offer, the app-server
returns the answer in a `thread/realtime/sdp` notification, and audio flows us <-> OpenAI.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import shutil
import tomllib
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

Notification = dict[str, Any]


class CodexRpcError(RuntimeError):
    pass


# Pipecat gives setup 20 seconds; leave room to tear down one stuck process and retry
# (6 + up to 4 to close + 6 = 16 s). Over 57 scored calls thread/realtime/start answered in a
# median 1.1 s, p90 1.4 s, max 5.1 s (bc8cabf6, which went on to work), so 4 s would have torn
# down a slow but healthy start; c6fc2af7 never answered at all.
REALTIME_START_TIMEOUT = 6.0


def _child_env() -> dict[str, str]:
    # Load-bearing: with an API key visible the app-server leaves subscription auth.
    env = dict(os.environ)
    env.pop("OPENAI_API_KEY", None)
    env.pop("CODEX_API_KEY", None)
    return env


# Codex features that start MCP servers or add tools the phone brain never needs. Each call
# spawns its own app-server, so these cost seconds and CPU under a 10-call burst.
_DISABLED_FEATURES = (
    "apps",
    "plugins",
    "remote_plugin",
    "browser_use",
    "browser_use_external",
    "in_app_browser",
    "computer_use",
    # NOT code_mode_host: our dynamicTools stop reaching the brain without it (bisected).
    "image_generation",
    "hooks",
    "skill_search",
    "tool_suggest",
    "multi_agent",
    "shell_tool",
    "unified_exec",
    "workspace_dependencies",
    "skill_mcp_dependency_install",
)


def _lean_args() -> list[str]:
    """Flags that keep the per-call app-server to realtime + our dynamic tools only.

    `-c mcp_servers={}` merges instead of replacing, so every MCP server in the operator's
    ~/.codex/config.toml is disabled by name.
    """
    args = []
    for feature in _DISABLED_FEATURES:
        args += ["--disable", feature]
    config = Path(os.getenv("CODEX_HOME", Path.home() / ".codex")) / "config.toml"
    with contextlib.suppress(OSError, tomllib.TOMLDecodeError):
        for name in tomllib.loads(config.read_text()).get("mcp_servers", {}):
            args += ["-c", f"mcp_servers.{name}.enabled=false"]
    return args


class CodexAppServer:
    def __init__(
        self,
        on_notification: Callable[[Notification], Awaitable[None] | None] | None = None,
        on_request: Callable[[str, dict], Awaitable[Any]] | None = None,
    ):
        """on_request(method, params) -> result answers server->client requests
        (e.g. `item/tool/call` for our dynamic tools)."""
        self._on_notification = on_notification
        self._on_request = on_request
        self._proc: asyncio.subprocess.Process | None = None
        self._pending: dict[int, asyncio.Future] = {}
        self._seq = 0
        self._reader_task: asyncio.Task | None = None
        self._write_lock = asyncio.Lock()
        self._tasks: set[asyncio.Task] = set()  # in-flight answers to server requests

    async def start(self) -> None:
        binary = shutil.which("codex")
        if not binary:
            raise CodexRpcError("codex CLI not found; install codex >= 0.154 and run `codex login`")
        self._proc = await asyncio.create_subprocess_exec(
            binary,
            "app-server",
            "--listen",
            "stdio://",
            "--enable",
            "realtime_conversation",
            "-c",
            "model_provider=openai",
            "-c",
            "suppress_unstable_features_warning=true",
            *_lean_args(),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            env=_child_env(),
            limit=16 * 1024 * 1024,
        )
        self._reader_task = asyncio.create_task(self._read_loop())
        await self.request(
            "initialize",
            {
                "clientInfo": {"name": "prosper-voice", "version": "0.1"},
                "capabilities": {"experimentalApi": True},
            },
            timeout=25,
        )

    async def _read_loop(self) -> None:
        assert self._proc and self._proc.stdout
        while line := await self._proc.stdout.readline():
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            rid = msg.get("id")
            if rid is not None and "method" not in msg and rid in self._pending:
                fut = self._pending.pop(rid)
                if not fut.done():
                    if "error" in msg:
                        err = msg["error"]
                        fut.set_exception(CodexRpcError(str(err.get("message") or err)[:500]))
                    else:
                        fut.set_result(msg.get("result"))
            elif rid is not None and "method" in msg:
                task = asyncio.create_task(
                    self._answer(rid, msg["method"], msg.get("params") or {})
                )
                self._tasks.add(task)
                task.add_done_callback(self._tasks.discard)
            elif self._on_notification is not None:
                res = self._on_notification(msg)
                if asyncio.iscoroutine(res):
                    await res
        for fut in self._pending.values():
            if not fut.done():
                fut.set_exception(CodexRpcError("codex app-server exited"))

    async def _answer(self, rid: Any, method: str, params: dict) -> None:
        if self._on_request is None:
            await self._send(
                {
                    "jsonrpc": "2.0",
                    "id": rid,
                    "error": {"code": -32601, "message": f"unhandled {method}"},
                }
            )
            return
        try:
            result = await self._on_request(method, params)
            await self._send({"jsonrpc": "2.0", "id": rid, "result": result})
        except Exception as exc:  # the agent reads the error instead of hanging
            await self._send(
                {"jsonrpc": "2.0", "id": rid, "error": {"code": -32000, "message": str(exc)[:500]}}
            )

    async def _send(self, obj: dict) -> None:
        assert self._proc and self._proc.stdin
        async with self._write_lock:
            self._proc.stdin.write((json.dumps(obj) + "\n").encode())
            await self._proc.stdin.drain()

    async def request(self, method: str, params: dict, timeout: float = 30.0) -> Any:
        self._seq += 1
        rid = self._seq
        fut = asyncio.get_running_loop().create_future()
        self._pending[rid] = fut
        await self._send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        return await asyncio.wait_for(fut, timeout)

    async def notify(self, method: str, params: dict) -> None:
        """Fire-and-forget request (response is ignored) — used for the audio stream."""
        self._seq += 1
        await self._send({"jsonrpc": "2.0", "id": self._seq, "method": method, "params": params})

    async def close(self) -> None:
        if self._proc and self._proc.returncode is None:
            self._proc.terminate()
            try:
                await asyncio.wait_for(self._proc.wait(), 4)
            except TimeoutError:
                self._proc.kill()
        if self._reader_task:
            self._reader_task.cancel()


async def start_realtime(
    srv: CodexAppServer,
    *,
    prompt: str,
    sdp_offer: str,
    voice: str = "cove",
    brain_instructions: str | None = None,
    tools: list[dict] | None = None,
    brain_model: str = "gpt-5.6-luna",
    timeout: float = REALTIME_START_TIMEOUT,
) -> str:
    """thread/start + thread/realtime/start (WebRTC). Returns the thread id.

    With `tools`, GPT-Live delegates work to the Codex thread agent (server handoff),
    which calls our tools back via `item/tool/call` requests. The SDP answer arrives
    separately as a `thread/realtime/sdp` notification.
    """
    thread: dict[str, Any] = {"cwd": "/", "modelProvider": "openai", "ephemeral": True}
    if tools is not None:
        thread.update(
            model=brain_model,
            config={"model_reasoning_effort": "low"},
            baseInstructions=brain_instructions,
            dynamicTools=[
                {
                    "type": "function",
                    "name": t["name"],
                    "description": t["description"],
                    "inputSchema": t["parameters"],
                }
                for t in tools
            ],
            sandbox="read-only",
            approvalPolicy="never",
        )
    th = await srv.request("thread/start", thread, timeout=timeout)
    tid = th["thread"]["id"]
    await srv.request(
        "thread/realtime/start",
        {
            "threadId": tid,
            "transport": {"type": "webrtc", "sdp": sdp_offer},
            "outputModality": "audio",
            "version": "v3",
            "voice": voice,
            "prompt": prompt,
            "includeStartupContext": False,
            # Without a brain, keep delegations off the Codex agent entirely.
            "clientManagedHandoffs": tools is None,
            "delegationAckFiller": True,
        },
        timeout=timeout,
    )
    return tid
