"""Real local HTTP boundary for character image waiting/import/review/export."""
import io
import json
import zipfile

from fastapi.testclient import TestClient
from PIL import Image

from backend.app import create_app


def png():
    output = io.BytesIO()
    Image.new("RGB", (20, 20), "green").save(output, format="PNG")
    return output.getvalue()


def common(state, rid, **extra):
    return {"request_id": rid, "expected_revision": state["revision"], "expected_direction_version": state["brief"]["version"], **extra}


def test_http_image_import_csrf_scope_review_export_and_real_story_gate(tmp_path):
    app = create_app(tmp_path, character_fixture=True)
    with TestClient(app, base_url="http://127.0.0.1:8765", client=("127.0.0.1", 50000)) as client:
        headers = {"x-csrf-token": client.get("/api/bootstrap").json()["csrf_token"]}
        project = client.post("/api/studio/character-projects", json={"synthetic_confirmed": True}, headers=headers).json()
        pid = project["id"]
        path = f"/api/studio/projects/{pid}/character"
        state = client.post(path + "/turns", headers=headers, json={"request_id": "direction", "expected_revision": 0,
            "synthetic_confirmed": True, "message": "가상 캐릭터 검증", "field_updates": {"appearance": "둥근 외형", "personality": "호기심", "desired_feeling": "친근함"}}).json()
        state = client.post(path + "/confirm", headers=headers, json={"request_id": "confirm-direction", "expected_revision": state["revision"], "expected_version": state["brief"]["version"]}).json()
        state = client.post(path + "/visual/jobs", headers=headers, json=common(state, "job", kind="candidate")).json()
        job = state["visuals"]["jobs"][-1]
        upload = common(state, "upload", provenance={"source": "codex_imagegen", "prompt": "The exact known prompt", "model": None})
        files = {"file": ("../ignored-name.png", png(), "image/png")}
        assert client.post(path + f"/visual/jobs/{job['id']}/image", data={"request": json.dumps(upload)}, files=files).status_code == 403
        response = client.post(path + f"/visual/jobs/{job['id']}/image", headers=headers, data={"request": json.dumps(upload)}, files=files)
        assert response.status_code == 200, response.text
        state = response.json()
        assert state["visuals"]["assets"][0]["provenance"]["prompt"] == "The exact known prompt"
        asset = state["visuals"]["assets"][0]
        response = client.get(asset["url"])
        assert response.status_code == 200 and response.headers["content-type"] == "image/png"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.content.startswith(b"\x89PNG")
        assert not (tmp_path / "ignored-name.png").exists()
        candidate = state["visuals"]["candidates"][-1]
        ref = {"candidate_id": candidate["candidate_id"], "candidate_version": candidate["version"]}
        state = client.post(path + "/visual/select", headers=headers, json=common(state, "select", **ref)).json()
        state = client.post(path + "/visual/coverage", headers=headers, json=common(state, "coverage", **ref, components=[{"id": "front", "label": "정면"}])).json()
        scope = {**ref, "expected_coverage_version": state["visuals"]["coverage_version"]}
        state = client.post(path + "/visual/components/front/attach", headers=headers, json=common(state, "attach", **scope, asset_id=asset["id"])).json()
        state = client.post(path + "/visual/sheet/build", headers=headers, json=common(state, "build", **scope)).json()
        assert client.get(path + "/visual/sheet/export").status_code == 409
        sheet = state["visuals"]["current_sheet_version"]
        state = client.post(path + "/visual/sheet/confirm", headers=headers, json=common(state, "approve", expected_sheet_version=sheet)).json()
        assert state["sheet_approved"] and client.get(path).json() == state
        projection = client.get(f"/api/studio/projects/{pid}").json()["project"]["character_package"]
        assert projection["sheet_status"] == "approved" and projection["approval_status"] == "approved"
        assert projection["source_versions"][-1]["version"] == sheet
        response = client.get(path + "/visual/sheet/export")
        assert response.status_code == 200 and response.headers["content-type"] == "application/zip"
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            assert json.loads(archive.read("sheet.json"))["sheet"]["version"] == sheet
        response = client.post(f"/api/studio/projects/{pid}/runs", headers=headers, json={"idea": "실제 캐릭터의 이야기는 아직 연결하지 않음"})
        assert response.status_code == 409 and "다음 단계" in response.json()["detail"]
        assert app.state.workflow_studio.list_runs(pid) == []
        corrupted_path = app.state.character_studio._visual_asset_path(pid, asset)
        corrupted_path.write_bytes(b"corrupt")
        assert client.get(path).status_code == 409
        assert client.get(asset["url"]).status_code == 409
        assert client.get(path + "/visual/sheet/export").status_code == 409
        assert client.post(f"/api/studio/projects/{pid}/runs", headers=headers, json={"idea": "변조된 이미지"}).status_code == 409


def test_http_rejects_bad_upload_metadata_and_cross_project_candidate(tmp_path):
    app = create_app(tmp_path, character_fixture=True)
    with TestClient(app, base_url="http://127.0.0.1:8765", client=("127.0.0.1", 50000)) as client:
        headers = {"x-csrf-token": client.get("/api/bootstrap").json()["csrf_token"]}
        project = client.post("/api/studio/character-projects", json={"synthetic_confirmed": True}, headers=headers).json()
        path = f"/api/studio/projects/{project['id']}/character"
        response = client.post(path + "/visual/jobs/visual-job-" + "a" * 32 + "/image", headers=headers,
            data={"request": "{invalid"}, files={"file": ("test.png", png(), "image/png")})
        assert response.status_code == 422 and "invalid" not in response.text
        response = client.post(path + "/visual/jobs", headers=headers, json={"request_id": "fake", "expected_revision": 0,
            "expected_direction_version": "1.0.1", "kind": "candidate", "sheet_approved": True})
        assert response.status_code == 422
