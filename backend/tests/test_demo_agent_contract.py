import pytest
from app.demo import settings as store
from app.demo.app import register_demo_routes
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "SETTINGS_PATH", tmp_path / "demo" / "voice-settings.json")
    app = FastAPI()
    register_demo_routes(app)
    with TestClient(app) as client:
        yield client


SAVED = {"voice": "spruce", "preset": "serena", "opening_language": "es", "guidance": "Use plain language."}


@pytest.mark.parametrize("invalid", [
    {**SAVED, "voice": "alloy"},
    {**SAVED, "guidance": "x" * 1201},
    {**SAVED, "guidance": 42},
    {**SAVED, "temperature": 0.8},
])
def test_invalid_save_preserves_last_settings(client, invalid):
    assert client.put("/api/demo/settings", json=SAVED).status_code == 200
    rejected = client.put("/api/demo/settings", json=invalid)
    assert rejected.status_code == 422
    assert rejected.headers["cache-control"] == "no-store"
    assert client.get("/api/demo/settings").json()["settings"] == SAVED


def test_failed_atomic_replace_keeps_saved_settings(client, monkeypatch):
    assert client.put("/api/demo/settings", json=SAVED).status_code == 200

    def disk_failure(source, destination):
        raise OSError("Storage unavailable")

    with monkeypatch.context() as patch:
        patch.setattr(store.os, "replace", disk_failure)
        failed = client.put("/api/demo/settings", json={**SAVED, "voice": "juniper"})
    assert failed.status_code == 503
    assert client.get("/api/demo/settings").json()["settings"] == SAVED
    assert list(store.SETTINGS_PATH.parent.iterdir()) == [store.SETTINGS_PATH]


def test_corrupt_settings_are_not_silently_reset(client):
    assert client.put("/api/demo/settings", json=SAVED).status_code == 200
    store.SETTINGS_PATH.write_text('{"voice":', encoding="utf-8")
    response = client.get("/api/demo/settings")
    assert response.status_code == 503
    assert response.headers["cache-control"] == "no-store"


def test_saved_changes_do_not_mutate_an_existing_call_snapshot(client):
    assert client.put("/api/demo/settings", json=SAVED).status_code == 200
    snapshot = store.load_settings()
    changed = {**SAVED, "voice": "juniper", "preset": "clara", "opening_language": "en"}
    assert client.put("/api/demo/settings", json=changed).status_code == 200
    assert snapshot.model_dump() == SAVED
    assert store.load_settings().model_dump() == changed


def test_cross_origin_browser_save_is_rejected_and_proxy_origin_is_accepted(client):
    assert client.put("/api/demo/settings", json=SAVED).status_code == 200
    changed = {**SAVED, "voice": "juniper"}
    rejected = client.put(
        "/api/demo/settings", json=changed,
        headers={"Origin": "https://other.example", "Sec-Fetch-Site": "cross-site"},
    )
    assert rejected.status_code == 403
    assert client.get("/api/demo/settings").json()["settings"] == SAVED
    accepted = client.put(
        "/api/demo/settings", json=changed,
        headers={
            "Origin": "https://studio.example", "Sec-Fetch-Site": "same-origin",
            "X-Forwarded-Host": "studio.example", "X-Forwarded-Proto": "https",
        },
    )
    assert accepted.status_code == 200
    assert client.get("/api/demo/settings").json()["settings"] == changed
