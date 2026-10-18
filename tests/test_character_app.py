"""Character-first endpoints inherit loopback, CSRF and exact-version controls."""
from fastapi.testclient import TestClient

from backend.app import create_app


def client_for(app):
    return TestClient(app, base_url="http://127.0.0.1:8765", client=("127.0.0.1", 50000))


def headers(client):
    return {"x-csrf-token": client.get("/api/bootstrap").json()["csrf_token"]}


def create(client):
    response = client.post("/api/studio/character-projects", json={"synthetic_confirmed": True}, headers=headers(client))
    assert response.status_code == 201, response.text
    return response.json()


def test_character_first_project_requires_sheet_and_scopes_requests(tmp_path, monkeypatch):
    monkeypatch.delenv("TOON_CHARACTER_ENABLE_OLLAMA", raising=False)
    with client_for(create_app(tmp_path, character_fixture=True)) as client:
        project = create(client)
        assert project["character_package"]["sheet_status"] == "missing"
        assert project["character_package"]["approval_status"] == "pending"
        assert not project["character_package"]["identity_invariants"]
        assert all(source["role"] != "character_fixture" for source in project["fixture_versions"])
        pid = project["id"]
        path = f"/api/studio/projects/{pid}/character"
        assert client.get(path).status_code == 200
        request = {"request_id": "turn-1", "expected_revision": 0, "message": "합성 캐릭터의 특징", "synthetic_confirmed": True}
        assert client.post(path + "/turns", json=request).status_code == 403
        assert client.post("/api/studio/projects/absent/character/turns", json=request, headers=headers(client)).status_code == 404
        assert client.post(path + "/turns", json={**request, "synthetic_confirmed": False}, headers=headers(client)).status_code == 422
        assert client.post(f"/api/studio/projects/{pid}/runs", json={"idea": "먼저 시작할 수 없는 합성 이야기"}, headers=headers(client)).status_code == 409


def test_character_dialogue_edit_confirm_reopen_and_restart(tmp_path, monkeypatch):
    monkeypatch.delenv("TOON_CHARACTER_ENABLE_OLLAMA", raising=False)
    app = create_app(tmp_path, character_fixture=True)
    with client_for(app) as client:
        project = create(client)
        pid = project["id"]
        path = f"/api/studio/projects/{pid}/character"
        request = {"request_id": "initial", "expected_revision": 0, "message": "합성 방향 입력", "synthetic_confirmed": True,
                   "field_updates": {"appearance": "합성 외형", "personality": "합성 성격", "desired_feeling": "합성 인상"}}
        response = client.post(path + "/turns", json=request, headers=headers(client))
        assert response.status_code == 200, response.text
        first = response.json()
        replay = client.post(path + "/turns", json=request, headers=headers(client))
        assert replay.json() == first
        assert first["can_confirm"] is True
        edit = {"request_id": "edit", "expected_revision": first["revision"], "message": "성격 항목 수정", "synthetic_confirmed": True,
                "field_updates": {"personality": "수정한 합성 성격"}}
        response = client.post(path + "/turns", json=edit, headers=headers(client))
        assert response.status_code == 200, response.text
        changed = response.json()
        assert changed["brief"]["appearance"] == first["brief"]["appearance"]
        assert changed["brief"]["personality"] == "수정한 합성 성격"
        stale = {"request_id": "stale", "expected_revision": first["revision"], "expected_version": first["brief"]["version"]}
        assert client.post(path + "/confirm", json=stale, headers=headers(client)).status_code == 409
        decision = {"request_id": "confirm", "expected_revision": changed["revision"], "expected_version": changed["brief"]["version"]}
        result = client.post(path + "/confirm", json=decision, headers=headers(client))
        assert result.status_code == 200, result.text
        confirmed = result.json()
        assert confirmed["direction_confirmed"] is True
        assert confirmed["sheet_approved"] is False
        assert client.post(f"/api/studio/projects/{pid}/runs", json={"idea": "시트 없는 합성 이야기"}, headers=headers(client)).status_code == 409

    with client_for(create_app(tmp_path, character_fixture=True)) as client:
        restored = client.get(path).json()
        assert restored == confirmed
        reopened = client.post(path + "/reopen", json={"request_id": "reopen", "expected_revision": restored["revision"],
                                                      "expected_version": restored["brief"]["version"]}, headers=headers(client))
        assert reopened.status_code == 200, reopened.text
        state = reopened.json()
        assert state["direction_confirmed"] is False
        assert state["brief"] == changed["brief"]
        assert state["versions"][0] == first["brief"]
