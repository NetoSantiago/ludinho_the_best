import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from fastapi.testclient import TestClient
import server


@pytest.fixture
def client():
    with TestClient(server.app) as test_client:
        yield test_client


@pytest.fixture
def message_spy(monkeypatch):
    messages = []

    async def fake_send_message(to: str, text: str):
        messages.append({"to": to, "text": text})
        return {"ok": True}

    monkeypatch.setattr(server, "send_message", fake_send_message)
    return messages


@pytest.fixture
def state_store(monkeypatch):
    store = {}

    def fake_get_state(phone: str):
        return store.get(phone)

    def fake_set_state(phone: str, state: str, data=None):
        store[phone] = {"state": state, "data": data or {}}

    def fake_clear_state(phone: str):
        store.pop(phone, None)

    monkeypatch.setattr(server, "get_state", fake_get_state)
    monkeypatch.setattr(server, "set_state", fake_set_state)
    monkeypatch.setattr(server, "clear_state", fake_clear_state)
    return store



@pytest.fixture
def existing_client(monkeypatch):
    monkeypatch.setattr(server, "supa_select_one", lambda *args, **kwargs: {"id": "cli-1"})
    return {"id": "cli-1"}
