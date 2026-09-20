import asyncio
from types import SimpleNamespace

from app.voice.gptlive import MeteredLive


def service(monkeypatch):
    logged, sent = [], []
    call = SimpleNamespace(log=lambda kind, **data: logged.append((kind, data)))
    svc = MeteredLive(call=call, api_key="test", settings=MeteredLive.Settings(model="gpt-live-1"))
    svc._session_started_on_connection = True

    async def no_sleep(_):
        pass

    async def send(event):
        sent.append(event.type)

    monkeypatch.setattr(asyncio, "sleep", no_sleep)
    monkeypatch.setattr(svc, "send_client_event", send)
    return svc, logged, sent


def test_empty_handoff_resumes_but_never_duplicates_work(monkeypatch):
    svc, logged, sent = service(monkeypatch)

    async def go():
        svc._backend_busy.add("delegation-1")
        await svc._resume_empty_handoff(0)
        assert not sent
        svc._backend_busy.clear()
        svc._open_function_calls["tool-1"] = "delegation-1"
        await svc._resume_empty_handoff(0)
        assert not sent
        svc._open_function_calls.clear()
        await svc._resume_empty_handoff(0)
        assert sent == ["response.create"]
        svc._speech_revision += 1
        await svc._resume_empty_handoff(0)
        assert len(sent) == 1
        svc._session_started_on_connection = False
        await svc._resume_empty_handoff(1)
        assert len(sent) == 1

    asyncio.run(go())
    assert logged[0][0] == "brain.handoff_resumed"


def test_handoff_retry_is_bounded(monkeypatch):
    svc, _, sent = service(monkeypatch)

    async def go():
        for _ in range(5):
            await svc._resume_empty_handoff(0)

    asyncio.run(go())
    assert sent == ["response.create", "response.create"]


def test_delegated_reply_and_failure_are_logged(monkeypatch):
    svc, logged, _ = service(monkeypatch)

    async def no_handle(self, evt):
        pass

    monkeypatch.setattr(MeteredLive.__mro__[1], "_handle_evt_response", no_handle)

    async def emit(kind, **event):
        await svc._handle_evt_response(
            SimpleNamespace(inner_type=kind, delegation_id="delegation-1", event=event)
        )

    async def go():
        await emit("response.created")
        assert svc._backend_busy
        await emit(
            "response.output_item.done",
            item={
                "type": "message",
                "content": [{"type": "output_text", "text": "What is your email?"}],
            },
        )
        await emit("response.failed", response={"error": {"message": "upstream failed"}})
        assert not svc._backend_busy

    asyncio.run(go())
    assert logged[0] == (
        "brain.reply",
        {"delegation_id": "delegation-1", "text": "What is your email?"},
    )
    assert logged[1][1]["error"]["message"] == "upstream failed"
