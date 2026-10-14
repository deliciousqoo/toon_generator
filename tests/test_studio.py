"""Durability, exact-version human gates and bounded role-worker behavior."""
import copy
import json
import threading
import time

import httpx
import pytest
from pydantic import ValidationError

from backend.studio import StudioConflict, StudioService
from backend.studio_contracts import ActionInput, ProjectBrief, RunInput, StoryArtifact
from backend.studio_workers import DeterministicFixtureProvider, configured_provider, evaluate_board, evaluate_story


@pytest.fixture
def service(tmp_path):
    engine = StudioService(tmp_path, background=False)
    yield engine
    engine.close()


def project(service):
    return service.create_project(ProjectBrief(name="합성 기술 검증", audience="합성 독자", series_direction="합성 시리즈", synthetic_confirmed=True))


def start(service, pid=None, **extra):
    pid = pid or project(service)["id"]
    return service.create_run(pid, RunInput(idea="합성 상황 입력", **extra))


def act(service, run, action, **extra):
    return service.action(run["project_id"], run["id"], ActionInput(action=action, expected_revision=run["revision"], **extra))


def board(service, run=None):
    run = run or start(service)
    return act(service, act(service, run, "approve_story"), "approve_format")


def test_durable_restart_preserves_exact_interrupt_and_handoff(tmp_path):
    first = StudioService(tmp_path, background=False)
    run = start(first)
    assert run["pending_action"] == "approve_story"
    assert run["format_proposal"] is None
    first_story = copy.deepcopy(run["story"])
    first.close()
    restarted = StudioService(tmp_path, background=False)
    try:
        restored = restarted.get_run(run["project_id"], run["id"])
        assert restored["story"] == first_story
        following = act(restarted, restored, "approve_story")
        assert following["pending_action"] == "approve_format"
        assert following["approvals"][0]["version"] == first_story["version"]
        result = act(restarted, following, "approve_format")
        storyboard = result["storyboard"]
        assert storyboard["story_version"] == first_story["version"]
        assert storyboard["format_version"] == result["format_proposal"]["version"]
        for beat, panel in zip(first_story["beats"], storyboard["panels"]):
            assert panel["beat_id"] == beat["id"]
            assert panel["action"] == beat["action"]
            assert panel["dialogue"] == beat["dialogue"]
            assert panel["visual_purpose"] == beat["visual_purpose"]
            assert panel["gaze_target"] and panel["pacing"]
        complete = act(restarted, result, "approve_storyboard")
        assert complete["status"] == "completed"
        assert complete["technical_review_complete"]
        assert not complete["generation_ready"] and not complete["creative_quality_verified"]
        assert complete["approvals"][-1]["gate"] == "TECHNICAL_BOARD"
        assert not any(a["gate"] == "G2" for a in complete["approvals"])
    finally:
        restarted.close()


def test_stale_approval_and_wrong_stage_are_rejected(service):
    run = start(service)
    with pytest.raises(StudioConflict):
        act(service, run, "approve_storyboard")
    following = act(service, run, "approve_story")
    with pytest.raises(StudioConflict):
        act(service, run, "approve_story")
    assert service.get_run(run["project_id"], run["id"])["revision"] == following["revision"]


def test_panel_dialogue_edit_preserves_story_other_panels_and_visual_fields(service):
    run = board(service)
    original = copy.deepcopy(run)
    selected = run["storyboard"]["panels"][1]["id"]
    revised = act(service, run, "revise_storyboard", feedback="대사: 합성 변경 대사", target_ids=[selected])
    assert revised["story"] == original["story"]
    assert revised["format_proposal"] == original["format_proposal"]
    assert revised["storyboard"]["version"] != original["storyboard"]["version"]
    before, after = original["storyboard"]["panels"], revised["storyboard"]["panels"]
    for a, b in zip(before, after):
        if a["id"] == selected:
            assert b["dialogue"] == "합성 변경 대사"
            assert {k: v for k, v in a.items() if k != "dialogue"} == {k: v for k, v in b.items() if k != "dialogue"}
        else:
            assert a == b
    assert len([e for e in revised["events"] if e["role"] == "story_generator"]) == 1
    assert any(v["artifact"] == original["storyboard"] for v in revised["versions"])


def test_story_dialogue_edit_keeps_action_payoff_and_invalidates_descendants(service):
    run = board(service)
    revised = act(service, run, "revise_story", feedback="대사: 새 합성 마지막 대사")
    assert revised["pending_action"] == "approve_story"
    assert revised["format_proposal"] is None and revised["storyboard"] is None
    assert revised["story"]["payoff"] == run["story"]["payoff"]
    assert revised["story"]["narrative_intent"] == run["story"]["narrative_intent"]
    assert [b["action"] for b in revised["story"]["beats"]] == [b["action"] for b in run["story"]["beats"]]
    assert revised["story"]["beats"][-1]["dialogue"] == "새 합성 마지막 대사"
    assert revised["story"]["beats"][:-1] == run["story"]["beats"][:-1]
    assert revised["approvals"] == run["approvals"]  # audit history is immutable
    assert not any(a["version"] == revised["story"]["version"] for a in revised["approvals"])


def test_project_boundary_and_invalid_panel_targets(service):
    one = board(service)
    other = start(service)
    with pytest.raises(KeyError):
        service.get_run(other["project_id"], one["id"])
    with pytest.raises(StudioConflict):
        act(service, one, "revise_storyboard", feedback="대사: 변경", target_ids=[f"{other['id']}-panel-1"])
    with pytest.raises(StudioConflict):
        act(service, one, "revise_storyboard", feedback="대사: 변경", target_ids=[one["storyboard"]["panels"][0]["id"]] * 2)
    source = copy.deepcopy(one["story"])
    source["source_versions"][0]["project_id"] = other["project_id"]
    with pytest.raises(ValidationError):
        StoryArtifact.model_validate(source)


def test_rejection_is_stopped_until_explicit_retry(service):
    run = board(service)
    stopped = act(service, run, "reject", feedback="합성 중단")
    assert stopped["status"] == "stopped" and stopped["retry_available"]
    assert stopped["storyboard"] == run["storyboard"]
    with pytest.raises(StudioConflict):
        act(service, stopped, "approve_storyboard")
    resumed = act(service, stopped, "retry")
    assert resumed["pending_action"] == "approve_storyboard"
    assert resumed["story"] == run["story"]
    assert len([e for e in resumed["events"] if e["role"] == "story_generator"]) == 1


class RevisingProvider(DeterministicFixtureProvider):
    def __init__(self, recommendation="revise"):
        self.story_calls = 0
        self.evaluator_calls = 0
        self.recommendation = recommendation

    def story(self, context):
        self.story_calls += 1
        return super().story(context)

    def evaluate_story(self, context):
        self.evaluator_calls += 1
        return {"recommendation": self.recommendation, "issues": [{"severity": "warning", "stage": "story", "code": "causality", "message": "합성 인과 검토", "target_id": context["story"]["beats"][-1]["id"]}],
                "feedback": "행동: 합성 인과 보완", "evidence": ["합성 마지막 비트에 직접 연결되는 행동이 필요함"], "source_versions": context["source_versions"]}


def test_creative_revision_loop_is_bounded_and_evidence_is_versioned(tmp_path):
    provider = RevisingProvider()
    service = StudioService(tmp_path, provider, background=False)
    try:
        run = start(service)
        assert provider.story_calls == 3 and provider.evaluator_calls == 3
        assert run["status"] == "blocked" and run["pending_action"] == "approve_story"
        assert any(i["code"] == "evaluation_needs_human" for i in run["issues"])
        assert len(run["evaluations"]) == 3
        for evaluation in run["evaluations"]:
            assert evaluation["rubric_version"] == "story-v1"
            assert evaluation["criteria"] and evaluation["evidence"]
            source = evaluation["source_versions"][-1]
            assert source["role"] == "story" and source["project_id"] == run["project_id"]
            assert any(v["kind"] == "story" and v["version"] == source["version"] for v in run["versions"])
        with pytest.raises(StudioConflict):
            act(service, run, "approve_story")
    finally:
        service.close()


def test_blocked_evaluator_never_automatically_rewrites(tmp_path):
    provider = RevisingProvider("blocked")
    service = StudioService(tmp_path, provider, background=False)
    try:
        run = start(service)
        assert provider.story_calls == 1
        assert run["status"] == "blocked"
    finally:
        service.close()


def test_evaluation_replay_uses_immutable_archive_without_new_provider_call(service):
    run = start(service)
    snapshot = service.graph.get_state(service._config(service._raw(run["id"])))
    state = dict(snapshot.values)
    saved = run["evaluations"][0]
    service.provider.evaluate_story = lambda context: (_ for _ in ()).throw(AssertionError("must not call again"))
    evaluated, issues = service._evaluation(state, "story_evaluation", "story_evaluator", {}, [])
    assert evaluated == saved and issues == saved["issues"]


def test_queued_resume_command_recovers_after_restart(tmp_path):
    engine = StudioService(tmp_path, background=False)
    run = start(engine)
    engine._launch = lambda rid: None
    queued = act(engine, run, "approve_story")
    assert queued["status"] == "queued"
    engine.close()
    resumed = StudioService(tmp_path, background=False)
    try:
        result = resumed.get_run(run["project_id"], run["id"])
        assert result["pending_action"] == "approve_format"
        assert result["story"] == run["story"]
        assert len(result["approvals"]) == 1
    finally:
        resumed.close()


def test_review_projection_before_interrupt_checkpoint_does_not_drop_approval(service):
    run = start(service)
    config = service._config(service._raw(run["id"]))
    # Simulate exiting after visible awaiting_review, before review-node checkpoint commit.
    snapshot = service.graph.get_state(config)
    service.graph.update_state(config, dict(snapshot.values), as_node="story_evaluator")
    assert not any(task.interrupts for task in service.graph.get_state(config).tasks)
    after = act(service, run, "approve_story")
    assert after["pending_action"] == "approve_format"
    assert len(after["approvals"]) == 1
    assert after["approvals"][0]["version"] == run["story"]["version"]


def test_transient_role_error_retries_once_and_preserves_other_roles(tmp_path):
    class Transient(DeterministicFixtureProvider):
        calls = 0

        def evaluate_story(self, context):
            self.calls += 1
            if self.calls == 1:
                raise httpx.ConnectError("synthetic connection interruption")
            return super().evaluate_story(context)

    provider = Transient()
    service = StudioService(tmp_path, provider, background=False)
    try:
        run = start(service)
        assert provider.calls == 2
        assert run["pending_action"] == "approve_story"
        assert len([e for e in run["events"] if e["role"] == "story_generator"]) == 1
        assert any("1회 재시도" in e["message"] for e in run["events"])
    finally:
        service.close()


def test_finite_node_and_time_limits_stop_execution(tmp_path):
    engine = StudioService(tmp_path, background=False)
    try:
        engine.MAX_NODES = 1
        limited = start(engine)
        assert limited["status"] == "blocked" and limited["pending_action"] is None
        assert limited["retry_available"]
        engine.MAX_NODES = 24
        engine.MAX_SECONDS = -1
        timed = start(engine)
        assert timed["status"] == "blocked"
    finally:
        engine.close()


def test_validator_detects_missing_beat_changed_mode_and_script_loss(service):
    run = board(service)
    missing = copy.deepcopy(run["storyboard"])
    missing["panels"].pop()
    codes = {i["code"] for i in evaluate_board(missing, run["story"], run["format_proposal"])}
    assert {"beat_coverage", "panel_order_count"} <= codes
    unsupported = {**run["format_proposal"], "text_mode": "mixed"}
    assert any(i["code"] == "unsupported_text_mode" for i in evaluate_board(run["storyboard"], run["story"], unsupported))
    assert unsupported["text_mode"] == "mixed"
    lost = copy.deepcopy(run["story"])
    lost["premise"] = "original script"
    assert any(i["code"] == "script_preservation" for i in evaluate_story(lost, {"input_kind": "script", "idea": "original script"}))


def test_optional_local_provider_requires_concrete_p1_record(tmp_path, monkeypatch):
    monkeypatch.setenv("TOON_STUDIO_ENABLE_OLLAMA", "1")
    monkeypatch.setenv("TOON_STUDIO_OLLAMA_MODEL", "synthetic-local-model")
    monkeypatch.delenv("TOON_STUDIO_PROVIDER_APPROVAL_FILE", raising=False)
    with pytest.raises(ValueError, match="P1"):
        configured_provider()
    path = tmp_path / "approval.json"
    record = {"execution_authorized": True, "provider": "ollama_local_json", "model": "synthetic-local-model", "input_scope": "synthetic_stage04", "endpoint": "http://127.0.0.1:11434", "max_calls": 8, "timeout_seconds": 60}
    path.write_text(json.dumps(record), encoding="utf-8")
    monkeypatch.setenv("TOON_STUDIO_PROVIDER_APPROVAL_FILE", str(path))
    selected = configured_provider()
    assert selected.name == "ollama_local_json" and selected.budget_id
    for field, invalid in (("execution_authorized", False), ("model", "different"), ("max_calls", True), ("timeout_seconds", 121), ("endpoint", "https://remote.invalid"), ("input_scope", "real_content")):
        path.write_text(json.dumps({**record, field: invalid}), encoding="utf-8")
        with pytest.raises(ValueError, match="P1"):
            configured_provider()


def test_provider_call_budget_persists_across_restart(tmp_path):
    class BudgetedFixture(DeterministicFixtureProvider):
        budget_id = "synthetic-budget"
        approval = {"max_calls": 1}

    first = StudioService(tmp_path, BudgetedFixture(), background=False)
    run = start(first)
    assert run["status"] == "blocked"
    assert first.db.execute("SELECT calls FROM provider_budget").fetchone()[0] == 1
    first.close()
    second = StudioService(tmp_path, BudgetedFixture(), background=False)
    try:
        restarted = second.get_run(run["project_id"], run["id"])
        retry = act(second, restarted, "retry")
        assert retry["status"] == "blocked"
        assert second.db.execute("SELECT calls FROM provider_budget").fetchone()[0] == 1
        assert len([v for v in retry["versions"] if v["kind"] == "story"]) == 1
    finally:
        second.close()


def test_global_tracing_environment_cannot_enable_external_run_upload(tmp_path, monkeypatch):
    from langsmith.utils import tracing_is_enabled

    class TracingProbe(DeterministicFixtureProvider):
        def story(self, context):
            assert tracing_is_enabled() is False
            return super().story(context)

    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    service = StudioService(tmp_path, TracingProbe(), background=False)
    try:
        assert start(service)["status"] == "awaiting_review"
    finally:
        service.close()


def test_background_run_returns_progress_and_stop_does_not_wait_for_provider(tmp_path):
    entered = threading.Event()
    release = threading.Event()

    class BlockingProvider(DeterministicFixtureProvider):
        def story(self, context):
            entered.set()
            assert release.wait(5)
            return super().story(context)

    service = StudioService(tmp_path, BlockingProvider())
    try:
        run = start(service)
        assert entered.wait(5)
        running = service.get_run(run["project_id"], run["id"])
        assert running["status"] == "running" and running["events"]
        at = time.monotonic()
        stopped = act(service, running, "reject", feedback="합성 실행 취소")
        assert time.monotonic() - at < 1
        assert stopped["status"] == "stopped"
        release.set()
        service.wait(run["id"])
        final = service.get_run(run["project_id"], run["id"])
        assert final["status"] == "stopped"
        assert final["story"] is None
        assert not any(e["role"] == "evaluator" for e in final["events"])
    finally:
        release.set()
        service.close()


def test_completed_board_rework_after_restart_preserves_approved_sources_and_audit(tmp_path):
    first = StudioService(tmp_path, background=False)
    complete = act(first, board(first), "approve_storyboard")
    archived_board = copy.deepcopy(complete["storyboard"])
    old_thread = first._raw(complete["id"])["_thread_id"]
    first.close()
    restarted = StudioService(tmp_path, background=False)
    try:
        restored = restarted.get_run(complete["project_id"], complete["id"])
        target = restored["storyboard"]["panels"][1]["id"]
        revised = act(restarted, restored, "revise_storyboard", feedback="대사: 완료 후 합성 수정", target_ids=[target])
        assert revised["status"] == "awaiting_review" and revised["pending_action"] == "approve_storyboard"
        assert not revised["technical_review_complete"]
        assert not revised["generation_ready"] and not revised["creative_quality_verified"]
        assert revised["story"] == complete["story"] and revised["format_proposal"] == complete["format_proposal"]
        assert revised["approvals"] == complete["approvals"]
        assert revised["approvals"][-1]["gate"] == "TECHNICAL_BOARD"
        assert revised["storyboard"]["version"] != archived_board["version"]
        assert restarted._raw(complete["id"])["_thread_id"] != old_thread
        assert any(v["artifact"] == archived_board for v in revised["versions"])
        for before, after in zip(archived_board["panels"], revised["storyboard"]["panels"]):
            if before["id"] == target:
                assert after["dialogue"] == "완료 후 합성 수정"
                assert {k: v for k, v in before.items() if k != "dialogue"} == {k: v for k, v in after.items() if k != "dialogue"}
            else:
                assert before == after
        assert len([e for e in revised["events"] if e["role"] == "story_generator"]) == 1
    finally:
        restarted.close()


def test_completed_story_rework_creates_new_g1_and_invalidates_downstream(service):
    complete = act(service, board(service), "approve_storyboard")
    for invalid in ("approve_storyboard", "reject", "retry"):
        with pytest.raises(StudioConflict):
            act(service, complete, invalid)
    revised = act(service, complete, "revise_story", feedback="대사: 완료 후 이야기 수정")
    assert revised["status"] == "awaiting_review" and revised["pending_action"] == "approve_story"
    assert not revised["technical_review_complete"]
    assert revised["format_proposal"] is None and revised["storyboard"] is None
    assert revised["story"]["version"] != complete["story"]["version"]
    assert revised["story"]["beats"][-1]["dialogue"] == "완료 후 이야기 수정"
    assert revised["approvals"] == complete["approvals"]
    assert any(v["artifact"] == complete["storyboard"] for v in revised["versions"])
    chosen = act(service, revised, "approve_story")
    assert chosen["approvals"][-1]["gate"] == "G1"
    assert chosen["approvals"][-1]["version"] == revised["story"]["version"]


@pytest.mark.parametrize("field,value", [("schema_version", "99.0.0"), ("schema_id", "future-studio-contract"), ("id", "different-registry-id")])
def test_stored_project_unknown_schema_or_registry_mismatch_fails_closed(service, field, value):
    saved = project(service)
    corrupted = {**saved, field: value}
    service.db.execute("UPDATE projects SET payload=? WHERE id=?", (json.dumps(corrupted), saved["id"]))
    service.db.commit()
    for read in (lambda: service.get_project(saved["id"]), service.list_projects):
        with pytest.raises(ValueError, match="저장된 프로젝트 계약") as error:
            read()
        assert saved["series_direction"] not in str(error.value)
    with pytest.raises(ValueError):
        start(service, saved["id"])
    assert json.loads(service.db.execute("SELECT payload FROM projects WHERE id=?", (saved["id"],)).fetchone()[0]) == corrupted


@pytest.mark.parametrize("package", ["fixture_versions", "references", "character_package", "series_package"])
def test_stored_project_cross_project_fixture_is_rejected(service, package):
    saved = project(service)
    other = project(service)
    corrupted = copy.deepcopy(saved)
    if package in ("fixture_versions", "references"):
        corrupted[package][0]["project_id"] = other["id"]
    else:
        corrupted[package]["project_id"] = other["id"]
    service.db.execute("UPDATE projects SET payload=? WHERE id=?", (json.dumps(corrupted), saved["id"]))
    service.db.commit()
    with pytest.raises(ValueError, match="저장된 프로젝트 계약"):
        service.get_project(saved["id"])


def test_stored_run_schema_validation_does_not_dump_supplied_values(service):
    run = start(service)
    raw = service._raw(run["id"])
    raw["schema_version"] = "unsupported-private-input-marker"
    service._save(raw)
    with pytest.raises(ValueError, match="저장된 작업 계약") as error:
        service.get_run(run["project_id"], run["id"])
    assert "unsupported-private-input-marker" not in str(error.value)


def test_unsupported_queued_run_never_executes_provider(service):
    service._launch = lambda rid: None
    service.provider.story = lambda context: (_ for _ in ()).throw(AssertionError("unsupported records must not execute"))
    queued = start(service)
    raw = service._raw(queued["id"])
    raw["schema_version"] = "99.0.0"
    service._save(raw)
    service._drive(queued["id"])
    preserved = service._raw(queued["id"])
    assert preserved["schema_version"] == "99.0.0"
    assert preserved["status"] == "blocked"
    assert preserved["_error"].startswith("ValueError:")
    events = [json.loads(row[0]) for row in service.db.execute("SELECT payload FROM events WHERE run_id=?", (queued["id"],)).fetchall()]
    assert not any(event["role"] == "story_generator" for event in events)
