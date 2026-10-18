"""Character-pinned episode scope, durable operations, budgets and actual rough gates."""
import copy
import io
import json
import zipfile

import pytest
from PIL import Image

from backend.character_service import CharacterService
from backend.episode_service import EpisodeConflict, EpisodeService
from backend.episode_workers import FixtureEpisodeProvider


def png(color="green"):
    output = io.BytesIO()
    Image.new("RGB", (20, 24), color).save(output, "PNG")
    return output.getvalue()


def approved_character(chars, pid="project-episode"):
    s = chars.ensure_project(pid)
    s = chars.submit_turn(pid, {"request_id": "direction", "expected_revision": 0, "message": "가상 검증 캐릭터", "synthetic_confirmed": True,
        "field_updates": {"appearance": "둥근 몸과 잎사귀", "personality": "호기심", "desired_feeling": "친근함"}})
    s = chars.confirm_direction(pid, {"request_id": "direction-ok", "expected_revision": s["revision"], "expected_version": s["brief"]["version"]})
    def req(rid, **extra):
        return {"request_id": rid, "expected_revision": s["revision"], "expected_direction_version": s["brief"]["version"], **extra}
    s = chars.create_visual_job(pid, req("candidate", kind="candidate"))
    s = chars.upload_visual_image(pid, s["visuals"]["jobs"][-1]["id"], req("candidate-image", provenance={"source": "user_upload"}), png())
    picked = s["visuals"]["candidates"][-1]
    s = chars.select_visual_candidate(pid, req("select", candidate_id=picked["candidate_id"], candidate_version=picked["version"]))
    extra = {"candidate_id": picked["candidate_id"], "candidate_version": picked["version"]}
    s = chars.save_visual_coverage(pid, req("coverage", **extra, components=[{"id": "front", "label": "정면"}]))
    extra["expected_coverage_version"] = s["visuals"]["coverage_version"]
    s = chars.attach_visual_component(pid, "front", req("attach", **extra, asset_id=picked["asset_id"]))
    s = chars.build_visual_sheet(pid, req("build", **extra))
    return chars.visual_sheet_decision(pid, req("sheet-confirm", expected_sheet_version=s["visuals"]["current_sheet_version"]), "confirm")


class RealStub(FixtureEpisodeProvider):
    fixture = False
    name = "chatgpt_subscription"

    def __init__(self):
        self.calls = []

    def intake(self, ctx):
        self.calls.append(("intake", ctx))
        return super().intake(ctx)

    def story(self, ctx):
        self.calls.append(("story", ctx))
        return super().story(ctx)

    def storyboard(self, ctx):
        self.calls.append(("board", ctx))
        return super().storyboard(ctx)

    def evaluate(self, ctx):
        self.calls.append(("evaluate", ctx))
        return super().evaluate(ctx)


@pytest.fixture
def engine(tmp_path):
    chars = CharacterService(tmp_path)
    approved_character(chars)
    provider = RealStub()
    service = EpisodeService(tmp_path, chars, provider)
    yield service, chars, provider
    service.close()
    chars.close()


def create(service, rid="create"):
    return service.create_episode("project-episode", {"request_id": rid, "expected_direction_version": "1.0.1", "expected_sheet_version": "1.0.1"})


def turn(service, s, rid, stage, **extra):
    previous = s["story"] if stage == "story" else s["storyboard"] if stage == "storyboard" else None
    return service.submit_turn(s["project_id"], s["id"], {"request_id": rid, "expected_revision": s["revision"], "stage": stage,
        "message": "가상 씨앗을 돌보고 작은 변화를 반갑게 발견하는 이야기", "expected_version": previous["version"] if previous else None, **extra})


def decision(service, s, action, rid=None):
    kind = "story" if action.endswith("story") else "format" if action.endswith("format") else "storyboard"
    return service.decision(s["project_id"], s["id"], {"request_id": rid or action, "expected_revision": s["revision"], "action": action, "expected_version": s[kind]["version"]})


def board_ready(service):
    s = turn(service, create(service), "intake", "intent")
    s = turn(service, s, "story", "story")
    s = decision(service, s, "confirm_story")
    s = decision(service, s, "confirm_format")
    return turn(service, s, "board", "storyboard")


def rough(service, s, panel, rid, fixture=False):
    s = service.create_rough_job(s["project_id"], s["id"], {"request_id": rid, "expected_revision": s["revision"], "expected_board_version": s["storyboard"]["version"], "panel_id": panel})
    return service.upload_rough(s["project_id"], s["id"], s["rough_jobs"][-1]["id"], {"request_id": rid + "-upload", "expected_revision": s["revision"], "expected_board_version": s["storyboard"]["version"], "provenance": {"source": "codex_imagegen", "fixture": fixture}}, png())


def test_complete_human_gates_snapshot_actual_images_and_export(engine):
    service, chars, provider = engine
    s = board_ready(service)
    assert [name for name, _ in provider.calls] == ["intake", "story", "evaluate", "board", "evaluate"]
    assert all(ctx["_image_inputs"][0].startswith("data:image/png;base64,") for _, ctx in provider.calls)
    assert s["calls_used"] == s["project_calls_used"] == 5
    assert not s["generation_ready"] and not s["usable_storyboard"]
    with pytest.raises(EpisodeConflict):
        decision(service, s, "confirm_board")
    for n, panel in enumerate(s["storyboard"]["panels"]):
        s = rough(service, s, panel["id"], f"rough-{n}")
    s = decision(service, s, "confirm_board")
    assert s["usable_storyboard"] and not s["generation_ready"]
    archive = zipfile.ZipFile(io.BytesIO(service.export_episode(s["project_id"], s["id"])))
    assert len([name for name in archive.namelist() if name.startswith("roughs/")]) == 3
    assert any(name.startswith("character/") for name in archive.namelist())
    assert len([name for name in archive.namelist() if name.startswith("rough-sources/")]) == 3
    assert json.loads(archive.read("manifest.json"))["board_version"] == s["storyboard"]["version"]


def test_exact_scope_preservation_and_single_visual_invalidation(engine):
    service, _, _ = engine
    s = board_ready(service)
    for n, panel in enumerate(s["storyboard"]["panels"]):
        s = rough(service, s, panel["id"], f"rough-{n}")
    old, old_roughs = copy.deepcopy(s["storyboard"]), dict(s["roughs"])
    s = turn(service, s, "dialogue-edit", "storyboard", target_ids=["panel-2"], edit_fields=["dialogue"])
    assert s["roughs"] == old_roughs
    assert s["storyboard"]["panels"][0] == old["panels"][0]
    assert s["storyboard"]["panels"][2] == old["panels"][2]
    s = turn(service, s, "action-edit", "storyboard", target_ids=["panel-2"], edit_fields=["action"])
    assert s["roughs"] == {k: v for k, v in old_roughs.items() if k != "panel-2"}
    assert len([v for v in s["versions"] if v["kind"] == "storyboard"]) == 3


def test_story_revision_reopens_g1_and_invalidates_downstream(engine):
    service, _, _ = engine
    s = board_ready(service)
    previous = copy.deepcopy(s["story"])
    s = turn(service, s, "story-edit", "story", target_ids=["beat-3"], edit_fields=["dialogue"])
    assert s["story"]["beats"][:2] == previous["beats"][:2]
    assert s["confirmed_story_version"] is None and s["format"] is None and s["storyboard"] is None


def test_duplicate_request_no_model_call_and_cross_project_rejected(engine):
    service, _, provider = engine
    s = create(service)
    req = {"request_id": "same", "expected_revision": 0, "stage": "intent", "message": "씨앗"}
    once = service.submit_turn(s["project_id"], s["id"], req)
    twice = service.submit_turn(s["project_id"], s["id"], req)
    assert once == twice and len(provider.calls) == 1
    with pytest.raises(EpisodeConflict):
        service.submit_turn(s["project_id"], s["id"], {**req, "message": "다름"})
    with pytest.raises(KeyError):
        service.get_state("project-other", s["id"])


def test_shared_project_budget_cannot_reset_with_new_episode(engine):
    service, chars, provider = engine
    with chars._db_lock, chars.db:
        chars.db.execute("INSERT INTO character_provider_budget VALUES(?,?)", ("chatgpt_subscription:project-episode", 38))
    s = turn(service, create(service), "intake", "intent")
    assert s["project_calls_used"] == 39
    s = turn(service, s, "no-budget", "story")
    assert s["status"] == "blocked" and s["story"] is None and len(provider.calls) == 1
    new = create(service, "create-two")
    new = turn(service, new, "last-intake", "intent")
    assert new["project_calls_used"] == 40
    new = turn(service, new, "over-budget", "story")
    assert new["project_calls_used"] == 40 and len(provider.calls) == 2


def test_sheet_reopen_preserves_reads_blocks_all_mutations(engine):
    service, chars, provider = engine
    s = board_ready(service)
    c = chars.get_state(s["project_id"])
    chars.visual_sheet_decision(s["project_id"], {"request_id": "reopen-sheet", "expected_revision": c["revision"], "expected_direction_version": c["brief"]["version"], "expected_sheet_version": c["visuals"]["current_sheet_version"]}, "reopen")
    reread = service.get_state(s["project_id"], s["id"])
    assert reread["storyboard"] == s["storyboard"] and reread["mutation_blocked"]
    with pytest.raises(EpisodeConflict):
        turn(service, s, "blocked-edit", "storyboard")
    assert len(provider.calls) == 5


def test_evaluator_failure_preserves_draft_no_auto_retry(engine):
    service, _, provider = engine
    s = turn(service, create(service), "intake", "intent")
    def fail(ctx):
        provider.calls.append(("failed-evaluation", ctx))
        raise RuntimeError("never expose user data")
    provider.evaluate = fail
    s = turn(service, s, "story-fail", "story")
    assert s["status"] == "blocked" and s["story"] is None
    assert s["calls_used"] == 3 and len(provider.calls) == 3
    assert "never expose" not in json.dumps(s)


def test_scoped_worker_drift_preserves_previous_result(engine):
    service, _, provider = engine
    s = board_ready(service)
    old = copy.deepcopy(s["storyboard"])
    original = provider.storyboard
    def drift(ctx):
        value = original(ctx)
        value["panels"][0]["action"] = "unrequested drift"
        return value
    provider.storyboard = drift
    s = turn(service, s, "drift", "storyboard", target_ids=["panel-2"], edit_fields=["dialogue"])
    assert s["storyboard"] == old and s["status"] == "blocked"
    assert s["calls_used"] == 6


def test_restart_does_not_reexecute_pending_remote_attempt(tmp_path):
    chars = CharacterService(tmp_path)
    approved_character(chars)
    provider = RealStub()
    service = EpisodeService(tmp_path, chars, provider)
    s = create(service)
    request = {"request_id": "interrupted", "expected_revision": 0, "stage": "intent", "message": "seed", "expected_version": None, "target_ids": [], "edit_fields": []}
    from backend.episode_service import digest, dump
    with service.db:
        service.db.execute("INSERT INTO episode_operations VALUES(?,?,?,?,?,?,?)", (s["project_id"], s["id"], "interrupted", "turn", digest(request), "pending", dump({"base": s, "request": request, "identity": None, "version": "1.0.1", "cache": {}, "inflight": "draft", "events": []})))
    service.close()
    service = EpisodeService(tmp_path, chars, provider)
    try:
        assert service.get_state(s["project_id"], s["id"])["status"] == "blocked"
        assert not provider.calls
        with pytest.raises(EpisodeConflict):
            service.submit_turn(s["project_id"], s["id"], request)
    finally:
        service.close()
        chars.close()


def test_rough_fixture_cannot_pass_g2_or_launder_through_revision(engine):
    service, _, _ = engine
    s = board_ready(service)
    for n, panel in enumerate(s["storyboard"]["panels"]):
        s = rough(service, s, panel["id"], f"rough-{n}", fixture=n == 0)
    with pytest.raises(EpisodeConflict):
        decision(service, s, "confirm_board")
    s = rough(service, s, "panel-1", "rough-revise")
    assert s["rough_assets"][-1]["provenance"]["fixture"]
    with pytest.raises(EpisodeConflict):
        decision(service, s, "confirm_board")


def test_duplicate_confirmation_cannot_rewind_complete_pipeline(engine):
    service, _, _ = engine
    s = board_ready(service)
    with pytest.raises(EpisodeConflict):
        decision(service, s, "confirm_story", "duplicate-story-confirm")
    with pytest.raises(EpisodeConflict):
        decision(service, s, "confirm_format", "duplicate-format-confirm")
    s = decision(service, s, "reopen_story")
    assert s["confirmed_format_version"] is None and not s["usable_storyboard"]


@pytest.mark.parametrize("target", ["story", "story_history", "snapshot_sheet", "operation_response"])
def test_nested_stored_scope_tampering_fails_closed(engine, target):
    service, _, _ = engine
    s = board_ready(service)
    from backend.episode_service import dump
    if target == "operation_response":
        row = service.db.execute("SELECT payload FROM episode_operations WHERE request_id='board'").fetchone()
        op = json.loads(row[0])
        op["response"]["project_id"] = "project-other"
        with service.db:
            service.db.execute("UPDATE episode_operations SET payload=? WHERE request_id='board'", (dump(op),))
        request = {"request_id": "board", "expected_revision": s["revision"] - 1, "stage": "storyboard", "message": "가상 씨앗을 돌보고 작은 변화를 반갑게 발견하는 이야기", "expected_version": None}
        with pytest.raises(EpisodeConflict):
            service.submit_turn(s["project_id"], s["id"], request)
        return
    bad = copy.deepcopy(s)
    if target == "story":
        bad["story"]["project_id"] = "project-other"
    elif target == "story_history":
        bad["versions"][0]["artifact"]["episode_id"] = "episode-other"
    else:
        bad["character_snapshot"]["sheet"]["project_id"] = "project-other"
    with service.db:
        service.db.execute("UPDATE episodes SET payload=? WHERE id=?", (dump(bad), s["id"]))
    with pytest.raises(EpisodeConflict):
        service.get_state(s["project_id"], s["id"])


def test_sheet_changed_during_role_blocks_evaluation_and_result_commit(engine):
    service, chars, provider = engine
    s = turn(service, create(service), "intake", "intent")
    original = provider.story
    def change_sheet(ctx):
        result = original(ctx)
        c = chars.get_state(s["project_id"])
        chars.visual_sheet_decision(s["project_id"], {"request_id": "concurrent-reopen", "expected_revision": c["revision"], "expected_direction_version": c["brief"]["version"], "expected_sheet_version": c["visuals"]["current_sheet_version"]}, "reopen")
        return result
    provider.story = change_sheet
    s = turn(service, s, "story-inflight", "story")
    assert s["story"] is None and s["mutation_blocked"] and s["calls_used"] == 2
    assert len(provider.calls) == 2


def test_model_identity_changed_during_role_stops_without_evaluator(engine):
    service, _, provider = engine
    provider.identity = "epoch-1"
    provider.execution_identity = lambda: provider.identity
    s = turn(service, create(service), "intake", "intent")
    original = provider.story
    def changed(ctx):
        result = original(ctx)
        provider.identity = "epoch-2"
        return result
    provider.story = changed
    s = turn(service, s, "identity-change", "story")
    assert s["status"] == "blocked" and s["story"] is None and s["calls_used"] == 2
    assert len(provider.calls) == 2


def test_rough_job_pins_nearest_preceding_continuity_and_own_edit_target(engine):
    service, _, _ = engine
    s = board_ready(service)
    s = rough(service, s, "panel-1", "first")
    first_aid = s["roughs"]["panel-1"]
    s = rough(service, s, "panel-2", "second")
    second_aid = s["roughs"]["panel-2"]
    second_job = s["rough_jobs"][-1]
    assert second_job["source_asset_ids"][-1] == first_aid
    roles = json.loads(second_job["prompt"].split("\n", 1)[1])["source_roles"]
    assert roles[first_aid] == "continuity_reference"
    s = rough(service, s, "panel-2", "second-revision")
    revised_job = s["rough_jobs"][-1]
    roles = json.loads(revised_job["prompt"].split("\n", 1)[1])["source_roles"]
    assert roles[first_aid] == "continuity_reference"
    assert roles[second_aid] == "edit_target"
    assert len(revised_job["source_asset_ids"]) == len(set(revised_job["source_asset_ids"]))
    s = rough(service, s, "panel-3", "third")
    third_job = s["rough_jobs"][-1]
    roles = json.loads(third_job["prompt"].split("\n", 1)[1])["source_roles"]
    assert roles[s["roughs"]["panel-2"]] == "continuity_reference"
    assert first_aid not in third_job["source_asset_ids"]


def test_export_retains_superseded_continuity_reference_in_source_closure(engine):
    service, _, _ = engine
    s = board_ready(service)
    s = rough(service, s, "panel-1", "first")
    old_first_aid = s["roughs"]["panel-1"]
    s = rough(service, s, "panel-2", "second")
    s = rough(service, s, "panel-3", "third")
    s = turn(service, s, "first-action-edit", "storyboard", target_ids=["panel-1"], edit_fields=["action"])
    assert "panel-1" not in s["roughs"]
    s = rough(service, s, "panel-1", "first-replacement")
    assert old_first_aid not in s["roughs"].values()
    s = decision(service, s, "confirm_board")
    archive = zipfile.ZipFile(io.BytesIO(service.export_episode(s["project_id"], s["id"])))
    assert f"rough-sources/{old_first_aid}.png" in archive.namelist()
    manifest = json.loads(archive.read("manifest.json"))
    assert f"rough-sources/{old_first_aid}.png" in manifest["files"]
