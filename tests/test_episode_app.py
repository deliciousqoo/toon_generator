"""HTTP boundary checks use isolated PNGs and a mock role provider, never inference."""
import hashlib
import io
import json
import zipfile

from fastapi.testclient import TestClient
from PIL import Image

from backend.app import create_app
from backend.episode_workers import FixtureEpisodeProvider


class MockSubscriptionRoles(FixtureEpisodeProvider):
    # These are HTTP contract tests, not evidence of real creative acceptance.
    name = "chatgpt_subscription"
    fixture = False

    def __init__(self):
        self.calls = []

    def execution_identity(self):
        return "isolated-test-account-model"

    def _record(self, role, context):
        self.calls.append((role, context))

    def intake(self, context):
        self._record("intake", context)
        return super().intake(context)

    def story(self, context):
        self._record("story", context)
        return super().story(context)

    def storyboard(self, context):
        self._record("storyboard", context)
        return super().storyboard(context)

    def evaluate(self, context):
        self._record("evaluator", context)
        return super().evaluate(context)


def png():
    output = io.BytesIO()
    Image.new("RGB", (32, 32), "green").save(output, format="PNG")
    return output.getvalue()


def make_character(client, headers, *, approve=True):
    project = client.post("/api/studio/character-projects", headers=headers, json={"synthetic_confirmed": True}).json()
    pid = project["id"]
    path = f"/api/studio/projects/{pid}/character"
    state = client.post(path + "/turns", headers=headers, json={"request_id": "direction", "expected_revision": 0,
        "synthetic_confirmed": True, "message": "가상 캐릭터 검증", "field_updates": {
            "appearance": "둥근 몸과 잎사귀", "personality": "실수해도 다시 시도", "desired_feeling": "친근함"}}).json()
    state = client.post(path + "/confirm", headers=headers, json={"request_id": "direction-confirm",
        "expected_revision": state["revision"], "expected_version": state["brief"]["version"]}).json()
    if not approve:
        return pid, state

    def request(rid, **extra):
        return {"request_id": rid, "expected_revision": state["revision"],
                "expected_direction_version": state["brief"]["version"], **extra}

    state = client.post(path + "/visual/jobs", headers=headers, json=request("candidate", kind="candidate")).json()
    job = state["visuals"]["jobs"][-1]
    state = client.post(path + f"/visual/jobs/{job['id']}/image", headers=headers,
        data={"request": json.dumps(request("candidate-import", provenance={"source": "user_upload"}))},
        files={"file": ("../ignored.png", png(), "image/png")}).json()
    candidate = state["visuals"]["candidates"][-1]
    ref = {"candidate_id": candidate["candidate_id"], "candidate_version": candidate["version"]}
    state = client.post(path + "/visual/select", headers=headers, json=request("select", **ref)).json()
    state = client.post(path + "/visual/coverage", headers=headers,
        json=request("coverage", **ref, components=[{"id": "front", "label": "정면"}])).json()
    scope = {**ref, "expected_coverage_version": state["visuals"]["coverage_version"]}
    state = client.post(path + "/visual/components/front/attach", headers=headers,
        json=request("front", **scope, asset_id=candidate["asset_id"])).json()
    state = client.post(path + "/visual/sheet/build", headers=headers, json=request("build", **scope)).json()
    state = client.post(path + "/visual/sheet/confirm", headers=headers,
        json=request("sheet-confirm", expected_sheet_version=state["visuals"]["current_sheet_version"])).json()
    assert state["sheet_approved"]
    return pid, state


def test_episode_http_pins_character_preserves_scoped_edits_imports_and_exports(tmp_path):
    app = create_app(tmp_path, character_fixture=True)
    provider = MockSubscriptionRoles()
    app.state.episode_studio.provider = provider
    with TestClient(app, base_url="http://127.0.0.1:8765", client=("127.0.0.1", 50000)) as client:
        headers = {"x-csrf-token": client.get("/api/bootstrap").json()["csrf_token"]}
        pid, character = make_character(client, headers)
        base = f"/api/studio/projects/{pid}/episodes"
        create = {"request_id": "episode-create", "expected_direction_version": character["brief"]["version"],
                  "expected_sheet_version": character["visuals"]["approved_sheet_version"]}
        assert client.post(base, json=create).status_code == 403
        response = client.post(base, headers=headers, json=create)
        assert response.status_code == 201, response.text
        state = response.json()
        path = base + "/" + state["id"]
        snapshot = state["character_snapshot"]
        assert snapshot["direction"] == character["brief"] and snapshot["sheet"] == character["visuals"]["sheets"][-1]
        assert client.post(base, headers=headers, json=create).json()["id"] == state["id"]

        def post(suffix, rid, **extra):
            nonlocal state
            response = client.post(path + suffix, headers=headers,
                json={"request_id": rid, "expected_revision": state["revision"], **extra})
            assert response.status_code == 200, response.text
            state = response.json()
            return state

        post("/turns", "intent", stage="intent", message="씨앗을 돌보다 실수하고 다시 시도하는 가상 이야기")
        post("/turns", "story", stage="story", message="이야기 초안을 만들어 주세요.")
        story = state["story"]
        assert state["confirmed_story_version"] is None
        post("/decisions", "story-confirm", action="confirm_story", expected_version=story["version"])
        assert state["storyboard"] is None
        post("/format", "format-change", expected_version=state["format"]["version"], cut_count=2, layout="vertical_grid")
        post("/decisions", "format-confirm", action="confirm_format", expected_version=state["format"]["version"])
        post("/turns", "board", stage="storyboard", message="확인한 구성으로 컷을 만들어 주세요.")
        before = state["storyboard"]["panels"]
        post("/turns", "dialogue-edit", stage="storyboard", expected_version=state["storyboard"]["version"],
             message="다시 천천히 해 볼게.", target_ids=[before[0]["id"]], edit_fields=["dialogue"])
        after = state["storyboard"]["panels"]
        assert after[1:] == before[1:]
        assert {k: v for k, v in after[0].items() if k != "dialogue"} == {k: v for k, v in before[0].items() if k != "dialogue"}
        assert after[0]["dialogue"] == "다시 천천히 해 볼게."
        assert client.get(path + "/export").status_code == 409
        rejected = client.post(path + "/decisions", headers=headers, json={"request_id": "no-rough-confirm",
            "expected_revision": state["revision"], "action": "confirm_board", "expected_version": state["storyboard"]["version"]})
        assert rejected.status_code == 409
        for index, panel in enumerate(after):
            post("/rough/jobs", f"rough-{index}", expected_board_version=state["storyboard"]["version"], panel_id=panel["id"])
            job = state["rough_jobs"][-1]
            metadata = {"request_id": f"rough-import-{index}", "expected_revision": state["revision"],
                "expected_board_version": state["storyboard"]["version"], "provenance": {"source": "user_upload"}}
            response = client.post(path + f"/rough/jobs/{job['id']}/image", headers=headers,
                data={"request": json.dumps(metadata)}, files={"file": ("../ignored.png", png(), "image/png")})
            assert response.status_code == 200, response.text
            state = response.json()
        post("/decisions", "board-confirm", action="confirm_board", expected_version=state["storyboard"]["version"])
        assert state["usable_storyboard"] and not state["generation_ready"]
        assert state["character_snapshot"] == snapshot
        for _, context in provider.calls:
            assert context["snapshot_fingerprint"] == snapshot["fingerprint"]
            assert len(context["_image_inputs"]) == 1
        response = client.get(path + "/export")
        assert response.status_code == 200 and response.headers["content-type"] == "application/zip"
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            assert archive.testzip() is None
            assert "manifest.json" in archive.namelist()
        assert client.get(path).json()["approved_board_version"] == state["storyboard"]["version"]
        for asset in state["rough_assets"]:
            response = client.get(asset["url"])
            assert response.status_code == 200
            assert hashlib.sha256(response.content).hexdigest() == asset["sha256"]


def test_episode_http_requires_current_approval_and_preserves_readable_old_results(tmp_path):
    app = create_app(tmp_path, character_fixture=True)
    app.state.episode_studio.provider = MockSubscriptionRoles()
    with TestClient(app, base_url="http://127.0.0.1:8765", client=("127.0.0.1", 50000)) as client:
        headers = {"x-csrf-token": client.get("/api/bootstrap").json()["csrf_token"]}
        pid, character = make_character(client, headers, approve=False)
        base = f"/api/studio/projects/{pid}/episodes"
        assert client.post(base, headers=headers, json={"request_id": "blocked-start",
            "expected_direction_version": character["brief"]["version"], "expected_sheet_version": "1.0.1"}).status_code == 409
        pid, character = make_character(client, headers)
        base = f"/api/studio/projects/{pid}/episodes"
        state = client.post(base, headers=headers, json={"request_id": "start",
            "expected_direction_version": character["brief"]["version"],
            "expected_sheet_version": character["visuals"]["approved_sheet_version"]}).json()
        path = base + "/" + state["id"]
        assert client.get(f"/api/studio/projects/project-other/episodes/{state['id']}").status_code == 404
        response = client.post(f"/api/studio/projects/{pid}/character/visual/sheet/reopen", headers=headers,
            json={"request_id": "reopen", "expected_revision": character["revision"],
                  "expected_direction_version": character["brief"]["version"],
                  "expected_sheet_version": character["visuals"]["approved_sheet_version"]})
        assert response.status_code == 200
        restored = client.get(path)
        assert restored.status_code == 200 and restored.json()["mutation_blocked"]
        assert restored.json()["character_snapshot"] == state["character_snapshot"]
        assert client.post(path + "/turns", headers=headers, json={"request_id": "stale-basis",
            "expected_revision": state["revision"], "stage": "intent", "message": "바뀐 시트를 몰래 쓰면 안 됨"}).status_code == 409
