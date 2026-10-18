"""Exact-version image import, scoped changes and human sheet review contracts."""
import copy
import io
import json
import os
import zipfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pytest
from PIL import Image
from pydantic import ValidationError

from backend.character_contracts import CharacterState
from backend.character_service import CharacterConflict, CharacterService


def image_bytes(color="green", format="PNG"):
    image = Image.new("RGB", (24, 32), color)
    output = io.BytesIO()
    image.save(output, format=format)
    return output.getvalue()


def request(state, rid, **extra):
    return {"request_id": rid, "expected_revision": state["revision"],
            "expected_direction_version": state["brief"]["version"], **extra}


def ready(service, pid="project-visual"):
    state = service.ensure_project(pid)
    state = service.submit_turn(pid, {"request_id": "direction", "expected_revision": state["revision"],
        "message": "개발 검증을 위한 가상 캐릭터", "synthetic_confirmed": True,
        "field_updates": {"appearance": "둥근 몸과 잎사귀 하나", "personality": "호기심이 많음", "desired_feeling": "친근함"}})
    return service.confirm_direction(pid, {"request_id": "direction-confirm", "expected_revision": state["revision"],
                                          "expected_version": state["brief"]["version"]})


def job(service, state, rid="job-1", kind="candidate", **extra):
    return service.create_visual_job(state["project_id"], request(state, rid, kind=kind, **extra))


def upload(service, state, rid="upload-1", color="green", fixture=False, job_id=None):
    return service.upload_visual_image(state["project_id"], job_id or state["visuals"]["jobs"][-1]["id"],
        request(state, rid, provenance={"source": "user_upload", "model": None, "prompt": "Known test input", "fixture": fixture}), image_bytes(color))


def candidate(service, state, prefix="first", **kwargs):
    return upload(service, job(service, state, prefix + "-job"), prefix + "-upload", **kwargs)


def selected_request(state, rid, **extra):
    selected = state["visuals"]["selected_candidate"]
    return request(state, rid, candidate_id=selected["candidate_id"], candidate_version=selected["version"], **extra)


def select(service, state, index=-1, rid="select"):
    picked = state["visuals"]["candidates"][index]
    return service.select_visual_candidate(state["project_id"], request(state, rid, candidate_id=picked["candidate_id"], candidate_version=picked["version"]))


def coverage(service, state, parts=None, rid="coverage"):
    return service.save_visual_coverage(state["project_id"], selected_request(state, rid, components=parts or [{"id": "front", "label": "정면"}]))


def attach(service, state, component_id="front", rid="attach", asset_id=None):
    return service.attach_visual_component(state["project_id"], component_id, selected_request(state, rid,
        expected_coverage_version=state["visuals"]["coverage_version"], asset_id=asset_id or state["visuals"]["candidates"][-1]["asset_id"]))


def build(service, state, rid="build"):
    return service.build_visual_sheet(state["project_id"], selected_request(state, rid, expected_coverage_version=state["visuals"]["coverage_version"]))


def decide(service, state, rid="approve", kind="confirm"):
    return service.visual_sheet_decision(state["project_id"], request(state, rid, expected_sheet_version=state["visuals"]["current_sheet_version"]), kind)


@pytest.fixture
def service(tmp_path):
    engine = CharacterService(tmp_path)
    yield engine
    engine.close()


def complete(service, fixture=False):
    state = candidate(service, ready(service), fixture=fixture)
    state = select(service, state)
    state = coverage(service, state)
    state = attach(service, state)
    return build(service, state)


def test_external_waiting_jobs_restart_without_generation(tmp_path):
    engine = CharacterService(tmp_path)
    state = job(engine, ready(engine), instruction="두꺼운 외곽선의 시각 후보")
    assert state["visuals"]["jobs"][0]["status"] == "awaiting_image"
    assert "둥근 몸" in state["visuals"]["jobs"][0]["prompt"]
    assert state["visuals"]["jobs"][0]["source_asset_ids"] == []
    assert not state["visuals"]["assets"] and not state["visual_ready"]
    engine.close()
    restored = CharacterService(tmp_path)
    try:
        assert restored.get_state("project-visual") == state
        assert restored.db.execute("SELECT count(*) FROM character_provider_budget").fetchone()[0] == 0
    finally:
        restored.close()


def test_human_selection_coverage_exact_sheet_and_restart(tmp_path):
    engine = CharacterService(tmp_path)
    state = complete(engine)
    assert state["stage"] == "sheet" and not state["sheet_approved"]
    assert state["visuals"]["coverage"] == [{"id": "front", "label": "정면"}]
    original_sheet = copy.deepcopy(state["visuals"]["sheets"][0])
    approved = decide(engine, state)
    assert approved["stage"] == "complete" and approved["sheet_approved"]
    assert engine.approved_visual_package("project-visual")["sheet"] == original_sheet
    assert approved["visuals"]["sheets"][0] == original_sheet
    assert approved["visuals"]["decisions"][-1]["actor"] == "human"
    engine.close()
    engine = CharacterService(tmp_path)
    try:
        assert engine.get_state("project-visual") == approved
        reopened = decide(engine, approved, rid="reopen-sheet", kind="reopen")
        assert not reopened["sheet_approved"] and reopened["visuals"]["sheets"] == approved["visuals"]["sheets"]
        assert reopened["visuals"]["components"] == approved["visuals"]["components"]
    finally:
        engine.close()


def test_upload_idempotency_binds_binary_and_provenance(service):
    state = job(service, ready(service))
    job_id = state["visuals"]["jobs"][0]["id"]
    payload = request(state, "upload", provenance={"source": "user_upload"})
    data = image_bytes()
    result = service.upload_visual_image("project-visual", job_id, payload, data)
    assert service.upload_visual_image("project-visual", job_id, payload, data) == result
    assert result["visuals"]["assets"][0]["provenance"]["unknowns"] == ["model", "workflow", "prompt", "seed"]
    with pytest.raises(CharacterConflict):
        service.upload_visual_image("project-visual", job_id, payload, image_bytes("blue"))
    with pytest.raises(CharacterConflict):
        service.upload_visual_image("project-visual", job_id, {**payload, "provenance": {"source": "codex_imagegen"}}, data)
    assert len(service.get_state("project-visual")["visuals"]["candidates"]) == 1


def test_candidate_revision_preserves_history_and_invalidates_selected_sheet(service):
    state = decide(service, complete(service))
    previous = copy.deepcopy(state)
    picked = state["visuals"]["selected_candidate"]
    state = job(service, state, "revise", "candidate_revision", instruction="잎사귀만 작게", candidate_id=picked["candidate_id"], candidate_version=picked["version"])
    assert not state["sheet_approved"]
    assert state["visuals"]["jobs"][-1]["source_asset_ids"] == [previous["visuals"]["candidates"][0]["asset_id"]]
    with pytest.raises(CharacterConflict):
        build(service, state, "revision-pending-build")
    with pytest.raises(CharacterConflict):
        decide(service, state, "revision-pending-approval")
    with pytest.raises(CharacterConflict):
        service.approved_visual_package("project-visual")
    state = upload(service, state, "revised-image", color="blue")
    assert state["stage"] == "candidates" and not state["visual_ready"]
    assert state["visuals"]["selected_candidate"] is None
    assert state["visuals"]["candidates"][-1]["version"] == "1.0.2"
    assert state["visuals"]["candidates"][-1]["parent_version"] == "1.0.1"
    assert state["visuals"]["sheets"] == previous["visuals"]["sheets"]
    assert state["visuals"]["candidates"][0] == previous["visuals"]["candidates"][0]
    assert state["brief"] == previous["brief"]


def test_partial_component_revision_preserves_other_images_and_exact_sheet(service):
    state = select(service, candidate(service, ready(service)))
    state = coverage(service, state, [{"id": "front", "label": "정면"}, {"id": "smile", "label": "웃음"}])
    state = attach(service, state)
    state = attach(service, state, "smile", "attach-smile")
    state = decide(service, build(service, state))
    original = copy.deepcopy(state)
    state = job(service, state, "smile-job", "sheet_component", instruction="입 모양만 더 크게 웃음", component_id="smile",
                candidate_id=state["visuals"]["selected_candidate"]["candidate_id"], candidate_version=state["visuals"]["selected_candidate"]["version"],
                expected_coverage_version=state["visuals"]["coverage_version"])
    assert not state["sheet_approved"]
    with pytest.raises(CharacterConflict):
        build(service, state, "pending-build")
    state = upload(service, state, "smile-image", color="yellow")
    assert state["visuals"]["components"]["front"] == original["visuals"]["components"]["front"]
    assert state["visuals"]["components"]["smile"] != original["visuals"]["components"]["smile"]
    assert state["visuals"]["current_sheet_version"] is None
    state = build(service, state, "build-revision")
    assert state["visuals"]["current_sheet_version"] == "1.0.2"
    assert state["visuals"]["sheets"][0] == original["visuals"]["sheets"][0]
    state = decide(service, state, "approve-revision")
    assert state["sheet_approved"]


def test_direction_reopen_clears_active_derivatives_and_cancels_jobs(service):
    state = decide(service, complete(service))
    state = job(service, state, "next-candidate")
    before = copy.deepcopy(state)
    state = service.reopen_direction("project-visual", {"request_id": "reopen-direction", "expected_revision": state["revision"], "expected_version": state["brief"]["version"]})
    assert state["stage"] == "direction" and not state["visual_ready"] and not state["sheet_approved"]
    assert state["visuals"]["selected_candidate"] is None and state["visuals"]["components"] == {}
    assert state["visuals"]["sheets"] == before["visuals"]["sheets"]
    assert state["visuals"]["assets"] == before["visuals"]["assets"]
    assert state["visuals"]["jobs"][-1]["status"] == "cancelled"
    with pytest.raises(CharacterConflict):
        upload(service, state, "late-image")


@pytest.mark.parametrize("data", [b"<svg><script>alert(1)</script></svg>", b"https://example.com/image.png", b"C:\\secret.png", b"not an image", b""])
def test_upload_decodes_bytes_and_rejects_paths_urls_svg(service, data):
    state = job(service, ready(service))
    with pytest.raises(CharacterConflict):
        service.upload_visual_image("project-visual", state["visuals"]["jobs"][-1]["id"], request(state, "invalid", provenance={"source": "user_upload"}), data)
    assert service.get_state("project-visual") == state


def test_jpeg_normalization_and_asset_ownership(service):
    state = job(service, ready(service))
    state = service.upload_visual_image("project-visual", state["visuals"]["jobs"][-1]["id"], request(state, "jpeg", provenance={"source": "user_upload"}), image_bytes(format="JPEG"))
    asset = state["visuals"]["assets"][0]
    assert service.visual_asset_bytes("project-visual", asset["id"]).startswith(b"\x89PNG\r\n\x1a\n")
    assert asset["media_type"] == "image/png" and (asset["width"], asset["height"]) == (24, 32)
    ready(service, "project-other")
    with pytest.raises(CharacterConflict):
        service.visual_asset_bytes("project-other", asset["id"])


@pytest.mark.parametrize("corrupt", [True, False])
def test_missing_or_corrupt_active_asset_blocks_read_confirmation_and_handoff(service, corrupt):
    state = complete(service)
    asset = state["visuals"]["assets"][0]
    path = service._visual_asset_path("project-visual", asset)
    if corrupt:
        path.write_bytes(b"bad image")
    else:
        path.unlink()
    with pytest.raises(CharacterConflict):
        service.get_state("project-visual")
    with pytest.raises(CharacterConflict):
        decide(service, state)
    with pytest.raises(CharacterConflict):
        service.approved_visual_package("project-visual")


def test_fixture_image_never_passes_sheet_approval_or_launders_by_revision(service):
    state = complete(service, fixture=True)
    with pytest.raises(CharacterConflict):
        decide(service, state)
    picked = state["visuals"]["selected_candidate"]
    state = job(service, state, "revision", "candidate_revision", instruction="색만 수정", candidate_id=picked["candidate_id"], candidate_version=picked["version"])
    state = upload(service, state, "revision-upload", fixture=False)
    assert state["visuals"]["assets"][-1]["provenance"]["fixture"] is True


def test_stale_direction_selection_coverage_and_sheet_versions_fail(service):
    state = complete(service)
    with pytest.raises(CharacterConflict):
        service.visual_sheet_decision("project-visual", request(state, "stale-sheet", expected_sheet_version="1.0.999"), "confirm")
    with pytest.raises(CharacterConflict):
        service.select_visual_candidate("project-visual", request(state, "bad-direction", expected_direction_version="1.0.999", candidate_id=state["visuals"]["selected_candidate"]["candidate_id"], candidate_version="1.0.1"))
    with pytest.raises(CharacterConflict):
        service.build_visual_sheet("project-visual", selected_request(state, "stale-scope", expected_coverage_version=999))
    with pytest.raises(CharacterConflict):
        service.save_visual_coverage("project-visual", selected_request(state, "duplicate", components=[{"id": "same", "label": "정면"}, {"id": "same", "label": "뒷면"}]))


def test_concurrent_completions_have_one_winner(service):
    state = job(service, ready(service))
    target = state["visuals"]["jobs"][-1]["id"]

    def finish(index):
        try:
            service.upload_visual_image("project-visual", target, request(state, f"race-{index}", provenance={"source": "user_upload"}), image_bytes())
            return "completed"
        except CharacterConflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(finish, range(2))) == ["completed", "conflict"]
    assert len(service.get_state("project-visual")["visuals"]["assets"]) == 1


def test_additive_old_direction_state_and_invalid_visual_lineage(service):
    state = ready(service)
    old = {key: value for key, value in state.items() if key != "visuals"}
    assert CharacterState.model_validate(old).visuals.assets == []
    state = candidate(service, state)
    broken = copy.deepcopy(state)
    broken["visuals"]["candidates"][0]["version"] = "1.0.2"
    with pytest.raises(ValidationError):
        CharacterState.model_validate(broken)


def test_approved_bundle_is_read_only_exact_and_checksum_verified(service):
    state = complete(service)
    with pytest.raises(CharacterConflict):
        service.export_visual_sheet("project-visual")
    state = decide(service, state)
    data = service.export_visual_sheet("project-visual")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        assert {"character-bible.md", "sheet.json", "manifest.json"}.issubset(archive.namelist())
        manifest = json.loads(archive.read("manifest.json"))
        sheet = json.loads(archive.read("sheet.json"))
        assert sheet["sheet"] == state["visuals"]["sheets"][0]
        assert manifest["direction_version"] == state["brief"]["version"]
        for asset in state["visuals"]["assets"]:
            assert archive.read(manifest["files"][asset["id"]]["path"]) == service.visual_asset_bytes("project-visual", asset["id"])
    assert service.get_state("project-visual") == state
    broken = copy.deepcopy(state)
    broken["visuals"]["assets"][0]["project_id"] = "project-other"
    with pytest.raises(ValidationError):
        CharacterState.model_validate(broken)


def test_old_component_job_asset_cannot_be_attached_after_coverage_label_changes(service):
    state = coverage(service, select(service, candidate(service, ready(service))))
    picked = state["visuals"]["selected_candidate"]
    state = job(service, state, "component-job", "sheet_component", instruction="정면 모습 제작", component_id="front",
                candidate_id=picked["candidate_id"], candidate_version=picked["version"], expected_coverage_version=state["visuals"]["coverage_version"])
    state = upload(service, state, "component-upload", color="blue")
    old_asset = state["visuals"]["components"]["front"]
    state = coverage(service, state, [{"id": "front", "label": "뒤에서 본 모습"}], "changed-label")
    assert state["visuals"]["components"] == {}
    with pytest.raises(CharacterConflict):
        attach(service, state, asset_id=old_asset, rid="reuse-wrong-scope")


def test_component_prompt_distinguishes_new_view_from_scoped_edit_source_roles(service):
    state = coverage(service, select(service, candidate(service, ready(service))))
    picked = state["visuals"]["selected_candidate"]
    state = job(service, state, "new-component", "sheet_component", instruction="정면 모습 제작", component_id="front",
                candidate_id=picked["candidate_id"], candidate_version=picked["version"], expected_coverage_version=state["visuals"]["coverage_version"])
    first = state["visuals"]["jobs"][-1]
    assert '"role":"identity_reference"' in first["prompt"]
    assert '"role":"edit_target"' not in first["prompt"]
    assert len(first["source_asset_ids"]) == 1
    state = upload(service, state, "new-component-upload", color="blue")
    original = state["visuals"]["components"]["front"]
    state = job(service, state, "edit-component", "sheet_component", instruction="잎사귀만 작게 수정", component_id="front",
                candidate_id=picked["candidate_id"], candidate_version=picked["version"], expected_coverage_version=state["visuals"]["coverage_version"])
    revision = state["visuals"]["jobs"][-1]
    assert revision["source_asset_ids"] == [first["source_asset_ids"][0], original]
    assert '"role":"identity_reference"' in revision["prompt"] and '"role":"edit_target"' in revision["prompt"]
    assert f'"asset_id":"{original}","image_index":2,"role":"edit_target"' in revision["prompt"]
    assert "Preserve the edit_target's pose" in revision["prompt"] and "change only the explicitly requested detail" in revision["prompt"]


def test_export_includes_selected_revision_source_closure_and_omits_unrelated_candidates(service):
    state = complete(service)
    picked = state["visuals"]["selected_candidate"]
    state = job(service, state, "revise-source", "candidate_revision", instruction="잎사귀만 작게", candidate_id=picked["candidate_id"], candidate_version=picked["version"])
    state = upload(service, state, "source-revised", color="blue")
    state = select(service, state, rid="select-revision")
    state = coverage(service, state, rid="coverage-revision")
    state = attach(service, state, rid="attach-revision")
    state = decide(service, build(service, state, "build-revision"), "approve-revision")
    selected_images = {asset["id"] for asset in state["visuals"]["assets"]}
    state = candidate(service, state, prefix="unrelated", color="yellow")
    with zipfile.ZipFile(io.BytesIO(service.export_visual_sheet("project-visual"))) as archive:
        exported = json.loads(archive.read("sheet.json"))
        assert {asset["id"] for asset in exported["assets"]} == selected_images
        assert exported["assets"][-1]["source_asset_ids"] == [exported["assets"][0]["id"]]
        assert {name for name in archive.namelist() if name.startswith("assets/")} == {f"assets/{aid}.png" for aid in selected_images}


def test_compact_image_layout_handles_long_project_ids_and_keeps_legacy_files_readable(service):
    pid = "project-" + "p" * 150
    state = candidate(service, ready(service, pid))
    asset = state["visuals"]["assets"][0]
    current = service._visual_asset_path(pid, asset)
    assert current.name == f"{asset['id']}.png"
    assert asset["sha256"] not in str(current)
    original = service.visual_asset_bytes(pid, asset["id"])
    if os.name == "nt":
        assert str(current).startswith("\\\\?\\")
        assert len(str(current)) > 260  # exercises I/O, not just path construction
    legacy = service.root.resolve() / "assets" / pid / asset["id"] / f"{asset['sha256']}.png"
    if os.name == "nt" and not str(legacy).startswith("\\\\?\\"):
        legacy = Path("\\\\?\\" + str(legacy))
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_bytes(original)
    current.unlink()
    assert service._visual_asset_path(pid, asset) == legacy
    assert service.visual_asset_bytes(pid, asset["id"]) == original
    assert service.get_state(pid) == state
