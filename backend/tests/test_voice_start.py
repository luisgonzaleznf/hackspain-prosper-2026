import asyncio
from types import SimpleNamespace

import pytest
from app.voice.codex.peer import CodexLivePeer


class FakeDataChannel:
    readyState = "open"

    def on(self, event):
        def decorator(handler):
            return handler

        return decorator


class FakePeerConnection:
    def __init__(self, *args, **kwargs):
        self.localDescription = None
        self.remote = None

    def on(self, event):
        def decorator(handler):
            return handler

        return decorator

    def addTrack(self, track):
        pass

    def createDataChannel(self, label):
        return FakeDataChannel()

    async def createOffer(self):
        return SimpleNamespace(sdp="offer")

    async def setLocalDescription(self, offer):
        self.localDescription = offer

    async def setRemoteDescription(self, description):
        self.remote = description


class FakeRpc:
    def __init__(self, behavior, on_notification, thread_id):
        self.behavior = behavior
        self.on_notification = on_notification
        self.thread_id = thread_id
        self.closed = False
        self.requests = []

    async def start(self):
        pass

    async def request(self, method, params, timeout=30.0):
        self.requests.append((method, timeout))
        if method == "thread/start":
            return {"thread": {"id": self.thread_id}}
        if method == "thread/realtime/start":
            if self.behavior == "hang":
                await asyncio.wait_for(asyncio.Future(), timeout)
            self.on_notification({"method": "thread/realtime/sdp", "params": {"sdp": "answer"}})
            return {}
        raise AssertionError(f"unexpected RPC method {method}")

    async def close(self):
        self.closed = True


def make_peer(monkeypatch, behaviors, events):
    monkeypatch.setattr("app.voice.codex.peer.RTCPeerConnection", FakePeerConnection)
    peer = CodexLivePeer(prompt="test", on_event=events.append)
    servers = iter(behaviors)
    created = []

    def new_server():
        server = FakeRpc(next(servers), peer._on_notification, f"thread-{len(created) + 1}")
        created.append(server)
        return server

    peer._new_server = new_server
    peer._srv = new_server()
    return peer, created


def run(coro):
    return asyncio.run(coro)


def test_voice_start_retries_a_hung_live_start(monkeypatch):
    monkeypatch.setattr("app.voice.codex.peer.LIVE_START_TIMEOUT", 0.01)
    events = []
    peer, servers = make_peer(monkeypatch, ["hang", "ok"], events)

    run(peer.start())

    assert peer.thread_id == "thread-2"
    assert peer._pc.remote.sdp == "answer"
    assert [server.closed for server in servers] == [True, False]
    live_calls = [
        (server, timeout)
        for server in servers
        for method, timeout in server.requests
        if method == "thread/realtime/start"
    ]
    assert len(live_calls) == 2
    assert all(timeout == 0.01 for _, timeout in live_calls)
    assert [event["type"] for event in events if "type" in event] == ["voice.start_retry"]


def test_voice_start_raises_after_one_retry_also_times_out(monkeypatch):
    monkeypatch.setattr("app.voice.codex.peer.LIVE_START_TIMEOUT", 0.01)
    events = []
    peer, servers = make_peer(monkeypatch, ["hang", "hang"], events)

    with pytest.raises(TimeoutError):
        run(peer.start())

    assert [server.closed for server in servers] == [True, True]
    live_calls = [
        method
        for server in servers
        for method, timeout in server.requests
        if method == "thread/realtime/start"
    ]
    assert len(live_calls) == 2
    assert [event["type"] for event in events if "type" in event] == ["voice.start_retry"]


def test_voice_start_healthy_path_does_not_retry(monkeypatch):
    monkeypatch.setattr("app.voice.codex.peer.LIVE_START_TIMEOUT", 0.01)
    events = []
    peer, servers = make_peer(monkeypatch, ["ok"], events)

    run(peer.start())

    assert peer.thread_id == "thread-1"
    assert len(servers) == 1
    assert [
        method for method, timeout in servers[0].requests if method == "thread/realtime/start"
    ] == ["thread/realtime/start"]
    assert not any(event.get("type") == "voice.start_retry" for event in events)
