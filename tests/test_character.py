"""Character-first scope, durable role handoffs and exact human direction decisions."""
import copy
import json
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from backend.character_contracts import CharacterState
from backend.character_service import CharacterConflict, CharacterNotFound, CharacterService
from backend.character_workers import DeterministicCharacterProvider, configured_character_provider, validate_approval


@pytest.fixture
def service(tmp_path):
    engine = CharacterService(tmp_path)
    engine.ensure_project("project-synthetic")
    yield engine
    engine.close()


def turn(service, state=None, message="합성 외형 입력", request_id="turn-1", **extra):
    state = state or service.get_state("project-synthetic")
    return service.submit_turn(state["project_id"], {"request_id": request_id, "expected_revision": state["revision"],
                               "message": message, "synthetic_confirmed": True, **extra})


def complete_direction(service):
    state = turn(service)
    state = turn(service, state, "합성 성격 입력", "turn-2")
    return turn(service, state, "합성 분위기 입력", "turn-3")


def decision(service, state, kind="confirm", request_id="confirm-1", **extra):
    return getattr(service, f"{kind}_direction")(state["project_id"], {
        "request_id": request_id, "expected_revision": state["revision"],
        "expected_version": state["brief"]["version"], **extra})


def test_incremental_questions_and_actual_role_handoffs(service):
    initial = service.get_state("project-synthetic")
    assert initial["brief"] is None and initial["question_field"] == "appearance"
    first = turn(service)
    assert first["brief"]["appearance"] == "합성 외형 입력"
    assert first["question_field"] == "personality" and not first["can_confirm"]
    assert [event["role"] for event in first["events"]] == ["character_designer", "character_validator", "character_evaluator", "human_review"]
    second = turn(service, first, "합성 성격 입력", "turn-2")
    assert second["brief"]["appearance"] == first["brief"]["appearance"]
    assert second["question_field"] == "desired_feeling"
    final = turn(service, second, "합성 느낌 입력", "turn-3")
    assert final["can_confirm"] and not final["unknowns"]
    assert final["brief"]["source_turn_ids"] == ["turn-1", "turn-2", "turn-3"]
    assert len(final["evaluations"]) == 3
    assert final["fixture"] and final["provider"] == "deterministic_character_fixture"
    assert not final["visual_ready"] and not final["sheet_approved"]


def test_restart_human_interrupt_and_immutable_confirmation(tmp_path):
    original = CharacterService(tmp_path)
    original.ensure_project("project-synthetic")
    state = complete_direction(original)
    exact_brief = copy.deepcopy(state["brief"])
    original.close()
    restarted = CharacterService(tmp_path)
    try:
        restored = restarted.get_state("project-synthetic")
        assert restored == state
        confirmed = decision(restarted, restored)
        assert confirmed["direction_confirmed"] and confirmed["stage"] == "candidates"
        assert confirmed["brief"] == exact_brief
        assert confirmed["decisions"][0]["version"] == exact_brief["version"]
        assert not confirmed["sheet_approved"] and not confirmed["visual_ready"]
        with pytest.raises(CharacterConflict):
            turn(restarted, confirmed, request_id="blocked-edit")
        reopened = decision(restarted, confirmed, "reopen", "reopen-1")
        revised = turn(restarted, reopened, "합성 성격 수정", "turn-4", field_updates={"personality": "합성 성격 수정"})
        assert revised["brief"]["version"] == "1.0.4"
        assert revised["versions"][2] == exact_brief
        assert revised["brief"]["appearance"] == exact_brief["appearance"]
        assert revised["decisions"] == reopened["decisions"]
        assert not revised["direction_confirmed"] and revised["can_confirm"]
    finally:
        restarted.close()


def test_idempotency_replays_exact_result_without_extra_versions(service):
    initial = service.get_state("project-synthetic")
    first = turn(service, initial)
    second = turn(service, first, "합성 성격", "turn-2")
    assert turn(service, initial) == first
    assert service.get_state("project-synthetic") == second
    with pytest.raises(CharacterConflict):
        turn(service, initial, message="다른 내용")
    with pytest.raises(CharacterConflict):
        turn(service, initial, request_id="new-stale-request")


def test_confirmation_requires_current_revision_exact_version_and_complete_inputs(service):
    first = turn(service)
    with pytest.raises(CharacterConflict):
        decision(service, first)
    ready = complete_from_first(service, first)
    with pytest.raises(CharacterConflict):
        decision(service, ready, expected_version="1.0.1")
    with pytest.raises(CharacterConflict):
        decision(service, ready, expected_revision=1)
    confirmed = decision(service, ready)
    assert decision(service, ready) == confirmed
    with pytest.raises(CharacterConflict):
        decision(service, ready, kind="reopen")  # reused id with a different action


def complete_from_first(service, first):
    second = turn(service, first, "합성 성격", "turn-2")
    return turn(service, second, "합성 느낌", "turn-3")


def test_projects_do_not_share_messages_versions_or_decisions(service):
    service.ensure_project("project-other")
    source = complete_direction(service)
    other = service.get_state("project-other")
    assert other["messages"] == [] and other["versions"] == []
    with pytest.raises(CharacterConflict):
        service.confirm_direction("project-other", {"request_id": "copy-confirm", "expected_revision": 0,
                                                   "expected_version": source["brief"]["version"]})
    with pytest.raises(CharacterNotFound):
        service.get_state("project-missing")
    with pytest.raises(CharacterNotFound):
        service.ensure_project("../project-synthetic")
    malformed = copy.deepcopy(source)
    malformed["versions"][0]["project_id"] = "project-other"
    with pytest.raises(ValidationError):
        CharacterState.model_validate(malformed)


def test_explicit_changes_preserve_fields_and_reference_observations(service):
    first = turn(service, references=[{"label": "합성 참고 자료", "desired_traits": ["둥근 실루엣의 느낌"],
                                       "not_to_copy": ["이름·고유 의상·특정 얼굴 배치"]}])
    revised = turn(service, first, "성격만 입력", "turn-2", field_updates={"personality": "합성 성격"})
    assert revised["brief"]["appearance"] == first["brief"]["appearance"]
    assert revised["brief"]["reference_observations"] == first["brief"]["reference_observations"]
    assert any(issue["code"] == "reference_review" for issue in revised["issues"])
    removed = turn(service, revised, "참고 자료 제거", "turn-3", references=[], field_updates={"desired_feeling": "합성 느낌"})
    assert removed["brief"]["reference_observations"] == []
    assert removed["can_confirm"]


def test_independent_validation_and_evaluator_block_false_readiness(tmp_path):
    class BadDesigner(DeterministicCharacterProvider):
        def draft(self, context):
            result = super().draft(context)
            result["fields"]["voice"] = "요청하지 않은 변경"
            return result

    service = CharacterService(tmp_path, BadDesigner())
    try:
        service.ensure_project("project-synthetic")
        blocked = turn(service, field_updates={"appearance": "합성 외형", "personality": "합성 성격", "desired_feeling": "합성 느낌"})
        assert blocked["status"] == "blocked" and not blocked["can_confirm"]
        assert any(issue["code"] == "outside_edit_scope" for issue in blocked["issues"])
        with pytest.raises(CharacterConflict):
            decision(service, blocked)
    finally:
        service.close()


def test_wrong_evaluation_version_fails_closed_and_preserves_prior_direction(tmp_path):
    class WrongEvaluator(DeterministicCharacterProvider):
        def evaluate(self, context):
            return {**super().evaluate(context), "version": "1.0.999"}

    engine = CharacterService(tmp_path, WrongEvaluator())
    try:
        engine.ensure_project("project-synthetic")
        blocked = turn(engine)
        assert blocked["status"] == "blocked" and blocked["brief"] is None
        assert blocked["versions"] == [] and len(blocked["messages"]) == 2
        assert "999" not in json.dumps(blocked)
    finally:
        engine.close()


def test_fixture_recovery_caches_completed_designer_role(tmp_path):
    calls = {"draft": 0}

    class CrashEvaluator(DeterministicCharacterProvider):
        def draft(self, context):
            calls["draft"] += 1
            return super().draft(context)

        def evaluate(self, context):
            raise KeyboardInterrupt("simulated process exit")

    first = CharacterService(tmp_path, CrashEvaluator())
    first.ensure_project("project-synthetic")
    with pytest.raises(KeyboardInterrupt):
        turn(first)
    first.close()
    restarted = CharacterService(tmp_path)
    try:
        recovered = restarted.get_state("project-synthetic")
        assert recovered["revision"] == 1 and recovered["brief"]["version"] == "1.0.1"
        assert calls["draft"] == 1
        assert len(recovered["messages"]) == 2
        assert turn(restarted, {**recovered, "revision": 0}) == recovered
    finally:
        restarted.close()


def approval(**extra):
    return {"execution_authorized": True, "provider": "ollama_character_local_json", "model": "test-model",
            "input_scope": "synthetic_character_direction", "endpoint": "http://127.0.0.1:11434",
            "allowed_roles": ["character_designer", "character_evaluator"], "max_calls": 2, "timeout_seconds": 10,
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(), **extra}


def test_stage04_optin_is_not_character_execution_permission(monkeypatch, tmp_path):
    monkeypatch.setenv("TOON_STUDIO_ENABLE_OLLAMA", "1")
    monkeypatch.setenv("TOON_STUDIO_OLLAMA_MODEL", "stage04-only")
    assert configured_character_provider().fixture
    monkeypatch.setenv("TOON_CHARACTER_ENABLE_OLLAMA", "1")
    monkeypatch.setenv("TOON_CHARACTER_OLLAMA_MODEL", "test-model")
    with pytest.raises(ValueError):
        configured_character_provider()
    record = tmp_path / "approval.json"
    record.write_text(json.dumps(approval(input_scope="synthetic_stage04")), encoding="utf-8")
    monkeypatch.setenv("TOON_CHARACTER_PROVIDER_APPROVAL_FILE", str(record))
    with pytest.raises(ValueError):
        configured_character_provider()
    record.write_text(json.dumps(approval()), encoding="utf-8")
    provider = configured_character_provider()
    assert not provider.fixture and provider.approval["max_calls"] == 2


@pytest.mark.parametrize("override", [{"execution_authorized": False}, {"max_calls": True}, {"max_calls": 49},
                                    {"timeout_seconds": float("nan")}, {"endpoint": "https://example.com"},
                                    {"allowed_roles": ["story_generator"]}, {"expires_at": "2020-01-01T00:00:00Z"}])
def test_character_grant_fails_closed(override):
    with pytest.raises(ValueError):
        validate_approval(approval(**override), "test-model")


def test_persisted_provider_budget_bounds_roles_across_restart(tmp_path):
    class BudgetedFixture(DeterministicCharacterProvider):
        model = "test-model"
        budget_id = "same-explicit-character-grant"

        def __init__(self):
            self.approval = approval(max_calls=2)

    engine = CharacterService(tmp_path, BudgetedFixture())
    engine.ensure_project("project-synthetic")
    first = turn(engine)
    assert first["brief"] is not None
    engine.close()
    restarted = CharacterService(tmp_path, BudgetedFixture())
    try:
        blocked = turn(restarted, first, "합성 수정", "turn-2")
        assert blocked["status"] == "blocked" and blocked["brief"] == first["brief"]
        assert len(blocked["versions"]) == 1
        assert restarted.db.execute("SELECT calls FROM character_provider_budget").fetchone()[0] == 2
    finally:
        restarted.close()


def test_inputs_require_synthetic_scope_and_no_unknown_privileges(service):
    payload = {"request_id": "turn-1", "expected_revision": 0, "message": "합성 입력", "synthetic_confirmed": True}
    with pytest.raises(ValidationError):
        service.submit_turn("project-synthetic", {**payload, "synthetic_confirmed": False})
    with pytest.raises(ValidationError):
        service.submit_turn("project-synthetic", {**payload, "sheet_approved": True})
    with pytest.raises(ValidationError):
        service.submit_turn("project-synthetic", {**payload, "references": [{"label": "ref", "desired_traits": ["느낌"], "not_to_copy": []}]})


def test_review_free_text_is_preserved_without_guessing_identity(service):
    ready = complete_direction(service)
    original_fields = {key: ready["brief"][key] for key in ("appearance", "personality", "desired_feeling", "identity_invariants")}
    note = "검토 의견" * 400
    recorded = turn(service, ready, note, "turn-4")
    assert recorded["status"] == "awaiting_review"
    assert {key: recorded["brief"][key] for key in original_fields} == original_fields
    assert recorded["messages"][-2]["content"] == note
    assert "항목" in recorded["messages"][-1]["content"]
    changed = turn(service, recorded, "성격: 합성 성격 수정", "turn-5")
    assert changed["brief"]["personality"] == "합성 성격 수정"
    assert changed["brief"]["appearance"] == ready["brief"]["appearance"]


@pytest.mark.parametrize("tamper", ["schema", "project", "request", "provider", "approval"])
def test_invalid_pending_operation_is_quarantined_before_provider_execution(tmp_path, tamper):
    class InterruptedDesigner(DeterministicCharacterProvider):
        def draft(self, context):
            raise KeyboardInterrupt("simulated process exit")

    first = CharacterService(tmp_path, InterruptedDesigner())
    first.ensure_project("project-synthetic")
    with pytest.raises(KeyboardInterrupt):
        turn(first)
    raw = first.db.execute("SELECT payload FROM character_operations").fetchone()[0]
    stored = json.loads(raw)
    if tamper == "schema":
        stored["base_state"]["schema_id"] = "unsupported-future-version"
    elif tamper == "project":
        stored["base_state"]["project_id"] = "project-other"
    elif tamper == "request":
        stored["request"]["request_id"] = "different-turn"
    elif tamper == "provider":
        stored["provider"] = "different-provider"
    else:
        stored["approval_id"] = "different-grant"
    first.db.execute("UPDATE character_operations SET payload=?", (json.dumps(stored),))
    first.db.commit()
    first.close()

    class NoCalls(DeterministicCharacterProvider):
        def draft(self, context):
            raise AssertionError("unsupported records must never execute")

    restarted = CharacterService(tmp_path, NoCalls())
    try:
        state = restarted.get_state("project-synthetic")
        assert state["status"] == "blocked" and state["brief"] is None
        assert state["issues"][0]["code"] == "stored_operation_invalid"
        assert restarted.db.execute("SELECT status FROM character_operations").fetchone()[0] == "quarantined"
    finally:
        restarted.close()


def test_valid_but_stale_pending_turn_never_calls_provider_after_restart(tmp_path):
    first = CharacterService(tmp_path)
    first.ensure_project("project-synthetic")
    ready = complete_direction(first)

    class InterruptedDesigner(DeterministicCharacterProvider):
        def draft(self, context):
            raise KeyboardInterrupt("simulated process exit")

    first.provider = InterruptedDesigner()
    with pytest.raises(KeyboardInterrupt):
        turn(first, ready, "합성 수정 의견", "stale-pending-turn")
    # A separate accepted decision advances the projection while the old operation survives.
    confirmed = decision(first, ready)
    saved_operation = first.db.execute("SELECT payload FROM character_operations WHERE request_id='stale-pending-turn'").fetchone()[0]
    first.close()
    calls = []

    class NoCalls(DeterministicCharacterProvider):
        def draft(self, context):
            calls.append("draft")
            return super().draft(context)

        def evaluate(self, context):
            calls.append("evaluate")
            return super().evaluate(context)

    restarted = CharacterService(tmp_path, NoCalls())
    try:
        state = restarted.get_state("project-synthetic")
        assert calls == []
        assert state["status"] == "blocked"
        assert state["issues"][0]["code"] == "stored_operation_invalid"
        for key in ("brief", "versions", "messages", "decisions", "direction_confirmed"):
            assert state[key] == confirmed[key]
        operation = restarted.db.execute("SELECT status,payload FROM character_operations WHERE request_id='stale-pending-turn'").fetchone()
        assert operation == ("quarantined", saved_operation)
        assert restarted.db.execute("SELECT count(*) FROM character_versions").fetchone()[0] == len(confirmed["versions"])
        reopened = decision(restarted, state, "reopen", "recovery-reopen")
        assert not reopened["direction_confirmed"] and not reopened["can_confirm"]
        assert reopened["stage"] == "direction" and reopened["status"] == "blocked"
        assert reopened["issues"] == state["issues"]
        with pytest.raises(CharacterConflict):
            decision(restarted, reopened, request_id="premature-recovery-confirm")
        revised = turn(restarted, reopened, "합성 성격 수정", "recovery-turn",
                       field_updates={"personality": "합성 성격 수정"})
        assert revised["can_confirm"] and revised["status"] == "awaiting_review"
        assert revised["issues"] == [] and calls == ["draft", "evaluate"]
        assert revised["brief"]["version"] == "1.0.4"
        assert revised["versions"][:3] == confirmed["versions"]
        recovered = decision(restarted, revised, request_id="recovery-confirm")
        assert recovered["direction_confirmed"] and recovered["decisions"][-1]["version"] == "1.0.4"
        assert not recovered["visual_ready"] and not recovered["sheet_approved"]
    finally:
        restarted.close()
