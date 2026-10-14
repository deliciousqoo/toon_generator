"""Exercise the new workspace through the real app boundary, with no model calls."""
import json

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.studio_contracts import studio_schema

BASE_URL = "http://127.0.0.1:8765"


def local_client(app):
    return TestClient(app, base_url=BASE_URL, client=("127.0.0.1", 50000))


def request(client, method, path, *, expected=200, data=None):
    token = client.get("/api/bootstrap").json()["csrf_token"]
    response = client.request(method, path, json=data, headers={"x-csrf-token": token})
    assert response.status_code == expected, response.text
    return response.json()


def project(client):
    return request(client, "POST", "/api/studio/projects", expected=201, data={
        "name": "합성 API 검증", "audience": "합성 독자", "series_direction": "합성 이야기 방향",
        "synthetic_confirmed": True,
    })


def settled(app, client, pid, rid):
    app.state.workflow_studio.wait(rid)
    return request(client, "GET", f"/api/studio/projects/{pid}/runs/{rid}")


def action(app, client, run, name, **extra):
    request(client, "POST", f"/api/studio/projects/{run['project_id']}/runs/{run['id']}/actions",
            expected=202, data={"action": name, "expected_revision": run["revision"], **extra})
    return settled(app, client, run["project_id"], run["id"])


def test_new_routes_inherit_local_origin_csrf_and_minimal_input(tmp_path, monkeypatch):
    monkeypatch.delenv("TOON_STUDIO_ENABLE_OLLAMA", raising=False)
    app = create_app(tmp_path)
    with local_client(app) as client:
        blocked = client.post("/api/studio/projects", json={})
        assert blocked.status_code == 403
        p = project(client)
        assert p["schema_version"] == "2.0.0"
        assert request(client, "GET", "/api/studio/projects")["projects"][0]["id"] == p["id"]
        # Studio v2 records must never leak into or mutate the legacy v1 API.
        assert request(client, "GET", "/api/projects") == []
        for source in p["fixture_versions"]:
            assert source["project_id"] == p["id"]
        foreign = client.get("/api/studio/projects", headers={"host": "example.invalid:8765"})
        assert foreign.status_code == 403
        data = {"name": "合成", "audience": "", "series_direction": "합성", "synthetic_confirmed": False}
        request(client, "POST", "/api/studio/projects", expected=422, data=data)
    assert app.state.workflow_studio._closed


def test_http_pause_restart_stale_review_and_technical_completion(tmp_path, monkeypatch):
    monkeypatch.delenv("TOON_STUDIO_ENABLE_OLLAMA", raising=False)
    app = create_app(tmp_path)
    with local_client(app) as client:
        p = project(client)
        started = request(client, "POST", f"/api/studio/projects/{p['id']}/runs", expected=202,
                          data={"idea": "합성 예시: 가상의 주인공이 작은 사건을 관찰한다.", "input_kind": "anecdote"})
        first = settled(app, client, p["id"], started["id"])
        assert first["pending_action"] == "approve_story"
        assert first["format_proposal"] is None
        saved_story = first["story"]

    restarted = create_app(tmp_path)
    with local_client(restarted) as client:
        restored = settled(restarted, client, p["id"], started["id"])
        assert restored["story"] == saved_story
        assert restored["pending_action"] == "approve_story"
        chosen = action(restarted, client, restored, "approve_story")
        assert chosen["pending_action"] == "approve_format"
        # A previously rendered confirmation cannot approve a later projection.
        request(client, "POST", f"/api/studio/projects/{p['id']}/runs/{started['id']}/actions", expected=409,
                data={"action": "approve_story", "expected_revision": restored["revision"]})
        board = action(restarted, client, chosen, "approve_format")
        assert board["pending_action"] == "approve_storyboard"
        assert board["storyboard"]["story_version"] == saved_story["version"]
        confirmed = action(restarted, client, board, "approve_storyboard")
        assert confirmed["status"] == "completed"
        assert confirmed["technical_review_complete"] is True
        assert confirmed["generation_ready"] is False
        assert confirmed["creative_quality_verified"] is False
        assert all(a["gate"] != "G2" for a in confirmed["approvals"])
        assert confirmed["approvals"][-1]["gate"] == "TECHNICAL_BOARD"
        other = project(client)
        request(client, "GET", f"/api/studio/projects/{other['id']}/runs/{started['id']}", expected=404)


def test_reject_requires_explicit_retry_and_preserves_story(tmp_path, monkeypatch):
    monkeypatch.delenv("TOON_STUDIO_ENABLE_OLLAMA", raising=False)
    app = create_app(tmp_path)
    with local_client(app) as client:
        p = project(client)
        started = request(client, "POST", f"/api/studio/projects/{p['id']}/runs", expected=202,
                          data={"idea": "합성 시작", "input_kind": "idea"})
        waiting = settled(app, client, p["id"], started["id"])
        stopped = action(app, client, waiting, "reject", feedback="다른 방향을 검토할 합성 반려")
        assert stopped["status"] == "stopped"
        assert stopped["story"] == waiting["story"]
        request(client, "POST", f"/api/studio/projects/{p['id']}/runs/{started['id']}/actions", expected=409,
                data={"action": "approve_story", "expected_revision": stopped["revision"]})
        resumed = action(app, client, stopped, "retry")
        assert resumed["pending_action"] == "approve_story"
        assert resumed["versions"]


def test_checked_in_v2_schema_matches_runtime_export():
    from pathlib import Path
    document = Path(__file__).resolve().parents[1] / "docs/contracts/studio-v2.schema.json"
    assert json.loads(document.read_text("utf-8")) == studio_schema()
